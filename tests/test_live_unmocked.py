import pytest
from typer.testing import CliRunner

from safeclaw.cli import app


runner = CliRunner()


@pytest.mark.live
def test_live_tools_command_unmocked():
    result = runner.invoke(app, ["tools"])
    assert result.exit_code == 0
    assert "Available local tools" in result.output


@pytest.mark.live
def test_live_doctor_command_unmocked():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "SafeClaw Doctor" in result.output
    assert "Summary:" in result.output


@pytest.mark.live
def test_live_whatsapp_setup_unmocked():
    result = runner.invoke(app, ["whatsapp-setup"])
    assert result.exit_code == 0
    assert "WhatsApp setup" in result.output
