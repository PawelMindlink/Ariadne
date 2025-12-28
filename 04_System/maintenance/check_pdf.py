import os
# Check if pypdf is installed, if not we will try basic file reading or assume based on size
try:
    from pypdf import PdfReader
except ImportError:
    print("pypdf not installed. Please run: pip install pypdf")
    exit()

def check_pdf_type():
    archive_dir = r"c:\Users\Paweł\Documents\GitHub\Ariadne\01_Archive\Unprocessed"
    pdfs = [f for f in os.listdir(archive_dir) if f.lower().endswith('.pdf')][:5] # Check first 5
    
    print("\n🔍 Inspecting PDFs for Text Content:\n")
    for pdf_file in pdfs:
        path = os.path.join(archive_dir, pdf_file)
        try:
            reader = PdfReader(path)
            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text()
            
            has_text = len(text_content.strip()) > 100
            print(f"- {pdf_file}: {'✅ Digital Text Found' if has_text else '⚠️ Likely Scan (No Text)'} ({len(text_content.strip())} chars)")
        except Exception as e:
            print(f"- {pdf_file}: ❌ Error reading ({e})")

if __name__ == "__main__":
    check_pdf_type()
