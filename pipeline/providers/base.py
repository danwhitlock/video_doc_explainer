from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """What every LLM backend (Ollama, Claude, ...) must provide.

    Callers depend only on this shape, never on a concrete provider class -
    that's what lets `LLM_PROVIDER` swap the model without touching
    extract.py or the Q&A code.
    """

    name: str
    model: str

    def extract(self, text: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Return field values matching `schema`, extracted from `text`."""
        ...

    def answer(self, question: str, passages: list[dict[str, Any]]) -> dict[str, Any]:
        """Answer `question` using only the given passages."""
        ...
