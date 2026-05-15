import json
from datetime import datetime
from typing import Any

from .config import MAX_TOOL_STEPS, MODEL, WORKSPACE
from .llm import complete_message
from .sessions import load_session, recall, remember, save_session
from .tools import TOOL_SPECS, available_tools, list_files, run_tool

SESSION_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Save a durable memory note for this session.",
            "parameters": {
                "type": "object",
                "properties": {"note": {"type": "string"}},
                "required": ["note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Read durable memory notes for this session.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _tool_message(session_id: str, tool_call: dict[str, Any]) -> dict[str, str]:
    name = tool_call["function"]["name"]
    try:
        arguments = json.loads(tool_call["function"].get("arguments") or "{}")
    except json.JSONDecodeError as exc:
        result = f"Invalid tool arguments: {exc}"
    else:
        if name == "remember":
            result = remember(session_id, arguments.get("note", ""))
        elif name == "recall_memory":
            result = recall(session_id)
        else:
            result = run_tool(name, arguments)
    return {
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "name": name,
        "content": result,
    }


def run_task(task: str, session_id: str = "default", model: str | None = None) -> str:
    session = load_session(session_id)
    if model:
        session["model"] = model
    active_model = session.get("model") or MODEL

    context = f"""
Workspace: {WORKSPACE}
Current files:
{list_files('.')}

Memory for this session:
{recall(session_id)}

{available_tools()}

User task:
{task}
"""
    session["messages"].append({"role": "user", "content": context})

    for _ in range(MAX_TOOL_STEPS):
        message = complete_message(session["messages"], tools=TOOL_SPECS + SESSION_TOOL_SPECS, model=active_model)
        session["messages"].append(message)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            result = message.get("content", "")
            break
        for tool_call in tool_calls:
            session["messages"].append(_tool_message(session_id, tool_call))
    else:
        result = "Stopped after reaching the tool step limit."

    logs = WORKSPACE / ".safeclaw_logs"
    logs.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (logs / f"task-{stamp}.md").write_text(f"# Task\n\n{task}\n\n# Result\n\n{result}\n")
    save_session(session)
    return result


def add_memory(session_id: str, note: str) -> str:
    return remember(session_id, note)


def get_history(session_id: str) -> list[dict[str, Any]]:
    return load_session(session_id).get("messages", [])
