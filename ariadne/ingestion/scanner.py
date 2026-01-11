import os
import hashlib
from ariadne.core.config import Config

class Scanner:
    def __init__(self, target_dir=Config.INBOX_DIR):
        self.target_dir = target_dir

    def scan(self):
        """
        Yields (filepath, filename) for every file in the inbox.
        Non-recursive to respect the 'Flat Inbox' philosophy or safe recursion.
        """
        if not os.path.exists(self.target_dir):
            return

        # Use scandir for performance (it's an iterator, doesn't load all list to memory)
        with os.scandir(self.target_dir) as entries:
            for entry in entries:
                if entry.is_file():
                    # Check for ignores (e.g. .DS_Store, temporary files)
                    if entry.name.startswith('.'):
                        continue
                    
                    yield entry.path, entry.name

    def calculate_hash(self, file_path):
        """
        Calculates SHA-256 hash of a file to detect duplicates.
        Reads in chunks to minimize memory usage for large PDFs.
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read 4k bytes at a time
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except IOError:
            return None
