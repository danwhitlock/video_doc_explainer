from __future__ import annotations

import os
from collections.abc import Mapping

from pipeline.providers.base import LLMProvider

DEFAULT_PROVIDER = "ollama"


def get_provider(env: Mapping[str, str] | None = None) -> LLMProvider:
    """Build the provider named by LLM_PROVIDER, using the model from env.

    `env` defaults to the real environment; tests pass a plain dict instead.
    There's deliberately no default model name - CLAUDE.md forbids hardcoding
    them, so a missing model is an error rather than a silent guess.
    """
    env = os.environ if env is None else env
    provider_name = (env.get("LLM_PROVIDER") or DEFAULT_PROVIDER).strip().lower()

    if provider_name == "ollama":
        # Imported here so choosing one provider never requires the other's setup.
        from pipeline.providers.ollama import OllamaProvider

        return OllamaProvider(model=_require(env, "OLLAMA_MODEL"))
    if provider_name == "claude":
        from pipeline.providers.claude import ClaudeProvider

        return ClaudeProvider(model=_require(env, "ANTHROPIC_MODEL"))

    raise ValueError(f"Unknown LLM_PROVIDER {provider_name!r}; expected 'ollama' or 'claude'")


def _require(env: Mapping[str, str], name: str) -> str:
    value = (env.get(name) or "").strip()
    if not value:
        raise ValueError(f"{name} is not set - see .env.example")
    return value
