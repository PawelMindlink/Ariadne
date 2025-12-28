import os
import sqlite3
import openpyxl
import json
import shutil
import sys
from datetime import datetime
import time

# Setup Paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX_DIR = os.path.join(ROOT_DIR, '00_Inbox')
DB_PATH = os.path.join(ROOT_DIR, '02_Database', 'ariadne.db')
APPS_DIR = os.path.join(ROOT_DIR, '03_Apps')
sys.path.append(APPS_DIR)

import ingest

def create_dummy_excel():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Variable', 'Value', 'Unit']) # Header
    ws.append(['Total Cholesterol', 180, 'mg/dL'])
    ws.append(['Vitamin D', 45, 'ng/mL'])
    file_path = os.path.join(INBOX_DIR, 'test_lab_results.xlsx')
    wb.save(file_path)
    return file_path

def create_dummy_xml():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Record type="HKQuantityTypeIdentifierStepCount" value="1000" unit="count" />
    <Record type="HKQuantityTypeIdentifierHeartRate" value="72" unit="bpm" />
</HealthData>
"""
    file_path = os.path.join(INBOX_DIR, 'test_export.xml')
    with open(file_path, 'w') as f:
        f.write(xml_content)
    return file_path

def verify_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check Excel Data
    c.execute("SELECT count(*) FROM observations WHERE variable_name='Total Cholesterol' AND value=180")
    excel_count = c.fetchone()[0]
    
    # Check XML Data
    c.execute("SELECT count(*) FROM observations WHERE variable_name='StepCount' AND value=1000")
    xml_count = c.fetchone()[0]
    
    conn.close()
    return excel_count, xml_count

def run_test():
    print("🧪 Starting Parser Test...")
    
    # 1. Clean Inbox
    if not os.path.exists(INBOX_DIR): os.makedirs(INBOX_DIR)
    
    # 2. Create Files
    excel_path = create_dummy_excel()
    xml_path = create_dummy_xml()
    print("✅ Created dummy files in Inbox.")
    
    # 3. Run Ingestion
    print("🚀 Running Ingestion...")
    ingest.run_ingestion()
    
    # 4. Verify
    print("🔍 Verifying Database...")
    excel_ok, xml_ok = verify_db()
    
    if excel_ok > 0 and xml_ok > 0:
        print("✅ SUCCESS: Both Excel and XML data found in DB.")
    else:
        print(f"❌ FAILURE: Excel Match={excel_ok}, XML Match={xml_ok}")
        
    # 5. Cleanup (Optional, maybe keep for user to see?)
    # os.remove(excel_path) # It moved to Archive anyway
    # os.remove(xml_path)

if __name__ == "__main__":
    run_test()
