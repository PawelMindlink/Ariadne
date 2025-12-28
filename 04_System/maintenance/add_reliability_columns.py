import sqlite3
import os

DB_PATH = r'c:\Users\Paweł\Documents\GitHub\Ariadne\02_Database\health_data.db'

def migrate():
    print("Migration started...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Add source_type
        try:
            cursor.execute("ALTER TABLE events ADD COLUMN source_type TEXT DEFAULT 'Unknown'")
            print("✅ Added 'source_type' column.")
        except sqlite3.OperationalError as e:
            if 'duplicate column' in str(e):
                print("ℹ️ 'source_type' column already exists.")
            else:
                raise e

        # 2. Add reliability
        try:
            cursor.execute("ALTER TABLE events ADD COLUMN reliability INTEGER DEFAULT 5")
            print("✅ Added 'reliability' column.")
        except sqlite3.OperationalError as e:
            if 'duplicate column' in str(e):
                print("ℹ️ 'reliability' column already exists.")
            else:
                raise e
        
        conn.commit()
        print("🚀 Migration complete.")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
