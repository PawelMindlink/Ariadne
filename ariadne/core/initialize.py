from ariadne.core.database import db
import os
import sqlite3

def init_db():
    conn = db.get_connection()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema_v2.sql')
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    print(f"Initializing Database at {db.db_path}...")
    try:
        conn.executescript(schema_sql)
        print("✅ Database Schema V2 applied successfully.")
        
        # Verify tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables found: {tables}")
        
    except sqlite3.Error as e:
        print(f"❌ Database initialization failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
