import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from ariadne.core.database import db
from ariadne.core.config import Config

def print_header(title):
    print("\n" + "="*50)
    print(f"   {title}")
    print("="*50)

def check_db():
    print_header("1. DATABASE (THE CRYSTAL)")
    nodes = 0
    edges = 0
    try:
        conn = db.get_connection()
        
        # Check WAL Mode
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        print(f"[*] Storage Mode:   {mode.upper()} (Should be WAL)")
        if mode.upper() != 'WAL':
            print("    [!] WARNING: Database is NOT in WAL mode.")
        
        # Check Stats
        nodes = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        edges = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        print(f"[*] Nodes (Facts):  {nodes}")
        print(f"[*] Edges (Links):  {edges}")
        
        conn.close()
        print("\n[OK] Database Connection Successful.")
        
    except Exception as e:
        print(f"\n[FAIL] Database Error: {e}")
    
    return nodes, edges

def check_folders():
    print_header("2. FOLDERS (PIPELINE)")
    
    inbox = Config.INBOX_DIR
    quarantine = Config.QUARANTINE_DIR
    
    if os.path.exists(inbox):
        count = len([f for f in os.listdir(inbox) if os.path.isfile(os.path.join(inbox, f))])
        print(f"[*] Inbox Pending:  {count} files")
    else:
        print("[!] Inbox folder MISSING")
        
    if os.path.exists(quarantine):
        count = 0
        print("[*] Quarantine Queues:")
        for root, dirs, files in os.walk(quarantine):
            if files:
                rel = os.path.relpath(root, quarantine)
                if rel == '.': continue
                print(f"    - {rel}: {len(files)} files")
                count += len(files)
        if count == 0:
            print("    (Empty - Good!)")
    else:
        print("[!] Quarantine folder MISSING")

def main():
    print_header("ARIADNE V2 SYSTEM CHECK")
    nodes, edges = check_db()
    check_folders()
    print_header("3. SYSTEM DIAGNOSIS")
    if nodes > 0:
        print("[*] STATUS: OPERATIONAL (Contains Data)")
    else:
        print("[*] STATUS: READY (Waiting for Data ingestion)")
        print("    (This is normal for a fresh install. Phase 2 needed.)")

    print("\n" + "="*50)
    print("   CHECK COMPLETE. YOU CAN CLOSE THIS WINDOW.")
    print("="*50)
    # input("Press Enter to exit...") # Removed input for CLI automation

if __name__ == "__main__":
    main()
