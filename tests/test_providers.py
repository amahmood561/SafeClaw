from safeclaw.providers import infer_provider_id, provider_preset, provider_presets_text


def test_provider_presets_include_openrouter_and_litellm():
    text = provider_presets_text()

    assert "openrouter" in text
    assert "LiteLLM" in text
    assert "Claude" in text or "claude" in text


def test_provider_preset_returns_custom_for_unknown_provider():
    preset = provider_preset("missing")

    assert preset.id == "custom"
    assert "/chat/completions" in preset.notes


def test_infer_provider_id_from_base_url():
    assert infer_provider_id("https://api.openai.com/v1/") == "openai"
    assert infer_provider_id("https://api.groq.com/openai/v1") == "groq"
    assert infer_provider_id("https://example.test/v1") == "custom"
