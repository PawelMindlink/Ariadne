import unittest
import os
import sys
import shutil

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ariadne.core.config import Config
from ariadne.core.database import db
from ariadne.ingestion.scanner import Scanner
from ariadne.ingestion.extractor import Extractor

class TestPipelineV2(unittest.TestCase):
    def setUp(self):
        # Use a temporary DB or just verify connection
        self.conn = db.get_connection()
        self.scanner = Scanner()
        self.extractor = Extractor()
        
    def tearDown(self):
        self.conn.close()

    def test_database_connection(self):
        """Verify DB is in WAL mode and has tables"""
        cursor = self.conn.cursor()
        mode = cursor.execute("PRAGMA journal_mode;").fetchone()[0]
        self.assertEqual(mode.upper(), 'WAL')
        
        # Check Node table
        tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")]
        self.assertIn('nodes', tables)
        self.assertIn('edges', tables)
        print("✅ Database (WAL) Connection and Schema Verified")

    def test_scanner_basic(self):
        """Scanner should find files in Inbox"""
        # Create a dummy file
        test_file = os.path.join(Config.INBOX_DIR, 'test_scan.txt')
        with open(test_file, 'w') as f:
            f.write("test")
            
        found = False
        for path, name in self.scanner.scan():
            if name == 'test_scan.txt':
                found = True
                break
        
        # Cleanup
        os.remove(test_file)
        self.assertTrue(found, "Scanner did not find the test file")
        print("✅ Scanner Verified")

    def test_extractor_native(self):
        """Extractor should read text file"""
        test_file = os.path.join(Config.INBOX_DIR, 'test_extract.txt')
        with open(test_file, 'w') as f:
            f.write("Hello Ariadne")
            
        text, method = self.extractor.extract_text(test_file)
        
        os.remove(test_file)
        self.assertEqual(text, "Hello Ariadne")
        self.assertEqual(method, "native")
        print("✅ Extractor Verified")

if __name__ == '__main__':
    unittest.main()
