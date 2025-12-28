import os
import shutil
from pypdf import PdfReader, PdfWriter

def unlock_quarantine():
    quarantine_dir = r"c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox\Password_Required"
    inbox_dir = r"c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox"
    
    # User provided password
    password = "PawelKaczynski2018" 

    if not os.path.exists(quarantine_dir):
        print("No Quarantine directory found.")
        return

    print(f"🔎 Scanning {quarantine_dir} for Locked PDFs...")
    
    files_unlocked = 0

    for file in os.listdir(quarantine_dir):
        if file.lower().endswith(".pdf"):
            src_path = os.path.join(quarantine_dir, file)
            
            try:
                reader = PdfReader(src_path)
                
                if reader.is_encrypted:
                    # Try to decrypt
                    if reader.decrypt(password):
                        print(f"   🔓 Decrypted {file}! Saving to Inbox...")
                        
                        # Save decrypted version to Inbox
                        writer = PdfWriter()
                        for page in reader.pages:
                            writer.add_page(page)
                        
                        dest_path = os.path.join(inbox_dir, file) 
                        with open(dest_path, "wb") as f:
                            writer.write(f)
                        
                        files_unlocked += 1
                        
                        # Optional: Remove from quarantine if successful?
                        # Yes, let's clean up
                        # os.remove(src_path) 
                    else:
                        print(f"   ❌ Password failed for {file}.")
                        
                else:
                    # Not encrypted? Just move it.
                    print(f"✅ Not encrypted: {file}. Moving to Inbox...")
                    shutil.move(src_path, os.path.join(inbox_dir, file))
                    files_unlocked += 1

            except Exception as e:
                print(f"⚠️ Error processing {file}: {e}")

    print(f"\nSummary:")
    print(f"🔓 Successfully Unlocked: {files_unlocked}")

if __name__ == "__main__":
    unlock_quarantine()
