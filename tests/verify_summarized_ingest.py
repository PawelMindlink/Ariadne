import sqlite3
import os
import sys

# Add app to path
sys.path.append(r'c:\Users\Paweł\Documents\GitHub\Ariadne\03_Apps')
from ingest import parse_garmin_summarized, get_db_connection

TEST_FILE = r'c:\Users\Paweł\Documents\GitHub\Ariadne\temp_debug_activity.json'
DB_PATH = r'c:\Users\Paweł\Documents\GitHub\Ariadne\02_Database\health_data.db'

def verify():
    print(f"🧪 Testing ingestion of {TEST_FILE}...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Parse
    try:
        parse_garmin_summarized(TEST_FILE, cursor)
        conn.commit()
        print("✅ Parsing executed.")
    except Exception as e:
        print(f"❌ Parsing Failed: {e}")
        return

    # 2. Check DB
    print("\n📊 Verifying Database Records:")
    rows = cursor.execute("SELECT type, count(*) FROM events WHERE type LIKE 'Activity_%' GROUP BY type").fetchall()
    
    found_pilates = False
    found_swim = False
    
    for r in rows:
        print(f" - {r[0]}: {r[1]}")
        if 'Pilates' in r[0]: found_pilates = True
        if 'Swimming' in r[0]: found_swim = True
        
    if found_pilates and found_swim:
        print("\n✅ SUCCESS: Found Pilates and Swimming!")
    else:
        print("\n⚠️ PARTIAL: Missing expected types.")

    conn.close()

if __name__ == "__main__":
    verify()
