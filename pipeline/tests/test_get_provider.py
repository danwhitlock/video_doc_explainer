import pytest

from pipeline.providers import get_provider
from pipeline.providers.base import LLMProvider


def test_defaults_to_ollama_when_llm_provider_unset():
    provider = get_provider({"OLLAMA_MODEL": "qwen2.5:7b"})

    assert isinstance(provider, LLMProvider)
    assert provider.name == "ollama"
    assert provider.model == "qwen2.5:7b"


def test_picks_claude_when_asked(monkeypatch):
    # The Anthropic client refuses to construct without a key; a dummy is
    # enough because nothing is ever sent.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    provider = get_provider({"LLM_PROVIDER": "claude", "ANTHROPIC_MODEL": "claude-haiku-4-5"})

    assert provider.name == "claude"
    assert provider.model == "claude-haiku-4-5"


def test_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER 'gpt'"):
        get_provider({"LLM_PROVIDER": "gpt", "OLLAMA_MODEL": "qwen2.5:7b"})


def test_rejects_missing_model():
    # Empty string counts as missing - that's what a blank line in .env gives you.
    with pytest.raises(ValueError, match="ANTHROPIC_MODEL is not set"):
        get_provider({"LLM_PROVIDER": "claude", "ANTHROPIC_MODEL": ""})
