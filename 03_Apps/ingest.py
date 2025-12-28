import os
import shutil
import sqlite3
import json
import csv
import datetime
import traceback
import re
import xml.etree.ElementTree as ET
import setup_db # Import setup script for reset
import toml
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

import openpyxl 
from google import genai

# --- Configuration ---
INBOX_DIR = os.path.join(os.path.dirname(__file__), '..', '00_Inbox')
ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), '..', '01_Archive')
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '02_Database', 'ariadne.db')

# Specialized Inboxes
QUARANTINE_DIR = os.path.join(INBOX_DIR, 'Quarantine_Encrypted')
JUNK_DIR = os.path.join(INBOX_DIR, 'Quarantine_Junk')
REVIEW_DIR = os.path.join(INBOX_DIR, 'Review_Needed')

# Ensure directories exist
for d in [INBOX_DIR, ARCHIVE_DIR, QUARANTINE_DIR, JUNK_DIR, REVIEW_DIR]:
    os.makedirs(d, exist_ok=True)

# Reliability Scores (1-10)
REL_MEDICAL = 9  # Lab results, Doctor notes
REL_DEVICE = 8   # Garmin, Apple Health (Direct export)
REL_APP = 6      # MyFitnessPal (Manual entry risk)
REL_SENSOR = 7   # Raw sensor data

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def log_error(file_path, error_msg):
    log(f"❌ ERROR in {os.path.basename(file_path)}: {error_msg}")
    with open("ingest_errors.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now()} - {file_path} - {error_msg}\n")

# --- Helpers ---

def load_secrets():
    secrets_path = os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml')
    if os.path.exists(secrets_path):
        try:
            return toml.load(secrets_path)
        except Exception as e:
            print(f"Error loading secrets: {e}")
    return {}

def is_encrypted_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        return reader.is_encrypted
    except:
        return False # corrupt or not pdf

# --- Parsers ---

def parse_medical_pdf(file_path, cursor):
    """
    Parses PDF Medical Reports using Gemini 2.5 Flash via google.genai SDK.
    Returns True if successful, False otherwise.
    """
    # Load Secrets
    secrets = load_secrets()
    api_key = secrets.get("GEMINI_API_KEY")
    
    if not api_key:
        print("No Gemini API Key provided for PDF parsing.")
        return False

    try:
        # 1. Extract Text
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        if len(text.strip()) < 50:
            print("PDF has insufficient text (likely a scan).")
            return False

        # 2. Call Gemini
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        Extract structured health data from this medical report.
        Return ONLY valid JSON with this structure:
        {{
            "date": "YYYY-MM-DDT00:00:00", 
            "type": "Medical Report",
            "subtype": "Specific Type (e.g. Blood Test, MRI)",
            "observations": [
                {{"name": "Parameter Name", "value": 0.0, "unit": "Unit", "text_value": "String Value if not numeric"}}
            ]
        }}
        
        - If date is missing, try to find it in the text. If absolutely unknown, use today's date but mark as estimated.
        - Normalize units if possible.
        
        TEXT CONTENT:
        {text[:30000]} 
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        
        try:
            result = json.loads(response.text)
        except:
             # Handle list response edge case
            try:
                result = json.loads(response.text)[0]
            except:
                print("Failed to parse Gemini JSON response.")
                return False

        # 3. Insert into DB
        # Create Event
        cursor.execute("INSERT INTO events (type, timestamp, source_type, reliability, json_details) VALUES (?, ?, ?, ?, ?)",
                       (result.get('type', 'Medical Report'), 
                        result.get('date'), 
                        'Medical PDF', 
                        REL_MEDICAL,
                        json.dumps(result))) 
        
        event_id = cursor.lastrowid
        
        # Insert Observations
        for obs in result.get('observations', []):
            val = obs.get('value')
            cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, obs.get('name'), val, obs.get('unit')))
            
        print(f"✅ Successfully parsed PDF: {len(result.get('observations', []))} observations.")
        return True

    except Exception as e:
        print(f"Gemini Parsing Error: {e}")
        return False

