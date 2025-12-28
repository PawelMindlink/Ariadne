import time
import os
import sys
import sqlite3
import pandas as pd
from unittest.mock import MagicMock
import toml

# --- SYSTEM & ENVIRONMENT MOCKING ---
# We must mock streamlit BEFORE importing agent
sys.modules["streamlit"] = MagicMock()
import streamlit as st
st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()] # Fix for unpacking c1, c2, c3

# Load secrets manually
secrets_path = os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml')
if os.path.exists(secrets_path):
    secrets = toml.load(secrets_path)
    st.secrets = secrets
else:
    print("❌ Critical: No secrets.toml found.")
    sys.exit(1)

# Now import agent functions
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '03_Apps'))
import agent

# --- CONFIG ---
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '02_Database', 'health_data.db')

def run_performance_test():
    log_buffer = ["🧪 STARTING USER SCENARIO TEST: 'Search for Systems Correlations'"]
    
    def log(msg):
        print(msg)
        log_buffer.append(msg)

    # SCENARIO: User suspects poor sleep connects to high heart rate.
    # Targeted Date: June 2025 (Confirmed data exists)
    user_query = "Show me my Deep Sleep duration and Average Heart Rate for June 2025. Is there a connection?"
    
    # 1. SQL GENERATION
    t0 = time.time()
    log(f"🗣️  User: '{user_query}'")
    
    sql_prompt = f"{agent.SCHEMA_CONTEXT}\n\nUSER QUESTION: {user_query}\n\nRules:\n1. Generate SQL."
    response_text = agent.get_gemini_response(sql_prompt)
    
    t1 = time.time()
    gen_time = t1 - t0
    log(f"⏱️  Gemini (SQL Generation): {gen_time:.4f}s")
    
    # Extract SQL
    import re
    sql_match = re.search(r"```sql\n(.*?)\n```", response_text, re.DOTALL)
    if sql_match:
        sql_query = sql_match.group(1)
    else:
        sql_query = response_text.replace("```sql", "").replace("```", "").strip() 
        
    log(f"💻 Generated SQL:\n{sql_query}")
    
    # 2. EXECUTION
    t2 = time.time()
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(sql_query, conn)
        row_count = len(df)
    except Exception as e:
        log(f"❌ SQL Error: {e}")
        row_count = 0
    conn.close()
    
    t3 = time.time()
    exec_time = t3 - t2
    log(f"⏱️  SQLite Execution:        {exec_time:.4f}s")
    log(f"📊 Rows Returned:           {row_count}")
    
    # 3. INTERPRETATION
    t4 = time.time()
    if row_count > 0:
        summary_prompt = f"User asked: '{user_query}'.\nData:\n{df.to_string()}\n\nInterpret holistically."
        final_response = agent.get_gemini_response(summary_prompt)
    else:
        final_response = "No data found."
        
    t5 = time.time()
    interpret_time = t5 - t4
    log(f"⏱️  Gemini (Interpretation): {interpret_time:.4f}s")
    
    total_time = (t1-t0) + (t3-t2) + (t5-t4)
    log("-" * 60)
    log(f"🚀 TOTAL RESPONSE TIME:     {total_time:.4f}s")
    log(f"📝 Final Answer:\n{final_response}")
    
    if total_time < 2.0:
        log("✅ PERFORMANCE: FAST (< 2s)")
    else:
        log(f"⚠️  PERFORMANCE: SLOW ({total_time:.2f}s > 2.0s)")
        log("    --> Recommendation: Use Caching or Smaller Model.")

    # Write to file
    with open("scenario_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log_buffer))
    print("✅ Results saved to scenario_results.txt")

if __name__ == "__main__":
    run_performance_test()
