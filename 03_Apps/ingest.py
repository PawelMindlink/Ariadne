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

# ...

# --- Parsers ---

def parse_excel(file_path, cursor):
    """Parses .xlsx files (Lab Results)."""
    # Assuming standard format: 'Variable', 'Value', 'Unit', 'Date' columns
    # Or just iterating rows.
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active # Assume first sheet
    
    # Simple extraction strategy: Treat rows as Variable | Value | Unit
    # Skip header
    records = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]: continue
        
        # Heuristic: [0]=Name, [1]=Value, [2]=Unit, [3]=Date(optional)
        variable = str(row[0]).strip()
        value = str(row[1]).strip()
        unit = str(row[2]).strip() if len(row) > 2 else ""
        
        try:
             # Try parse value
             val_num = float(value)
        except:
             val_num = None # Keep as text logic later or skip? For now assume numeric.
             
        # Create Observation
        # But we need an EVENT first. One event per File? Or one event per Row?
        # Better: One Event for the File "Lab Report"
        records.append({
            'variable_name': variable,
            'value': val_num if val_num is not None else value, # flexible
            'unit': unit
        })
    return records 

def parse_xml_export(file_path, cursor):
    """Parses raw .xml exports (Apple Health / Custom)."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    records = []
    # Apple Health style <Record type="HKQuantityTypeIdentifierHeartRate" value="60" ... />
    for child in root:
        if child.tag == 'Record':
            rec_type = child.get('type', 'Unknown')
            val = child.get('value', '0')
            unit = child.get('unit', '')
            
            # Simplified map
            name = rec_type.replace("HKQuantityTypeIdentifier", "")
            try:
                records.append({
                    'variable_name': name,
                    'value': float(val),
                    'unit': unit
                })
            except:
                pass
    return records


# --- Configuration ---
INBOX_DIR = os.path.join(os.path.dirname(__file__), '..', '00_Inbox')
ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), '..', '01_Archive')
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '02_Database', 'health_data.db')
ERRORS_DIR = os.path.join(INBOX_DIR, 'Errors')

# Ensure directories exist
os.makedirs(ERRORS_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)
LOCKED_DIR = os.path.join(INBOX_DIR, 'Locked')
os.makedirs(LOCKED_DIR, exist_ok=True)
JUNK_DIR = os.path.join(INBOX_DIR, 'Junk')
os.makedirs(JUNK_DIR, exist_ok=True)

# --- Reliability Constants ---
REL_MEDICAL = 10
REL_SENSOR = 8
REL_APP = 7
REL_MANUAL = 5

def is_pdf_encrypted(file_path):
    try:
        reader = PdfReader(file_path)
        return reader.is_encrypted
    except Exception:
        return False

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def reset_database():
    """Wipes and recreates the database."""
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("🗑️ Database deleted.")
        except Exception as e:
            print(f"Error deleting DB: {e}")
            return False
    
    try:
        setup_db.create_schema()
        print("🆕 Database initialized.")
        return True
    except Exception as e:
        print(f"Error initializing DB: {e}")
        return False

def log_error(file_path, error_msg):
    print(f"❌ ERROR processing {file_path}: {error_msg}")
    # Move to error folder
    try:
        shutil.move(file_path, os.path.join(ERRORS_DIR, os.path.basename(file_path)))
        with open(os.path.join(ERRORS_DIR, f"{os.path.basename(file_path)}.log"), "w") as f:
            f.write(error_msg)
    except Exception as e:
        print(f"  Critical: Could not move file to Errors: {e}")

def archive_file(file_path):
    print(f"✅ Archived: {os.path.basename(file_path)}")
    try:
        # Flatten structure for archive simplicity or keep it? 
        # For now, let's just move the file to root of Archive with a timestamp prefix to avoid collisions
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{timestamp}_{os.path.basename(file_path)}"
        shutil.move(file_path, os.path.join(ARCHIVE_DIR, new_name))
    except Exception as e:
        print(f"  Warning: Could not archive file: {e}")

# --- Parsers ---

def parse_garmin_sleep(file_path, cursor):
    """Parses Garmin sleepData.json"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Garmin often wraps list in a list or just a list
    if isinstance(data, list):
        sleep_records = data
    else:
        # Fallback if structure is different
        sleep_records = [data]

    for record in sleep_records:
        if not isinstance(record, dict): continue
        if 'sleepStartTimestampGMT' not in record: continue

        # 1. Create Event
        # Timestamp format: 2025-08-20T21:34:39.0
        ts_str = record.get('sleepStartTimestampGMT')
        # Simple fix for potential missing milliseconds if needed
        
        cursor.execute("INSERT INTO events (timestamp, type, source_id, json_details, source_type, reliability) VALUES (?, ?, ?, ?, ?, ?)",
                       (ts_str, 'Sleep', 1, json.dumps(record), 'Garmin', REL_SENSOR)) # Assuming Source ID 1 is Garmin
        event_id = cursor.lastrowid

        # 2. Extract Observations
        # Duration
        if 'deepSleepSeconds' in record:
            cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Deep Sleep', record['deepSleepSeconds'], 'seconds'))
        if 'lightSleepSeconds' in record:
            cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Light Sleep', record['lightSleepSeconds'], 'seconds'))
        if 'remSleepSeconds' in record:
            cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'REM Sleep', record['remSleepSeconds'], 'seconds'))
        
        # Scores
        scores = record.get('sleepScores', {})
        if 'overallScore' in scores:
             cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Sleep Score', scores['overallScore'], 'score'))
        
        # SPO2
        spo2 = record.get('spo2SleepSummary', {})
        if 'averageSPO2' in spo2:
             cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Avg Sleep SPO2', spo2['averageSPO2'], 'percent'))


