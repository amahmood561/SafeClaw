"""First-run setup.

SafeClaw's pitch is self-hosted and local. The defaults said otherwise: the
shipped .env pointed at api.openai.com and the very first thing doctor told a
new user was "OpenAI API key - FAIL". This makes the local path the default and
an API key the opt-in.
"""
from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path

from .providers import PROVIDER_PRESETS

OLLAMA_TAGS = "http://localhost:11434/api/tags"

# Models that are actually usable as an agent. Tool calling is the constraint:
# a model that cannot call tools can chat, but it cannot do anything.
PREFERRED_LOCAL = ("qwen2.5", "llama3.1", "llama3.2", "mistral", "command-r")


def detect_ollama(timeout: float = 2.0) -> dict:
    """Return {running, models}. Never raises: this runs on a cold machine."""
    try:
        with urllib.request.urlopen(OLLAMA_TAGS, timeout=timeout) as response:
            payload = json.loads(response.read())
        models = [m.get("name", "") for m in payload.get("models", [])]
        return {"running": True, "models": [m for m in models if m]}
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return {"running": False, "models": []}


def suggest_local_model(models: list[str]) -> str | None:
    """Pick the best installed model, preferring ones known to call tools."""
    for family in PREFERRED_LOCAL:
        for model in models:
            if model.startswith(family):
                return model
    return models[0] if models else None


def env_lines(provider: str, model: str, base_url: str, api_key: str = "") -> dict[str, str]:
    return {
        "SAFECLAW_PROVIDER_PRESET": provider,
        "OPENAI_BASE_URL": base_url,
        "OPENAI_MODEL": model,
        "OPENAI_API_KEY": api_key,
    }


def apply_to_env(env_path: Path, values: dict[str, str]) -> Path:
    """Rewrite only the keys we own, preserving every other line and comment."""
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    remaining = dict(values)
    out: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if key in remaining:
            out.append(f"{key}={remaining.pop(key)}")
        else:
            out.append(line)
    for key, value in remaining.items():
        out.append(f"{key}={value}")
    env_path.write_text("\n".join(out).rstrip("\n") + "\n")
    return env_path


def local_choice(models: list[str]) -> dict[str, str] | None:
    model = suggest_local_model(models)
    if not model:
        return None
    preset = PROVIDER_PRESETS["ollama"]
    return env_lines("ollama", model, preset.base_url, api_key="ollama")


def detect_claude_cli() -> str | None:
    """Path to the `claude` binary, if this machine already has one logged in."""
    return shutil.which("claude")


def claude_cli_choice() -> dict[str, str]:
    """No key, no endpoint: completions are a subprocess to the local CLI."""
    return {
        "SAFECLAW_PROVIDER_PRESET": "claude-cli",
        "OPENAI_BASE_URL": "subprocess://claude",
        "OPENAI_MODEL": "",
        "OPENAI_API_KEY": "",
    }


def hosted_choice(provider_id: str, api_key: str) -> dict[str, str]:
    preset = PROVIDER_PRESETS.get(provider_id, PROVIDER_PRESETS["openai"])
    return env_lines(preset.id, preset.model, preset.base_url, api_key=api_key)
