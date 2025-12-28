import os
import sqlite3
import pandas as pd
from collections import defaultdict

# Config
ROOT_DIR = r'c:\Users\Paweł\Documents\GitHub\Ariadne'
INBOX = os.path.join(ROOT_DIR, '00_Inbox')
ARCHIVE = os.path.join(ROOT_DIR, '01_Archive')
DB_PATH = os.path.join(ROOT_DIR, '02_Database', 'health_data.db')

def analyze_directory(path):
    stats = {
        'total': 0,
        'by_ext': defaultdict(int),
        'locked_pdf': 0,
        'empty_dirs': [],
        'files': []
    }
    
    for root, dirs, files in os.walk(path):
        if not files and not dirs:
            stats['empty_dirs'].append(root)
            
        for f in files:
            stats['total'] += 1
            ext = os.path.splitext(f)[1].lower()
            stats['by_ext'][ext] += 1
            stats['files'].append(f)
            
            # Check for locked PDF
            if ext == '.pdf':
                full_path = os.path.join(root, f)
                try:
                    with open(full_path, 'rb') as pdf_file:
                        # Very naive check for encryption dictionary
                        if b'/Encrypt' in pdf_file.read(1024): 
                            stats['locked_pdf'] += 1
                except:
                    pass
    return stats

def analyze_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        # Count distinct filenames
        db_files = set(row[0] for row in conn.execute("SELECT filename FROM files").fetchall())
        db_events = conn.execute("SELECT count(*) FROM events").fetchone()[0]
        conn.close()
        return db_files, db_events
    except:
        return set(), 0

def main():
    print("🔎 STARTING FORENSIC FILE INVENTORY...")
    
    # 1. File System Analysis
    inbox_stats = analyze_directory(INBOX)
    archive_stats = analyze_directory(ARCHIVE)
    
    # 2. Database Analysis
    db_img_files, total_events = analyze_db()
    
    # 3. Correlation
    all_fs_files = set(inbox_stats['files'] + archive_stats['files'])
    
    # Intersection
    ingested_count = len(db_img_files.intersection(all_fs_files))
    
    # 4. Report
    report = f"""
# Forensic File Report

## 1. Storage Status
*   Inbox Total: {inbox_stats['total']}
    *   Locked PDFs: {inbox_stats['locked_pdf']}
    *   Extensions: {dict(inbox_stats['by_ext'])}
*   Archive Total: {archive_stats['total']}
    *   Extensions: {dict(archive_stats['by_ext'])}

## 2. Database Integrity
*   Total Events Indexed: {total_events}
*   Files Tracked in DB: {len(db_img_files)}
*   Ingestion Coverage: ~{ingested_count} files found in FS match DB records.

## 3. Cleanup Opportunities
*   Empty Directories: {len(inbox_stats['empty_dirs']) + len(archive_stats['empty_dirs'])}
*   Junk Candidates:
    *   Zips (Archive): {archive_stats['by_ext'].get('.zip', 0)}
"""
    
    # Write to file with explicit encoding
    with open('inventory_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
        if inbox_stats['empty_dirs']:
             f.write("\n\nEmpty Inbox Dirs:\n")
             for d in inbox_stats['empty_dirs']:
                 f.write(f"- {d}\n")

    print("✅ Report written to inventory_report.txt")

if __name__ == "__main__":
    main()
