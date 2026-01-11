import streamlit as st
import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ariadne.core.database import db
from ariadne.core.config import Config

st.set_page_config(page_title="Ariadne V2 Admin", layout="wide")

st.title("🕷️ Ariadne V2: System Monitor")

# --- Section 1: Database Health ---
st.header("1. The Crystal (Database V2)")

try:
    conn = db.get_connection()
    
    # Query Stats
    nodes_count = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
    edges_count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
    wal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Nodes", nodes_count)
    col2.metric("Edges", edges_count)
    col3.metric("Mode", wal_mode.upper())
    
    conn.close()
    
except Exception as e:
    st.error(f"Database Error: {e}")

# --- Section 2: Inbox & Quarantine ---
st.header("2. The Pipeline (Inbox & Quarantine)")

def count_files(directory):
    if not os.path.exists(directory):
        return 0
    return len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])

inbox_count = count_files(Config.INBOX_DIR)
quarantine_count = count_files(Config.QUARANTINE_DIR)

col1, col2 = st.columns(2)
col1.metric("📥 Inbox (Pending)", inbox_count)
col2.metric("☣️ Quarantine (Review Needed)", quarantine_count)

# --- Section 3: Quarantine Details ---
st.subheader("Quarantine Inspector")
if os.path.exists(Config.QUARANTINE_DIR):
    for root, dirs, files in os.walk(Config.QUARANTINE_DIR):
        if files:
            subdir = os.path.basename(root)
            if subdir == os.path.basename(Config.QUARANTINE_DIR): continue
            
            st.warning(f"Reason: {subdir} ({len(files)} files)")
            st.code("\n".join(files[:5]))
else:
    st.info("Quarantine is empty.")

# --- Action Buttons ---
st.header("Actions")
if st.button("🔄 Run Basic Pipeline Scan (Dry Run)"):
    st.info("Running pipeline... (Check terminal for output)")

# --- Section 4: Data Explorer (The Weaver's Output) ---
st.header("4. Data Explorer (The Crystal)")

try:
    conn = db.get_connection()
    
    # 4.1 Observations (The Facts)
    st.subheader("🧬 Observations (Extracted Facts)")
    obs_df = pd.read_sql_query("""
        SELECT 
            obs.id,
            doc.body->>'$.name' as Source_Document,
            concept.body->>'$.name' as Concept,
            obs.value_text as Value,
            obs.observation_date as Date
        FROM observations obs
        LEFT JOIN nodes doc ON obs.source_document_id = doc.id
        LEFT JOIN nodes concept ON obs.concept_node_id = concept.id
        ORDER BY obs.id DESC LIMIT 50
    """, conn)
    
    if not obs_df.empty:
        st.dataframe(obs_df, use_container_width=True)
    else:
        st.info("No observations found yet. Run the Ingestion Pipeline.")

    # 4.2 Nodes (The Entities)
    st.subheader("🕸️ Nodes (Entities & Events)")
    nodes_df = pd.read_sql_query("""
        SELECT id, type, body FROM nodes ORDER BY id DESC LIMIT 50
    """, conn)
    
    if not nodes_df.empty:
        # Simple dataframe
        st.dataframe(nodes_df[['id', 'type']], use_container_width=True)
        
        # JSON Inspector
        st.caption("Select a Node ID to inspect raw JSON:")
        node_id = st.number_input("Node ID", min_value=1, step=1)
        
        selected_node = nodes_df[nodes_df['id'] == node_id]
        if not selected_node.empty:
            st.json(selected_node.iloc[0]['body'])
    else:
        st.info("No nodes in the Crystal.")

    conn.close()

except Exception as e:
    st.error(f"Data Explorer Error: {e}")
