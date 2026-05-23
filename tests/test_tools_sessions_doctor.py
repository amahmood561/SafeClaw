import json

from safeclaw.doctor import Check, doctor_summary
from safeclaw.sessions import (
    edit_memory,
    forget_memory,
    import_session,
    list_memory,
    recall,
    remember,
    search_memory,
    session_status,
)
from safeclaw.tools import list_files, run_tool, safe_path


def test_safe_path_blocks_workspace_escape():
    try:
        safe_path("../outside.txt")
    except ValueError as exc:
        assert "escapes workspace" in str(exc)
    else:
        raise AssertionError("safe_path should block path escape")


def test_file_tools_hide_safeclaw_internal_storage(workspace):
    internal = workspace / ".safeclaw_sessions"
    internal.mkdir()
    (internal / "desktop.json").write_text('{"secret": true}')
    (workspace / "visible.txt").write_text("visible")

    assert "visible.txt" in list_files(".")
    assert ".safeclaw_sessions" not in list_files(".")

    blocked = run_tool(
        "read_file",
        {"path": ".safeclaw_sessions/desktop.json"},
        permission_profile="readonly",
        interactive=False,
    )
    assert "internal storage" in blocked


def test_permission_profiles_block_and_allow_write():
    blocked = run_tool(
        "write_file",
        {"path": "test-permissions.txt", "content": "blocked"},
        permission_profile="readonly",
        interactive=False,
    )
    assert "Blocked by permission profile" in blocked

    needs_approval = run_tool(
        "write_file",
        {"path": "test-permissions.txt", "content": "blocked"},
        permission_profile="workspace-write",
        approval_mode="ask",
        interactive=False,
    )
    assert "requires interactive approval" in needs_approval

    allowed = run_tool(
        "write_file",
        {"path": "test-permissions.txt", "content": "allowed", "backup": False},
        permission_profile="workspace-write",
        approval_mode="auto",
        interactive=False,
    )
    assert "Wrote test-permissions.txt" in allowed


def test_structured_approval_events(monkeypatch, capsys):
    monkeypatch.setenv("SAFECLAW_EVENT_STREAM", "true")
    monkeypatch.setattr("builtins.input", lambda _prompt="": "n")

    denied = run_tool(
        "write_file",
        {"path": "approval-event.txt", "content": "blocked"},
        permission_profile="workspace-write",
        approval_mode="ask",
        interactive=True,
    )

    assert "Denied by user" in denied
    events = [
        json.loads(line.removeprefix("SAFECLAW_EVENT "))
        for line in capsys.readouterr().err.splitlines()
        if line.startswith("SAFECLAW_EVENT ")
    ]
    assert events[0]["type"] == "approval_required"
    assert events[0]["tool"] == "write_file"
    assert events[0]["reason"]
    assert events[-1] == {"type": "tool_blocked", "tool": "write_file", "profile": "workspace-write", "reason": "Denied by user: write_file"}


def test_search_edit_and_backup_flow():
    assert "Wrote test-edit.txt" in run_tool(
        "write_file",
        {"path": "test-edit.txt", "content": "alpha beta", "backup": False},
        permission_profile="workspace-write",
        approval_mode="auto",
        interactive=False,
    )
    assert "test-edit.txt" in run_tool(
        "search_files",
        {"query": "alpha", "path": "."},
        permission_profile="readonly",
        interactive=False,
    )
    edited = run_tool(
        "edit_file",
        {"path": "test-edit.txt", "old": "alpha", "new": "gamma"},
        permission_profile="workspace-write",
        approval_mode="auto",
        interactive=False,
    )
    assert "Edited test-edit.txt" in edited
    assert ".safeclaw_backups" in edited


def test_tool_depth_file_operations(workspace):
    created = run_tool(
        "create_file",
        {"path": "notes/a.txt", "content": "alpha"},
        permission_profile="workspace-write",
        approval_mode="auto",
        interactive=False,
    )
    assert "Created notes/a.txt" in created
    assert "Refusing to create existing file" in run_tool(
        "create_file",
        {"path": "notes/a.txt", "content": "again"},
        permission_profile="workspace-write",
        approval_mode="auto",
        interactive=False,
    )

    (workspace / "notes" / "b.txt").write_text("beta")
    many = run_tool(
        "read_many_files",
        {"paths": ["notes/a.txt", "notes/b.txt"]},
        permission_profile="readonly",
        interactive=False,
    )
    assert "## notes/a.txt" in many
    assert "alpha" in many
    assert "## notes/b.txt" in many

    diff = run_tool(
        "diff_file",
        {"path": "notes/a.txt", "proposed_content": "alpha\nnew\n"},
        permission_profile="readonly",
        interactive=False,
    )
    assert "--- notes/a.txt" in diff
    assert "+new" in diff

    moved = run_tool(
        "move_file",
        {"source": "notes/a.txt", "destination": "notes/moved.txt"},
        permission_profile="workspace-write",
        approval_mode="auto",
        interactive=False,
    )
    assert "Moved notes/a.txt to notes/moved.txt" in moved
    assert not (workspace / "notes" / "a.txt").exists()
    assert (workspace / "notes" / "moved.txt").exists()

    deleted = run_tool(
        "delete_file",
        {"path": "notes/moved.txt"},
        permission_profile="workspace-write",
        approval_mode="auto",
        interactive=False,
    )
    assert "Deleted notes/moved.txt" in deleted
    assert ".safeclaw_backups" in deleted
    assert not (workspace / "notes" / "moved.txt").exists()


def test_tool_depth_permissions_and_shell_guard(monkeypatch):
    assert "Blocked by permission profile" in run_tool(
        "delete_file",
        {"path": "missing.txt"},
        permission_profile="readonly",
        interactive=False,
    )
    assert "Test execution is disabled" in run_tool(
        "run_tests",
        {"command": "pytest"},
        permission_profile="shell-ask",
        approval_mode="auto",
        interactive=False,
    )


def test_memory_lifecycle():
    session = "pytest-memory"
    assert "Memory saved" in remember(session, "blue config")
    assert "blue config" in recall(session)
    assert "blue config" in search_memory(session, "blue")
    memory_id = int(list_memory(session)[0]["id"])
    assert "Updated memory" in edit_memory(session, memory_id, "green config")
    assert "green config" in recall(session)
    assert "Forgot 1" in forget_memory(session, str(memory_id))
    assert "No memory saved" in recall(session)


def test_session_export_import(tmp_path):
    session = "pytest-export"
    remember(session, "export me")
    export_path = tmp_path / "session.json"

    from safeclaw.sessions import export_session

    assert "Exported session" in export_session(session, str(export_path))
    payload = json.loads(export_path.read_text())
    assert payload["session"]["id"] == session
    assert payload["memory"][0]["note"] == "export me"

    assert "Imported session" in import_session(str(export_path), "pytest-imported")
    status = session_status("pytest-imported")
    assert status["id"] == "pytest-imported"
    assert status["memories"] == 1


def test_doctor_summary():
    assert doctor_summary([Check("Python", "ok", "3.10")]) == "all checks passed"
    assert doctor_summary([Check("Twilio", "warn", "missing")]) == "0 failures, 1 warning(s)"
    assert doctor_summary([Check("Key", "fail", "missing"), Check("Twilio", "warn", "missing")]) == "1 failure(s), 1 warning(s)"