def parse_google_fit_daily(file_path, cursor):
    """Parses Google Fit 'Daily activity metrics' CSV"""
    filename = os.path.basename(file_path)
    # Filename format examples: 
    # - 2023-12-31.csv
    # - 20251221_190047_2015-03-24.csv
    
    # Regex to find YYYY-MM-DD
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if match:
        file_date = match.group(1)
    else:
        file_date = None

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            start_time = row.get('Start time')
            if not start_time: continue
            
            # Combine Date + Time
            if file_date:
                # Assuming start_time is like "00:00" or "00:00:00"
                full_ts = f"{file_date}T{start_time}"
            else:
                full_ts = start_time

            # We create an event for this window
            cursor.execute("INSERT INTO events (timestamp, type, source_id, json_details, source_type, reliability) VALUES (?, ?, ?, ?, ?, ?)",
                       (full_ts, 'Activity_Window', 2, json.dumps(row), 'Google Fit', REL_APP)) # Assuming Source ID 2 is Google Fit
            event_id = cursor.lastrowid

            # 2. Extract Observations
            # Steps
            steps = row.get('Step count')
            if steps:
                cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Steps', float(steps), 'count'))
            
            # Calories
            cals = row.get('Calories (kcal)')
            if cals:
                cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Calories', float(cals), 'kcal'))
            
            # Heart Rate
            avg_hr = row.get('Average heart rate (bpm)') # Assuming this is the correct key
            if avg_hr:
                cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Heart Rate (Avg)', float(avg_hr), 'bpm'))

