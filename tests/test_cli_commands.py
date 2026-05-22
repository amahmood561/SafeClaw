from typer.testing import CliRunner

from safeclaw import cli
from safeclaw.doctor import Check


runner = CliRunner()


def invoke(*args, input=None):
    return runner.invoke(cli.app, list(args), input=input)


def test_help_lists_all_commands():
    result = invoke("--help")
    assert result.exit_code == 0
    for command in [
        "run",
        "chat",
        "tools",
        "doctor",
        "sessions",
        "status",
        "session-config",
        "reset",
        "compact",
        "memory",
        "memory-search",
        "memory-forget",
        "memory-edit",
        "export",
        "import",
        "db-list",
        "db-test",
        "db-schema",
        "db-table",
        "db-query",
        "whatsapp",
        "whatsapp-setup",
        "service-install",
        "service-start",
        "service-stop",
        "service-status",
        "service-uninstall",
    ]:
        assert command in result.output


def test_run_command_calls_agent(monkeypatch):
    calls = {}

    def fake_run_task(task, session_id="default", model=None, permission_profile=None, interactive=True):
        calls.update(
            task=task,
            session_id=session_id,
            model=model,
            permission_profile=permission_profile,
            interactive=interactive,
        )
        return "task-result"

    monkeypatch.setattr(cli, "run_task", fake_run_task)
    result = invoke("run", "hello", "--session", "s1", "--model", "m1", "--permission-profile", "readonly")

    assert result.exit_code == 0
    assert "task-result" in result.output
    assert calls == {
        "task": "hello",
        "session_id": "s1",
        "model": "m1",
        "permission_profile": "readonly",
        "interactive": True,
    }


def test_run_command_can_emit_structured_events(monkeypatch):
    calls = {}

    def fake_run_task(task, session_id="default", model=None, permission_profile=None, interactive=True, event_callback=None):
        calls.update(event_callback=event_callback)
        if event_callback:
            event_callback({"type": "task_done", "session": session_id, "content": "ok"})
        return "task-result"

    monkeypatch.setattr(cli, "run_task", fake_run_task)
    result = invoke("run", "hello", "--session", "s1", "--events")

    assert result.exit_code == 0
    assert "task-result" in result.output
    assert "SAFECLAW_EVENT" in result.stderr
    assert '"type": "task_done"' in result.stderr
    assert calls["event_callback"] is not None


def test_chat_command_handles_memory_reset_and_task(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "recall", lambda session: f"memory:{session}")
    monkeypatch.setattr(cli, "reset_session", lambda session: calls.append(("reset", session)))

    def fake_run_task(task, session_id="default", model=None, permission_profile=None, interactive=True):
        calls.append(("run", task, session_id, model, permission_profile, interactive))
        return "chat-result"

    monkeypatch.setattr(cli, "run_task", fake_run_task)
    result = invoke(
        "chat",
        "--session",
        "chat1",
        "--model",
        "m1",
        "--permission-profile",
        "readonly",
        input="memory\nreset\nhello\nexit\n",
    )

    assert result.exit_code == 0
    assert "memory:chat1" in result.output
    assert "Session reset" in result.output
    assert "chat-result" in result.output
    assert ("reset", "chat1") in calls
    assert ("run", "hello", "chat1", "m1", "readonly", True) in calls


def test_tools_command_shows_available_tools(monkeypatch):
    monkeypatch.setattr(cli, "available_tools", lambda: "tool-list")
    result = invoke("tools")

    assert result.exit_code == 0
    assert "tool-list" in result.output


def test_doctor_command_prints_summary(monkeypatch):
    monkeypatch.setattr(cli, "run_doctor", lambda port=8080: [Check("Python", "ok", "3.10")])
    monkeypatch.setattr(cli, "doctor_summary", lambda checks: "all checks passed")

    result = invoke("doctor", "--port", "9999")

    assert result.exit_code == 0
    assert "SafeClaw Doctor" in result.output
    assert "Python" in result.output
    assert "all checks passed" in result.output


def test_doctor_strict_exits_nonzero_on_failure(monkeypatch):
    monkeypatch.setattr(cli, "run_doctor", lambda port=8080: [Check("OpenAI API key", "fail", "missing")])
    monkeypatch.setattr(cli, "doctor_summary", lambda checks: "1 failure(s), 0 warning(s)")

    result = invoke("doctor", "--strict")

    assert result.exit_code == 1
    assert "OpenAI API key" in result.output


def test_sessions_command_lists_sessions(monkeypatch):
    monkeypatch.setattr(cli, "list_sessions", lambda: [{"id": "default", "messages": 2}])
    result = invoke("sessions")

    assert result.exit_code == 0
    assert "default" in result.output


def test_status_command(monkeypatch):
    monkeypatch.setattr(cli, "session_status", lambda session: {"id": session, "messages": 0})
    result = invoke("status", "--session", "s1")

    assert result.exit_code == 0
    assert "s1" in result.output


