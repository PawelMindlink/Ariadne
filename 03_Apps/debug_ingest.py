import ingest
import sqlite3
import traceback
import os
import sys
import importlib

# Force reload to avoid stale cache
importlib.reload(ingest)

# Safe print helper
def safe_print(s):
    try:
        print(s, end='', flush=True)
    except:
        print(s.encode('ascii', 'ignore').decode(), end='', flush=True)

def run():
    print("🧪 Debugging Ingestion in local dir...")
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    # Init Schema
    cursor.execute('''CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        type TEXT,
        source_id INTEGER,
        json_details TEXT,
        created_at TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER,
        variable_name TEXT,
        value REAL,
        unit TEXT,
        normalized_value REAL,
        normalized_unit TEXT
    )''')
    conn.commit()
    
    # Find PDFs
    inbox = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '00_Inbox', 'Decrypted'))
    print(f"DEBUG: Inbox Path: {inbox}")
    
    if os.path.exists(inbox):
        files = [f for f in os.listdir(inbox) if f.lower().endswith('.pdf')]
        print(f"📉 Found {len(files)} PDFs to process.")
        
        success_count = 0
        fail_count = 0
        
        for f in files:
            target = os.path.join(inbox, f)
            safe_print(f"   Processing: {f}...")
            try:
                # We use a fresh connection per file if needed, or share one.
                # Ingest expects open cursor? No, it takes connection for pdf?
                # parse_medical_pdf(file_path, cursor) -> It takes a cursor actually, based on previous read.
                # Let's check ingest.py signature.
                cursor = conn.cursor()
                result = ingest.parse_medical_pdf(target, cursor)
                if result:
                    print("✅")
                    success_count += 1
                else:
                     print("❌ (False return)")
                     fail_count += 1
            except Exception as e:
                with open("trace.log", "w", encoding="utf-8") as tf:
                     tf.write(traceback.format_exc())
                print(f"🔥 CRASH: {e}")
                # traceback.print_exc() 
                fail_count += 1
                break # Stop after first crash to read log
                
        print(f"Done. Success: {success_count}, Fail: {fail_count}")

    else:
        print("DEBUG: Inbox path does not exist!")
        return

if __name__ == "__main__":
    run()
