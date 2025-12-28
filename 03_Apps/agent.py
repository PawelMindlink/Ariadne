import streamlit as st
import sqlite3
import pandas as pd
import os
from google import genai
import hashlib
from datetime import datetime

# ... (Previous imports)

# --- CACHE LOGIC ---
def setup_cache():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cache 
                 (hash TEXT PRIMARY KEY, prompt TEXT, response TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

def get_cached_response(prompt):
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT response FROM cache WHERE hash=?", (prompt_hash,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def save_to_cache(prompt, response):
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO cache (hash, prompt, response, timestamp) VALUES (?, ?, ?, ?)", 
              (prompt_hash, prompt, response, datetime.now()))
    conn.commit()
    conn.close()

# Initialize Cache Table on startup
try:
    setup_cache()
except Exception as e:
    st.error(f"Cache Setup Failed: {e}")

# --- AI CONFIGURATION ---
SYSTEM_PROMPT = """
You are Ariadne, an advanced Medical Diagnostician and Health Intelligence Agent.
Your Goal: Identify root causes, find hidden correlations in data, and act as a proactive health detective.

CORE BEHAVIORS:
1.  **Analyze, Don't Just Display**: Never just say "Here is a graph". Explain *why* the data looks like that.
2.  **Correlate**: Always look for connections. Example: "Your deep sleep is low. Coincidentally, your heart rate was high during that workout 4 hours before bed."
3.  **Hypothesize (System 2 Thinking)**: If B12 is high, ask: "Do you take supplements? Do you eat fortified foods?" Generate hypotheses.
4.  **Ask Clarifying Questions**: If data is ambiguous, ask the user for context. "This file 'Recepty' has a date of 2023, is it relevant to your current condition?"
5.  **Be Clinical but Accessible**: Use medical terminology correctly but explain it simply.

DATA SOURCES:
- You have access to a SQL database (`ariadne.db`) with:
    - `events` (Workouts, Lab Tests, Sleep)
    - `observations` (Granular metrics like 'Hemoglobin', 'Heart Rate', 'Steps')
- Use `files` table to trace where data came from.

WHEN ANSWERING:
- Start with the direct answer/diagnosis.
- Provide evidence (data points).
- Suggest next steps (e.g., "Check correlations with diet").
"""

def get_gemini_response(prompt, history=[]):
    # 1. Check Cache
    cached = get_cached_response(prompt)
    if cached:
        return cached

    # 2. Call API
    try:
        # Construct full prompt with Persona
        full_prompt = f"{SYSTEM_PROMPT}\n\nUSER QUESTION: {prompt}"
        
        client = genai.Client(api_key=load_secrets().get("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp', # upgraded model
            contents=full_prompt
        )
        # 3. Save to Cache
        save_to_cache(prompt, response.text)
        return response.text
    except Exception as e:
        return f"Error: {e}"

# --- UI ---
st.title("🧶 Ariadne Health Agent")
st.caption("Navigating the labyrinth of your health data")

# --- SIDEBAR: INGESTION ---
with st.sidebar:
    st.header("📥 Data Inbox")
    
    # Check pending files
    # Check pending files
    inbox_path = os.path.join(os.path.dirname(__file__), '..', '00_Inbox')
    pending_files = 0
    for root, dirs, files in os.walk(inbox_path):
        if 'Errors' in root: continue
        for f in files:
            if f.lower().endswith(('.pdf', '.tcx', '.json', '.csv', '.xml')):
                pending_files += 1
    
    if pending_files > 0:
        st.warning(f"📝 {pending_files} files waiting to be processed.")
    else:
        st.success("✅ Inbox is empty.")

    st.info("Place your files (PDF, XML, JSON, CSV) in the `00_Inbox` folder.")
    
    if st.button("Process New Files", type="primary"):
        with st.spinner("Processing files... (This may take a while)"):
            stats, logs = ingest.run_ingestion()
        
        if stats['processed_files'] > 0:
            st.success(f"✅ Processed {stats['processed_files']} files!")
        elif stats['errors'] > 0:
            st.error(f"❌ Encountered {stats['errors']} errors.")
        else:
            st.info("No new files found.")
            
        # Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Processed", stats['processed_files'])
        c2.metric("Archived", stats['unprocessed_files'])
        c3.metric("Errors", stats['errors'])
        
        with st.expander("View Logs"):
            for log in logs:
                st.text(log)
    
    st.divider()
    st.divider()
    # Maintenance section removed per user request.

    st.divider()
    st.markdown("### 🤖 Capabilities")
    st.markdown("- **Systemic Analysis**: Connects Labs with Lifestyle.")
    st.markdown("- **Evidence-Based**: Cites dates and sources.")
    st.markdown("- **Secure**: Data stays on your device.")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am ready to analyze your medical reports and activity history. Ask me: 'How has my cholesterol changed?'"}
    ]

# Display Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Ask about your health data..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- AGENT LOGIC ---
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # 1. Decide: SQL or Chat?
            sql_prompt = f"{SCHEMA_CONTEXT}\n\nUSER QUESTION: {prompt}\n\nRules:\n1. If the user asks for data count, stats, or specific records, generate a SQL query.\n2. Return the SQL inside a markdown block ```sql ... ```.\n3. If no data needed, just answer.\n4. Do NOT verify, just generate SQL."
            
            response_text = get_gemini_response(sql_prompt)
            
            # Robust SQL Extraction including Regex
            import re
            sql_match = re.search(r"```sql\n(.*?)\n```", response_text, re.DOTALL)
            
            sql_query = None
            if sql_match:
                sql_query = sql_match.group(1)
            elif response_text.strip().upper().startswith("SELECT"):
                 sql_query = response_text.strip()
            
            final_response = ""
            
            if sql_query:
                st.markdown("**Generated Query:**")
                st.code(sql_query, language="sql")
                
                # Execute
                try:
                    conn = get_db_connection() # Ensure we use the connection factory
                    df = pd.read_sql_query(sql_query, conn)
                    conn.close()
                    
                    if not df.empty:
                        st.dataframe(df)
                        # 2. Interpret
                        # 2. Interpret
                        SYSTEM_INSTRUCTION = """
                        ROLE: Expert Medical & Systems Consultant (Ariadne).
                        METHODOLOGY: Systems Theory & First Principles.
                        RULES:
                        1. HOLISTIC: Never analyze metrics in isolation. Connect Systems (e.g. Cardiorespiratory <-> Metabolic <-> Hormonal).
                        2. CAUSAL LOOPS: Look for downstream effects (e.g. Poor Sleep -> High RHR -> Low Readiness).
                        3. DATA RELIABILITY: Trust 'Report_*' (Medical, Score 10) > 'Garmin' (Sensor, Score 8) > 'Manual' (Score 5).
                        4. TONE: Professional, Empathetic, Analytical, High-Agency.
                        """
                        
                        summary_prompt = f"{SYSTEM_INSTRUCTION}\n\nCONTEXT: User asked: '{prompt}'.\nDATA FOUND:\n{df.to_string()}\n\nTASK: Provide a holistic answer based on this data. Highlight First Principle causal links."
                        final_response = get_gemini_response(summary_prompt)
                    else:
                        final_response = "I ran the query but found no matching data in the database."
                except Exception as e:
                    final_response = f"SQL Execution Error: {e}"
            else:
                # Just chat
                final_response = response_text
            
            st.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})
