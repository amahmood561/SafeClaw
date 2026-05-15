import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import WORKSPACE

SESSIONS_DIR = WORKSPACE / ".safeclaw_sessions"
MEMORY_DIR = WORKSPACE / ".safeclaw_memory"
EXPORTS_DIR = WORKSPACE / ".safeclaw_exports"


def _safe_id(session_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in session_id)
    return cleaned or "default"


def session_path(session_id: str) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSIONS_DIR / f"{_safe_id(session_id)}.json"


def memory_path(session_id: str) -> Path:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return MEMORY_DIR / f"{_safe_id(session_id)}.md"


def memory_json_path(session_id: str) -> Path:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return MEMORY_DIR / f"{_safe_id(session_id)}.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_session(session_id: str) -> dict[str, Any]:
    path = session_path(session_id)
    if not path.exists():
        return {
            "id": session_id,
            "model": None,
            "permission_profile": None,
            "messages": [],
            "created_at": _now(),
            "updated_at": None,
        }
    return json.loads(path.read_text())


def save_session(session: dict[str, Any]) -> None:
    session["updated_at"] = _now()
    session_path(session["id"]).write_text(json.dumps(session, indent=2))


def append_message(session_id: str, message: dict[str, Any]) -> dict[str, Any]:
    session = load_session(session_id)
    session["messages"].append(message)
    save_session(session)
    return session


def reset_session(session_id: str) -> None:
    session_path(session_id).unlink(missing_ok=True)
    memory_path(session_id).unlink(missing_ok=True)
    memory_json_path(session_id).unlink(missing_ok=True)


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
    note = note.strip()
    if not note:
        return "No memory note provided."
    entries = list_memory(session_id)
    next_id = 1
    if entries:
        next_id = max(int(item.get("id", 0)) for item in entries) + 1
    entries.append({"id": next_id, "created_at": _now(), "updated_at": None, "note": note})
    _save_memory(session_id, entries)
    return f"Memory saved as #{next_id}."


def recall(session_id: str) -> str:
    entries = list_memory(session_id)
    if not entries:
        return "No memory saved for this session."
    lines = []
    for item in entries:
        updated = f", updated {item['updated_at']}" if item.get("updated_at") else ""
        lines.append(f"- #{item['id']} {item['created_at']}{updated}: {item['note']}")
    return "\n".join(lines)


def _legacy_memory_entries(session_id: str) -> list[dict[str, Any]]:
    path = memory_path(session_id)
    if not path.exists():
        return []
    entries = []
    for index, line in enumerate(path.read_text(errors="replace").splitlines(), start=1):
        note = line.strip()
        if note.startswith("- "):
            note = note[2:]
        if note:
            entries.append({"id": index, "created_at": "legacy", "updated_at": None, "note": note})
    return entries


def list_memory(session_id: str) -> list[dict[str, Any]]:
    path = memory_json_path(session_id)
    if path.exists():
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    legacy = _legacy_memory_entries(session_id)
    if legacy:
        _save_memory(session_id, legacy)
    return legacy


def _save_memory(session_id: str, entries: list[dict[str, Any]]) -> None:
    memory_json_path(session_id).write_text(json.dumps(entries, indent=2))


def search_memory(session_id: str, query: str) -> str:
    query_lower = query.lower()
    matches = [item for item in list_memory(session_id) if query_lower in str(item.get("note", "")).lower()]
    if not matches:
        return "No matching memory found."
    return "\n".join(f"- #{item['id']} {item['created_at']}: {item['note']}" for item in matches)


def forget_memory(session_id: str, target: str) -> str:
    entries = list_memory(session_id)
    if not entries:
        return "No memory saved for this session."
    target = str(target).strip()
    if not target:
        return "No memory id or search text provided."
    removed = []
    kept = []
    for item in entries:
        note = str(item.get("note", ""))
        item_id = str(item.get("id", ""))
        if target == item_id or target.lower() in note.lower():
            removed.append(item)
        else:
            kept.append(item)
    if not removed:
        return "No matching memory found."
    _save_memory(session_id, kept)
    return f"Forgot {len(removed)} memory item(s)."


def edit_memory(session_id: str, memory_id: int, note: str) -> str:
    entries = list_memory(session_id)
    for item in entries:
        if int(item.get("id", 0)) == memory_id:
            item["note"] = note.strip()
            item["updated_at"] = _now()
            _save_memory(session_id, entries)
            return f"Updated memory #{memory_id}."
    return f"Memory #{memory_id} not found."


def session_status(session_id: str) -> dict[str, Any]:
    session = load_session(session_id)
    return {
        "id": session.get("id", session_id),
        "model": session.get("model"),
        "permission_profile": session.get("permission_profile"),
        "messages": len(session.get("messages", [])),
        "memories": len(list_memory(session_id)),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "session_path": str(session_path(session_id)),
        "memory_path": str(memory_json_path(session_id)),
    }


def update_session_settings(
    session_id: str,
    model: str | None = None,
    permission_profile: str | None = None,
) -> str:
    session = load_session(session_id)
    changes = []
    valid_profiles = {"readonly", "workspace-write", "network-allow", "shell-ask", "shell-allow", "messaging-allow"}
    if model is not None:
        session["model"] = model or None
        changes.append("model")
    if permission_profile is not None:
        if permission_profile and permission_profile not in valid_profiles:
            return f"Unknown permission profile: {permission_profile}"
        session["permission_profile"] = permission_profile or None
        changes.append("permission_profile")
    if not changes:
        return "No session settings changed."
    save_session(session)
    return f"Updated session settings: {', '.join(changes)}."


def auto_compact_session(session: dict[str, Any], threshold: int = 80, keep_last: int = 40) -> bool:
    messages = session.get("messages", [])
    if len(messages) <= threshold:
        return False
    older = messages[:-keep_last]
    summary_lines = []
    for msg in older:
        role = msg.get("role", "unknown")
        content = str(msg.get("content", ""))
        if content:
            summary_lines.append(f"{role}: {content[:300]}")
    session["messages"] = [
        {
            "role": "system",
            "content": "Automatically compacted prior conversation summary:\n" + "\n".join(summary_lines),
        }
    ] + messages[-keep_last:]
    return True


def export_session(session_id: str, output_path: str | None = None) -> str:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    export_path = Path(output_path).expanduser() if output_path else EXPORTS_DIR / f"{_safe_id(session_id)}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    if not export_path.is_absolute():
        export_path = WORKSPACE / export_path
    export_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "exported_at": _now(),
        "session": load_session(session_id),
        "memory": list_memory(session_id),
    }
    export_path.write_text(json.dumps(payload, indent=2))
    return f"Exported session to {export_path}"


def import_session(input_path: str, session_id: str | None = None) -> str:
    path = Path(input_path).expanduser()
    if not path.is_absolute():
        path = WORKSPACE / path
    payload = json.loads(path.read_text())
    session = payload.get("session", payload)
    target_id = session_id or session.get("id") or "default"
    session["id"] = target_id
    save_session(session)
    memory = payload.get("memory")
    if isinstance(memory, list):
        _save_memory(target_id, memory)
    return f"Imported session as {target_id}."


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
