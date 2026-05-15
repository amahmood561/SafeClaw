import requests
from .config import API_KEY, BASE_URL, MODEL

SYSTEM_PROMPT = """
You are SafeClaw, a self-hosted agent with explicit permissions.
Use tools when you need to inspect or change local files, run allowed commands, or send configured WhatsApp messages.
Be direct, safe, and useful. Do not claim a tool succeeded until you have seen its result.
"""

class LLMError(RuntimeError):
    pass

def complete_message(messages, tools=None, model=None):
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
        raise LLMError(response.text)
    return response.json()["choices"][0]["message"]


def complete(messages):
    return complete_message(messages).get("content", "")
