import sqlite3
import pandas as pd
import os

db_path = r'c:\Users\Paweł\Documents\GitHub\Ariadne\02_Database\health_data.db'
if not os.path.exists(db_path):
    print("DB not found!")
    exit()

conn = sqlite3.connect(db_path)
try:
    df = pd.read_sql("SELECT DISTINCT type FROM events", conn)
    print("ALL TYPES:")
    print(df['type'].tolist())
    
    df_files = pd.read_sql("SELECT DISTINCT filename FROM files", conn)
    print("\nFILES:")
    print(df_files['filename'].tolist()[:10]) # Show first 10
finally:
    conn.close()
