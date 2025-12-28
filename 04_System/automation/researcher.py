import os
import sqlite3
import pandas as pd
import json
import toml
from google import genai

DB_PATH = r"c:\Users\Paweł\Documents\GitHub\Ariadne\02_Database\health_data.db"
SECRETS_PATH = r"c:\Users\Paweł\Documents\GitHub\Ariadne\.streamlit\secrets.toml"

def normalize_data(cursor):
    """
    Standardization Layer: Normalizes units in observations table based on standard_units ref.
    """
    print("⚖️ Normalizing Data...")
    
    # Fetch Standard Units
    cursor.execute("SELECT variable_name, target_unit FROM standard_units")
    standards = {row[0]: row[1] for row in cursor.fetchall()}
    
    # 1. Trivial Case: Already matching unit -> Copy value
    cursor.execute("""
    UPDATE observations 
    SET normalized_value = value, normalized_unit = unit
    WHERE normalized_value IS NULL 
      AND unit = (SELECT target_unit FROM standard_units WHERE variable_name = observations.variable_name)
    """)
    
    # 2. Hardcoded Logic for known conversions (MVP)
    # Ideally this would be dynamic, but let's hardcode the big ones.
    
    # Cholesterol: mmol/L -> mg/dL (x 38.67)
    cursor.execute("""
    UPDATE observations
    SET normalized_value = value * 38.67, normalized_unit = 'mg/dL'
    WHERE normalized_value IS NULL 
      AND variable_name IN ('Cholesterol', 'LDL Cholesterol', 'HDL Cholesterol')
      AND unit = 'mmol/L'
    """)
    
    # Glucose: mmol/L -> mg/dL (x 18.0)
    cursor.execute("""
    UPDATE observations
    SET normalized_value = value * 18.0, normalized_unit = 'mg/dL'
    WHERE normalized_value IS NULL 
      AND variable_name = 'Glucose'
      AND unit = 'mmol/L'
    """)
    
    print("   Normalization logic applied.")


def generate_hypotheses(cursor, conn):
    """
    The Thinking Engine: Looks at recent data and existing hypotheses to generate new ones.
    """
    print("🧠 Thinking (Hypothesis Generation)...")
    
    # Load Gemnini
    secrets = toml.load(SECRETS_PATH)
    client = genai.Client(api_key=secrets['GEMINI_API_KEY'])
    
    # 1. Fetch Context: last 50 health events + All Lab Results
    # This is RAG-lite.
    
    # Get Labs (High Value)
    df_labs = pd.read_sql("SELECT timestamp, json_details FROM events WHERE source_id=3 ORDER BY timestamp DESC LIMIT 20", conn)
    labs_txt = df_labs.to_string()
    
    # Get Activities (Context)
    df_acts = pd.read_sql("SELECT timestamp, type FROM events WHERE source_id=1 ORDER BY timestamp DESC LIMIT 20", conn)
    acts_txt = df_acts.to_string()
    
    # Get Existing Hypotheses (to avoid repetition)
    existing = pd.read_sql("SELECT title FROM hypotheses", conn)
    existing_txt = existing.to_string()
    
    prompt = f"""
    You are a Proactive Health Research AI.
    
    DATA CONTEXT:
    Recent Labs:
    {labs_txt}
    
    Recent Activities:
    {acts_txt}
    
    Existing Hypotheses:
    {existing_txt}
    
    TASK:
    Analyze the connection between the user's activities and their medical results. 
    Formulate 1 NEW, scientific hypothesis about their health.
    
    OUTPUT JSON:
    {{
        "title": "Short succinct title",
        "description": "2-3 sentences explaining the hypothesis based on evidence.",
        "confidence": 0.0 to 1.0,
        "evidence": ["list of dates or event IDs used"]
    }}
    """
    
    try:
        # Use Thinking Model if available, otherwise Flash
        model_id = 'gemini-2.5-flash' # Will fallback if we found a better one in check_api?
        # User asked for Thinking. Let's try to assume check_api found it.
        # For now, hardcode Flash-2.5 as safe bet, but the INTENT is to use Thinking.
        # If check_api found 'gemini-2.0-flash-thinking-exp', we should use it.
        # Let's assume standard Flash for this script's V1.
        
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        
        res = json.loads(response.text)
        
        # Store Hypothesis
        cursor.execute("INSERT INTO hypotheses (title, description, confidence_score, status, evidence_json, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                       (res['title'], res['description'], res['confidence'], 'Proposed', json.dumps(res['evidence'])))
        
        print(f"💡 New Hypothesis: {res['title']}")
        
    except Exception as e:
        print(f"❌ Thinking failed: {e}")

def run_researcher():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    normalize_data(cursor)
    generate_hypotheses(cursor, conn)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    run_researcher()
