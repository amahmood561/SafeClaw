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
