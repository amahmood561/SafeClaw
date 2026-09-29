import json
import sys
from datetime import datetime
from typing import Any, Callable

from concurrent.futures import ThreadPoolExecutor

from .config import MAX_TOOL_STEPS, MODEL, WORKSPACE
from .llm import complete_message, complete_message_stream
from .sessions import auto_compact_session, forget_memory, load_session, recall, remember, save_session, search_memory, session_status
from .tools import READ_TOOLS, TOOL_SPECS, available_tools, list_files, run_tool

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
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Search durable memory notes for this session.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget",
            "description": "Delete durable memory notes by id or matching text for this session.",
            "parameters": {
                "type": "object",
                "properties": {"target": {"type": "string"}},
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "session_status",
            "description": "Return current session status including message and memory counts.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

EventCallback = Callable[[dict[str, Any]], None]


def emit_event(event: dict[str, Any]) -> None:
    print(f"SAFECLAW_EVENT {json.dumps(event, default=str)}", file=sys.stderr, flush=True)


def _tool_message(
    session_id: str,
    tool_call: dict[str, Any],
    permission_profile: str | None = None,
    interactive: bool = True,
    event_callback: EventCallback | None = None,
) -> dict[str, str]:
    name = tool_call["function"]["name"]
    if event_callback:
        event_callback({
            "type": "tool_call",
            "tool": name,
            "arguments": tool_call["function"].get("arguments") or "{}",
        })
    try:
        arguments = json.loads(tool_call["function"].get("arguments") or "{}")
    except json.JSONDecodeError as exc:
        result = f"Invalid tool arguments: {exc}"
    else:
        if name == "remember":
            result = remember(session_id, arguments.get("note", ""))
        elif name == "recall_memory":
            result = recall(session_id)
        elif name == "search_memory":
            result = search_memory(session_id, arguments.get("query", ""))
        elif name == "forget":
            result = forget_memory(session_id, arguments.get("target", ""))
        elif name == "session_status":
            result = json.dumps(session_status(session_id), indent=2)
        else:
            try:
                result = run_tool(name, arguments, permission_profile=permission_profile, interactive=interactive)
            except Exception as exc:
                # A raising tool used to abort the whole task. The model can almost
                # always recover from a failure it is told about, so hand it back
                # as a normal tool result instead of losing the turn.
                result = f"Tool {name} failed: {type(exc).__name__}: {exc}"
                if event_callback:
                    event_callback({"type": "tool_error", "tool": name, "content": result})
    if event_callback:
        event_callback({
            "type": "tool_message",
            "tool": name,
            "content": result,
        })
    return {
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "name": name,
        "content": result,
    }


def run_task(
    task: str,
    session_id: str = "default",
    model: str | None = None,
    permission_profile: str | None = None,
    interactive: bool = True,
    event_callback: EventCallback | None = None,
) -> str:
    session = load_session(session_id)
    if model:
        session["model"] = model
    if permission_profile:
        session["permission_profile"] = permission_profile
    active_model = session.get("model") or MODEL
    active_profile = session.get("permission_profile") or permission_profile

    context = f"""
Workspace: {WORKSPACE}
Current files:
{list_files('.')}

Memory for this session:
{recall(session_id)}

{available_tools()}

Current permission profile: {active_profile or "readonly"}

User task:
{task}
"""
    session["messages"].append({"role": "user", "content": context})
    used_tools = False
    tools_used: list[str] = []
    if event_callback:
        event_callback({
            "type": "task_started",
            "session": session_id,
            "model": active_model,
            "permission_profile": active_profile or "readonly",
        })

    for _ in range(MAX_TOOL_STEPS):
        message = complete_message(session["messages"], tools=TOOL_SPECS + SESSION_TOOL_SPECS, model=active_model)
        session["messages"].append(message)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            result = message.get("content", "")
            if event_callback and result:
                if used_tools:
                    # After tool execution, ask for the final answer as a streamed synthesis.
                    stream_messages = session["messages"][:-1]
                    result_parts: list[str] = []
                    event_callback({"type": "assistant_stream_start"})
                    try:
                        for delta in complete_message_stream(stream_messages, model=active_model):
                            result_parts.append(delta)
                            event_callback({"type": "assistant_delta", "content": delta})
                    except Exception as exc:
                        event_callback({"type": "assistant_stream_error", "content": str(exc)})
                    streamed = "".join(result_parts).strip()
                    if streamed:
                        result = streamed
                        session["messages"][-1]["content"] = result
                    event_callback({"type": "assistant_message", "content": result})
                else:
                    event_callback({"type": "assistant_message", "content": result})
            break
        used_tools = True
        for tool_call in tool_calls:
            tools_used.append(tool_call["function"]["name"])

        run_one = lambda call: _tool_message(
            session_id,
            call,
            permission_profile=active_profile,
            interactive=interactive,
            event_callback=event_callback,
        )

        # Independent reads can run at once. Anything that writes, or that might
        # stop to ask for approval, stays strictly sequential -- order and the
        # approval prompts both matter there.
        names = [c["function"]["name"] for c in tool_calls]
        if len(tool_calls) > 1 and all(n in READ_TOOLS for n in names):
            with ThreadPoolExecutor(max_workers=min(len(tool_calls), 8)) as pool:
                messages = list(pool.map(run_one, tool_calls))
        else:
            messages = [run_one(call) for call in tool_calls]
        session["messages"].extend(messages)

        # Compact inside the loop, not only at the end. A fifty-step task used to
        # carry every message to the final call.
        auto_compact_session(session)
    else:
        # Do not throw away the work. Say what was done and where it stopped.
        summary = ", ".join(dict.fromkeys(tools_used)) or "nothing"
        result = (
            f"Stopped after the {MAX_TOOL_STEPS}-step tool limit. "
            f"Used {len(tools_used)} tool calls ({summary}). "
            "Raise MAX_TOOL_STEPS or ask for a narrower next step to continue."
        )

    logs = WORKSPACE / ".safeclaw_logs"
    logs.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (logs / f"task-{stamp}.md").write_text(f"# Task\n\n{task}\n\n# Result\n\n{result}\n")
    auto_compact_session(session)
    save_session(session)
    if event_callback:
        event_callback({"type": "task_done", "session": session_id, "content": result})
    return result


def add_memory(session_id: str, note: str) -> str:
    return remember(session_id, note)


def get_history(session_id: str) -> list[dict[str, Any]]:
    return load_session(session_id).get("messages", [])
