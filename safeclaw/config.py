import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
WORKSPACE = Path(os.getenv("WORKSPACE", "./workspace")).resolve()
ALLOW_SHELL = os.getenv("ALLOW_SHELL", "false").lower() == "true"
PERMISSION_PROFILE = os.getenv("SAFECLAW_PERMISSION_PROFILE", "readonly")
APPROVAL_MODE = os.getenv("SAFECLAW_APPROVAL_MODE", "ask").lower()
# A real task routinely needs dozens of tool calls. Six was enough to read a file
# and answer a question, and not enough to debug anything -- the model got cut off
# mid-task with no explanation. This is a safety net against runaway loops, not a
# budget: the loop normally ends because the model stopped asking for tools.
MAX_TOOL_STEPS = int(os.getenv("MAX_TOOL_STEPS", "50"))
# Which provider the completions go to. "claude-cli" shells out to a local Claude
# Code login instead of calling an HTTP endpoint, so it needs no API key.
PROVIDER_PRESET = os.getenv("SAFECLAW_PROVIDER_PRESET", "openai")
SQLITE_DATABASES = os.getenv("SAFECLAW_SQLITE_DATABASES", "")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")
SAFECLAW_ALLOWED_SENDERS = [
    item.strip()
    for item in os.getenv("SAFECLAW_ALLOWED_SENDERS", "").split(",")
    if item.strip()
]
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SAFECLAW_ALLOWED_TELEGRAM_USERS = [
    item.strip()
    for item in os.getenv("SAFECLAW_ALLOWED_TELEGRAM_USERS", "").split(",")
    if item.strip()
]

WORKSPACE.mkdir(parents=True, exist_ok=True)
