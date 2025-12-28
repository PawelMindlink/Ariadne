import unittest
import os
import sys
import sqlite3
import json

# Add Apps to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '03_Apps'))

from ingest import parse_garmin_json, parse_fit_csv, parse_garmin_tcx

# Mock DB for testing
class TestIngestion(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # Setup minimal schema
        self.cursor.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, timestamp TEXT, type TEXT, source_id INTEGER, json_details TEXT)")
        self.cursor.execute("CREATE TABLE observations (id INTEGER PRIMARY KEY, event_id INTEGER, variable_name TEXT, value REAL, unit TEXT, normalized_value REAL, normalized_unit TEXT)")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_garmin_json(self):
        # Create dummy file
        dummy_json = [{"calendarDate": "2023-01-01", "sleepScores": {"overall": {"value": 85}}, "durationInSeconds": 28000}]
        with open("test_garmin.json", "w") as f:
            json.dump(dummy_json, f)
            
        try:
            parse_garmin_json("test_garmin.json", self.cursor)
            
            # Verify Event
            self.cursor.execute("SELECT * FROM events")
            event = self.cursor.fetchone()
            self.assertIsNotNone(event)
            self.assertEqual(event[1], "2023-01-01T00:00:00") # timestamp
            
            # Verify Observation
            self.cursor.execute("SELECT * FROM observations WHERE variable_name='Sleep Score'")
            obs = self.cursor.fetchone()
            self.assertIsNotNone(obs)
            self.assertEqual(obs[3], 85.0) # value
            
        finally:
            if os.path.exists("test_garmin.json"):
                os.remove("test_garmin.json")

    def test_fit_csv(self):
        # Create dummy CSV
        with open("test_metrics.csv", "w") as f:
            f.write("Date,Step count,Calories (kcal)\n")
            f.write("2023-01-02,5000,200\n")
            
        try:
            parse_fit_csv("test_metrics.csv", self.cursor)
            
            self.cursor.execute("SELECT * FROM events")
            event = self.cursor.fetchone()
            self.assertEqual(event[1], "2023-01-02T00:00:00")
            
            self.cursor.execute("SELECT * FROM observations WHERE variable_name='Steps'")
            obs = self.cursor.fetchone()
            self.assertEqual(obs[3], 5000)
            
        finally:
             if os.path.exists("test_metrics.csv"):
                os.remove("test_metrics.csv")

if __name__ == '__main__':
    unittest.main()
