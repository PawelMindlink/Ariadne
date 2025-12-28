import os
import shutil
import sqlite3
import sys

# Setup paths
ROOT = r'c:\Users\Paweł\Documents\GitHub\Ariadne'
INBOX = os.path.join(ROOT, '00_Inbox')
LOCKED_DIR = os.path.join(INBOX, 'Locked')
JUNK_DIR = os.path.join(INBOX, 'Junk')
DB_PATH = os.path.join(ROOT, '02_Database', 'health_data.db')

sys.path.append(os.path.join(ROOT, '03_Apps'))
# Import ingest after path setup
try:
    import ingest
except ImportError:
    print("❌ Failed to import ingest module")
    sys.exit(1)

def create_dummy_locked_pdf(filename):
    # Creating a fake PDF header that might trigger basic checks, 
    # but strictly we rely on pypdf.is_encrypted. 
    # Actually, creating a real encrypted PDF is hard without a library.
    # We'll mock the 'is_pdf_encrypted' function in ingest for this test strictly?
    # No, let's just test the 'Junk' filter which is easier to test with empty file.
    # Testing 'Locked' without a real encrypted PDF is tricky.
    
    # Let's verify 'Junk' and 'Reliability Scoring' primarily.
    path = os.path.join(INBOX, filename)
    with open(path, 'w') as f:
        pass # Empty file
    return path

def verify_junk_filter():
    print("\n🗑️ Testing Junk Filter...")
    f = create_dummy_locked_pdf("junk_test.txt")
    
    # Run ingest loop logic (partially) or just full run?
    # Full run is safer.
    # capture logs
    ingest.run_ingestion()
    
    if os.path.exists(os.path.join(JUNK_DIR, "junk_test.txt")):
        print("✅ Success: Empty file moved to Junk.")
    else:
        print("❌ Failure: Empty file NOT in Junk.")

def verify_reliability_score():
    print("\n📊 Testing Reliability Score in DB...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if we have any data with reliability set (from previous run or manual insert?)
    # Since we migrated, default is 5.
    # The 'run_ingestion' above might have processed files if any were in inbox.
    
    # Let's manually insert via parser if possible, or just query existing.
    # We parsed 'temp_debug_activity.json' previously.
    # We should re-parse a sample to see it get new columns.
    
    # Create a dummy Google Fit JSON to test parsing
    # Must match regex (\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2})
    dummy_json = os.path.join(INBOX, "2025-01-01T12_00_00_TEST.json")
    with open(dummy_json, 'w') as f:
        f.write('{"calories(kcal)": 100, "distanceMeters": 1000, "averageHeartRateBpm": 60}')
        
    # Run ingest
    ingest.run_ingestion()
    
    # Check DB
    row = cursor.execute("SELECT reliability, source_type FROM events WHERE type='Activity_Unknown' ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        print(f"  > Found Event: Reliability={row[0]}, Source={row[1]}")
        if row[0] == 7 and row[1] == 'Google Fit':
             print("✅ Success: Google Fit JSON got Reliability 7.")
        else:
             print("❌ Failure: Incorrect scores.")
    else:
        print("⚠️ Warning: No event found to verify.")
        
    conn.close()

if __name__ == "__main__":
    verify_junk_filter()
    verify_reliability_score()
