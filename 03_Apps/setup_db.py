import sqlite3
import os

# Paths
DB_FOLDER = os.path.join(os.path.dirname(__file__), '..', '02_Database')
DB_PATH = os.path.join(DB_FOLDER, 'ariadne.db')

def create_schema():
    print(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Enable Foreign Keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Table: sources
    # (id, name, type [Lab/Wearable/App], trust_score [1-10])
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL, -- 'Lab', 'Wearable', 'App'
        trust_score INTEGER CHECK(trust_score BETWEEN 1 AND 10)
    );
    """)

    # Table: files
    # (id, filename, file_path, ingestion_date, raw_text_backup)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        ingestion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        raw_text_backup TEXT
    );
    """)

    # Table: events
    # (id, timestamp, type [Meal, Workout, Sleep, Lab_Test], source_id, file_id, json_details)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP NOT NULL,
        type TEXT NOT NULL, -- 'Meal', 'Workout', 'Sleep', 'Lab_Test'
        source_id INTEGER,
        file_id INTEGER,
        json_details TEXT,
        FOREIGN KEY(source_id) REFERENCES sources(id),
        FOREIGN KEY(file_id) REFERENCES files(id)
    );
    """)

    # Table: observations
    # (id, event_id, variable_name, value, unit, context_tag)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        variable_name TEXT NOT NULL,
        value REAL, -- Assuming numeric, but could be text. Spec doesn't strictly say. Sticking to flexible types or just REAL/TEXT.
        unit TEXT,
        context_tag TEXT,
        FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
    );
    """)

    # Create Hypotheses Table (Agent Memory)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hypotheses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 1,
        description TEXT,
        confidence FLOAT,
        status TEXT DEFAULT 'active', -- active, confirmed, refuted
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create Facts Table (Structured Facts extracted from conversation)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 1,
        category TEXT, -- e.g., 'Medication', 'Lifestyle', 'Symptom'
        key TEXT,      -- e.g., 'Supplement'
        value TEXT,    -- e.g., 'Vitamin D'
        confidence FLOAT DEFAULT 1.0,
        source TEXT,   -- e.g., 'Chat', 'File: report.pdf'
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()
    print("Database schema initialized successfully.")

if __name__ == "__main__":
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)
    create_schema()
