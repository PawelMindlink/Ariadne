import os
import shutil
import re

ARCHIVE_DIR = r'c:\Users\Paweł\Documents\GitHub\Ariadne\01_Archive'
INBOX_DIR = r'c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox'

def restore_archive():
    print("📦 Starting Archive Restoration...")
    
    if not os.path.exists(ARCHIVE_DIR):
        print("Archive not found.")
        return

    # Walk through root and subdirectories
    for root, dirs, files in os.walk(ARCHIVE_DIR):
        for filename in files:
            if filename == 'desktop.ini': continue
            
            src_path = os.path.join(root, filename)
            
            # Prefix regex: 20251226_184451_timestamp_original.ext
            # We look for the pattern YYYYMMDD_HHMMSS_...
            # The previous ingest logic might have stacked prefixes if run multiple times, 
            # so we should strip ALL leading timestamps.
            
            original_name = filename
            # Repeat stripping until no match
            while re.match(r"^\d{8}_\d{6}_", original_name):
                original_name = original_name[16:]

            dest_path = os.path.join(INBOX_DIR, original_name)
            
            try:
                # Handle duplicates - if exists, we might want to rename or skip
                # For safety, let's skip if exact name exists, but maybe log it.
                if os.path.exists(dest_path):
                    # Check size? if same size, skip.
                    if os.path.getsize(src_path) == os.path.getsize(dest_path):
                         # print(f"⚠️ Skipping duplicate {original_name}")
                         continue
                
                shutil.move(src_path, dest_path)
                restored_count += 1
                if restored_count % 100 == 0:
                    print(f"Restored {restored_count} files...")
            except Exception as e:
                print(f"❌ Error moving {filename}: {e}")

    print(f"✅ Restored {restored_count} files to {INBOX_DIR}")

if __name__ == "__main__":
    restore_archive()
