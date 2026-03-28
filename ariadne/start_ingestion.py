from ariadne.core.database import db
from ariadne.core.config import Config
from ariadne.core.ai import ai
from ariadne.ingestion.scanner import Scanner
from ariadne.ingestion.extractor import Extractor
import os
import shutil
import json

class GraphBuilder:
    def __init__(self):
        self.conn = db.get_connection()

    def insert_graph_data(self, graph_json, source_filename, file_hash=None):
        """
        Takes the JSON from Gemini and inserts it into SQLite v2.
        Using the OBSERVATION model.
        """
        cursor = self.conn.cursor()
        
        try:
            # 1. Create Source Document Node
            doc_body = {
                "name": source_filename, 
                "hash": file_hash,
                "status": "processed"
            }
            cursor.execute(
                "INSERT INTO nodes (type, body) VALUES (?, ?) RETURNING id",
                ("Document", json.dumps(doc_body))
            )
            doc_id = cursor.fetchone()[0]
            
            # 2. Process Nodes (Entities)
            node_map = {} # Name -> DB_ID
            for node in graph_json.get("nodes", []):
                name = node.get("name")
                type_ = node.get("type", "Unknown")
                
                # Check if exists (Simple deduplication by name for now)
                # In real prod we need smarter entity resolution
                existing = cursor.execute(
                    "SELECT id FROM nodes WHERE json_extract(body, '$.name') = ?", (name,)
                ).fetchone()
                
                if existing:
                    node_id = existing[0]
                else:
                    cursor.execute(
                        "INSERT INTO nodes (type, body) VALUES (?, ?) RETURNING id",
                        (type_, json.dumps(node))
                    )
                    node_id = cursor.fetchone()[0]
                
                node_map[name] = node_id

            # 3. Process Observations (The Truths)
            for obs in graph_json.get("observations", []):
                feature = obs.get("feature") # e.g. "Fracture"
                value = obs.get("value")     # e.g. "Present"
                date = obs.get("date")
                
                node_id = node_map.get(feature)
                if node_id:
                    cursor.execute("""
                        INSERT INTO observations 
                        (source_document_id, concept_node_id, value_text, observation_date)
                        VALUES (?, ?, ?, ?)
                    """, (doc_id, node_id, value, date))

            # 4. Process Edges (Relationships)
            for edge in graph_json.get("edges", []):
                src = node_map.get(edge.get("source"))
                tgt = node_map.get(edge.get("target"))
                rel = edge.get("rel")
                
                if src and tgt:
                    # Upsert Edge
                    cursor.execute("""
                        INSERT OR IGNORE INTO edges (source_id, target_id, rel_type)
                        VALUES (?, ?, ?)
                    """, (src, tgt, rel))
            
            self.conn.commit()
            return True, doc_id
            
        except Exception as e:
            self.conn.rollback()
            print(f"DB Error: {e}")
            return False, None

def run_ingestion():
    print("🚀 Starting AI Ingestion (The Weaver)...")
    scanner = Scanner()
    extractor = Extractor()
    builder = GraphBuilder()
    
    count = 0
    # ... (inside run_ingestion loop) ...
    for file_path, filename in scanner.scan():
        print(f"Processing: {filename}...")
        
        # 0. Calculate Hash (Digital Fingerprint)
        file_hash = scanner.calculate_hash(file_path)
        if not file_hash:
            print("  -> ❌ Error calculating hash. Skipping.")
            continue

        # 1. Check for Duplicate (by Hash)
        conn = db.get_connection()
        existing_doc = conn.execute(
            "SELECT id FROM nodes WHERE type='Document' AND json_extract(body, '$.hash') = ?", 
            (file_hash,)
        ).fetchone()
        conn.close()

        if existing_doc:
            print(f"  -> ⚠️ Duplicate content detected (ID: {existing_doc[0]}). Skipping.")
            # Move to Archive to clean inbox
            target = os.path.join(Config.ARCHIVE_DIR, filename)
            if os.path.exists(target):
                 base, ext = os.path.splitext(filename)
                 import time
                 timestamp = int(time.time())
                 target = os.path.join(Config.ARCHIVE_DIR, f"{base}_{timestamp}{ext}")
            try:
                shutil.move(file_path, target)
                print("  -> Moved duplicate to Archive.")
            except Exception as e:
                print(f"  -> ❌ Move failed: {e}")
            continue

        # 2. Extract Text
        text, method = extractor.extract_text(file_path)
        if method != 'native':
            print(f"  -> Skipping (Method: {method}) -> Moving to Quarantine")
            quarantine_path = os.path.join(Config.QUARANTINE_DIR, "needs_ocr")
            os.makedirs(quarantine_path, exist_ok=True)
            shutil.move(file_path, os.path.join(quarantine_path, filename))
            continue
            
        # 3. AI Analysis
        print("  -> Asking Gemini...")
        graph_data = ai.extract_graph_from_text(text, dates_hint=filename)
        
        if not graph_data:
            print("  -> AI Failed to extract data. -> Moving to Quarantine/Errors")
            quarantine_path = os.path.join(Config.QUARANTINE_DIR, "ai_failed")
            os.makedirs(quarantine_path, exist_ok=True)
            shutil.move(file_path, os.path.join(quarantine_path, filename))
            continue
            
        # 4. DB Insert
        success, doc_id = builder.insert_graph_data(graph_data, filename, file_hash)
        
        if success:
            print(f"  -> ✅ Success! Document ID: {doc_id}")
            # Move to Archive
            try:
                target = os.path.join(Config.ARCHIVE_DIR, filename)
                if os.path.exists(target):
                    base, ext = os.path.splitext(filename)
                    import time
                    timestamp = int(time.time())
                    target = os.path.join(Config.ARCHIVE_DIR, f"{base}_{timestamp}{ext}")
                shutil.move(file_path, target)
                count += 1
            except Exception as e:
                print(f"  -> ❌ Move failed: {e}")
        else:
            print("  -> ❌ DB Insertion Failed")
            
    print(f"Done. Processed {count} files.")
    return count

if __name__ == "__main__":
    run_ingestion()
