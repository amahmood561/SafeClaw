from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
from xml.sax.saxutils import escape

from .agent import run_task
from .config import SAFECLAW_ALLOWED_SENDERS, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM
from .sessions import recall, reset_session, session_status, update_session_settings


def _twiml(body: str) -> bytes:
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escape(body)}</Message></Response>'.encode()


def whatsapp_setup_status(public_url: str = "https://your-public-url") -> str:
    configured = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM)
    allowed = ", ".join(SAFECLAW_ALLOWED_SENDERS) if SAFECLAW_ALLOWED_SENDERS else "not set"
    return f"""
WhatsApp setup

1. Start SafeClaw:
   safeclaw whatsapp --port 8080

2. Expose it with ngrok or Cloudflare Tunnel:
   ngrok http 8080

3. In Twilio WhatsApp Sandbox or Sender settings, set incoming webhook to:
   {public_url.rstrip("/")}/whatsapp

4. Add allowed senders in .env:
   SAFECLAW_ALLOWED_SENDERS=whatsapp:+15551234567

Current outbound config:
  TWILIO_ACCOUNT_SID: {"set" if TWILIO_ACCOUNT_SID else "missing"}
  TWILIO_AUTH_TOKEN: {"set" if TWILIO_AUTH_TOKEN else "missing"}
  TWILIO_WHATSAPP_FROM: {"set" if TWILIO_WHATSAPP_FROM else "missing"}
  outbound ready: {configured}
  allowed senders: {allowed}

Useful WhatsApp commands:
  /help
  /status
  /memory
  /reset
  /permissions
  /permissions readonly
  /model gpt-4.1-mini
""".strip()


def _sender_allowed(sender: str) -> bool:
    return not SAFECLAW_ALLOWED_SENDERS or sender in SAFECLAW_ALLOWED_SENDERS


def _whatsapp_help() -> str:
    return """
SafeClaw commands:
/help - show commands
/status - show session status
/memory - show saved memory
/reset - reset this chat session
/permissions - show current safety profile
/permissions PROFILE - set profile for this chat
/model MODEL_NAME - set this chat model

Send any normal message to ask SafeClaw to help.
Risky actions that need terminal approval are blocked over WhatsApp.
""".strip()


class WhatsAppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path != "/whatsapp":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode()
        form = parse_qs(payload)
        body = (form.get("Body") or [""])[0].strip()
        sender = (form.get("From") or ["whatsapp:unknown"])[0]
        session_id = f"whatsapp-{sender}"

        if not _sender_allowed(sender):
            reply = "This sender is not allowed to use this SafeClaw instance."
        elif not body:
            reply = "Send a message and I will respond."
        elif body.lower() in {"reset", "/reset", "new", "/new"}:
            reset_session(session_id)
            reply = "Session reset."
        elif body.lower() in {"help", "/help"}:
            reply = _whatsapp_help()
        elif body.lower() in {"status", "/status"}:
            reply = str(session_status(session_id))
        elif body.lower() in {"memory", "/memory"}:
            reply = recall(session_id)
        elif body.lower() in {"permissions", "/permissions"}:
            status = session_status(session_id)
            reply = f"Permission profile: {status.get('permission_profile') or 'readonly'}"
        elif body.lower().startswith(("/permissions ", "permissions ")):
            profile = body.split(maxsplit=1)[1].strip()
            reply = update_session_settings(session_id, permission_profile=profile)
        elif body.lower().startswith(("/model ", "model ")):
            model = body.split(maxsplit=1)[1].strip()
            reply = update_session_settings(session_id, model=model)
        else:
            reply = run_task(body, session_id=session_id, interactive=False)

        response = _twiml(reply)
        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


def serve_whatsapp(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), WhatsAppHandler)
    print(f"WhatsApp webhook listening on http://{host}:{port}/whatsapp")
    server.serve_forever()