def test_session_config_command(monkeypatch):
    calls = {}

    def fake_update(session, model=None, permission_profile=None):
        calls.update(session=session, model=model, permission_profile=permission_profile)
        return "updated"

    monkeypatch.setattr(cli, "update_session_settings", fake_update)
    result = invoke("session-config", "--session", "s1", "--model", "m1", "--permission-profile", "readonly")

    assert result.exit_code == 0
    assert "updated" in result.output
    assert calls == {"session": "s1", "model": "m1", "permission_profile": "readonly"}


def test_reset_command(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "reset_session", lambda session: calls.append(session))

    result = invoke("reset", "--session", "s1")

    assert result.exit_code == 0
    assert "Reset session: s1" in result.output
    assert calls == ["s1"]


def test_compact_command(monkeypatch):
    monkeypatch.setattr(cli, "compact_session", lambda session, keep_last=12: f"compacted:{session}:{keep_last}")
    result = invoke("compact", "--session", "s1", "--keep-last", "3")

    assert result.exit_code == 0
    assert "compacted:s1:3" in result.output


def test_memory_commands(monkeypatch):
    monkeypatch.setattr(cli, "recall", lambda session: f"memory:{session}")
    monkeypatch.setattr(cli, "search_memory", lambda session, query: f"search:{session}:{query}")
    monkeypatch.setattr(cli, "forget_memory", lambda session, target: f"forget:{session}:{target}")
    monkeypatch.setattr(cli, "edit_memory", lambda session, memory_id, note: f"edit:{session}:{memory_id}:{note}")

    assert "memory:s1" in invoke("memory", "--session", "s1").output
    assert "search:s1:blue" in invoke("memory-search", "blue", "--session", "s1").output
    assert "forget:s1:blue" in invoke("memory-forget", "blue", "--session", "s1").output
    assert "edit:s1:1:new note" in invoke("memory-edit", "1", "new note", "--session", "s1").output


def test_export_import_commands(monkeypatch):
    monkeypatch.setattr(cli, "export_session", lambda session, output=None: f"export:{session}:{output}")
    monkeypatch.setattr(cli, "import_session", lambda path, session_id=None: f"import:{path}:{session_id}")

    assert "export:s1:out.json" in invoke("export", "--session", "s1", "--output", "out.json").output
    assert "import:out.json:s2" in invoke("import", "out.json", "--session", "s2").output


def test_database_commands(monkeypatch):
    monkeypatch.setattr(cli, "list_databases", lambda: "db-list")
    monkeypatch.setattr(cli, "test_database", lambda name: f"db-test:{name}")
    monkeypatch.setattr(cli, "describe_database", lambda name: f"db-schema:{name}")
    monkeypatch.setattr(cli, "describe_table", lambda name, table: f"db-table:{name}:{table}")
    monkeypatch.setattr(cli, "run_readonly_query", lambda name, query, limit=50: f"db-query:{name}:{query}:{limit}")

    assert "db-list" in invoke("db-list").output
    assert "db-test:app" in invoke("db-test", "app").output
    assert "db-schema:app" in invoke("db-schema", "app").output
    assert "db-table:app:users" in invoke("db-table", "app", "users").output
    assert "db-query:app:select 1:3" in invoke("db-query", "app", "select 1", "--limit", "3").output


def test_whatsapp_command_calls_server(monkeypatch):
    calls = {}

    def fake_serve(host="0.0.0.0", port=8080):
        calls.update(host=host, port=port)

    monkeypatch.setattr(cli, "serve_whatsapp", fake_serve)
    result = invoke("whatsapp", "--host", "127.0.0.1", "--port", "9999")

    assert result.exit_code == 0
    assert calls == {"host": "127.0.0.1", "port": 9999}


def test_whatsapp_setup_command(monkeypatch):
    monkeypatch.setattr(cli, "whatsapp_setup_status", lambda public_url="https://your-public-url": f"setup:{public_url}")
    result = invoke("whatsapp-setup", "--public-url", "https://safe.example")

    assert result.exit_code == 0
    assert "setup:https://safe.example" in result.output


def test_service_commands(monkeypatch):
    monkeypatch.setattr(cli, "install_macos_whatsapp_service", lambda host="0.0.0.0", port=8080, start=True: f"install:{host}:{port}:{start}")
    monkeypatch.setattr(cli, "start_macos_whatsapp_service", lambda: "started")
    monkeypatch.setattr(cli, "stop_macos_whatsapp_service", lambda: "stopped")
    monkeypatch.setattr(cli, "macos_whatsapp_service_status", lambda: "service-status")
    monkeypatch.setattr(cli, "uninstall_macos_whatsapp_service", lambda: "uninstalled")

    assert "install:127.0.0.1:9999:False" in invoke("service-install", "--host", "127.0.0.1", "--port", "9999", "--no-start").output
    assert "started" in invoke("service-start").output
    assert "stopped" in invoke("service-stop").output
    assert "service-status" in invoke("service-status").output
    assert "uninstalled" in invoke("service-uninstall").output
