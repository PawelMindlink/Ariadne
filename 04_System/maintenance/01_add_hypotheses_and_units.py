import sqlite3
import os

DB_PATH = r"c:\Users\Paweł\Documents\GitHub\Ariadne\02_Database\health_data.db"

def migrate():
    print(f"🔄 Migrating Database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Hypotheses Table
    print("   - Creating 'hypotheses' table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hypotheses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        status TEXT DEFAULT 'Proposed',  -- Proposed, Validated, Refuted
        confidence_score REAL,
        created_at TEXT,
        evidence_json TEXT  -- JSON list of related event_ids or citations
    )
    """)

    # 2. Standard Units Table (The Rosetta Stone)
    print("   - Creating 'standard_units' table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS standard_units (
        variable_name TEXT PRIMARY KEY,
        target_unit TEXT,
        description TEXT
    )
    """)
    
    # Pre-seed some standard units
    initial_units = [
        ('Cholesterol', 'mg/dL', 'Total Cholesterol'),
        ('LDL Cholesterol', 'mg/dL', 'Low-Density Lipoprotein'),
        ('HDL Cholesterol', 'mg/dL', 'High-Density Lipoprotein'),
        ('Triglycerides', 'mg/dL', 'Fats in blood'),
        ('Glucose', 'mg/dL', 'Blood Sugar'),
        ('TSH', 'uIU/mL', 'Thyroid Stimulating Hormone'),
        ('Vitamin D', 'ng/mL', '25-hydroxy vitamin D'),
        ('Hemoglobin', 'g/dL', 'Red blood cell protein'),
        ('Steps', 'count', 'Daily step count'),
        ('Sleep Duration', 'minutes', 'Total sleep time in minutes'),
        ('Heart Rate', 'bpm', 'Beats per minute')
        # We can add explicit conversion logic in python, table just defines the GOAL.
    ]
    
    print("   - Seeding standard units...")
    cursor.executemany("""
    INSERT OR IGNORE INTO standard_units (variable_name, target_unit, description)
    VALUES (?, ?, ?)
    """, initial_units)

    # 3. Add 'normalized_value' and 'normalized_unit' to observations if not exists
    # Check if column exists
    cursor.execute("PRAGMA table_info(observations)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'normalized_value' not in columns:
        print("   - Adding 'normalized_value' to observations...")
        cursor.execute("ALTER TABLE observations ADD COLUMN normalized_value REAL")
    
    if 'normalized_unit' not in columns:
        print("   - Adding 'normalized_unit' to observations...")
        cursor.execute("ALTER TABLE observations ADD COLUMN normalized_unit TEXT")

    conn.commit()
    conn.close()
    print("✅ Migration Complete.")

if __name__ == "__main__":
    migrate()
