import os
import shutil
from pathlib import Path

ARCHIVE_DIR = r"c:\Users\Paweł\Documents\GitHub\Ariadne\01_Archive"

def organize_archive():
    print(f"🧹 Organizing {ARCHIVE_DIR}...")
    
    # Define Categories
    folders = {
        "Medical_Reports": [],
        "Fitness_Data": [],
        "System_Logs": []
    }
    
    # Create destinations
    for folder in folders:
        path = os.path.join(ARCHIVE_DIR, folder)
        os.makedirs(path, exist_ok=True)
        
    count = 0
    for entry in os.scandir(ARCHIVE_DIR):
        if entry.is_file():
            name = entry.name.lower()
            src = entry.path
            
            # Categorize
            if "sleepdata" in name or name.endswith(".tcx") or "fitbit" in name:
                dst_folder = "Fitness_Data"
            elif name.endswith(".pdf"):
                dst_folder = "Medical_Reports"
            elif name.endswith(".json") or name.endswith(".log"):
                dst_folder = "System_Logs" # Likely app logs or non-medical JSONs
            else:
                continue # Skip unknown files for safety
                
            dst = os.path.join(ARCHIVE_DIR, dst_folder, entry.name)
            try:
                shutil.move(src, dst)
                count += 1
            except Exception as e:
                print(f"Error moving {name}: {e}")
                
    print(f"✨ Done. Organized {count} files.")

if __name__ == "__main__":
    organize_archive()
