import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
WORKSPACE = Path(os.getenv("WORKSPACE", "./workspace")).resolve()
ALLOW_SHELL = os.getenv("ALLOW_SHELL", "false").lower() == "true"

WORKSPACE.mkdir(parents=True, exist_ok=True)
