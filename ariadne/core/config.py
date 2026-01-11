import os
import toml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Project Root (Base of the git repo)
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    # Inbox Paths
    INBOX_DIR = os.path.join(BASE_DIR, '00_Inbox')
    ARCHIVE_DIR = os.path.join(BASE_DIR, '01_Archive')
    QUARANTINE_DIR = os.path.join(BASE_DIR, '03_Quarantine')
    PROCESSING_DIR = os.path.join(BASE_DIR, '01_Processing')

    # Database
    DB_PATH = os.path.join(BASE_DIR, '02_Database', 'ariadne_v2.db') # New V2 DB

    # Secrets
    _secrets = None

    @classmethod
    def get_gemini_key(cls):
        # 1. Try Environment Variable (Docker/Cloud friendly)
        key = os.getenv("GEMINI_API_KEY")
        if key:
            return key
        
        # 2. Try .streamlit/secrets.toml (Legacy support)
        if cls._secrets is None:
            cls._load_secrets_toml()
        
        return cls._secrets.get("GEMINI_API_KEY")

    @classmethod
    def _load_secrets_toml(cls):
        toml_path = os.path.join(cls.BASE_DIR, '.streamlit', 'secrets.toml')
        if os.path.exists(toml_path):
            try:
                cls._secrets = toml.load(toml_path)
            except Exception as e:
                print(f"Warning: Failed to load secrets.toml: {e}")
                cls._secrets = {}
        else:
            cls._secrets = {}

# Create critical directories if they don't exist
for d in [Config.INBOX_DIR, Config.ARCHIVE_DIR, Config.QUARANTINE_DIR, Config.PROCESSING_DIR, os.path.dirname(Config.DB_PATH)]:
    os.makedirs(d, exist_ok=True)
