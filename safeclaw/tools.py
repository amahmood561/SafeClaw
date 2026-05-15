import os
import subprocess
from pathlib import Path
from typing import Any

import requests

from .config import (
    ALLOW_SHELL,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
    WORKSPACE,
)


def safe_path(path: str) -> Path:
    target = (WORKSPACE / path).resolve()
    try:
        target.relative_to(WORKSPACE)
    except ValueError:
        raise ValueError("Path escapes workspace")
    return target


def list_files(path: str = ".") -> str:
    base = safe_path(path)
    if not base.exists():
        return f"Not found: {path}"
    lines = []
    for p in sorted(base.rglob("*")):
        if p.is_file():
            lines.append(str(p.relative_to(WORKSPACE)))
    return "\n".join(lines) or "No files found."


def read_file(path: str) -> str:
    target = safe_path(path)
    return target.read_text(errors="replace")


def write_file(path: str, content: str) -> str:
    target = safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"Wrote {target.relative_to(WORKSPACE)}"


def shell(command: str) -> str:
    if not ALLOW_SHELL:
        return "Shell is disabled. Set ALLOW_SHELL=true to enable."
    result = subprocess.run(
        command,
        shell=True,
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return (result.stdout + result.stderr).strip()


def send_whatsapp(to: str, body: str) -> str:
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM):
        return "WhatsApp outbound is not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM."
    response = requests.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json",
        auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
        data={
            "From": TWILIO_WHATSAPP_FROM,
            "To": to,
            "Body": body,
        },
        timeout=30,
    )
    if response.status_code >= 400:
        return f"WhatsApp send failed: {response.text}"
    return "WhatsApp message sent."


TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files under a workspace path.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "default": "."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text content to a workspace file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shell",
            "description": "Run a shell command in the workspace if ALLOW_SHELL=true.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp",
            "description": "Send an outbound WhatsApp message through Twilio if configured.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "A Twilio WhatsApp address, like whatsapp:+15551234567."},
                    "body": {"type": "string"},
                },
                "required": ["to", "body"],
            },
        },
    },
]


def run_tool(name: str, arguments: dict[str, Any]) -> str:
    functions = {
        "list_files": list_files,
        "read_file": read_file,
        "write_file": write_file,
        "shell": shell,
        "send_whatsapp": send_whatsapp,
    }
    if name not in functions:
        return f"Unknown tool: {name}"
    try:
        return str(functions[name](**arguments))
    except Exception as exc:
        return f"Tool error in {name}: {exc}"


def available_tools() -> str:
    return """
Available local tools:
- list_files(path='.')
- read_file(path)
- write_file(path, content)
- shell(command) disabled unless ALLOW_SHELL=true
- send_whatsapp(to, body) if Twilio env vars are configured

This version supports automatic OpenAI-style function calling.
""".strip()
