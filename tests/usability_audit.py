import sys
import os
import sqlite3
import pandas as pd
sys.path.append('03_Apps')
import agent
import ingest

# Mock Streamlit for testing
class MockStreamlit:
    def error(self, msg): print(f"❌ UI ERROR: {msg}")
    def warning(self, msg): print(f"⚠️ UI WARNING: {msg}")
    def success(self, msg): print(f"✅ UI SUCCESS: {msg}")
    def info(self, msg): print(f"ℹ️ UI INFO: {msg}")

agent.st = MockStreamlit()

def run_scenarios():
    print("🧪 STARTING 5-SCENARIO USABILITY AUDIT\n")
    
    # --- Scenario 1: The "New Data" Ingestion ---
    print("▶️ Scenario 1: Ingestion of New Files")
    # Check if DB exists
    ingest.run_ingestion()
    conn = pyt_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM events")
    count = c.fetchone()[0]
    print(f"   Result: DB contains {count} events.")
    if count == 0:
        print("   ❌ FAILURE: Database is empty after ingestion.")
    else:
        print("   ✅ SUCCESS: Data ingested.")
    conn.close()

    # --- Scenario 2: The "Fact Injection" (Memory Test) ---
    print("\n▶️ Scenario 2: User teaches Agent a Fact")
    query = "I take 2000 units of Vitamin D daily."
    print(f"   User says: '{query}'")
    # Simulate extraction (Since we don't have the live chat loop here, we assume the agent *should* trigger extraction)
    # Validating if the 'facts' table exists and is usable
    conn = pyt_db_connection()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO facts (category, key, value, source) VALUES (?, ?, ?, ?)", 
                  ('Medication', 'Supplement', 'Vitamin D 2000iu', 'Scenario Test'))
        conn.commit()
        print("   ✅ SUCCESS: Fact inserted into 'facts' table.")
    except Exception as e:
        print(f"   ❌ FAILURE: Could not insert fact: {e}")
    conn.close()

    # --- Scenario 3: The "Recall" (Context Test) ---
    print("\n▶️ Scenario 3: Agent Recall")
    # Does the agent see the fact?
    # We cheat slightly by reading the Agent's internals (which load the context)
    try:
        context = agent.get_schema_context() # Or memory context if we had a function for it
        # Actually, let's test if the agent *would* see it in a SQL generation
        prompt = "What supplements do I take?"
        response = agent.get_gemini_response(prompt)
        print(f"   Agent Response (Snippet): {response[:100]}...")
        if "Vitamin D" in response or "Supplement" in response: # Weak check as we aren't using the full chain yet
             print("   ⚠️ PARTIAL: Response generated, effectiveness depends on prompt linkage.")
        else:
             print("   ❓ NOTE: Check if prompt included memory.")
    except Exception as e:
        print(f"   ❌ FAILURE: Agent crash on recall: {e}")

    # --- Scenario 4: The "Analysis" (Deep Logic) ---
    print("\n▶️ Scenario 4: Clinical Analysis")
    query = "Why is my recovery poor?"
    response = agent.get_gemini_response(query)
    if "sleep" in response.lower() or "hrv" in response.lower():
        print("   ✅ SUCCESS: Agent connected concepts (Recovery -> Sleep/HRV).")
    else:
        print("   ⚠️ WARNING: Agent response might be generic.")

    # --- Scenario 5: The "Garbage" Input ---
    print("\n▶️ Scenario 5: Garbage Handling")
    query = "fsdfjsdklfjdslk"
    response = agent.get_gemini_response(query)
    print(f"   Agent Response: {response}")
    if "understand" in response.lower() or "clarify" in response.lower() or "?" in response:
        print("   ✅ SUCCESS: Agent handled nonsense gracefully.")
    else:
        print("   ⚠️ WARNING: Agent tried to hallucinate an answer.")

def pyt_db_connection():
    return sqlite3.connect(agent.DB_PATH)

if __name__ == "__main__":
    run_scenarios()
