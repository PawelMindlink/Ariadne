import sqlite3
import pandas as pd
import os

DB_PATH = r'c:\Users\Paweł\Documents\GitHub\Ariadne\02_Database\health_data.db'

def maintain():
    conn = sqlite3.connect(DB_PATH)
    print("🔌 Connected to DB.")
    
    # 1. Add Indices
    print("⚡ Adding Indices...")
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)",
        "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_observations_event_id ON observations(event_id)"
    ]
    for idx in indices:
        conn.execute(idx)
    conn.commit()
    print("✅ Indices Created/Verified.")
    
    # 2. Check Activity Types
    print("\n📊 Activity Types in DB:")
    df = pd.read_sql("SELECT type, count(*) as count FROM events WHERE type LIKE 'Activity_%' GROUP BY type", conn)
    print(df)
    
    # 3. Specific Check for MMA/Strength
    print("\n🔍 Checking for specific recent adds:")
    df_recent = pd.read_sql("SELECT timestamp, type, json_details FROM events WHERE type LIKE '%Martial%' OR type LIKE '%Strength%' OR type LIKE '%Walking%' ORDER BY id DESC LIMIT 5", conn)
    print(df_recent)
    
    conn.close()

if __name__ == "__main__":
    maintain()
