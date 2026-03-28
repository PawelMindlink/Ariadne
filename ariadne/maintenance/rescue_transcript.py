import os
import shutil

ROOT = r"c:\Users\Paweł\Documents\GitHub\Ariadne"

def find_and_rescue():
    target_name_part = "ZnanyLekarz"
    
    found_path = None
    for root, dirs, files in os.walk(ROOT):
        for file in files:
            if target_name_part in file:
                found_path = os.path.join(root, file)
                print(f"Found: {found_path}")
                break
        if found_path: break
        
    if found_path:
        dest_dir = os.path.join(ROOT, "01_Archive", "Consultations")
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, os.path.basename(found_path))
        
        try:
            shutil.move(found_path, dest_path)
            print(f"✅ Moved to: {dest_path}")
        except Exception as e:
            print(f"❌ Error moving: {e}")
    else:
        print("❌ File not found anywhere.")

if __name__ == "__main__":
    find_and_rescue()