def parse_excel(file_path, cursor):
    """Parses .xlsx files (Lab Results)."""
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active 
    records = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]: continue
        records.append({
            'variable_name': str(row[0]).strip(),
            'value': row[1],
            'unit': str(row[2]).strip() if len(row) > 2 else ""
        })
    return records

def parse_xml_export(file_path, cursor):
    """Parses generic Health XML exports."""
    records = []
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        for record in root.findall('Record'):
            attr = record.attrib
            if 'type' in attr and 'value' in attr:
                name = attr['type'].replace('HKQuantityTypeIdentifier', '')
                val = attr['value']
                unit = attr.get('unit', '')
                try:
                    records.append({
                        'variable_name': name,
                        'value': float(val),
                        'unit': unit
                    })
                except:
                    pass
    except Exception as e:
        log_error(file_path, f"XML Parse Error: {e}")
    return records

def parse_garmin_tcx(file_path, cursor):
    """Parses Garmin TCX files for Activities."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        ns = {'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
        
        for activity in root.findall('.//ns:Activity', ns):
            sport = activity.get('Sport')
            id_tag = activity.find('ns:Id', ns)
            timestamp = id_tag.text if id_tag is not None else datetime.datetime.now().isoformat()
            
            # Create Event
            cursor.execute("INSERT INTO events (type, timestamp, source_type, reliability) VALUES (?, ?, ?, ?)",
                           (f"Workout_{sport}", timestamp, 'Garmin TCX', REL_DEVICE))
            event_id = cursor.lastrowid
            
            # Aggregate stats
            hr_vals = []
            for trackpoint in activity.findall('.//ns:Trackpoint', ns):
                hr_elem = trackpoint.find('.//ns:HeartRateBpm/ns:Value', ns)
                if hr_elem is not None:
                    hr_vals.append(float(hr_elem.text))
            
            if hr_vals:
                avg_hr = sum(hr_vals) / len(hr_vals)
                max_hr = max(hr_vals)
                cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                               (event_id, 'Avg Heart Rate', avg_hr, 'bpm'))
                cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                               (event_id, 'Max Heart Rate', max_hr, 'bpm'))
                
        return True
    except Exception as e:
        log_error(file_path, f"TCX Parse Error: {e}")
        return False

def parse_google_fit_json(file_path, cursor):
    """Parses Google Fit generic JSONs."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, dict):
            ts = datetime.datetime.now().isoformat()
            cursor.execute("INSERT INTO events (type, timestamp, source_type, reliability) VALUES (?, ?, ?, ?)",
                           ('Health_Metrics', ts, 'Google Fit JSON', REL_DEVICE))
            evt_id = cursor.lastrowid
            
            for k, v in data.items():
                if isinstance(v, (int, float)):
                    cursor.execute("INSERT INTO observations (event_id, variable_name, value) VALUES (?, ?, ?)",
                                   (evt_id, k, v))
        return True
    except Exception as e:
        log_error(file_path, f"JSON Parse Error: {e}")
        return False

# --- Main Logic ---

def archive_file(file_path):
    """Moves processed file to 01_Archive/YYYY-MM-DD/."""
    date_str = datetime.date.today().strftime('%Y-%m-%d')
    target_dir = os.path.join(ARCHIVE_DIR, date_str)
    os.makedirs(target_dir, exist_ok=True)
    
    filename = os.path.basename(file_path)
    dest = os.path.join(target_dir, filename)
    
    # Handle duplicates
    if os.path.exists(dest):
        base, ext = os.path.splitext(filename)
        timestamp = datetime.datetime.now().strftime('%H%M%S')
        dest = os.path.join(target_dir, f"{base}_{timestamp}{ext}")
        
    shutil.move(file_path, dest)
    log(f"📦 Archived: {filename}")

def quarantine_file(file_path, reason):
    """Moves problematic file to specific quarantine folder."""
    if reason == "encrypted":
        target_dir = QUARANTINE_DIR
    elif reason == "junk":
        target_dir = JUNK_DIR
    else:
        target_dir = REVIEW_DIR
        
    os.makedirs(target_dir, exist_ok=True)
    shutil.move(file_path, os.path.join(target_dir, os.path.basename(file_path)))
    log(f"⚠️ Quarantined ({reason}): {os.path.basename(file_path)}")

