import os
import toml
from google import genai

def test_api():
    print("🧪 Testing Gemini API Connection (New SDK)...")
    
    secrets_path = os.path.join(os.path.dirname(__file__), '..', '..', '.streamlit', 'secrets.toml')
    try:
        config = toml.load(secrets_path)
        api_key = config.get('GEMINI_API_KEY')
        
        client = genai.Client(api_key=api_key)
        
        print(f"🔑 Key found: {api_key[:5]}...")
        
        # List models
        print("listing models...")
        # New SDK might have differnt list method or we just skip and try a generation
        # client.models.list() is the standard way usually
        try:
            for m in client.models.list():
                if "thinking" in m.name.lower() or "flash" in m.name.lower():
                    print(f"- {m.name}")
        except Exception as e:
            print(f"List error: {e}")

        # Try with Flash 2.5 (Confirmed available)
        print("\nTesting Generation (Gemini 2.5 Flash)...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents="Hello"
        )
        print(f"✅ Success! Response: {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_api()
