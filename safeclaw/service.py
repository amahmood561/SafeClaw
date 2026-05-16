import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path


LABEL = "com.safeclaw.whatsapp"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def _plist_path() -> Path:
    return _launch_agents_dir() / f"{LABEL}.plist"


def _program_arguments(host: str, port: int) -> list[str]:
    root = _repo_root()
    venv_bin = root / ".venv" / "bin" / "safeclaw"
    if venv_bin.exists():
        command = [str(venv_bin)]
    else:
        found = shutil.which("safeclaw")
        command = [found] if found else [sys.executable, "-m", "safeclaw.cli"]
    return command + [
        "whatsapp",
        "--host",
        host,
        "--port",
        str(port),
    ]


def _log_dir() -> Path:
    path = Path.home() / "Library" / "Logs" / "SafeClaw"
    path.mkdir(parents=True, exist_ok=True)
    return path


def install_macos_whatsapp_service(host: str = "0.0.0.0", port: int = 8080, start: bool = True) -> str:
    launch_dir = _launch_agents_dir()
    launch_dir.mkdir(parents=True, exist_ok=True)
    logs = _log_dir()
    root = _repo_root()
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"),
        "WORKSPACE": os.environ.get("WORKSPACE", str(root / "workspace")),
    }
    plist = {
        "Label": LABEL,
        "ProgramArguments": _program_arguments(host, port),
        "WorkingDirectory": str(root),
        "EnvironmentVariables": env,
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(logs / "whatsapp.out.log"),
        "StandardErrorPath": str(logs / "whatsapp.err.log"),
    }
    path = _plist_path()
    path.write_bytes(plistlib.dumps(plist))
    if start:
        subprocess.run(["launchctl", "unload", str(path)], capture_output=True, text=True)
        result = subprocess.run(["launchctl", "load", str(path)], capture_output=True, text=True)
        if result.returncode != 0:
            return f"Wrote {path}, but launchctl load failed:\n{result.stderr.strip()}"
    return f"Installed SafeClaw WhatsApp service at {path}"


def start_macos_whatsapp_service() -> str:
    path = _plist_path()
    if not path.exists():
        return "Service is not installed. Run: safeclaw service-install"
    subprocess.run(["launchctl", "unload", str(path)], capture_output=True, text=True)
    result = subprocess.run(["launchctl", "load", str(path)], capture_output=True, text=True)
    if result.returncode != 0:
        return f"Could not start service:\n{result.stderr.strip()}"
    return "SafeClaw WhatsApp service started."


def stop_macos_whatsapp_service() -> str:
    path = _plist_path()
    if not path.exists():
        return "Service is not installed."
    result = subprocess.run(["launchctl", "unload", str(path)], capture_output=True, text=True)
    if result.returncode != 0 and result.stderr.strip():
        return f"Could not stop service:\n{result.stderr.strip()}"
    return "SafeClaw WhatsApp service stopped."


def uninstall_macos_whatsapp_service() -> str:
    path = _plist_path()
    if path.exists():
        subprocess.run(["launchctl", "unload", str(path)], capture_output=True, text=True)
        path.unlink()
    return "SafeClaw WhatsApp service uninstalled."


def macos_whatsapp_service_status() -> str:
    path = _plist_path()
    logs = _log_dir()
    result = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    loaded = LABEL in result.stdout
    return f"""
SafeClaw WhatsApp service

Installed: {path.exists()}
Loaded: {loaded}
Plist: {path}
Stdout log: {logs / "whatsapp.out.log"}
Stderr log: {logs / "whatsapp.err.log"}

Commands:
  safeclaw service-install
  safeclaw service-start
  safeclaw service-stop
  safeclaw service-status
  safeclaw service-uninstall
""".strip()
