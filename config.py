import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
OWNER_ID = int(os.environ["OWNER_ID"])
FERNET = Fernet(os.environ["ENC_KEY"].encode())

UPDATES_URL = os.getenv("UPDATES_URL", "https://t.me/telegram")
SCAN_MIN = int(os.getenv("SCAN_INTERVAL_MIN", "30"))
WARN_LIMIT = int(os.getenv("WARN_LIMIT", "3"))
DB_PATH = os.getenv("DB_PATH", "bot.db")
