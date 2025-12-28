import os
import shutil
from pypdf import PdfReader, PdfWriter

def restore_pdfs():
    archive_dir = r"c:\Users\Paweł\Documents\GitHub\Ariadne\01_Archive\Unprocessed"
    inbox_dir = r"c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox"
    quarantine_dir = os.path.join(inbox_dir, "Password_Required")
    
    # User provided password
    password = "87022501359" 

    if not os.path.exists(quarantine_dir):
        os.makedirs(quarantine_dir)

    print(f"🔎 Scanning {archive_dir} for PDFs...")
    
    files_moved = 0
    files_decrypted = 0
    files_quarantined = 0

    for root, dirs, files in os.walk(archive_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                src_path = os.path.join(root, file)
                
                # Check encryption
                try:
                    reader = PdfReader(src_path)
                    
                    if reader.is_encrypted:
                        print(f"🔒 Encrypted: {file}")
                        # Try to decrypt
                        if reader.decrypt(password):
                            print(f"   🔓 Decrypted with password! Saving to Inbox...")
                            
                            # Save decrypted version to Inbox
                            writer = PdfWriter()
                            for page in reader.pages:
                                writer.add_page(page)
                            
                            dest_path = os.path.join(inbox_dir, file) # Consider handling name collisions
                            with open(dest_path, "wb") as f:
                                writer.write(f)
                            files_decrypted += 1
                        else:
                            print(f"   ❌ Password failed. Moving to Quarantine...")
                            shutil.copy2(src_path, os.path.join(quarantine_dir, file))
                            files_quarantined += 1
                            
                    else:
                        # Not encrypted, just move to Inbox for processing
                        print(f"✅ Normal PDF: {file}. Restoring to Inbox...")
                        shutil.copy2(src_path, os.path.join(inbox_dir, file))
                        files_moved += 1

                except Exception as e:
                    print(f"⚠️ Error processing {file}: {e}")
                    # Move to quarantine just in case? Or leave for manual review?
                    # For now, let's copy to quarantine so user sees it
                    shutil.copy2(src_path, os.path.join(quarantine_dir, file))
                    files_quarantined += 1

    print(f"\nSummary:")
    print(f"✅ Digital/Normal PDFs Restored: {files_moved}")
    print(f"🔓 Encrypted -> Decrypted: {files_decrypted}")
    print(f"🚧 Password Failed (Quarantined): {files_quarantined}")

if __name__ == "__main__":
    restore_pdfs()
