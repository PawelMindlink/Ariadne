from ariadne.core.config import Config
from google import genai
from google.genai import types
import json
import time

class AI:
    def __init__(self):
        self.api_key = Config.get_gemini_key()
        if not self.api_key:
            raise ValueError("Gemini API Key missing! Check .env or secrets.toml")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.0-flash-exp" # Fast, cheap, good for extraction

    def extract_graph_from_text(self, text, dates_hint=None):
        """
        The Core 'Weaver' Function.
        Takes raw medical text and returns a structured JSON of Nodes, Edges, Observations.
        """
        
        schema_definition = """
        {
            "nodes": [
                {"name": "Fracture", "type": "Concept/Condition", "code": "SNOMED:..."}
            ],
            "edges": [
                {"source": "Patient", "target": "Fracture", "rel": "HAS_CONDITION", "weight": 1.0}
            ],
            "observations": [
                 {"feature": "Fracture", "value": "Present", "date": "YYYY-MM-DD", "source": "Doctor Smith"}
            ]
        }
        """

        prompt = f"""
        You are an expert Medical Knowledge Graph engineer.
        Task: Extract structured clinical facts from the text below.
        
        Rules:
        1. **Strict Dates:** Use YYYY-MM-DD. If fuzzy, allow YYYY-MM. If missing, use 'UNKNOWN'.
        2. **Terminology:** Map conditions/meds to standard SNOMED or LOINC names if obvious.
        3. **Observation Model:** Distinguish between a 'Fact' and an 'Observation'. Who said it? When?
        4. **Output:** Return ONLY valid JSON matching this schema: {schema_definition}
        
        Context Dates (Hints from filename/metadata): {dates_hint}
        
        --- TEXT START ---
        {text[:20000]} 
        --- TEXT END ---
        """
        # Limit text to avoid token limits for now, though Gemini 2.0 has 1M context.

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            # Parse JSON
            raw_json = response.text
            return json.loads(raw_json)

        except Exception as e:
            print(f"AI Extraction Error: {e}")
            return None

# Singleton for easy import
ai = AI()
