"""M2: the local path is the default, and setup never eats an existing config."""
from safeclaw.setup_wizard import (
    apply_to_env,
    detect_ollama,
    hosted_choice,
    local_choice,
    suggest_local_model,
)


def test_prefers_a_model_that_can_actually_call_tools():
    # A model that cannot call tools can chat but cannot do anything.
    assert suggest_local_model(["gemma:2b", "qwen2.5:7b"]) == "qwen2.5:7b"
    assert suggest_local_model(["llama3.2:3b"]) == "llama3.2:3b"


def test_falls_back_to_whatever_is_installed():
    assert suggest_local_model(["some-obscure-model:latest"]) == "some-obscure-model:latest"


def test_no_models_means_no_suggestion():
    assert suggest_local_model([]) is None
    assert local_choice([]) is None


def test_local_choice_needs_no_real_api_key():
    values = local_choice(["qwen2.5:7b"])
    assert values["OPENAI_BASE_URL"] == "http://localhost:11434/v1"
    assert values["OPENAI_MODEL"] == "qwen2.5:7b"
    assert values["SAFECLAW_PROVIDER_PRESET"] == "ollama"
    assert "api.openai.com" not in values["OPENAI_BASE_URL"]


def test_detect_ollama_never_raises_on_a_cold_machine():
    result = detect_ollama(timeout=0.01)
    assert set(result) == {"running", "models"}
    assert isinstance(result["models"], list)


def test_apply_to_env_preserves_comments_and_unrelated_keys(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "# a comment worth keeping\n"
        "OPENAI_MODEL=gpt-4.1-mini\n"
        "WORKSPACE=./workspace\n"
        "MAX_TOOL_STEPS=50\n"
    )
    apply_to_env(env, local_choice(["qwen2.5:7b"]))
    text = env.read_text()

    assert "# a comment worth keeping" in text
    assert "WORKSPACE=./workspace" in text, "must not drop keys it does not own"
    assert "MAX_TOOL_STEPS=50" in text
    assert "OPENAI_MODEL=qwen2.5:7b" in text
    assert "gpt-4.1-mini" not in text, "the old value must be replaced, not duplicated"


def test_apply_to_env_adds_missing_keys(tmp_path):
    env = tmp_path / ".env"
    env.write_text("WORKSPACE=./workspace\n")
    apply_to_env(env, local_choice(["qwen2.5:7b"]))
    assert "OPENAI_BASE_URL=http://localhost:11434/v1" in env.read_text()


def test_apply_to_env_writes_each_key_once(tmp_path):
    env = tmp_path / ".env"
    env.write_text("OPENAI_MODEL=old\n")
    apply_to_env(env, local_choice(["qwen2.5:7b"]))
    apply_to_env(env, local_choice(["llama3.2:3b"]))
    assert env.read_text().count("OPENAI_MODEL=") == 1


def test_hosted_choice_still_works_for_people_who_want_it(tmp_path):
    values = hosted_choice("groq", "test-key-not-real")
    assert values["OPENAI_API_KEY"] == "test-key-not-real"
    assert "groq" in values["OPENAI_BASE_URL"]


def test_claude_cli_choice_needs_no_key_and_no_endpoint():
    from safeclaw.setup_wizard import claude_cli_choice

    values = claude_cli_choice()
    assert values["SAFECLAW_PROVIDER_PRESET"] == "claude-cli"
    assert values["OPENAI_API_KEY"] == "", "the whole point is that there is no key"
    assert not values["OPENAI_BASE_URL"].startswith("http"), "completions are a subprocess, not a request"
