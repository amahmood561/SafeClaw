from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderPreset:
    id: str
    name: str
    base_url: str
    model: str
    api_key_hint: str
    notes: str


PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    "openai": ProviderPreset(
        id="openai",
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        model="gpt-4.1-mini",
        api_key_hint="OPENAI_API_KEY",
        notes="Best tested path for SafeClaw tool calling and streaming.",
    ),
    "ollama": ProviderPreset(
        id="ollama",
        name="Ollama",
        base_url="http://localhost:11434/v1",
        model="llama3.1",
        api_key_hint="ollama",
        notes="Local OpenAI-compatible endpoint. Tool support depends on the local model.",
    ),
    "groq": ProviderPreset(
        id="groq",
        name="Groq",
        base_url="https://api.groq.com/openai/v1",
        model="openai/gpt-oss-20b",
        api_key_hint="GROQ_API_KEY value saved as OPENAI_API_KEY",
        notes="Fast OpenAI-compatible endpoint. Tool support depends on the selected model.",
    ),
    "openrouter": ProviderPreset(
        id="openrouter",
        name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        model="anthropic/claude-3.5-sonnet",
        api_key_hint="OpenRouter API key saved as OPENAI_API_KEY",
        notes="Recommended route for Claude compatibility without a native Anthropic adapter.",
    ),
    "litellm": ProviderPreset(
        id="litellm",
        name="LiteLLM",
        base_url="http://localhost:4000/v1",
        model="anthropic/claude-3-5-sonnet-latest",
        api_key_hint="LiteLLM proxy key saved as OPENAI_API_KEY",
        notes="Use when you run your own OpenAI-compatible gateway.",
    ),
    "custom": ProviderPreset(
        id="custom",
        name="Custom OpenAI-compatible",
        base_url="https://your-provider.example/v1",
        model="your-model",
        api_key_hint="Provider API key saved as OPENAI_API_KEY",
        notes="Must support OpenAI-compatible /chat/completions.",
    ),
}


def provider_preset(provider_id: str) -> ProviderPreset:
    return PROVIDER_PRESETS.get(provider_id, PROVIDER_PRESETS["custom"])


def infer_provider_id(base_url: str) -> str:
    normalized = (base_url or "").rstrip("/")
    for preset in PROVIDER_PRESETS.values():
        if preset.id != "custom" and normalized == preset.base_url.rstrip("/"):
            return preset.id
    return "custom"


def provider_presets_text() -> str:
    lines = ["SafeClaw provider presets", ""]
    for preset in PROVIDER_PRESETS.values():
        lines.append(f"- {preset.id}: {preset.name}")
        lines.append(f"  Base URL: {preset.base_url}")
        lines.append(f"  Example model: {preset.model}")
        lines.append(f"  Notes: {preset.notes}")
    return "\n".join(lines)
