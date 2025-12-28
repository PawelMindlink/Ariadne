import time
import os
import sys
# import psutil removed (not installed)
from datetime import datetime

# --- 1. IMPORT LATENCY ---
t_start = time.time()
print(f"[{datetime.now().time()}] 🚀 STARTING DIAGNOSTIC...")

try:
    import sqlite3
    import pandas as pd
    from google import genai
    import toml
except Exception as e:
    print(f"❌ Import Error: {e}")

t_imports = time.time()
print(f"⏱️  Imports Loaded: {t_imports - t_start:.4f}s")

# --- 2. SETUP & AUTH ---
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS_PATH = os.path.join(ROOT_DIR, '.streamlit', 'secrets.toml')
DB_PATH = os.path.join(ROOT_DIR, '02_Database', 'health_data.db')

if os.path.exists(SECRETS_PATH):
    secrets = toml.load(SECRETS_PATH)
    client = genai.Client(api_key=secrets["GEMINI_API_KEY"])
else:
    print("❌ Critical: No secrets file.")
    sys.exit(1)

# --- 3. DATABASE LATENCY ---
t_db_start = time.time()
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT count(*) FROM events")
count = cursor.fetchone()[0]
conn.close()
t_db_end = time.time()
print(f"⏱️  DB Connection & Simple Query: {t_db_end - t_db_start:.4f}s (Rows: {count})")

# --- 4. MODEL LATENCY WITH CACHE (Simulated Agent Logic) ---
import hashlib

def get_cached_response(prompt):
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    c = conn.cursor()
    c.execute("SELECT response FROM cache WHERE hash=?", (prompt_hash,))
    row = c.fetchone()
    return row[0] if row else None

def save_to_cache(prompt, response):
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO cache (hash, prompt, response, timestamp) VALUES (?, ?, ?, ?)", 
              (prompt_hash, prompt, response, datetime.now()))
    conn.commit()

# Ensure Table Exists for Test
conn = sqlite3.connect(DB_PATH)
conn.execute("CREATE TABLE IF NOT EXISTS cache (hash TEXT PRIMARY KEY, prompt TEXT, response TEXT, timestamp DATETIME)")

def test_agent_simulation(model_name, prompt, run_label):
    print(f"\n🧪 {run_label}: {model_name}")
    t_start = time.time()
    
    # 1. Check Cache
    cached = get_cached_response(prompt)
    if cached:
        print("   ✅ CACHE HIT!")
        latency = time.time() - t_start
        print(f"   ⏱️  Total Latency: {latency:.4f}s")
        return latency

    # 2. Call API
    print("   ⚠️  CACHE MISS - Calling API...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        # 3. Save
        save_to_cache(prompt, response.text)
        
        latency = time.time() - t_start
        print(f"   ✅ Response Received & Cached")
        print(f"   ⏱️  Total Latency: {latency:.4f}s")
        return latency
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 999.0

# Scenario Prompt (Real payload)
# We recreate the exact prompt sent in the scenario test
SYSTEM_INSTRUCTION = """
ROLE: Expert Medical & Systems Consultant (Ariadne).
METHODOLOGY: Systems Theory & First Principles.
RULES:
1. HOLISTIC: Never analyze metrics in isolation. Connect Systems.
2. CAUSAL LOOPS: Look for downstream effects.
3. DATA RELIABILITY: Trust 'Report_*' > 'Garmin' > 'Manual'.
4. TONE: Professional, Empathetic, Analytical, High-Agency.
"""
SAMPLE_DATA = "Date, Deep Sleep, Heart Rate\n2025-06-01, 220min, 105bpm\n... (30 lines of data) ..."
PROMPT = f"{SYSTEM_INSTRUCTION}\n\nCONTEXT: User asked: 'Connection?'.\nDATA FOUND:\n{SAMPLE_DATA}\n\nTASK: Provide a holistic answer."

# Unique Prompt to ensure fresh start each script run
UNIQUE_PROMPT = f"{PROMPT}\nTIMESTAMP: {time.time()}"

# Test 1: Gemini 2.0 Flash (Fast Baseline - No Thinking)
# We append model name to prompt to ensure UNIQUE HASH for each run, forcing a Cache Miss.
prompt_fast = f"{UNIQUE_PROMPT}\nMODEL_TRACE: gemini-2.0-flash"
latency_fast = test_agent_simulation('gemini-2.0-flash', prompt_fast, "RUN 1 (Fast/No-Think)")

# Test 2: Gemini 3 Flash Preview (Thinking)
prompt_think = f"{UNIQUE_PROMPT}\nMODEL_TRACE: gemini-3-flash-preview"
latency_think = test_agent_simulation('gemini-3-flash-preview', prompt_think, "RUN 2 (Thinking)")

# --- 5. SYSTEM RESOURCE SNAPSHOT ---
# process = psutil.Process(os.getpid())
# print(f"\n📊 Memory Usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
# --- 5. LOGGING TO FILE ---
with open("latency_benchmark.txt", "w", encoding="utf-8") as f:
    f.write(f"Fast Model (gemini-2.0-flash): {latency_fast:.4f}s\n")
    f.write(f"Thinking Model (gemini-3-flash-preview): {latency_think:.4f}s\n")
    f.write(f"Cost of Thinking: {latency_think - latency_fast:.4f}s slower\n")
    
print("\n✅ Report saved to latency_benchmark.txt")
