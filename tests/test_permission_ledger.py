"""M4: the permission ledger.

The panel exists to be believed, so these assert the two things that would make
it a liar: counting work that never happened, and disagreeing with the profile
that tasks actually run under.
"""
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "mac-app" / "src" / "renderer.js"
INDEX = ROOT / "mac-app" / "src" / "index.html"
HARNESS = ROOT / "mac-app" / "test" / "ledger.harness.js"

from safeclaw.tools import CAPABILITY_TOOLS, capability_of, capability_report


# --- the enforced rules -----------------------------------------------------

def test_every_tool_belongs_to_exactly_one_capability():
    seen = {}
    for capability, tools in CAPABILITY_TOOLS.items():
        for tool in tools:
            assert tool not in seen, f"{tool} is in both {seen.get(tool)} and {capability}"
            seen[tool] = capability


def test_readonly_permits_reading_and_nothing_else():
    report = capability_report("readonly")
    allowed = [c for c, info in report["capabilities"].items() if info["allowed"]]
    assert allowed == ["read"]


def test_an_unknown_profile_falls_back_to_the_safest_one():
    assert capability_report("not-a-real-profile")["profile"] == "readonly"


def test_writing_and_shell_always_require_approval():
    caps = capability_report("workspace-write")["capabilities"]
    assert caps["write"]["needs_approval"]
    assert caps["shell"]["needs_approval"]


def test_capability_of_covers_the_real_tool_names():
    assert capability_of("read_file") == "read"
    assert capability_of("apply_patch") == "write"
    assert capability_of("send_whatsapp") == "messaging"
    assert capability_of("nonsense") == "other"


# --- the panel --------------------------------------------------------------

def test_the_ledger_is_pinned_above_sessions():
    """Chat is the part every agent has. This is the part that is not."""
    html = INDEX.read_text()
    assert html.index("ledger-section") < html.index(">Sessions<")


def test_the_panel_reads_the_profile_chat_actually_uses():
    # There are several profile fields. Reading the wrong one would describe
    # permissions that no task is running under.
    source = RENDERER.read_text()
    body = source.split("function ledgerProfile()", 1)[1].split("}", 1)[0]
    assert "chatPermission" in body


def test_javascript_capabilities_match_the_enforced_ones():
    source = RENDERER.read_text()
    block = source.split("const CAPABILITY_TOOLS = {", 1)[1].split("};", 1)[0]
    for capability, tools in CAPABILITY_TOOLS.items():
        assert f"{capability}:" in block, f"{capability} missing from the panel"
        for tool in tools:
            assert f"'{tool}'" in block, f"{tool} would never be attributed to {capability}"


@pytest.mark.skipif(not __import__("shutil").which("node"), reason="node not installed")
def test_the_ledger_counts_results_not_requests():
    """A refused write must never be reported as something it touched."""
    out = subprocess.run(
        ["node", str(HARNESS)], capture_output=True, text=True, cwd=ROOT, timeout=60,
    )
    assert out.returncode == 0, out.stderr
    stages = out.stdout.split("\n\n")

    requested = next(s for s in stages if "awaiting your approval" in s)
    assert "⏸ write 1 awaiting your approval" in requested
    assert "✓ write" not in requested, "a requested tool has not touched anything yet"

    refused = next(s for s in stages if "refused" in s)
    assert "✕ write 1 refused" in refused
    assert "✓ write" not in refused, "a refused tool must never be counted as used"
    assert "✓ read 2 calls" in refused, "real work must still be counted"


# --- approval diff ----------------------------------------------------------

from safeclaw.tools import WORKSPACE, approval_diff


def test_a_write_shows_what_would_change(workspace):
    (workspace / "notes.txt").write_text("alpha\nbeta\ngamma\n")
    diff = approval_diff("write_file", {"path": "notes.txt", "content": "alpha\nBETA\ngamma\n"})
    assert "-beta" in diff
    assert "+BETA" in diff
    assert "alpha" in diff, "context lines make the change readable"


def test_a_new_file_diffs_against_nothing(workspace):
    diff = approval_diff("create_file", {"path": "fresh.txt", "content": "hello\n"})
    assert "/dev/null" in diff
    assert "+hello" in diff


def test_a_delete_shows_what_is_being_lost(workspace):
    (workspace / "doomed.txt").write_text("important\n")
    diff = approval_diff("delete_file", {"path": "doomed.txt"})
    assert "-important" in diff


def test_an_edit_that_changes_nothing_says_so(workspace):
    (workspace / "same.txt").write_text("unchanged\n")
    assert approval_diff("write_file", {"path": "same.txt", "content": "unchanged\n"}) == "(no change)"


def test_a_long_diff_is_truncated_rather_than_flooding_the_card(workspace):
    (workspace / "big.txt").write_text("".join(f"line {i}\n" for i in range(400)))
    diff = approval_diff("write_file", {"path": "big.txt", "content": "replaced\n"}, max_lines=20)
    assert len(diff.splitlines()) <= 21
    assert "more lines" in diff


def test_tools_that_change_nothing_on_disk_have_no_diff(workspace):
    for tool in ("fetch_url", "shell", "send_whatsapp", "read_file"):
        assert approval_diff(tool, {"path": "x", "url": "y", "command": "z"}) is None


def test_a_path_escaping_the_workspace_produces_no_diff(workspace):
    # safe_path raises for these; the card must not leak file contents from
    # outside the workspace on the way to being refused.
    assert approval_diff("write_file", {"path": "../../etc/passwd", "content": "x"}) is None


def test_the_approval_event_carries_the_diff():
    source = (ROOT / "safeclaw" / "tools.py").read_text()
    block = source.split('"type": "approval_required"', 1)[1].split("})", 1)[0]
    assert '"diff"' in block


# --- the card ---------------------------------------------------------------

def test_the_approval_card_escapes_tool_supplied_text():
    """A filename is enough to inject markup otherwise.

    kind, reason and subject all originate in tool output, which is not trusted.
    """
    source = RENDERER.read_text()
    card = source.split("function renderApprovalCard", 1)[1].split("const actions", 1)[0]
    assert "${kind}" not in card, "raw interpolation of tool-supplied text"
    assert "escapeHtml(kind)" in card
    assert "escapeHtml(event.reason" in card


def test_the_diff_preview_escapes_every_line():
    source = RENDERER.read_text()
    body = source.split("function renderDiffPreview", 1)[1].split("\nfunction ", 1)[0]
    assert "escapeHtml(line)" in body


# --- provenance -------------------------------------------------------------

def test_an_answer_keeps_the_calls_that_produced_it():
    source = RENDERER.read_text()
    assert "function recordProvenance" in source
    assert "function renderProvenance" in source
    # Reset per turn, or one answer would show another answer's evidence.
    assert "activeProvenance = [];" in source


def test_provenance_is_attached_when_the_answer_lands():
    # There are two task_done handlers: one for the task panel, one for chat.
    # The provenance block belongs to the chat one.
    source = RENDERER.read_text()
    handlers = source.split("if (event.type === 'task_done') {")[1:]
    assert any("renderProvenance" in h[:400] for h in handlers), (
        "no task_done handler attaches the calls behind the answer"
    )


def test_provenance_marks_denied_and_failed_calls():
    source = RENDERER.read_text()
    body = source.split("function recordProvenance", 1)[1].split("\nfunction ", 1)[0]
    assert "tool_error" in body and "error = true" in body
    assert "approval_denied" in body and "denied = true" in body
