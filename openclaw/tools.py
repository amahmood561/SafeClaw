import os
import subprocess
from pathlib import Path
from .config import WORKSPACE, ALLOW_SHELL


def safe_path(path: str) -> Path:
    target = (WORKSPACE / path).resolve()
    if not str(target).startswith(str(WORKSPACE)):
        raise ValueError("Path escapes workspace")
    return target


def list_files(path: str = ".") -> str:
    base = safe_path(path)
    if not base.exists():
        return f"Not found: {path}"
    lines = []
    for p in sorted(base.rglob("*")):
        if p.is_file():
            lines.append(str(p.relative_to(WORKSPACE)))
    return "\n".join(lines) or "No files found."


def read_file(path: str) -> str:
    target = safe_path(path)
    return target.read_text(errors="replace")


def write_file(path: str, content: str) -> str:
    target = safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"Wrote {target.relative_to(WORKSPACE)}"


def shell(command: str) -> str:
    if not ALLOW_SHELL:
        return "Shell is disabled. Set ALLOW_SHELL=true to enable."
    result = subprocess.run(
        command,
        shell=True,
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return (result.stdout + result.stderr).strip()


def available_tools() -> str:
    return """
Available local tools:
- list_files(path='.')
- read_file(path)
- write_file(path, content)
- shell(command) disabled unless ALLOW_SHELL=true

This starter version does not do automatic function calling.
The agent will tell you when to run a tool or edit a file.
""".strip()
