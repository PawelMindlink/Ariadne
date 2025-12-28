import os
import toml
from google import genai
from google.genai import types

def test_json():
    print("🧪 Testing JSON Mode (New SDK)...")
    
    secrets_path = os.path.join(os.path.dirname(__file__), '..', '..', '.streamlit', 'secrets.toml')
    try:
        config = toml.load(secrets_path)
        client = genai.Client(api_key=config['GEMINI_API_KEY'])
        
        prompt = "List 3 fruits in JSON format: {'fruits': ['a','b']}"
        
        # Try Dict approach
        try:
            print("Attempt 1: Dict Config...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            print(f"✅ Success! Response: {response.text}")
        except Exception as e:
            print(f"❌ Attempt 1 Failed: {e}")

        # Try Output Schema approach
        try:
            print("\nAttempt 2: Structured Output...")
            # Pydantic or types
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type='application/json')
            )
            print(f"✅ Success! Response: {response.text}")
        except Exception as e:
            print(f"❌ Attempt 2 Failed: {e}")

    except Exception as e:
        print(f"❌ Critical: {e}")

if __name__ == "__main__":
    test_json()
