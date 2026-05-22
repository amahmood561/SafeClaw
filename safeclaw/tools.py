import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests

from .database import describe_database, describe_table, list_databases, run_readonly_query, test_database
from .config import (
    ALLOW_SHELL,
    APPROVAL_MODE,
    PERMISSION_PROFILE,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
    WORKSPACE,
)

MAX_TOOL_OUTPUT = 12000
MAX_READ_BYTES = 250000

READ_TOOLS = {"list_files", "read_file", "search_files"}
WRITE_TOOLS = {"write_file", "edit_file", "apply_patch"}
NETWORK_TOOLS = {"fetch_url", "web_search"}
SHELL_TOOLS = {"shell"}
MESSAGING_TOOLS = {"send_whatsapp"}
DATABASE_TOOLS = {"list_databases", "test_database", "describe_database", "describe_table", "run_readonly_query"}
RISKY_TOOLS = WRITE_TOOLS | NETWORK_TOOLS | SHELL_TOOLS | MESSAGING_TOOLS
EVENT_PREFIX = "SAFECLAW_EVENT "

PROFILE_CAPABILITIES = {
    "readonly": READ_TOOLS,
    "workspace-write": READ_TOOLS | WRITE_TOOLS,
    "network-allow": READ_TOOLS | NETWORK_TOOLS,
    "shell-ask": READ_TOOLS | SHELL_TOOLS,
    "shell-allow": READ_TOOLS | SHELL_TOOLS,
    "messaging-allow": READ_TOOLS | MESSAGING_TOOLS,
    "db-readonly": READ_TOOLS | DATABASE_TOOLS,
}


def safe_path(path: str) -> Path:
    target = (WORKSPACE / path).resolve()
    try:
        target.relative_to(WORKSPACE)
    except ValueError:
        raise ValueError("Path escapes workspace")
    return target


def _trim_output(value: str, limit: int = MAX_TOOL_OUTPUT) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n\n[trimmed {len(value) - limit} characters]"


def _backup_file(target: Path) -> Path:
    backups = WORKSPACE / ".safeclaw_backups"
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    relative = target.relative_to(WORKSPACE)
    safe_name = "__".join(relative.parts)
    backup = backups / f"{safe_name}.{stamp}.bak"
    backup.write_bytes(target.read_bytes())
    return backup


def _normal_profile(permission_profile: str | None = None) -> str:
    profile = permission_profile or PERMISSION_PROFILE or "readonly"
    return profile if profile in PROFILE_CAPABILITIES else "readonly"


def _preview_arguments(arguments: dict[str, Any], limit: int = 500) -> str:
    redacted = dict(arguments)
    for key in list(redacted):
        if key.lower() in {"content", "patch", "body"}:
            value = str(redacted[key])
            redacted[key] = value[:200] + ("..." if len(value) > 200 else "")
    text = repr(redacted)
    return text[:limit] + ("..." if len(text) > limit else "")


def _event_stream_enabled() -> bool:
    return os.getenv("SAFECLAW_EVENT_STREAM", "").lower() in {"1", "true", "yes"}


def _emit_event(event: dict[str, Any]) -> None:
    if not _event_stream_enabled():
        return
    print(f"{EVENT_PREFIX}{json.dumps(event, default=str)}", file=sys.stderr, flush=True)


def _approval_subject(tool_name: str, arguments: dict[str, Any]) -> str:
    if tool_name == "shell":
        return str(arguments.get("command", ""))
    if tool_name in {"write_file", "edit_file", "read_file"}:
        return str(arguments.get("path", ""))
    if tool_name == "apply_patch":
        return _preview_arguments({"patch": arguments.get("patch", "")}, limit=700)
    if tool_name == "fetch_url":
        return str(arguments.get("url", ""))
    if tool_name == "web_search":
        return str(arguments.get("query", ""))
    if tool_name == "send_whatsapp":
        return f"{arguments.get('to', '')}: {str(arguments.get('body', ''))[:160]}"
    return _preview_arguments(arguments)


def _approval_reason(tool_name: str) -> str:
    if tool_name in WRITE_TOOLS:
        return "This action can change files in the workspace."
    if tool_name in SHELL_TOOLS:
        return "This action can execute a shell command on this machine."
    if tool_name in NETWORK_TOOLS:
        return "This action can fetch data from the network."
    if tool_name in MESSAGING_TOOLS:
        return "This action can send a WhatsApp message outside this machine."
    return "This action requires explicit approval."


def _approval_required(tool_name: str, profile: str, approval_mode: str) -> bool:
    if approval_mode == "auto":
        return False
    if tool_name == "shell" and profile == "shell-allow":
        return False
    return tool_name in RISKY_TOOLS


