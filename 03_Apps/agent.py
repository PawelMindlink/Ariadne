import streamlit as st
import sqlite3
import pandas as pd
import os
from google import genai
import hashlib
from datetime import datetime
import toml

# ... (Previous imports)

# --- CONFIGURATION ---
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '02_Database', 'ariadne.db')

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def load_secrets():
    secrets_path = os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml')
    if os.path.exists(secrets_path):
        try:
            return toml.load(secrets_path) 
        except:
             return {}
    return {}

# --- DYNAMIC SCHEMA CONTEXT ---
def get_schema_context():
    """Dynamically generates schema context for the LLM."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_text = "DATABASE SCHEMA:\n"
        for table in tables:
            if table == "sqlite_sequence": continue
            cursor.execute(f"PRAGMA table_info({table});")
            columns = [f"{row[1]} ({row[2]})" for row in cursor.fetchall()]
            schema_text += f"- Table `{table}`: {', '.join(columns)}\n"
            
        conn.close()
        return schema_text
    except Exception as e:
        return f"Error loading schema: {e}"

# Initialize Schema Context (Critical for SQL Generation)
SCHEMA_CONTEXT = get_schema_context()

# --- PERFORMANCE OPTIMIZATION ---
@st.cache_data(ttl=60) # Cache for 60 seconds
def get_pending_file_count(inbox_path):
    pending = 0
    # Limit depth or just strict walk
    for root, dirs, files in os.walk(inbox_path):
        if 'Errors' in root or 'Quarantine' in root: continue
        for f in files:
            if f.lower().endswith(('.pdf', '.tcx', '.json', '.csv', '.xml')):
                pending += 1
    return pending

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
# --- AI CONFIGURATION ---
PROMPT_PATH = os.path.join(os.path.dirname(__file__), '..', '04_System', 'prompts', 'system_prompt.md')

def load_system_prompt():
    if os.path.exists(PROMPT_PATH):
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    return "You are a helpful medical assistant. (Fallback)"

SYSTEM_PROMPT = load_system_prompt()

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
    pending_files = get_pending_file_count(inbox_path)
    
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
    
    # --- MEMORY VIEW ---
    with st.expander("🧠 Pamięć Agenta (Co wiem?)"):
        st.markdown("**Ostatnio przetworzone pliki:**")
        conn = get_db_connection()
        try:
            files_df = pd.read_sql("SELECT filename, ingestion_date FROM files ORDER BY ingestion_date DESC LIMIT 5", conn)
            st.dataframe(files_df, use_container_width=True)
            
            st.markdown("**Aktywne Hipotezy:**")
            # Check if hypotheses table exists
            try:
                hyp_df = pd.read_sql("SELECT description, confidence FROM hypotheses ORDER BY confidence DESC LIMIT 5", conn)
                if not hyp_df.empty:
                    st.dataframe(hyp_df, use_container_width=True)
                else:
                    st.info("Brak aktywnych hipotez.")
            except:
                st.warning("Tabela hipotez nie została jeszcze zainicjalizowana.")
        except Exception as e:
            st.error(f"Błąd odczytu pamięci: {e}")
        conn.close()

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
