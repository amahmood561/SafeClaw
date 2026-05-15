import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import WORKSPACE

SESSIONS_DIR = WORKSPACE / ".safeclaw_sessions"
MEMORY_DIR = WORKSPACE / ".safeclaw_memory"


def _safe_id(session_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in session_id)
    return cleaned or "default"


def session_path(session_id: str) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSIONS_DIR / f"{_safe_id(session_id)}.json"


def memory_path(session_id: str) -> Path:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return MEMORY_DIR / f"{_safe_id(session_id)}.md"


def load_session(session_id: str) -> dict[str, Any]:
    path = session_path(session_id)
    if not path.exists():
        return {
            "id": session_id,
            "model": None,
            "messages": [],
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": None,
        }
    return json.loads(path.read_text())


def save_session(session: dict[str, Any]) -> None:
    session["updated_at"] = datetime.now().isoformat(timespec="seconds")
    session_path(session["id"]).write_text(json.dumps(session, indent=2))


def append_message(session_id: str, message: dict[str, Any]) -> dict[str, Any]:
    session = load_session(session_id)
    session["messages"].append(message)
    save_session(session)
    return session


def reset_session(session_id: str) -> None:
    session_path(session_id).unlink(missing_ok=True)
    memory_path(session_id).unlink(missing_ok=True)


def list_sessions() -> list[dict[str, Any]]:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    sessions = []
    for path in sorted(SESSIONS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        sessions.append({
            "id": data.get("id", path.stem),
            "model": data.get("model"),
            "messages": len(data.get("messages", [])),
            "updated_at": data.get("updated_at"),
        })
    return sessions


def remember(session_id: str, note: str) -> str:
    path = memory_path(session_id)
    stamp = datetime.now().isoformat(timespec="seconds")
    with path.open("a") as handle:
        handle.write(f"- {stamp}: {note.strip()}\n")
    return "Memory saved."


def recall(session_id: str) -> str:
    path = memory_path(session_id)
    if not path.exists():
        return "No memory saved for this session."
    return path.read_text().strip() or "No memory saved for this session."


def compact_session(session_id: str, keep_last: int = 12) -> str:
    session = load_session(session_id)
    messages = session.get("messages", [])
    if len(messages) <= keep_last:
        return "Session is already compact."
    older = messages[:-keep_last]
    summary_lines = []
    for msg in older:
        role = msg.get("role", "unknown")
        content = str(msg.get("content", ""))
        if content:
            summary_lines.append(f"{role}: {content[:300]}")
    summary = "\n".join(summary_lines)
    session["messages"] = [
        {
            "role": "system",
            "content": "Compacted prior conversation summary:\n" + summary,
        }
    ] + messages[-keep_last:]
    save_session(session)
    return f"Compacted {len(older)} older messages."
