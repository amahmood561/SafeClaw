import time

import requests

from .agent import run_task
from .config import SAFECLAW_ALLOWED_TELEGRAM_USERS, TELEGRAM_BOT_TOKEN
from .sessions import recall, reset_session, session_status, update_session_settings


TELEGRAM_API = "https://api.telegram.org"
MAX_TELEGRAM_MESSAGE = 3900


def telegram_setup_status() -> str:
    configured = bool(TELEGRAM_BOT_TOKEN)
    allowed = ", ".join(SAFECLAW_ALLOWED_TELEGRAM_USERS) if SAFECLAW_ALLOWED_TELEGRAM_USERS else "not set"
    return f"""
Telegram setup

1. Open Telegram and message @BotFather.

2. Create a bot:
   /newbot

3. Copy the bot token into .env:
   TELEGRAM_BOT_TOKEN=123456:ABC-your-token

4. Message your bot once from your phone.

5. Start SafeClaw Telegram polling:
   safeclaw telegram

6. Recommended: restrict who can use the bot:
   SAFECLAW_ALLOWED_TELEGRAM_USERS=123456789

Current Telegram config:
  TELEGRAM_BOT_TOKEN: {"set" if configured else "missing"}
  allowed users: {allowed}

Useful Telegram commands:
  /help
  /status
  /memory
  /reset
  /permissions
  /permissions readonly
  /model gpt-4.1-mini

Why Telegram is easier:
  No public webhook, Twilio number, ngrok, or Cloudflare Tunnel is required.
  SafeClaw polls Telegram from your Mac while the app is running.
""".strip()


def _telegram_help() -> str:
    return """
SafeClaw Telegram commands:
/help - show commands
/status - show session status
/memory - show saved memory
/reset - reset this chat session
/permissions - show current safety profile
/permissions PROFILE - set profile for this chat
/model MODEL_NAME - set this chat model

Send any normal message to ask SafeClaw to help.
Risky actions that need terminal approval are blocked over Telegram.
""".strip()


def _sender_allowed(sender_id: str) -> bool:
    return not SAFECLAW_ALLOWED_TELEGRAM_USERS or sender_id in SAFECLAW_ALLOWED_TELEGRAM_USERS


def _reply_for_message(body: str, sender_id: str) -> str:
    session_id = f"telegram-{sender_id}"
    text = body.strip()
    lowered = text.lower()

    if not _sender_allowed(sender_id):
        return "This Telegram user is not allowed to use this SafeClaw instance."
    if not text:
        return "Send a message and I will respond."
    if lowered in {"reset", "/reset", "new", "/new"}:
        reset_session(session_id)
        return "Session reset."
    if lowered in {"help", "/help", "start", "/start"}:
        return _telegram_help()
    if lowered in {"status", "/status"}:
        return str(session_status(session_id))
    if lowered in {"memory", "/memory"}:
        return recall(session_id)
    if lowered in {"permissions", "/permissions"}:
        status = session_status(session_id)
        return f"Permission profile: {status.get('permission_profile') or 'readonly'}"
    if lowered.startswith(("/permissions ", "permissions ")):
        profile = text.split(maxsplit=1)[1].strip()
        return update_session_settings(session_id, permission_profile=profile)
    if lowered.startswith(("/model ", "model ")):
        model = text.split(maxsplit=1)[1].strip()
        return update_session_settings(session_id, model=model)

    return run_task(text, session_id=session_id, interactive=False)


def _chunks(text: str) -> list[str]:
    if not text:
        return [""]
    return [text[index : index + MAX_TELEGRAM_MESSAGE] for index in range(0, len(text), MAX_TELEGRAM_MESSAGE)]


def send_telegram_message(chat_id: str | int, text: str, token: str | None = None) -> None:
    bot_token = token or TELEGRAM_BOT_TOKEN
    if not bot_token:
        raise RuntimeError("Telegram bot token is missing. Set TELEGRAM_BOT_TOKEN in .env.")

    for chunk in _chunks(text):
        response = requests.post(
            f"{TELEGRAM_API}/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": chunk},
            timeout=30,
        )
        response.raise_for_status()


def _get_updates(offset: int | None, timeout: int, token: str) -> list[dict]:
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    response = requests.get(f"{TELEGRAM_API}/bot{token}/getUpdates", params=params, timeout=timeout + 10)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram getUpdates failed: {payload}")
    return payload.get("result", [])


def serve_telegram(poll_interval: float = 1.0, once: bool = False) -> None:
    if not TELEGRAM_BOT_TOKEN:
        print(telegram_setup_status())
        return

    print("Telegram bot polling started. Press Ctrl+C to stop.")
    if not SAFECLAW_ALLOWED_TELEGRAM_USERS:
        print("Warning: SAFECLAW_ALLOWED_TELEGRAM_USERS is not set. Anyone who can message this bot can use it.")

    offset = None
    while True:
        updates = _get_updates(offset=offset, timeout=30, token=TELEGRAM_BOT_TOKEN)
        for update in updates:
            offset = int(update["update_id"]) + 1
            message = update.get("message") or update.get("edited_message") or {}
            chat = message.get("chat") or {}
            sender = message.get("from") or {}
            chat_id = chat.get("id")
            sender_id = str(sender.get("id") or chat_id or "unknown")
            body = message.get("text") or ""
            if chat_id is None:
                continue
            reply = _reply_for_message(body, sender_id)
            send_telegram_message(chat_id, reply)
        if once:
            return
        time.sleep(poll_interval)
