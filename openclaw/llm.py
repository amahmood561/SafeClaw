import requests
from .config import API_KEY, BASE_URL, MODEL

SYSTEM_PROMPT = """
You are OpenClaw Local, a practical local computer agent.
You can propose file changes, plans, commands, and use tool results given to you.
Be direct, safe, and useful. Do not pretend to access tools you were not given.
"""

class LLMError(RuntimeError):
    pass

def complete(messages):
    if not API_KEY or API_KEY == "your_key_here":
        raise LLMError("Missing OPENAI_API_KEY. Add it to your .env file.")

    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "temperature": 0.2,
    }
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if response.status_code >= 400:
        raise LLMError(response.text)
    return response.json()["choices"][0]["message"]["content"]
