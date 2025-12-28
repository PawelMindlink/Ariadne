import os
import shutil

ROOT_DIR = r"c:\Users\Paweł\Documents\GitHub\Ariadne"
INBOX_DIR = os.path.join(ROOT_DIR, "00_Inbox")
SYSTEM_DIR = os.path.join(ROOT_DIR, "04_System", "maintenance")

def cleanup_project():
    print("🧹 Starting Project Cleanup...")
    
    # 1. Move Root Scripts
    scripts_to_move = ["check_api.py", "check_pdf.py", "inventory.py"]
    for script in scripts_to_move:
        src = os.path.join(ROOT_DIR, script)
        dst = os.path.join(SYSTEM_DIR, script)
        if os.path.exists(src):
            try:
                shutil.move(src, dst)
                print(f"✅ Moved {script} to System/maintenance")
            except Exception as e:
                print(f"❌ Error moving {script}: {e}")

    # 2. Delete Known Empty/Junk Folders in Inbox
    junk_folders = ["IT_ORDERS", "customer_data", "IT_CONSENT_HISTORY", "IT_DEVICE_AND_CONTENT", "IT_FORMS", "IT_GLOBAL_EVENT", "Errors", "Takeout"]
    # 'Takeout' might have data, but usually it's the wrapper. Let's be careful.
    # User said "Check if empty".
    
    for folder in junk_folders:
        path = os.path.join(INBOX_DIR, folder)
        if os.path.exists(path):
            # Check if empty (ignoring desktop.ini)
            files = os.listdir(path)
            if not files or (len(files) == 1 and files[0] == "desktop.ini"):
                try:
                    shutil.rmtree(path)
                    print(f"🗑️ Deleted empty/junk folder: {folder}")
                except Exception as e:
                    print(f"❌ Error deleting {folder}: {e}")
            else:
                print(f"⚠️ {folder} is NOT empty. Skipping deletion.")

    # 3. Flatten 'Badania' and 'Recepty'
    # Move all PDFs from these subfolders to Inbox Root
    flatten_targets = ["Badania", "Recepty", "Dieta"]
    
    for target in flatten_targets:
        target_path = os.path.join(INBOX_DIR, target)
        if os.path.exists(target_path):
            print(f"📂 Flattening {target}...")
            for root, dirs, files in os.walk(target_path):
                for file in files:
                    if file.lower().endswith(".pdf"):
                        src = os.path.join(root, file)
                        dst = os.path.join(INBOX_DIR, file)
                        
                        # Handle collision
                        if os.path.exists(dst):
                            base, ext = os.path.splitext(file)
                            dst = os.path.join(INBOX_DIR, f"{base}_restored{ext}")
                        
                        try:
                            shutil.move(src, dst)
                            print(f"   Moved {file} to Inbox")
                        except Exception as e:
                            print(f"   Error moving {file}: {e}")
            
            # Try to remove the folder if empty now
            try:
                shutil.rmtree(target_path)
                print(f"   Deleted flattened folder {target}")
            except Exception as e:
                print(f"   Could not delete {target} (maybe not empty?): {e}")

if __name__ == "__main__":
    cleanup_project()