def parse_google_fit_json(file_path, cursor):
    """Parses Google Fit single activity JSON files"""
    filename = os.path.basename(file_path)
    
    # Filename example: 2018-06-11T21_04_29+02_00_MARTIAL_ARTS.json
    # We can try to extract Activity Type from filename if it's not in the JSON, 
    # but let's see if we can parse the JSON first.
    
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding JSON: {filename}")
            return

    # Check if it's a sleep file (handled elsewhere? or maybe unify)
    # The user says these are activities like MMA.
    
    # 1. Determine Timestamp
    # If filename has timestamp, use it.
    # regex for ISO ish timestamp in filename
    ts_match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2})", filename)
    timestamp = None
    if ts_match:
        timestamp = ts_match.group(1).replace('_', ':')
    
    # 2. Determine Type
    # Extract from filename suffix (e.g., _MARTIAL_ARTS.json)
    activity_type = 'Activity_Unknown'
    type_match = re.search(r"\d{2}_\d{2}_\d{2}[+\-]\d{2}_\d{2}_(.*)\.json", filename)
    if type_match:
        raw_type = type_match.group(1)
        # Clean up type (e.g. MARTIAL_ARTS -> Martial Arts)
        activity_type = f"Activity_{raw_type.replace('_', ' ').title()}"
    
    # 3. Insert Event
    if timestamp:
         cursor.execute("INSERT INTO events (timestamp, type, source_id, json_details, source_type, reliability) VALUES (?, ?, ?, ?, ?, ?)",
                       (timestamp, activity_type, 2, json.dumps(data), 'Google Fit', REL_APP))
         event_id = cursor.lastrowid
         
         # 4. Extract Observations (Data seems flat or simple in these JSONs?)
         # We need to see strict structure. For now, dump everything as JSON details 
         # and maybe extract strict fields if known keys exist.
         
         # Example keys based on previous experience with Google Fit JSONs:
         # 'distanceMeters', 'calories(kcal)', 'stepDetail'
         
         if isinstance(data, dict):
             if 'calories(kcal)' in data:
                  cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Calories', float(data['calories(kcal)']), 'kcal'))
             if 'distanceMeters' in data:
                  cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Distance', float(data['distanceMeters']), 'm'))
             if 'averageHeartRateBpm' in data:
                   cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Heart Rate (Avg)', float(data['averageHeartRateBpm']), 'bpm'))


