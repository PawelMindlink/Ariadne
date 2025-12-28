import os
import shutil
from pypdf import PdfReader, PdfWriter

def deep_unlock():
    # Scan EVERYWHERE
    scan_dirs = [
        r"c:\Users\Paweł\Documents\GitHub\Ariadne\01_Archive",
        r"c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox"
    ]
    
    inbox_dir = r"c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox"
    quarantine_dir = r"c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox\Still_Locked"
    
    if not os.path.exists(quarantine_dir):
        os.makedirs(quarantine_dir)

    passwords = ["PawelKaczynski2018", "87022501359"] # Try both provided
    
    print(f"🕵️ Deep Scan for Encrypted Files...")
    
    unlocked_count = 0
    locked_count = 0
    
    for scan_dir in scan_dirs:
        for root, dirs, files in os.walk(scan_dir):
            if "Still_Locked" in root: continue # Skip our destination

            for file in files:
                if file.lower().endswith(".pdf"):
                    file_path = os.path.join(root, file)
                    
                    try:
                        reader = PdfReader(file_path)
                        if reader.is_encrypted:
                            print(f"🔒 Found Encrypted: {file} in {root}")
                            
                            decrypted = False
                            for pwd in passwords:
                                if reader.decrypt(pwd):
                                    print(f"   🔓 Unlocked with {pwd}!")
                                    
                                    # Save decrypted copy to Inbox
                                    writer = PdfWriter()
                                    for page in reader.pages:
                                        writer.add_page(page)
                                    
                                    # Handle name collision
                                    base_name = os.path.basename(file)
                                    dest_path = os.path.join(inbox_dir, base_name)
                                    if os.path.exists(dest_path):
                                        dest_path = os.path.join(inbox_dir, f"Unlocked_{base_name}")

                                    with open(dest_path, "wb") as f:
                                        writer.write(f)
                                    
                                    unlocked_count += 1
                                    decrypted = True
                                    
                                    # If it was in Archive/Quarantine, maybe delete the original or move it?
                                    # For now, leaving original in Archive is safer, but redundant.
                                    # But user asked to "bring them back".
                                    break # Stop trying passwords
                            
                            if not decrypted:
                                print(f"   ❌ Failed to unlock. Moving to Still_Locked.")
                                shutil.copy2(file_path, os.path.join(quarantine_dir, file))
                                locked_count += 1

                    except Exception as e:
                        # Corrupt or other error
                        pass

    print(f"\nSummary:")
    print(f"🔓 Recovered: {unlocked_count}")
    print(f"🔒 Still Locked: {locked_count} (See 00_Inbox/Still_Locked)")

if __name__ == "__main__":
    deep_unlock()
