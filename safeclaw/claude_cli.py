"""Use a local Claude Code login as SafeClaw's model. No API key.

Why this exists: every other provider needs a key pasted into .env. If someone
already has Claude Code installed and logged in, that is an OAuth session they
control, and SafeClaw can borrow it by shelling out to `claude -p`.

Two rules shape the whole module.

1. **Claude is the brain. SafeClaw keeps the hands.** Claude Code's own tools are
   disabled with --disallowed-tools. If they were left on, Claude Code would read
   and write files under *its* permission model and SafeClaw's profiles would be
   bypassed, which would remove the only reason SafeClaw exists.

2. **SafeClaw owns the conversation.** Each call sends the full rendered history
   rather than using --resume. SafeClaw compacts its own history; a resumed CLI
   session would keep everything, so the two would silently diverge. Stateless is
   slower but it cannot drift.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import uuid

from .llm import SYSTEM_PROMPT, LLMError

# Everything Claude Code can do on its own. SafeClaw performs the actions.
DISALLOWED = [
    "Bash", "Edit", "Write", "Read", "Glob", "Grep", "WebFetch", "WebSearch",
    "Task", "NotebookEdit", "TodoWrite", "BashOutput", "KillShell",
]

TOOL_PROTOCOL = """
To use a tool, reply with ONLY a JSON object and nothing else:
{"tool_calls":[{"name":"<tool name>","arguments":{...}}]}

No prose before or after it, and no markdown fence. Request several tools at once
by adding more entries to the list.

You have no direct access to this machine. You cannot see any file, directory,
database or command output unless it appears above as the result of a tool call.

If a question is about the state of this machine and you do not already have a
tool result answering it, you MUST request a tool. Describing files you have not
listed, or contents you have not read, is a failure even when the guess is
plausible. Answer in prose only when the question needs no tool, or when a tool
result above already answers it.
"""

ROLE_LABEL = {"user": "User", "assistant": "Assistant", "system": "System"}


def is_available() -> bool:
    return shutil.which("claude") is not None


def _render_tools(tools: list[dict] | None) -> str:
    if not tools:
        return ""
    lines = ["You have these tools available:", ""]
    for spec in tools:
        fn = spec.get("function", spec)
        params = fn.get("parameters", {}).get("properties", {})
        args = ", ".join(f"{k}: {v.get('type','any')}" for k, v in params.items())
        lines.append(f"- {fn.get('name')}({args}) - {fn.get('description','')}".rstrip())
    return "\n".join(lines) + "\n" + TOOL_PROTOCOL


def build_system_prompt(tools: list[dict] | None = None) -> str:
    """SafeClaw's system prompt, which fully replaces Claude Code's.

    Appending was not enough. Claude Code's own prompt describes a coding
    assistant with its own tools, so with those tools disallowed it explained
    what it could not do instead of requesting a SafeClaw tool.
    """
    parts = [SYSTEM_PROMPT.strip()]
    if tools:
        parts.append(_render_tools(tools))
    return "\n\n".join(parts)


def render_prompt(messages: list[dict], tools: list[dict] | None = None) -> str:
    """Flatten an OpenAI-style history into one user-turn prompt."""
    parts: list[str] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content") or ""
        if role == "tool":
            # The result of something SafeClaw actually ran. Label it clearly so
            # the model treats it as observed fact rather than its own suggestion.
            parts.append(f"Result of {message.get('name','tool')}:\n{content}")
        elif role == "assistant" and message.get("tool_calls"):
            requested = ", ".join(c["function"]["name"] for c in message["tool_calls"])
            parts.append(f"Assistant: (requested {requested})")
        elif content:
            parts.append(f"{ROLE_LABEL.get(role, role)}: {content}")
    return "\n\n".join(p for p in parts if p).strip()


def parse_reply(text: str) -> dict:
    """Turn Claude's text back into an OpenAI-shaped assistant message.

    Tolerant on purpose: a model that wraps the JSON in a fence, or adds a
    sentence before it, should still work rather than silently losing the call.
    """
    stripped = (text or "").strip()
    candidate = stripped
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.S)
    if fence:
        candidate = fence.group(1)
    elif not stripped.startswith("{"):
        brace = re.search(r'(\{\s*"tool_calls".*\})', stripped, re.S)
        if brace:
            candidate = brace.group(1)

    try:
        payload = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return {"role": "assistant", "content": stripped}

    calls = payload.get("tool_calls") if isinstance(payload, dict) else None
    if not isinstance(calls, list) or not calls:
        return {"role": "assistant", "content": stripped}

    tool_calls = []
    for call in calls:
        name = call.get("name") or call.get("function", {}).get("name")
        if not name:
            continue
        arguments = call.get("arguments", call.get("function", {}).get("arguments", {}))
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments)
        tool_calls.append({
            "id": f"call_{uuid.uuid4().hex[:12]}",
            "type": "function",
            "function": {"name": name, "arguments": arguments},
        })
    if not tool_calls:
        return {"role": "assistant", "content": stripped}
    return {"role": "assistant", "content": "", "tool_calls": tool_calls}


def invoke(prompt: str, system: str | None = None, model: str | None = None,
           timeout: int = 300, cwd: str | None = None) -> dict:
    """Run one `claude -p` call. Returns {content, cost, session_id}."""
    if not is_available():
        raise LLMError(
            "The `claude` command was not found. Install Claude Code and run `claude` once to log in, "
            "or choose another provider with `safeclaw init --force`."
        )
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "json",
        # No session state, and per-machine context (cwd, git, memory paths) kept
        # out of the system prompt. Without these the reply drifts into whatever
        # else that login has been doing.
        "--no-session-persistence",
        "--exclude-dynamic-system-prompt-sections",
        "--disallowed-tools", ",".join(DISALLOWED),
    ]
    if system:
        cmd += ["--system-prompt", system]
    if model:
        cmd += ["--model", model]

    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired:
        raise LLMError(f"claude did not respond within {timeout}s.")
    except OSError as exc:
        raise LLMError(f"Could not run claude: {exc}")

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()[:400]
        raise LLMError(f"claude exited {completed.returncode}: {detail}")

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise LLMError(f"Unexpected output from claude: {completed.stdout[:300]}")

    if data.get("is_error"):
        raise LLMError(data.get("result") or "claude reported an error")

    return {
        "content": data.get("result", ""),
        "cost": data.get("total_cost_usd"),
        "session_id": data.get("session_id"),
        "turns": data.get("num_turns"),
    }


def complete_message(messages, tools=None, model=None) -> dict:
    result = invoke(
        render_prompt(messages),
        system=build_system_prompt(tools),
        model=model,
    )
    message = parse_reply(result["content"])
    # Surfaced so the caller can show a running meter. This is billed to the
    # user's own Claude subscription, and a fifty-step task is real money.
    message["_cost_usd"] = result["cost"]
    return message
