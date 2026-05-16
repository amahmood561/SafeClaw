import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_installer(tmp_path, global_install=False):
    install_dir = tmp_path / "safeclaw"
    bin_dir = tmp_path / "bin"
    env = os.environ.copy()
    env.update(
        {
            "SAFECLAW_REPO": f"file://{ROOT}",
            "SAFECLAW_DIR": str(install_dir),
            "SAFECLAW_BIN_DIR": str(bin_dir),
            "SAFECLAW_UPDATE_SHELL_RC": "false",
            "SAFECLAW_GLOBAL": "true" if global_install else "false",
        }
    )
    result = subprocess.run(
        ["bash", str(ROOT / "install.sh")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result, install_dir, bin_dir


def test_install_script_does_not_create_global_launcher_by_default(tmp_path):
    result, install_dir, bin_dir = run_installer(tmp_path, global_install=False)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (install_dir / ".venv" / "bin" / "safeclaw").exists()
    assert not (bin_dir / "safeclaw").exists()
    assert "Installing global safeclaw launcher" not in result.stdout
    assert "SAFECLAW_GLOBAL=true" in result.stdout


def test_install_script_creates_global_launcher_when_requested(tmp_path):
    result, install_dir, bin_dir = run_installer(tmp_path, global_install=True)

    assert result.returncode == 0, result.stdout + result.stderr
    launcher = bin_dir / "safeclaw"
    assert launcher.exists()
    assert os.access(launcher, os.X_OK)
    assert f'exec "{install_dir}/.venv/bin/safeclaw" "$@"' in launcher.read_text()
    assert "Installing global safeclaw launcher" in result.stdout

    help_result = subprocess.run(
        [str(launcher), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert help_result.returncode == 0
    assert "SafeClaw: a self-hosted agent" in help_result.stdout
