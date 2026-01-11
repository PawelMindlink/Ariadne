import sqlite3
import os
from .config import Config

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.db_path = Config.DB_PATH
        return cls._instance

    def get_connection(self):
        """
        Returns a new connection with WAL mode enabled and strict foreign keys.
        """
        conn = sqlite3.connect(
            self.db_path, 
            timeout=30.0  # Increased timeout for robustness
        )
        
        # Enable Write-Ahead Logging for concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        
        # Enable Foreign Keys
        conn.execute("PRAGMA foreign_keys=ON;")
        
        # Fast I/O
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA mmap_size=30000000000;") # 30GB mmap limit (effectively unlimited)

        conn.row_factory = sqlite3.Row
        return conn

    def close(self):
        pass # Connections are managed per-scope usually

# Singleton instance
db = Database()
