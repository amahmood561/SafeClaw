"""M3: use a local Claude Code login as the model, with no API key.

These tests never invoke the real `claude` binary. The one thing that cannot be
asserted here is that the model reliably emits the tool protocol -- that was
measured by hand and is recorded in ROADMAP.md.
"""
import json

import pytest

from safeclaw.claude_cli import (
    DISALLOWED,
    build_system_prompt,
    parse_reply,
    render_prompt,
)
from safeclaw.llm import LLMError
import safeclaw.claude_cli as claude_cli


SPECS = [
    {"type": "function", "function": {
        "name": "list_files", "description": "List files.",
        "parameters": {"properties": {"path": {"type": "string"}}}}},
]


# --- the permission model must survive -------------------------------------

def test_claude_codes_own_tools_are_disabled():
    """Claude is the brain, SafeClaw keeps the hands.

    If Claude Code's tools were left on it would read and write files under its
    own permission model, bypassing SafeClaw's profiles entirely -- which would
    remove the only reason SafeClaw exists.
    """
    for tool in ("Bash", "Edit", "Write", "Read", "WebFetch", "Glob", "Grep"):
        assert tool in DISALLOWED


# --- prompt construction ----------------------------------------------------

def test_system_prompt_replaces_rather_than_appends():
    prompt = build_system_prompt(SPECS)
    assert "SafeClaw" in prompt
    assert "list_files(path: string)" in prompt
    assert "tool_calls" in prompt


def test_model_is_told_it_cannot_see_the_machine():
    # It invented a plausible file listing until the prompt said this outright.
    prompt = build_system_prompt(SPECS)
    assert "no direct access" in prompt.lower()


def test_tool_results_are_labelled_as_observed_fact():
    rendered = render_prompt([
        {"role": "user", "content": "what files?"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c1", "function": {"name": "list_files", "arguments": "{}"}}]},
        {"role": "tool", "name": "list_files", "content": "a.txt"},
    ])
    assert "Result of list_files" in rendered
    assert "requested list_files" in rendered


def test_history_is_sent_every_call_not_resumed():
    # SafeClaw compacts its own history; a resumed CLI session would keep
    # everything and the two would silently diverge.
    assert "--resume" not in " ".join(str(x) for x in DISALLOWED)
    rendered = render_prompt([{"role": "user", "content": "first"},
                              {"role": "assistant", "content": "second"},
                              {"role": "user", "content": "third"}])
    for part in ("first", "second", "third"):
        assert part in rendered


# --- parsing ----------------------------------------------------------------

def test_bare_json_becomes_an_openai_tool_call():
    msg = parse_reply('{"tool_calls":[{"name":"list_files","arguments":{"path":"."}}]}')
    assert msg["tool_calls"][0]["function"]["name"] == "list_files"
    assert json.loads(msg["tool_calls"][0]["function"]["arguments"]) == {"path": "."}
    assert msg["tool_calls"][0]["id"].startswith("call_")
    assert msg["tool_calls"][0]["type"] == "function"


def test_a_fenced_block_still_parses():
    msg = parse_reply('```json\n{"tool_calls":[{"name":"read_file","arguments":{"path":"a"}}]}\n```')
    assert msg["tool_calls"][0]["function"]["name"] == "read_file"


def test_json_after_a_stray_sentence_still_parses():
    msg = parse_reply('Let me check.\n{"tool_calls":[{"name":"list_files","arguments":{}}]}')
    assert msg["tool_calls"][0]["function"]["name"] == "list_files"


def test_several_tool_calls_in_one_reply():
    msg = parse_reply('{"tool_calls":[{"name":"a","arguments":{}},{"name":"b","arguments":{}}]}')
    assert [c["function"]["name"] for c in msg["tool_calls"]] == ["a", "b"]
    assert len({c["id"] for c in msg["tool_calls"]}) == 2, "ids must be unique"


def test_prose_stays_prose():
    msg = parse_reply("There are three files in that directory.")
    assert msg["content"] == "There are three files in that directory."
    assert "tool_calls" not in msg


def test_malformed_json_falls_back_to_prose_rather_than_crashing():
    msg = parse_reply('{"tool_calls": [ broken')
    assert msg["role"] == "assistant"
    assert "tool_calls" not in msg


def test_empty_tool_call_list_is_not_a_tool_call():
    assert "tool_calls" not in parse_reply('{"tool_calls":[]}')


def test_a_call_without_a_name_is_skipped():
    assert "tool_calls" not in parse_reply('{"tool_calls":[{"arguments":{"path":"."}}]}')


# --- failure surfaces -------------------------------------------------------

def test_a_missing_binary_explains_the_fix(monkeypatch):
    monkeypatch.setattr(claude_cli, "is_available", lambda: False)
    with pytest.raises(LLMError) as exc:
        claude_cli.invoke("hi")
    assert "claude" in str(exc.value).lower()
    assert "log in" in str(exc.value).lower()


def test_a_nonzero_exit_is_reported_not_swallowed(monkeypatch):
    class Done:
        returncode, stdout, stderr = 1, "", "not logged in"
    monkeypatch.setattr(claude_cli, "is_available", lambda: True)
    monkeypatch.setattr(claude_cli.subprocess, "run", lambda *a, **k: Done())
    with pytest.raises(LLMError) as exc:
        claude_cli.invoke("hi")
    assert "not logged in" in str(exc.value)


def test_cost_is_surfaced_so_a_meter_can_be_shown(monkeypatch):
    class Done:
        returncode = 0
        stderr = ""
        stdout = json.dumps({"result": "hello", "total_cost_usd": 0.24, "session_id": "s1"})
    monkeypatch.setattr(claude_cli, "is_available", lambda: True)
    monkeypatch.setattr(claude_cli.subprocess, "run", lambda *a, **k: Done())

    msg = claude_cli.complete_message([{"role": "user", "content": "hi"}])
    assert msg["_cost_usd"] == 0.24, "a fifty-step task is real money; the caller must be able to show it"


def test_the_invocation_is_isolated(monkeypatch):
    captured = {}
    class Done:
        returncode = 0
        stderr = ""
        stdout = json.dumps({"result": "ok"})
    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return Done()
    monkeypatch.setattr(claude_cli, "is_available", lambda: True)
    monkeypatch.setattr(claude_cli.subprocess, "run", fake_run)

    claude_cli.invoke("hi", system="be terse")
    cmd = captured["cmd"]
    # Without these the reply drifts into whatever else that login has been doing.
    assert "--no-session-persistence" in cmd
    assert "--exclude-dynamic-system-prompt-sections" in cmd
    assert "--system-prompt" in cmd
    assert "--disallowed-tools" in cmd