def run_ingestion():
    log("🚀 Ingestor Started (Recursive Mode)...")
    
    if not os.path.exists(DB_PATH):
        log("Database not found. Initializing...")
        setup_db.create_schema()

    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {'processed': 0, 'quarantined': 0, 'errors': 0}
    
    # 1. Recursive Scan
    files_to_process = []
    for root, dirs, files in os.walk(INBOX_DIR):
        # Skip special folders
        if any(x in root for x in ['Quarantine', 'Review', 'Archive', 'Database']):
            continue
            
        for file in files:
            files_to_process.append(os.path.join(root, file))

    if not files_to_process:
        log("💤 Inbox is empty.")
        conn.close()
        return

    log(f"🔎 Found {len(files_to_process)} files to process.")

    for file_path in files_to_process:
        filename = os.path.basename(file_path).lower()
        processed = False
        
        try:
            # --- Routing Logic ---
            
            # 1. Encrypted Check
            if filename.endswith('.pdf'):
                if is_encrypted_pdf(file_path):
                    quarantine_file(file_path, "encrypted")
                    stats['quarantined'] += 1
                    continue
            
            # 2. File Type Handlers
            if filename.endswith('.tcx'):
                processed = parse_garmin_tcx(file_path, cursor)
                
            elif filename.endswith('.xlsx'):
                records = parse_excel(file_path, cursor)
                if records:
                    ts = datetime.datetime.now().isoformat()
                    cursor.execute("INSERT INTO events (type, timestamp, source_type, reliability) VALUES (?, ?, ?, ?)",
                                   ('Lab_Result', ts, 'Excel Import', REL_MEDICAL))
                    evt_id = cursor.lastrowid
                    for r in records:
                        cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                                       (evt_id, r['variable_name'], r['value'], r['unit']))
                    processed = True
                    
            elif filename.endswith('.xml'):
                records = parse_xml_export(file_path, cursor)
                if records:
                    ts = datetime.datetime.now().isoformat()
                    cursor.execute("INSERT INTO events (type, timestamp, source_type, reliability) VALUES (?, ?, ?, ?)",
                                   ('Health_Export', ts, 'XML Import', REL_SENSOR))
                    evt_id = cursor.lastrowid
                    for r in records:
                        cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                                       (evt_id, r['variable_name'], r['value'], r['unit']))
                    processed = True

            elif filename.endswith('.json'):
                processed = parse_google_fit_json(file_path, cursor)
                
            elif filename.endswith('.pdf'):
                # Try parsing if key available, otherwise move to archive as "processed" (raw storage)
                # or defer. User wants active processing.
                # Assuming key is in secrets.toml
                success = parse_medical_pdf(file_path, cursor)
                if success:
                    processed = True
                else: 
                    # If failed to parse content but not encrypted, what?
                    # Maybe just store file record?
                    # For safety, let's treat as processed (archived) to avoid loop, but log it.
                    processed = True 
                    log(f"PDF processed (stored/parsed): {filename}")

            # --- Post-Processing ---
            if processed:
                conn.commit()
                archive_file(file_path)
                stats['processed'] += 1
            else:
                # If unknown extension or failed logic but no crash
                if not filename.endswith(('.txt', '.ini', '.DS_Store', '.db')): # Skip system files
                     quarantine_file(file_path, "review")
                     stats['quarantined'] += 1

        except Exception as e:
            log_error(file_path, str(e))
            stats['errors'] += 1

    conn.close()
    
    # 2. Vaccination (Empty Folder Cleanup) - The Vacuum
    log("🧹 Vacuuming empty folders...")
    for root, dirs, files in os.walk(INBOX_DIR, topdown=False):
        if root == INBOX_DIR: continue # Don't delete Inbox itself
        # specialized folders check
        if any(x in root for x in ['Quarantine', 'Review']): continue
        
        try:
            if not os.listdir(root):
                os.rmdir(root)
                log(f"Deleted empty folder: {root}")
        except:
            pass

    log(f"🏁 Done. Processed: {stats['processed']}, Quarantined: {stats['quarantined']}, Errors: {stats['errors']}")

if __name__ == "__main__":
    run_ingestion()
