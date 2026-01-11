import os
import shutil
import datetime

# Define Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
INBOX_DIR = os.path.join(BASE_DIR, '00_Inbox')
ARCHIVE_DIR = os.path.join(BASE_DIR, '01_Archive')

# Create Cleanup Target
timestamp = datetime.datetime.now().strftime("%Y_%m_%d")
CLEANUP_TARGET = os.path.join(ARCHIVE_DIR, f"Legacy_Cleanup_{timestamp}")
os.makedirs(CLEANUP_TARGET, exist_ok=True)

def clean_inbox():
    print(f"Cleaning Inbox: {INBOX_DIR}")
    print(f"Target: {CLEANUP_TARGET}")
    
    count = 0
    for item in os.listdir(INBOX_DIR):
        item_path = os.path.join(INBOX_DIR, item)
        
        # Skip hidden files
        if item.startswith('.'):
            continue
            
        # Logic: Move ALL directories. Keep ONLY files at root.
        if os.path.isdir(item_path):
            try:
                shutil.move(item_path, os.path.join(CLEANUP_TARGET, item))
                print(f"Moved Folder: {item}")
                count += 1
            except Exception as e:
                print(f"Error moving {item}: {e}")
        else:
            print(f"Kept File: {item}")

    print(f"\nDone. Moved {count} folders to Archive.")

if __name__ == "__main__":
    clean_inbox()
