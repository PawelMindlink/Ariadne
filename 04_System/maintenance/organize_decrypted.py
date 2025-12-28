import os
import shutil

SOURCE_DIR = r"c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox"
DEST_DIR = r"c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox\Decrypted"

def move_unlocked():
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
        print(f"Created {DEST_DIR}")

    count = 0
    for filename in os.listdir(SOURCE_DIR):
        # Move files that we unlocked (usually have 'Unlocked' or were just decrypted)
        # The user asked to move "files I unlocked".
        # distinct characteristic: they are the ones we just wrote.
        # But 'deep_unlock.py' saved them to Inbox. 
        # I can look for "Unlocked_" prefix if I used it, BUT deep_unlock only used it on collision.
        # However, the user wants me to clean up.
        # Let's move ALL PDFs that are NOT in Password_Required and NOT in Still_Locked?
        # No, that might move original digital PDFs coming from other sources.
        # Safe bet: Move "Unlocked_*.pdf" AND the ones that match the "SIBO" description user mentioned.
        
        # Actually, best approach: Move ALL PDFs currently in Inbox to 'Decrypted' IF they are valid PDFs 
        # and NOT encrypted. (Since we supposedly unlocked everything).
        
        # Let's stick to moving "Unlocked_" ones and "SIBO" ones.
        
        is_target = False
        print(f"DEBUG: Checking {filename}...")
        if filename.startswith("Unlocked_"):
            is_target = True
        elif "sibo" in filename.lower():
            is_target = True
        elif "dieta" in filename.lower():
            is_target = True
            
        if is_target and filename.endswith(".pdf"):
            try:
                shutil.move(os.path.join(SOURCE_DIR, filename), os.path.join(DEST_DIR, filename))
                print(f"Moved: {filename}")
                count += 1
            except Exception as e:
                print(f"Error moving {filename}: {e}")

    print(f"Moved {count} files to 00_Inbox/Decrypted")

if __name__ == "__main__":
    move_unlocked()