def _ask_approval(tool_name: str, arguments: dict[str, Any], profile: str, approval_mode: str, interactive: bool) -> str | None:
    if approval_mode == "deny":
        return f"Blocked by approval mode: {tool_name} requires approval."
    if not _approval_required(tool_name, profile, approval_mode):
        return None
    if not interactive:
        return f"Blocked: {tool_name} requires interactive approval."
    if not sys.stdin.isatty() and not _event_stream_enabled():
        return f"Blocked: {tool_name} requires terminal approval."
    _emit_event({
        "type": "approval_required",
        "tool": tool_name,
        "profile": profile,
        "approval_mode": approval_mode,
        "reason": _approval_reason(tool_name),
        "subject": _approval_subject(tool_name, arguments),
        "arguments_preview": _preview_arguments(arguments),
    })
    print("\nSafeClaw approval required", file=sys.stderr)
    print(f"Tool: {tool_name}", file=sys.stderr)
    print(f"Profile: {profile}", file=sys.stderr)
    print(f"Args: {_preview_arguments(arguments)}", file=sys.stderr)
    answer = input("Allow this action? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        _emit_event({"type": "approval_decision", "tool": tool_name, "decision": "denied"})
        return f"Denied by user: {tool_name}"
    _emit_event({"type": "approval_decision", "tool": tool_name, "decision": "allowed"})
    return None


def _permission_error(tool_name: str, profile: str) -> str | None:
    allowed = PROFILE_CAPABILITIES[_normal_profile(profile)]
    if tool_name in allowed:
        return None
    return f"Blocked by permission profile '{profile}': {tool_name} is not allowed."


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
    data = target.read_bytes()
    if len(data) > MAX_READ_BYTES:
        data = data[:MAX_READ_BYTES]
        suffix = f"\n\n[trimmed file after {MAX_READ_BYTES} bytes]"
    else:
        suffix = ""
    return data.decode(errors="replace") + suffix


def write_file(path: str, content: str, backup: bool = True, overwrite: bool = True) -> str:
    target = safe_path(path)
    backup_message = ""
    if target.exists():
        if not overwrite:
            return f"Refusing to overwrite existing file: {target.relative_to(WORKSPACE)}"
        if backup:
            backup_path = _backup_file(target)
            backup_message = f" Backup saved to {backup_path.relative_to(WORKSPACE)}."
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"Wrote {target.relative_to(WORKSPACE)}.{backup_message}"


def search_files(query: str, path: str = ".", include_content: bool = True, max_results: int = 50) -> str:
    base = safe_path(path)
    if not base.exists():
        return f"Not found: {path}"
    query_lower = query.lower()
    results: list[str] = []
    for item in sorted(base.rglob("*")):
        if len(results) >= max_results:
            break
        if not item.is_file():
            continue
        relative = str(item.relative_to(WORKSPACE))
        if query_lower in relative.lower():
            results.append(relative)
            continue
        if not include_content:
            continue
        try:
            text = item.read_text(errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if query_lower in line.lower():
                results.append(f"{relative}:{line_no}: {line.strip()[:200]}")
                break
    return "\n".join(results) or "No matches found."


def edit_file(path: str, old: str, new: str, replace_all: bool = False, backup: bool = True) -> str:
    target = safe_path(path)
    if not target.exists():
        return f"Not found: {path}"
    text = target.read_text(errors="replace")
    count = text.count(old)
    if count == 0:
        return "No matching text found."
    if count > 1 and not replace_all:
        return f"Found {count} matches. Set replace_all=true to replace all matches."
    updated = text.replace(old, new) if replace_all else text.replace(old, new, 1)
    backup_message = ""
    if backup:
        backup_path = _backup_file(target)
        backup_message = f" Backup saved to {backup_path.relative_to(WORKSPACE)}."
    target.write_text(updated)
    replaced = count if replace_all else 1
    return f"Edited {target.relative_to(WORKSPACE)}; replaced {replaced} occurrence(s).{backup_message}"


def apply_patch(patch: str, backup: bool = True) -> str:
    if not patch.strip():
        return "No patch provided."
    if backup:
        for line in patch.splitlines():
            if not line.startswith(("--- ", "+++ ")):
                continue
            patch_path = line[4:].strip()
            if patch_path == "/dev/null":
                continue
            if patch_path.startswith(("a/", "b/")):
                patch_path = patch_path[2:]
            target = safe_path(patch_path)
            if target.exists() and target.is_file():
                _backup_file(target)
    check = subprocess.run(
        ["git", "apply", "--check", "-"],
        cwd=WORKSPACE,
        input=patch,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if check.returncode != 0:
        return f"Patch check failed:\n{check.stderr.strip()}"
    result = subprocess.run(
        ["git", "apply", "-"],
        cwd=WORKSPACE,
        input=patch,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return f"Patch apply failed:\n{result.stderr.strip()}"
    return "Patch applied."


def fetch_url(url: str, max_chars: int = 12000) -> str:
    response = requests.get(url, timeout=30, headers={"User-Agent": "SafeClaw/0.1"})
    content_type = response.headers.get("content-type", "")
    response.raise_for_status()
    body = response.text
    return _trim_output(f"URL: {url}\nStatus: {response.status_code}\nContent-Type: {content_type}\n\n{body}", max_chars)


def web_search(query: str, max_results: int = 5) -> str:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    response = requests.get(url, timeout=30, headers={"User-Agent": "SafeClaw/0.1"})
    response.raise_for_status()
    lines = []
    pattern = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
    for href, title in pattern.findall(response.text):
        clean_title = html.unescape(re.sub(r"<[^>]+>", "", title))
        clean_title = " ".join(clean_title.split())
        clean_url = html.unescape(href)
        parsed = urlparse(clean_url)
        if parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            if target:
                clean_url = unquote(target)
        if not clean_title:
            continue
        lines.append(f"{clean_title}\n{clean_url}")
        if len(lines) >= max_results:
            break
    if not lines:
        return f"No search results parsed. Raw search page: {url}"
    return "\n".join(lines)


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
                    "backup": {"type": "boolean", "default": True},
                    "overwrite": {"type": "boolean", "default": True},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search file names and optionally file contents under a workspace path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                    "include_content": {"type": "boolean", "default": True},
                    "max_results": {"type": "integer", "default": 50},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace text in a workspace file, creating a backup by default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                    "replace_all": {"type": "boolean", "default": False},
                    "backup": {"type": "boolean", "default": True},
                },
                "required": ["path", "old", "new"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_patch",
            "description": "Apply a unified diff patch inside the workspace, backing up changed files by default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patch": {"type": "string"},
                    "backup": {"type": "boolean", "default": True},
                },
                "required": ["patch"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch a URL and return a trimmed text response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "max_chars": {"type": "integer", "default": 12000},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using a simple public search page and return parsed result snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
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
    {
        "type": "function",
        "function": {
            "name": "list_databases",
            "description": "List configured read-only databases.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "test_database",
            "description": "Test a configured read-only database connection.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_database",
            "description": "List tables and row counts for a configured read-only database.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_table",
            "description": "Describe columns for a table in a configured read-only database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "table": {"type": "string"},
                },
                "required": ["name", "table"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_readonly_query",
            "description": "Run one read-only SQLite SELECT/WITH/EXPLAIN query against a configured database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["name", "query"],
            },
        },
    },
]


def run_tool(
    name: str,
    arguments: dict[str, Any],
    permission_profile: str | None = None,
    approval_mode: str | None = None,
    interactive: bool = True,
) -> str:
    functions = {
        "list_files": list_files,
        "read_file": read_file,
        "write_file": write_file,
        "search_files": search_files,
        "edit_file": edit_file,
        "apply_patch": apply_patch,
        "fetch_url": fetch_url,
        "web_search": web_search,
        "shell": shell,
        "send_whatsapp": send_whatsapp,
        "list_databases": list_databases,
        "test_database": test_database,
        "describe_database": describe_database,
        "describe_table": describe_table,
        "run_readonly_query": run_readonly_query,
    }
    if name not in functions:
        return f"Unknown tool: {name}"
    profile = _normal_profile(permission_profile)
    blocked = _permission_error(name, profile)
    if blocked:
        _emit_event({"type": "tool_blocked", "tool": name, "profile": profile, "reason": blocked})
        return blocked
    approval = _ask_approval(name, arguments, profile, approval_mode or APPROVAL_MODE, interactive)
    if approval:
        _emit_event({"type": "tool_blocked", "tool": name, "profile": profile, "reason": approval})
        return approval
    try:
        _emit_event({"type": "tool_started", "tool": name, "arguments_preview": _preview_arguments(arguments)})
        result = str(functions[name](**arguments))
        _emit_event({"type": "tool_result", "tool": name, "content": _trim_output(result, 3000)})
        return result
    except Exception as exc:
        result = f"Tool error in {name}: {exc}"
        _emit_event({"type": "tool_error", "tool": name, "content": result})
        return result


def available_tools() -> str:
    return """
Available local tools:
- list_files(path='.')
- read_file(path)
- write_file(path, content, backup=True, overwrite=True)
- search_files(query, path='.', include_content=True)
- edit_file(path, old, new, replace_all=False, backup=True)
- apply_patch(patch, backup=True)
- fetch_url(url)
- web_search(query)
- shell(command) disabled unless ALLOW_SHELL=true
- send_whatsapp(to, body) if Twilio env vars are configured
- list_databases()
- test_database(name)
- describe_database(name)
- describe_table(name, table)
- run_readonly_query(name, query, limit=50)

Permission profiles:
- readonly: read/list/search workspace files only
- workspace-write: readonly plus write_file/edit_file/apply_patch
- network-allow: readonly plus fetch_url/web_search
- shell-ask: readonly plus shell with approval and ALLOW_SHELL=true
- shell-allow: readonly plus shell without approval and ALLOW_SHELL=true
- messaging-allow: readonly plus send_whatsapp
- db-readonly: readonly plus configured read-only database tools

This version supports automatic OpenAI-style function calling.
""".strip()
