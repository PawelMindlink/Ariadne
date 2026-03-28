import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import shutil
import time
import sqlite3
from ariadne.core.database import db
from ariadne.core.config import Config
from ariadne import start_ingestion

# SOURCE_DIR = r"c:\Users\Paweł\Documents\GitHub\Ariadne\01_Archive\Medical_Reports"
SOURCE_DIR = os.path.join(Config.ARCHIVE_DIR, "Medical_Reports")
TARGET_DIR = Config.INBOX_DIR

def run_stress_test(limit=50):
    print(f"🔥 Starting Stress Test (Limit: {limit} files)...")
    
    # 1. Baseline
    conn = db.get_connection()
    try:
        start_nodes = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        start_obs = conn.execute("SELECT count(*) FROM observations").fetchone()[0]
    except:
        start_nodes = 0
        start_obs = 0
    conn.close()
    
    print(f"📊 Baseline: {start_nodes} Nodes, {start_obs} Observations")
    
    # 2. Stage Files
    files = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith('.pdf')]
    to_process = files[:limit]
    
    if not to_process:
        print("❌ No files found in source!")
        return

    print(f"📦 Staging {len(to_process)} files to Inbox...")
    for f in to_process:
        src = os.path.join(SOURCE_DIR, f)
        dst = os.path.join(TARGET_DIR, f)
        shutil.copy(src, dst) # COPY, don't move, so we can re-run tests
        
    print("✅ Staging complete.")
    
    # 3. Run Ingestion
    start_time = time.time()
    processed_count = start_ingestion.run_ingestion()
    duration = time.time() - start_time
    
    # 4. Results
    conn = db.get_connection()
    end_nodes = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
    end_obs = conn.execute("SELECT count(*) FROM observations").fetchone()[0]
    conn.close()
    
    print("\n" + "="*30)
    print("📈 STRESS TEST RESULTS")
    print("="*30)
    print(f"Files Processed: {processed_count} / {len(to_process)}")
    print(f"Time Taken:      {duration:.2f}s ({duration/max(1, processed_count):.2f}s/file)")
    print(f"Nodes Growth:    {start_nodes} -> {end_nodes} (+{end_nodes - start_nodes})")
    print(f"Obs Growth:      {start_obs} -> {end_obs} (+{end_obs - start_obs})")
    print("="*30)

if __name__ == "__main__":
    # Ensure Inbox is empty-ish or just run
    run_stress_test(limit=50)
