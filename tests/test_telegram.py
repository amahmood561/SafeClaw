from safeclaw import telegram


def test_telegram_setup_status_shows_token_and_allowlist(monkeypatch):
    monkeypatch.setattr(telegram, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(telegram, "SAFECLAW_ALLOWED_TELEGRAM_USERS", ["123"])

    status = telegram.telegram_setup_status()

    assert "TELEGRAM_BOT_TOKEN: set" in status
    assert "allowed users: 123" in status
    assert "safeclaw telegram" in status


def test_telegram_rejects_unallowed_user(monkeypatch):
    monkeypatch.setattr(telegram, "SAFECLAW_ALLOWED_TELEGRAM_USERS", ["123"])

    assert "not allowed" in telegram._reply_for_message("hello", "999")


def test_telegram_commands_use_session_helpers(monkeypatch):
    monkeypatch.setattr(telegram, "SAFECLAW_ALLOWED_TELEGRAM_USERS", [])
    monkeypatch.setattr(telegram, "session_status", lambda session_id: {"permission_profile": "readonly", "session": session_id})
    monkeypatch.setattr(telegram, "recall", lambda session_id: f"memory:{session_id}")
    monkeypatch.setattr(telegram, "reset_session", lambda session_id: None)
    monkeypatch.setattr(telegram, "update_session_settings", lambda session_id, model=None, permission_profile=None: f"settings:{session_id}:{model}:{permission_profile}")

    assert "SafeClaw on Telegram" in telegram._reply_for_message("/help", "42")
    assert "telegram-42" in telegram._reply_for_message("/status", "42")
    assert "memory:telegram-42" == telegram._reply_for_message("/memory", "42")
    assert "Session reset." == telegram._reply_for_message("/reset", "42")
    assert "Permission profile: readonly" == telegram._reply_for_message("/permissions", "42")
    assert "settings:telegram-42:None:workspace-write" == telegram._reply_for_message("/permissions workspace-write", "42")
    assert "settings:telegram-42:gpt-4.1-mini:None" == telegram._reply_for_message("/model gpt-4.1-mini", "42")


def test_telegram_task_menu_is_phone_native(monkeypatch):
    monkeypatch.setattr(telegram, "SAFECLAW_ALLOWED_TELEGRAM_USERS", [])
    monkeypatch.setattr(telegram, "session_status", lambda session_id: {"permission_profile": "readonly"})

    reply = telegram._reply_for_message("show me what tasks i can run", "42")

    assert "Good phone-safe tasks" in reply
    assert "summarize my SafeClaw setup" in reply
    assert "For shell commands or risky changes" in reply
    assert "sandboxed workspace" not in reply


def test_telegram_normal_message_runs_task(monkeypatch):
    calls = {}
    monkeypatch.setattr(telegram, "SAFECLAW_ALLOWED_TELEGRAM_USERS", [])

    def fake_run_task(task, session_id="default", interactive=True):
        calls.update(task=task, session_id=session_id, interactive=interactive)
        return "answer"

    monkeypatch.setattr(telegram, "run_task", fake_run_task)

    assert telegram._reply_for_message("summarize setup", "55") == "answer"
    assert calls == {"task": "summarize setup", "session_id": "telegram-55", "interactive": False}


def test_send_telegram_message_posts_chunks(monkeypatch):
    posts = []

    class Response:
        def raise_for_status(self):
            return None

    def fake_post(url, json, timeout):
        posts.append({"url": url, "json": json, "timeout": timeout})
        return Response()

    monkeypatch.setattr(telegram.requests, "post", fake_post)

    telegram.send_telegram_message(123, "x" * (telegram.MAX_TELEGRAM_MESSAGE + 5), token="token")

    assert len(posts) == 2
    assert posts[0]["url"] == "https://api.telegram.org/bottoken/sendMessage"
    assert posts[0]["json"]["chat_id"] == 123
    assert len(posts[0]["json"]["text"]) == telegram.MAX_TELEGRAM_MESSAGE
    assert posts[1]["json"]["text"] == "x" * 5


def test_serve_telegram_once_processes_update(monkeypatch):
    sent = []
    monkeypatch.setattr(telegram, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(telegram, "SAFECLAW_ALLOWED_TELEGRAM_USERS", [])
    monkeypatch.setattr(
        telegram,
        "_get_updates",
        lambda offset, timeout, token: [
            {
                "update_id": 7,
                "message": {
                    "chat": {"id": 100},
                    "from": {"id": 42},
                    "text": "hello",
                },
            }
        ],
    )
    monkeypatch.setattr(telegram, "_reply_for_message", lambda body, sender_id: f"{sender_id}:{body}")
    monkeypatch.setattr(telegram, "send_telegram_message", lambda chat_id, text: sent.append((chat_id, text)))

    telegram.serve_telegram(once=True)

    assert sent == [(100, "42:hello")]
