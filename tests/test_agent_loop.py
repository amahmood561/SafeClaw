"""M1: the loop must survive a long task, a failing tool, and report where it stopped."""
import safeclaw.agent as agent
from safeclaw.config import MAX_TOOL_STEPS


def _call(name, cid="c1", args="{}"):
    return {"id": cid, "type": "function", "function": {"name": name, "arguments": args}}


def test_new_users_get_a_step_limit_that_can_finish_a_task():
    """Six was enough to read a file and not enough to debug anything.

    Asserted against what a new user actually receives. The resolved value is
    whatever their own .env says, which is not this project's business.
    """
    from pathlib import Path

    example = Path(__file__).resolve().parents[1] / ".env.example"
    line = next(l for l in example.read_text().splitlines() if l.startswith("MAX_TOOL_STEPS="))
    assert int(line.split("=", 1)[1]) >= 50

    source = (Path(__file__).resolve().parents[1] / "safeclaw" / "config.py").read_text()
    assert 'os.getenv("MAX_TOOL_STEPS", "50")' in source, "the code fallback must match"


def test_a_raising_tool_does_not_end_the_turn(monkeypatch, workspace):
    def boom(*a, **k):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(agent, "run_tool", boom)
    msg = agent._tool_message("s1", _call("read_file"))

    assert msg["role"] == "tool"
    assert "failed" in msg["content"]
    assert "disk on fire" in msg["content"], "the model must be told what actually broke"


def test_tool_error_is_reported_to_the_ui(monkeypatch, workspace):
    events = []
    monkeypatch.setattr(agent, "run_tool", lambda *a, **k: (_ for _ in ()).throw(ValueError("nope")))
    agent._tool_message("s1", _call("read_file"), event_callback=events.append)

    assert any(e["type"] == "tool_error" for e in events)


def test_malformed_arguments_still_come_back_as_a_tool_message(workspace):
    msg = agent._tool_message("s1", _call("read_file", args="{not json"))
    assert msg["role"] == "tool"
    assert "Invalid tool arguments" in msg["content"]


def test_hitting_the_limit_reports_what_it_did(monkeypatch, workspace):
    # A model that never stops asking for tools should not silently discard the work.
    monkeypatch.setattr(
        agent, "complete_message",
        lambda *a, **k: {"role": "assistant", "content": "", "tool_calls": [_call("list_files")]},
    )
    monkeypatch.setattr(agent, "run_tool", lambda *a, **k: "ok")

    result = agent.run_task("loop forever", session_id="limit-test")

    assert "tool limit" in result
    assert "list_files" in result, "must name the tools it actually used"
    assert str(MAX_TOOL_STEPS) in result


def test_independent_reads_run_in_parallel(monkeypatch, workspace):
    import threading
    concurrent, peak, lock = 0, 0, threading.Lock()

    def slow_read(*a, **k):
        nonlocal concurrent, peak
        with lock:
            concurrent += 1
            peak = max(peak, concurrent)
        threading.Event().wait(0.05)
        with lock:
            concurrent -= 1
        return "ok"

    monkeypatch.setattr(agent, "run_tool", slow_read)
    calls = [_call("read_file", cid=f"c{i}") for i in range(4)]
    replies = [
        {"role": "assistant", "content": "", "tool_calls": calls},
        {"role": "assistant", "content": "done"},
    ]
    monkeypatch.setattr(agent, "complete_message", lambda *a, **k: replies.pop(0))

    agent.run_task("read four files", session_id="parallel-test")
    assert peak > 1, "independent reads should overlap"


def test_writes_stay_sequential(monkeypatch, workspace):
    # Order and approval prompts both matter for writes; never overlap them.
    import threading
    concurrent, peak, lock = 0, 0, threading.Lock()

    def slow_write(*a, **k):
        nonlocal concurrent, peak
        with lock:
            concurrent += 1
            peak = max(peak, concurrent)
        threading.Event().wait(0.05)
        with lock:
            concurrent -= 1
        return "ok"

    monkeypatch.setattr(agent, "run_tool", slow_write)
    calls = [_call("write_file", cid=f"w{i}") for i in range(4)]
    replies = [
        {"role": "assistant", "content": "", "tool_calls": calls},
        {"role": "assistant", "content": "done"},
    ]
    monkeypatch.setattr(agent, "complete_message", lambda *a, **k: replies.pop(0))

    agent.run_task("write four files", session_id="sequential-test")
    assert peak == 1, "writes must not overlap"


def test_shipped_defaults_do_not_demand_an_api_key_first():
    """M2: the README says local and self-hosted. The defaults must agree."""
    from pathlib import Path

    example = (Path(__file__).resolve().parents[1] / ".env.example").read_text()
    settings = {
        line.split("=", 1)[0]: line.split("=", 1)[1]
        for line in example.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    # Assert the active setting, not a mention in a comment. An earlier version of
    # this test passed because "ollama" appeared in a list of presets.
    assert settings["SAFECLAW_PROVIDER_PRESET"] == "ollama"
    assert "localhost:11434" in settings["OPENAI_BASE_URL"]
    assert settings["OPENAI_API_KEY"] != "your_key_here", "the default path needs no real key"
