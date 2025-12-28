import ingest
import sqlite3
import traceback
import sys
import os

# Ensure we can import ingest
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '03_Apps'))

def run():
    print("🧪 Reproducing Ingestion Crash...")
    conn = sqlite3.connect(':memory:')
    file_path = r"c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox\PDFMailer.pdf"
    
    if not os.path.exists(file_path):
        # Allow checking any PDF
        inbox = r"c:\Users\Paweł\Documents\GitHub\Ariadne\00_Inbox"
        pdfs = [f for f in os.listdir(inbox) if f.lower().endswith('.pdf')]
        if pdfs:
            file_path = os.path.join(inbox, pdfs[0])
            print(f"Using {file_path}")
        else:
            print("No PDF found to test.")
            return

    try:
        ingest.parse_medical_pdf(file_path, conn)
        print("✅ Success (Unexpected)")
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    run()
