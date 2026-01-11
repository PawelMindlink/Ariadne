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

    def insert_graph_data(self, graph_json, source_filename):
        """
        Takes the JSON from Gemini and inserts it into SQLite v2.
        Using the OBSERVATION model.
        """
        cursor = self.conn.cursor()
        
        try:
            # 1. Create Source Document Node
            cursor.execute(
                "INSERT INTO nodes (type, body) VALUES (?, ?) RETURNING id",
                ("Document", json.dumps({"name": source_filename, "status": "processed"}))
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
    for file_path, filename in scanner.scan():
        print(f"Processing: {filename}...")
        
        # 1. Extract Text
        text, method = extractor.extract_text(file_path)
        if method != 'native':
            print(f"  -> Skipping (Method: {method}) -> Moving to Quarantine")
            quarantine_path = os.path.join(Config.QUARANTINE_DIR, "needs_ocr")
            os.makedirs(quarantine_path, exist_ok=True)
            shutil.move(file_path, os.path.join(quarantine_path, filename))
            continue
            
        # 2. AI Analysis
        print("  -> Asking Gemini...")
        graph_data = ai.extract_graph_from_text(text, dates_hint=filename)
        
        if not graph_data:
            print("  -> AI Failed to extract data. -> Moving to Quarantine/Errors")
            quarantine_path = os.path.join(Config.QUARANTINE_DIR, "ai_failed")
            os.makedirs(quarantine_path, exist_ok=True)
            shutil.move(file_path, os.path.join(quarantine_path, filename))
            continue
            
        # 3. DB Insert
        success, doc_id = builder.insert_graph_data(graph_data, filename)
        
        if success:
            print(f"  -> ✅ Success! Document ID: {doc_id}")
            # Move to Archive
            target = os.path.join(Config.ARCHIVE_DIR, filename)
            shutil.move(file_path, target)
            count += 1
        else:
            print("  -> ❌ DB Insertion Failed")
            
    print(f"Done. Processed {count} files.")

if __name__ == "__main__":
    run_ingestion()
