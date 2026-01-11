from ariadne.ingestion.scanner import Scanner
from ariadne.ingestion.extractor import Extractor
from ariadne.core.config import Config
from ariadne.core.database import db
import os
import shutil
import datetime

class Pipeline:
    def __init__(self):
        self.scanner = Scanner()
        self.extractor = Extractor()
        self.conn = db.get_connection()

    def run(self):
        """
        Main Loop: Scan -> Extract -> logic -> DB/Quarantine
        """
        print("Starting Pipeline Run...")
        count = 0
        for file_path, filename in self.scanner.scan():
            result = self.process_file(file_path, filename)
            print(f"[{result}] {filename}")
            count += 1
        print(f"Pipeline finished. Processed {count} files.")

    def process_file(self, file_path, filename):
        # 1. Deduplication (Hash Check)
        # TODO: Check if hash exists in DB. For now, skip.
        
        # 2. Extract Text
        text, method = self.extractor.extract_text(file_path)
        
        if method == 'error':
             self.move_to_quarantine(file_path, "extraction_error")
             return "ERROR"
             
        if method == 'needs_ocr_scan':
             # For Phase 1, we treat this as a "Review Needed" or we could just skip.
             # User wanted strict quality.
             self.move_to_quarantine(file_path, "needs_ocr")
             return "NEEDS_OCR"

        if not text or len(text.strip()) == 0:
             self.move_to_quarantine(file_path, "empty_text")
             return "EMPTY"

        # 3. Quality Gate (The Annoyance Factor)
        # We need a DATE. For Phase 1 (Basic), if we can't find a 4-digit year, we flag it.
        # This is a naive check but proves the concept.
        import re
        if not re.search(r'20[0-9]{2}', text):
             self.move_to_quarantine(file_path, "missing_date")
             return "QUARANTINE_NO_DATE"

        # 4. Success (Move to Processing for Phase 1, or Archive)
        # In a real run, we would insert into DB here. 
        # For now, just mark as VALID.
        return "VALID_CANDIDATE"

    def move_to_quarantine(self, file_path, reason):
        target_dir = os.path.join(Config.QUARANTINE_DIR, reason)
        os.makedirs(target_dir, exist_ok=True)
        filename = os.path.basename(file_path)
        try:
             # Using copy for safety during dev, move in prod
             shutil.copy2(file_path, os.path.join(target_dir, filename))
        except Exception as e:
             print(f"Failed to move {filename}: {e}")

if __name__ == "__main__":
    p = Pipeline()
    p.run()
