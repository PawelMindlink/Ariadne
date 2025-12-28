import os
import shutil
import re

SOURCE_DIR = r"c:\Users\Paweł\Documents\GitHub\Ariadne\01_Archive"
DEST_DIR = r"c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox"

def restore_recent_pdfs():
    print("running restore...")
    count = 0
    for filename in os.listdir(SOURCE_DIR):
        if filename.lower().endswith(".pdf"):
            # Strip timestamp prefix if present (e.g. 20251226_185238_Original.pdf)
            # Regex to match the standard ingest prefix format?
            # Or just move it back and let ingest handle it (it might double prefix?)
            # ingest.py usually adds a prefix. restore_archive.py stripped it.
            # Let's try to strip it.
            
            # Pattern: YYYYMMDD_HHMMSS_OriginalName.pdf
            match = re.match(r"^\d{8}_\d{6}_(.+)", filename)
            if match:
                original_name = match.group(1)
            else:
                original_name = filename
            
            src = os.path.join(SOURCE_DIR, filename)
            dst = os.path.join(DEST_DIR, original_name)
            
            try:
                shutil.move(src, dst)
                print(f"Restored: {original_name}")
                count += 1
            except Exception as e:
                print(f"Error moving {filename}: {e}")

    print(f"Restored {count} PDFs.")

if __name__ == "__main__":
    restore_recent_pdfs()
