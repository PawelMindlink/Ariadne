import os
import shutil

ARCHIVE_DIR = r'c:\Users\Paweł\Documents\GitHub\Ariadne\01_Archive'
INBOX_DIR = r'c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox'

def restore_tcx():
    print("📦 Restoring TCX files...")
    count = 0
    for root, dirs, files in os.walk(ARCHIVE_DIR):
        for file in files:
            if file.lower().endswith('.tcx'):
                src = os.path.join(root, file)
                dest = os.path.join(INBOX_DIR, file)
                try:
                    shutil.move(src, dest)
                    count += 1
                except Exception as e:
                    print(f"Error moving {file}: {e}")
                    
    print(f"✅ Moved {count} TCX files to Inbox.")

if __name__ == "__main__":
    restore_tcx()
