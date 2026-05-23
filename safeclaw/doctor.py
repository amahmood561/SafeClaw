import os
import platform
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import (
    ALLOW_SHELL,
    API_KEY,
    APPROVAL_MODE,
    BASE_URL,
    MAX_TOOL_STEPS,
    MODEL,
    PERMISSION_PROFILE,
    SAFECLAW_ALLOWED_TELEGRAM_USERS,
    SAFECLAW_ALLOWED_SENDERS,
    TELEGRAM_BOT_TOKEN,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
    WORKSPACE,
)
from .service import LABEL


VALID_PROFILES = {"readonly", "workspace-write", "network-allow", "shell-ask", "shell-allow", "messaging-allow", "db-readonly"}
VALID_APPROVAL_MODES = {"ask", "deny", "auto"}
REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Check:
    name: str
    status: str
    detail: str
    fix: str = ""


def _status(ok: bool, warning: bool = False) -> str:
    if ok:
        return "ok"
    if warning:
        return "warn"
    return "fail"


def _port_open(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def _service_loaded() -> bool:
    if platform.system() != "Darwin":
        return False
    try:
        import subprocess

        result = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=5)
    except Exception:
        return False
    return LABEL in result.stdout


def run_doctor(port: int = 8080) -> list[Check]:
    checks: list[Check] = []

    py_ok = sys.version_info >= (3, 10)
    checks.append(
        Check(
            "Python",
            _status(py_ok),
            f"{sys.version.split()[0]} on {platform.system()}",
            "Install Python 3.10 or newer." if not py_ok else "",
        )
    )

    env_candidates = [Path.cwd() / ".env", REPO_ROOT / ".env"]
    env_path = next((path for path in env_candidates if path.exists()), env_candidates[0])
    checks.append(
        Check(
            ".env",
            _status(env_path.exists(), warning=True),
            str(env_path.resolve()) if env_path.exists() else "missing",
            "Copy .env.example to .env and set OPENAI_API_KEY." if not env_path.exists() else "",
        )
    )

    key_ok = bool(API_KEY and API_KEY != "your_key_here")
    checks.append(
        Check(
            "OpenAI API key",
            _status(key_ok),
            "set" if key_ok else "missing",
            "Set OPENAI_API_KEY in .env." if not key_ok else "",
        )
    )

    checks.append(Check("Model", "ok", MODEL))
    checks.append(Check("Base URL", "ok", BASE_URL))

    workspace_ok = WORKSPACE.exists() and WORKSPACE.is_dir() and os.access(WORKSPACE, os.W_OK)
    checks.append(
        Check(
            "Workspace",
            _status(workspace_ok),
            str(WORKSPACE),
            "Create the workspace folder or fix its permissions." if not workspace_ok else "",
        )
    )

    profile_ok = PERMISSION_PROFILE in VALID_PROFILES
    checks.append(
        Check(
            "Permission profile",
            _status(profile_ok),
            PERMISSION_PROFILE,
            f"Use one of: {', '.join(sorted(VALID_PROFILES))}." if not profile_ok else "",
        )
    )

    approval_ok = APPROVAL_MODE in VALID_APPROVAL_MODES
    checks.append(
        Check(
            "Approval mode",
            _status(approval_ok),
            APPROVAL_MODE,
            f"Use one of: {', '.join(sorted(VALID_APPROVAL_MODES))}." if not approval_ok else "",
        )
    )

    checks.append(Check("Shell", "warn" if ALLOW_SHELL else "ok", "enabled" if ALLOW_SHELL else "disabled"))

    tool_steps_ok = MAX_TOOL_STEPS > 0
    checks.append(
        Check(
            "Max tool steps",
            _status(tool_steps_ok),
            str(MAX_TOOL_STEPS),
            "Set MAX_TOOL_STEPS to a positive integer." if not tool_steps_ok else "",
        )
    )

    twilio_configured = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM)
    checks.append(
        Check(
            "Twilio outbound",
            _status(twilio_configured, warning=True),
            "configured" if twilio_configured else "not configured",
            "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM for outbound WhatsApp." if not twilio_configured else "",
        )
    )

    checks.append(
        Check(
            "Allowed senders",
            _status(bool(SAFECLAW_ALLOWED_SENDERS), warning=True),
            ", ".join(SAFECLAW_ALLOWED_SENDERS) if SAFECLAW_ALLOWED_SENDERS else "not set",
            "Set SAFECLAW_ALLOWED_SENDERS=whatsapp:+15551234567 to restrict webhook access." if not SAFECLAW_ALLOWED_SENDERS else "",
        )
    )

    checks.append(
        Check(
            "Telegram bot",
            _status(bool(TELEGRAM_BOT_TOKEN), warning=True),
            "configured" if TELEGRAM_BOT_TOKEN else "not configured",
            "Set TELEGRAM_BOT_TOKEN for Telegram phone access." if not TELEGRAM_BOT_TOKEN else "",
        )
    )

    checks.append(
        Check(
            "Allowed Telegram users",
            _status(bool(SAFECLAW_ALLOWED_TELEGRAM_USERS), warning=True),
            ", ".join(SAFECLAW_ALLOWED_TELEGRAM_USERS) if SAFECLAW_ALLOWED_TELEGRAM_USERS else "not set",
            "Set SAFECLAW_ALLOWED_TELEGRAM_USERS=123456789 to restrict bot access." if not SAFECLAW_ALLOWED_TELEGRAM_USERS else "",
        )
    )

    port_busy = _port_open("127.0.0.1", port)
    checks.append(
        Check(
            f"Port {port}",
            _status(not port_busy, warning=True),
            "in use" if port_busy else "available",
            f"Use another port or stop the process using {port}." if port_busy else "",
        )
    )

    if platform.system() == "Darwin":
        checks.append(
            Check(
                "macOS service",
                _status(_service_loaded(), warning=True),
                "loaded" if _service_loaded() else "not loaded",
                "Run safeclaw service-install for persistent WhatsApp mode." if not _service_loaded() else "",
            )
        )

    return checks


def doctor_summary(checks: list[Check]) -> str:
    failures = sum(1 for check in checks if check.status == "fail")
    warnings = sum(1 for check in checks if check.status == "warn")
    if failures:
        return f"{failures} failure(s), {warnings} warning(s)"
    if warnings:
        return f"0 failures, {warnings} warning(s)"
    return "all checks passed"
