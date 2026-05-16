import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP_COMMAND = ROOT / "mac-setup" / "SafeClaw Setup.command"
SETUP_README = ROOT / "mac-setup" / "README.md"


def test_mac_setup_command_exists_and_is_executable():
    assert SETUP_COMMAND.exists()
    assert os.access(SETUP_COMMAND, os.X_OK)


def test_mac_setup_command_has_valid_shell_syntax():
    result = subprocess.run(
        ["bash", "-n", str(SETUP_COMMAND)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr


def test_mac_setup_readme_documents_double_click_flow():
    text = SETUP_README.read_text()

    assert "Double-click" in text
    assert "SafeClaw Setup.command" in text
    assert "Permission profile" in text
    assert "WhatsApp" in text


def test_mac_setup_documents_whatsapp_walkthrough():
    readme = SETUP_README.read_text()
    command = SETUP_COMMAND.read_text()

    assert "WhatsApp walkthrough" in readme
    assert "Twilio WhatsApp Sandbox" in readme
    assert "https://your-public-url/whatsapp" in readme
    assert "SAFECLAW_ALLOWED_SENDERS" in readme
    assert "show_whatsapp_walkthrough" in command
    assert "WEBHOOK_URL_VALUE" in command
    assert "pbcopy" in command
