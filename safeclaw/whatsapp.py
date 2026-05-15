from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
from xml.sax.saxutils import escape

from .agent import run_task


def _twiml(body: str) -> bytes:
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escape(body)}</Message></Response>'.encode()


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

        if not body:
            reply = "Send a message and I will respond."
        elif body.lower() in {"reset", "/reset", "new", "/new"}:
            from .sessions import reset_session

            reset_session(session_id)
            reply = "Session reset."
        else:
            reply = run_task(body, session_id=session_id)

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
