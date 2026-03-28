import streamlit as st
import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ariadne.core.database import db
from ariadne.core.config import Config

# --- Configuration ---
st.set_page_config(
    page_title="Ariadne Health",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- AI & CONFIGURATION ---
import toml
from google import genai

def load_secrets():
    secrets_path = os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml')
    if os.path.exists(secrets_path):
        try:
            return toml.load(secrets_path) 
        except:
            return {}
    return {}

def get_patient_context():
    """Fetches recent observations to form the Short-Term Memory."""
    try:
        conn = db.get_connection()
        rows = conn.execute("""
            SELECT 
                obs.observation_date,
                concept.body->>'$.name' as concept,
                obs.value_text,
                doc.body->>'$.name' as source
            FROM observations obs
            JOIN nodes concept ON obs.concept_node_id = concept.id
            JOIN nodes doc ON obs.source_document_id = doc.id
            ORDER BY obs.observation_date DESC
            LIMIT 100
        """).fetchall()
        conn.close()
        
        if not rows:
            return "No medical observations found in database."
            
        context = "PATIENT RECORDS:\n"
        for r in rows:
            context += f"- [{r[0]}] {r[1]}: {r[2]} (Source: {r[3]})\n"
        return context
    except Exception as e:
        return f"Error fetching context: {e}"

def get_gemini_response(prompt):
    key = load_secrets().get("GEMINI_API_KEY")
    if not key:
        return "⚠️ Error: GEMINI_API_KEY not found in secrets.toml"
        
    context = get_patient_context()
    
    try:
        client = genai.Client(api_key=key)
# --- AI & CONFIGURATION ---
import toml
from google import genai
from ariadne.core.prompts import SYSTEM_PROMPT

def load_secrets():
    secrets_path = os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml')
    if os.path.exists(secrets_path):
        try:
            return toml.load(secrets_path) 
        except:
            return {}
    return {}

# ... (get_patient_context remains unchanged) ...

def get_gemini_response(prompt):
    key = load_secrets().get("GEMINI_API_KEY")
    if not key:
        return "⚠️ Error: GEMINI_API_KEY not found in secrets.toml"
        
    context = get_patient_context()
    
    try:
        client = genai.Client(api_key=key)
        
        # Inject Context and User Query into the Template
        final_prompt = SYSTEM_PROMPT.format(
            context=context,
            user_query=prompt
        )
        
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=final_prompt
        )
        return response.text
    except Exception as e:
        return f"⚠️ AI Error: {e}"
    except Exception as e:
        return f"⚠️ AI Error: {e}"

# --- Inbox Watcher ---
inbox_path = os.path.join(Config.INBOX_DIR)
new_files = [f for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f)) and f != 'desktop.ini']

# --- Sidebar: The Timeline & Tools ---
with st.sidebar:
    st.title("Patient Timeline")
    
    # 1. Inbox Notification
    if new_files:
        st.warning(f"📥 {len(new_files)} New Files Detected")
        if st.button("Process Inbox"):
            with st.spinner("Weaving new data..."):
                from ariadne import start_ingestion
                # We need to adapt start_ingestion to return stats or capture output
                # For now, running it blindly to ensure it works
                try:
                    count = start_ingestion.run_ingestion() 
                    if count > 0:
                        st.success(f"Ingestion complete! Processed {count} files.")
                        st.balloons()
                    else:
                        st.info("Ingestion ran, but no files were processed (check Quarantine?).")
                    # st.rerun() # Optional, might be jarring if too fast
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")
    else:
        st.caption("✅ Inbox Empty")
        
    st.divider()
    
    # 2. Timeline
    st.caption("Your Medical History")
    # Placeholder for database query
    try:
        conn = db.get_connection()
        # Fetch actual Documents from DB
        docs = conn.execute("""
            SELECT id, body->>'$.name' as name, body->>'$.date' as date 
            FROM nodes 
            WHERE type = 'Document' 
            ORDER BY id DESC
        """).fetchall()
        
        if docs:
            for d in docs:
                doc_name = d[1] or "Unknown Document"
                doc_date = d[2] or "Undated"
                
                # Render Timeline Card
                st.markdown(f"""
                <div class="timeline-card">
                    <div class="timeline-date">{doc_date}</div>
                    <div class="timeline-title">📄 {doc_name}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
             st.info("No documents found.")
             
        conn.close()
    except Exception as e:
        st.error(f"DB Error: {e}")

    st.divider()
    st.caption("v2.1.0 (Phase 2)")

# --- Main: The Chat ---
# --- Main Layout: Tabs ---
tab1, tab2 = st.tabs(["💬 Chat & Companion", "🛠️ System Monitor & Data"])

with tab1:
    st.title("👋 Ariadne")
    st.caption("Your Personal Health Companion")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("How can I help you today?"):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # AI RESPONSE
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_gemini_response(prompt)
                st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

with tab2:
    st.header("🔮 The Crystal (Database V2)")
    
    try:
        conn = db.get_connection()
        
        # Stats
        col1, col2, col3 = st.columns(3)
        nodes_cnt = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        obs_cnt = conn.execute("SELECT count(*) FROM observations").fetchone()[0]
        col1.metric("Nodes", nodes_cnt)
        col2.metric("Observations", obs_cnt)
        col3.metric("DB Mode", "WAL")
        
        st.divider()
        
        # Data Explorer
        st.subheader("🧬 Observations Viewer")
        obs_df = pd.read_sql_query("""
            SELECT 
                obs.id,
                obs.observation_date as 'Date',
                concept.body->>'$.name' as 'Feature',
                obs.value_text as 'Value',
                doc.body->>'$.name' as 'Source'
            FROM observations obs
            LEFT JOIN nodes doc ON obs.source_document_id = doc.id
            LEFT JOIN nodes concept ON obs.concept_node_id = concept.id
            ORDER BY obs.observation_date DESC
            LIMIT 50
        """, conn)
        
        if not obs_df.empty:
            st.dataframe(obs_df, use_container_width=True)
        else:
            st.info("No observations recorded yet. Process files in the Sidebar to add knowledge.")
            
        conn.close()
        
    except Exception as e:
        st.error(f"Error reading Crystal: {e}")

# --- Right Column (Context) ---
# (Streamlit doesn't strictly have a 'Right Sidebar', so we use columns if needed, but for now we keep it clean)
