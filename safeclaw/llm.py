import json

import requests
from .config import API_KEY, BASE_URL, MODEL, PROVIDER_PRESET

SYSTEM_PROMPT = """
You are SafeClaw, a self-hosted agent with explicit permissions.
Use tools when you need to inspect or change local files, run allowed commands, or send configured WhatsApp messages.
Be direct, safe, and useful. Do not claim a tool succeeded until you have seen its result.
"""

class LLMError(RuntimeError):
    def __init__(self, message, error_type=None, code=None, status_code=None):
        super().__init__(message)
        self.error_type = error_type
        self.code = code
        self.status_code = status_code


def _llm_error_from_response(response):
    try:
        payload = response.json()
    except Exception:
        return LLMError(response.text, status_code=response.status_code)
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return LLMError(
            error.get("message") or response.text,
            error_type=error.get("type"),
            code=error.get("code"),
            status_code=response.status_code,
        )
    return LLMError(response.text, status_code=response.status_code)


def provider_test(api_key=None, base_url=None, model=None, timeout=30):
    """Check whether an OpenAI-compatible chat-completions provider responds."""
    active_key = api_key if api_key is not None else API_KEY
    active_base_url = (base_url or BASE_URL).rstrip("/")
    active_model = model or MODEL
    if not active_key or active_key == "your_key_here":
        raise LLMError("Missing OPENAI_API_KEY. Add it to your .env file.")
    payload = {
        "model": active_model,
        "messages": [
            {"role": "system", "content": "Reply with exactly: safeclaw-ok"},
            {"role": "user", "content": "SafeClaw provider test"},
        ],
        "temperature": 0,
        "max_tokens": 16,
    }
    response = requests.post(
        f"{active_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {active_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise _llm_error_from_response(response)
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {
        "ok": True,
        "base_url": active_base_url,
        "model": active_model,
        "content": content,
    }

def using_claude_cli() -> bool:
    return PROVIDER_PRESET == "claude-cli"


def complete_message(messages, tools=None, model=None):
    if using_claude_cli():
        # Imported here: claude_cli imports SYSTEM_PROMPT and LLMError from this
        # module, so a top-level import would be circular.
        from .claude_cli import complete_message as claude_complete
        return claude_complete(messages, tools=tools, model=model or None)

    if not API_KEY or API_KEY == "your_key_here":
        raise LLMError("Missing OPENAI_API_KEY. Add it to your .env file.")

    payload = {
        "model": model or MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "temperature": 0.2,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if response.status_code >= 400:
        raise _llm_error_from_response(response)
    return response.json()["choices"][0]["message"]


def complete_message_stream(messages, model=None):
    if using_claude_cli():
        # The CLI returns one complete reply, so there is nothing to stream.
        # Yield it whole rather than pretending to stream and dropping content.
        from .claude_cli import complete_message as claude_complete
        content = claude_complete(messages, model=model or None).get("content", "")
        if content:
            yield content
        return

    if not API_KEY or API_KEY == "your_key_here":
        raise LLMError("Missing OPENAI_API_KEY. Add it to your .env file.")

    payload = {
        "model": model or MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "temperature": 0.2,
        "stream": True,
    }
    with requests.post(
        f"{BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
        stream=True,
    ) as response:
        if response.status_code >= 400:
            raise _llm_error_from_response(response)
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                payload = json.loads(data)
            except Exception:
                continue
            delta = payload.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content")
            if content:
                yield content


def complete(messages):
    return complete_message(messages).get("content", "")