def parse_garmin_summarized(file_path, cursor):
    """Parses Garmin 'summarizedActivities' JSON export"""
    filename = os.path.basename(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            # The file structure is a List of Objects, each containing "summarizedActivitiesExport" list
            # Or just a list of objects?
            # Based on view_file: [ { "summarizedActivitiesExport": [ ... ] } ]
            root_data = json.load(f)
        except json.JSONDecodeError:
            log_error(file_path, "JSON Decode Error")
            return

    if not isinstance(root_data, list): root_data = [root_data]

    count = 0
    for block in root_data:
        activities = block.get('summarizedActivitiesExport', [])
        for act in activities:
            # 1. Timestamp
            # beginTimestamp is in MS
            ts_ms = act.get('beginTimestamp')
            if not ts_ms: continue
            
            # Convert to ISO format (YYYY-MM-DDTHH:MM:SS)
            try:
                import datetime
                dt = datetime.datetime.fromtimestamp(ts_ms / 1000.0)
                timestamp = dt.isoformat()
            except Exception:
                timestamp = str(ts_ms) # Fallback

            # 2. Type
            # activityType: "pilates", "lap_swimming", "walking"
            raw_type = act.get('activityType', 'unknown')
            event_type = f"Activity_{raw_type.replace('_', ' ').title()}"
            
            # 3. Insert Event
            # Store full JSON for detail
            cursor.execute("INSERT INTO events (timestamp, type, source_id, json_details, source_type, reliability) VALUES (?, ?, ?, ?, ?, ?)",
                           (timestamp, event_type, 1, json.dumps(act), 'Garmin', REL_SENSOR))
            event_id = cursor.lastrowid
            
            # 4. Observations
            # Calories
            if 'calories' in act:
                 cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Calories', float(act['calories']), 'kcal'))
            
            # Duration (ms -> min?)
            if 'duration' in act:
                 # duration is usually ms in these files based on 'duration': 752984.98
                 dur_min = float(act['duration']) / 60000.0
                 cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Duration', dur_min, 'minutes'))
            
            # Heart Rate
            if 'avgHr' in act:
                 cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Heart Rate (Avg)', float(act['avgHr']), 'bpm'))
            if 'maxHr' in act:
                 cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Heart Rate (Max)', float(act['maxHr']), 'bpm'))
            
            # Steps
            if 'steps' in act:
                 cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Steps', float(act['steps']), 'count'))
            
            # Distance
            if 'distance' in act:
                 # distance usually cm or meters? 
                 # sample: "distance": 0.0 for pilates (makes sense)
                 # sample: "distance": 188734.99 for walking (looks like cm? 188km is too much, 1887 meters is short for 27 mins? No duration is 1680328ms = 28 mins)
                 # Wait, 1680328 ms = 1680 sec = 28 mins.
                 # Walking speed 5km/h => ~2.3km in 28 mins.
                 # 188734.99 could be cm? 188734 cm = 1.8km. Matches.
                 # Let's assume cm and convert to meters.
                 dist_m = float(act['distance']) / 100.0
                 cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Distance', dist_m, 'm'))
            
            count += 1
            
    print(f"Parsed {count} summarized activities from {filename}")

def parse_garmin_tcx(file_path, cursor):
    """Parses Garmin TCX Activity files (XML)"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # TCX files usually have a namespace: {http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}
    # We can handle this by treating tag names carefully or using namespace map.
    # Simple strategy: ignore namespace in tag matching or use wildcard.
    
    # Helper to strip namespace
    def clean_tag(tag):
        return tag.split('}', 1)[1] if '}' in tag else tag

    # Iterate over Activities
    # Structure: TrainingCenterDatabase -> Activities -> Activity
    
    activities_node = None
    for child in root:
        if clean_tag(child.tag) == 'Activities':
            activities_node = child
            break
            
    if not activities_node: return

    for activity in activities_node:
        if clean_tag(activity.tag) != 'Activity': continue
        
        sport = activity.attrib.get('Sport', 'Exercise')
        id_node = None
        
        # Find Id (Timestamp)
        for child in activity:
            if clean_tag(child.tag) == 'Id':
                id_node = child.text
                break
        
        if not id_node: continue
        timestamp = id_node
        
        # Create Event
        cursor.execute("INSERT INTO events (timestamp, type, source_id, json_details, source_type, reliability) VALUES (?, ?, ?, ?, ?, ?)",
                       (timestamp, f'Activity_{sport}', 1, json.dumps({'origin': 'tcx'}), 'Garmin', REL_SENSOR))
        event_id = cursor.lastrowid
        
        # Parse Laps for summary data
        # We will aggregate Laps if multiple, or just take the first. simpler to summarize.
        total_seconds = 0.0
        total_calories = 0.0
        hr_sum = 0
        hr_count = 0
        max_hr = 0
        
        for child in activity:
            if clean_tag(child.tag) == 'Lap':
                for lap_data in child:
                    tag = clean_tag(lap_data.tag)
                    if tag == 'TotalTimeSeconds':
                        total_seconds += float(lap_data.text)
                    elif tag == 'Calories':
                        total_calories += float(lap_data.text)
                    elif tag == 'AverageHeartRateBpm':
                        # Value is inside <Value> tag
                        val = lap_data.find(".//{*}Value") # Namespace wildcard
                        if val is None: val = lap_data.find("Value") # Try w/o namespace
                        if val is not None:
                            hr = float(val.text)
                            hr_sum += hr
                            hr_count += 1
                    elif tag == 'MaximumHeartRateBpm':
                        val = lap_data.find(".//{*}Value")
                        if val is None: val = lap_data.find("Value")
                        if val is not None:
                            max_hr = max(max_hr, float(val.text))

        # Insert Observations
        if total_seconds > 0:
            cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Duration', total_seconds, 'seconds'))
        if total_calories > 0:
            cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Calories', total_calories, 'kcal'))
        if hr_count > 0:
            avg_hr = hr_sum / hr_count
            cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Heart Rate (Avg)', avg_hr, 'bpm'))
        if max_hr > 0:
            cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, 'Heart Rate (Max)', max_hr, 'bpm'))



def load_secrets():
    """Load secrets from .streamlit/secrets.toml"""
    secrets_path = os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml')
    if os.path.exists(secrets_path):
        try:
            return toml.load(secrets_path)
        except Exception as e:
            print(f"Error loading secrets: {e}")
    return {}

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
        # Truncate text to fit context if massive, though Flash 2.5 has 1M context.

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
                import ast
                # sometimes it returns a list representation text
                # clean backticks
                clean = response.text.replace('```json', '').replace('```', '').strip()
                if clean.startswith('['):
                     result = json.loads(clean)[0]
                else:
                     result = json.loads(clean)
            except:
                print(f"Gemini Parsing Error: {response.text[:100]}")
                return False

        # 3. Insert into DB
        # Date Handling
        event_ts = result.get("date", datetime.datetime.now().isoformat())
        event_type = f"Report_{result.get('subtype', 'General')}"
        
        # Insert Event (Schema: id, timestamp, type, source_id, file_id, json_details)
        # Note: file_id is not passed here, we might need it? 
        # Actually parse_garmin_tcx inserts into events?
        # Let's check how other parsers do it. 
        # Most parsers in this file seem to work with a cursor that might not have file_id set?
        # Wait, the schema showed file_id. 
        # Let's just insert into (source_id, type, timestamp, json_details) 
        # and let file_id be null or handled if the schema allows text columns or default.
        
        # Serializing the whole data as json_details
        json_details = json.dumps(result)
        
        cursor.execute("INSERT INTO events (source_id, type, timestamp, json_details, source_type, reliability) VALUES (?, ?, ?, ?, ?, ?)",
                       (3, event_type, event_ts, json_details, 'Medical Report', REL_MEDICAL))
        event_id = cursor.lastrowid
        
        # Insert Observations
        for obs in result.get("observations", []):
            val = obs.get("value")
            text_val = obs.get("text_value")
            
            # Prefer numeric, fallback to text if 0/None and text exists
            final_val = val if val else (0 if not text_val else 0) 
            final_unit = obs.get("unit", "")
            name = obs.get("name", "Unknown")
            
            # If we have a text value and numeric is 0, we might want to store it differently
            # For now, let's just log numeric values if possible, or append text to name?
            # Creating a robust schema is hard, let's stick to the current observations table (value is REAL?)
            # Validating schema... observations(value) is likely REAL/NUMERIC.
            
            cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                           (event_id, name, final_val, final_unit))
            
        print(f"✅ Parsed PDF: {event_type} with {len(result.get('observations', []))} metrics.")
        return True

    except Exception as e:
        print(f"Gemini Parsing Error: {str(e)}")
        return False


# --- Main Loop ---

def run_ingestion():
    # Return a log list and stats to display in UI
    logs = []
    def log(msg):
        print(msg)
        logs.append(msg)

    log("🚀 Ingestor Started...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Pre-populate Sources if empty
    try:
        cursor.execute("SELECT count(*) FROM sources")
        if cursor.fetchone()[0] == 0:
            log("initializing Sources...")
            cursor.execute("INSERT INTO sources (id, name, type, trust_score) VALUES (1, 'Garmin', 'Wearable', 9)")
            cursor.execute("INSERT INTO sources (id, name, type, trust_score) VALUES (2, 'Google Fit', 'App', 7)")
            conn.commit()
    except sqlite3.OperationalError:
        # Table might not exist if DB was manually deleted/corrupted. Auto-recover.
        log("⚠️ Tables missing. Re-initializing schema...")
        setup_db.create_schema()
        # Retry source insert
        cursor.execute("INSERT OR IGNORE INTO sources (id, name, type, trust_score) VALUES (1, 'Garmin', 'Wearable', 9)")
        cursor.execute("INSERT OR IGNORE INTO sources (id, name, type, trust_score) VALUES (2, 'Google Fit', 'App', 7)")
        conn.commit()
    except Exception as e:
        log(f"Error checking sources: {e}")



    # --- Statistics for User Insights ---
    stats = {
        'processed_files': 0,
        'unprocessed_files': 0,
        'archived_files': 0,
        'deleted_zips': 0,
        'errors': 0
    }

    
    log("🔎 Scanning Inbox...")
    
    # Move Unprocessed to Archive to keep Inbox clean
    UNPROCESSED_DIR = os.path.join(ARCHIVE_DIR, 'Unprocessed')
    os.makedirs(UNPROCESSED_DIR, exist_ok=True)
    
    all_files = []
    for root, dirs, files in os.walk(INBOX_DIR):
        # Skip special folders inside Inbox if any (currently only Errors should stay)
        if 'Errors' in root: continue
            
        for file in files:
            all_files.append(os.path.join(root, file))

    log(f"found {len(all_files)} files to process.")

    log(f"found {len(all_files)} files to process.")

    from ingest import is_pdf_encrypted, LOCKED_DIR, JUNK_DIR # explicit import for scope if needed, or rely on global

    for file_path in all_files:
        filename = os.path.basename(file_path)
        
        # --- 1. Junk Filter ---
        if os.path.getsize(file_path) == 0:
            log(f"🗑️ Junk (Empty): {filename}")
            shutil.move(file_path, os.path.join(JUNK_DIR, filename))
            stats['deleted_zips'] += 1 # reusing counter or add new
            continue
            
        if filename.startswith('.'): # system files
             continue

        # --- 2. Quarantine (Locked) ---
        if filename.lower().endswith('.pdf') and is_pdf_encrypted(file_path):
            log(f"🔒 Locked PDF detected: {filename} -> Moving to Quarantine.")
            shutil.move(file_path, os.path.join(LOCKED_DIR, filename))
            stats['unprocessed_files'] += 1
            continue

    # --- BATCH PROCESSING VARS ---
    BATCH_SIZE = 5
    files_in_batch = 0

    for file_path in all_files:
        if not os.path.exists(file_path): continue # handled already
        
        filename = os.path.basename(file_path).lower()
        
        # 1. DELETE ZIPS (User instruction: they are already unzipped)
        if filename.endswith('.zip'):
            try:
                os.remove(file_path)
                log(f"🗑️ Deleted Zip: {filename}")
                stats['deleted_zips'] += 1
            except Exception as e:
                log_error(file_path, f"Could not delete zip: {e}")
            continue

        # Skip system files
        if filename == 'desktop.ini' or filename.startswith('.'): continue

        try:
            processed = False
            
            # --- ROUTING LOGIC ---
            if filename.endswith('sleepdata.json'):
                log(f"Processing Garmin Sleep: {filename}")
                parse_garmin_sleep(file_path, cursor)
                processed = True
                stats['processed_files'] += 1
            
            elif 'daily activity metrics' in file_path.lower() and filename.endswith('.csv'):
                log(f"Processing Google Fit Daily: {filename}")
                parse_google_fit_daily(file_path, cursor)
                processed = True
                stats['processed_files'] += 1
            
            elif 'summarizedActivities' in filename and filename.endswith('.json'):
                log(f"Processing Garmin Summarized Activities: {filename}")
                parse_garmin_summarized(file_path, cursor)
                processed = True
                stats['processed_files'] += 1


            elif filename.endswith('.json'):
                 # Generic fallback for single activity JSONs from Google Fit (if verified)
                 # Reverting the previous strict block to be safer
                 if 'daily activity metrics' not in file_path.lower():
                     parse_google_fit_json(file_path, cursor)
                     processed = True
                     stats['processed_files'] += 1

            elif filename.endswith('.tcx'):
                log(f"Processing Garmin TCX: {filename}")
                parse_garmin_tcx(file_path, cursor)
                processed = True
                stats['processed_files'] += 1

            elif filename.endswith('.xlsx'):
                log(f"Processing Excel Lab Report: {filename}")
                # Create an event first? 
                # For now, let's inject a generic event wrapper inside parse_excel OR handle it here.
                # The helper function assumes 'cursor' is passed and handles inserts?
                # Looking at parse_excel... it returns 'records' list! It DOES NOT insert.
                # Pivot: I need to handle insertion here or update parse_excel to insert.
                # Actually, parse_garmin_tcx DOES insert. parse_medical_pdf DOES insert.
                # But my new functions return a list.
                # REVISION: I will update the routing to iterate the returned list and insert.
                
                records = parse_excel(file_path, cursor)
                if records:
                    # Create generic event
                    ts = datetime.datetime.now().isoformat()
                    # Check if date is in records? (Advanced)
                    
                    cursor.execute("INSERT INTO events (source_id, type, timestamp, source_type, reliability) VALUES (?, ?, ?, ?, ?)",
                                   (4, 'Lab_Result', ts, 'Excel Import', REL_MEDICAL))
                    evt_id = cursor.lastrowid
                    
                    for r in records:
                        cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                                       (evt_id, r['variable_name'], r['value'], r['unit']))
                    
                    processed = True
                    stats['processed_files'] += 1
                    
            elif filename.endswith('.xml'):
                log(f"Processing XML Export: {filename}")
                records = parse_xml_export(file_path, cursor)
                if records:
                     ts = datetime.datetime.now().isoformat()
                     cursor.execute("INSERT INTO events (source_id, type, timestamp, source_type, reliability) VALUES (?, ?, ?, ?, ?)",
                                   (4, 'Health_Export', ts, 'XML Import', REL_SENSOR))
                     evt_id = cursor.lastrowid
                     
                     for r in records:
                        cursor.execute("INSERT INTO observations (event_id, variable_name, value, unit) VALUES (?, ?, ?, ?)",
                                       (evt_id, r['variable_name'], r['value'], r['unit']))
                     
                     processed = True
                     stats['processed_files'] += 1

            elif filename.endswith('.pdf'):
                log(f"Processing Medical PDF: {filename}")
                # We need to pass None for API key here and let the function load it, 
                # OR load it once at start of run_ingestion. 
                # For simplicity, letting function load it or we can optimize later.
                if parse_medical_pdf(file_path, cursor):
                    processed = True
                    stats['processed_files'] += 1
                else:
                    log(f"⚠️ PDF Processing failed (or skipped) for {filename}")
                    processed = False # Treat as unprocessed

            
            # --- POST-PROCESSING ---
            if processed:
                # Track file in DB
                try:
                    cursor.execute("INSERT INTO files (filename, file_path) VALUES (?, ?)", (filename, file_path))
                except Exception:
                    pass # Ignore if duplicate or failure for now
                
                # Batch Commit
                files_in_batch += 1
                if files_in_batch >= BATCH_SIZE:
                    conn.commit()
                    files_in_batch = 0
                    
                archive_file(file_path)
                stats['archived_files'] += 1
            else:
                # Move to Unprocessed in ARCHIVE
                rel_path = os.path.relpath(file_path, INBOX_DIR)
                dest_path = os.path.join(UNPROCESSED_DIR, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                shutil.move(file_path, dest_path)
                stats['unprocessed_files'] += 1

        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            log_error(file_path, str(e))
            stats['errors'] += 1

    # --- CLEANUP (Delete empty changes) ---
    log("🧹 Cleaning empty directories...")
    for root, dirs, files in os.walk(INBOX_DIR, topdown=False):
        if root == INBOX_DIR: continue
        if 'Errors' in root: continue # Start of Errors folder
        
        # If directory is empty, remove it
        if not os.listdir(root):
            try:
                os.rmdir(root)
            except OSError:
                pass 

    # Final commit
    conn.commit()
    conn.close()
    
    # --- REPORT ---
    log("\n" + "="*30)
    log("       INGESTION SUMMARY")
    log("="*30)
    log(f"✅ Processed & Archived : {stats['processed_files']}")
    log(f"📦 Moved to Archive     : {stats['unprocessed_files']}")
    log(f"🗑️ Deleted Zips         : {stats['deleted_zips']}")
    log(f"❌ Errors               : {stats['errors']}")
    log("="*30)
    
    return stats, logs

def main():
    run_ingestion()

if __name__ == "__main__":
    main()

