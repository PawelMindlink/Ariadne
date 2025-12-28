import os
import toml
from google import genai

def list_all():
    print("📋 Listing All Models...")
    secrets_path = os.path.join(os.path.dirname(__file__), '..', '..', '.streamlit', 'secrets.toml')
    try:
        config = toml.load(secrets_path)
        client = genai.Client(api_key=config['GEMINI_API_KEY'])
        
        pager = client.models.list()
        count = 0
        with open("models_list.txt", "w", encoding="utf-8") as f:
            for m in pager:
                line = f"Model: {m.name} | {m.display_name} | {m.description}"
                # print(line) # Skip printing to avoid utf-8 console errors
                f.write(line + "\n")
                count += 1
            print(f"Total Models Found: {count}")
            print(f"✅ List written to models_list.txt")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_all()
