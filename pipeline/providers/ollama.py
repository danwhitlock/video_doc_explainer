from __future__ import annotations

import json
from typing import Any

import ollama


class OllamaProvider:
    """LLMProvider backed by a local Ollama server - no API key needed."""

    def __init__(self, model: str, client: Any | None = None) -> None:
        self.name = "ollama"
        self.model = model
        self._client = client or ollama.Client()

    def extract(self, text: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Ask the model to fill in `schema`'s fields from `text`.

        Ollama's `format` option constrains the model's output to match the
        given JSON schema, so the response should already be valid JSON -
        extract.py is what validates it actually matches the pack's schema.
        """
        response = self._client.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract the fields described by the JSON schema from the document text. "
                        "Only use information present in the text."
                    ),
                },
                {"role": "user", "content": text},
            ],
            format=schema,
        )
        return json.loads(response.message.content)

    def answer(self, question: str, passages: list[dict[str, Any]]) -> dict[str, Any]:
        """Answer `question` using only the given passages, cited by id."""
        context = "\n\n".join(f"[{passage['id']}] {passage['text']}" for passage in passages)
        response = self._client.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Answer the question using only the passages below. "
                        "If the passages don't contain the answer, say so."
                    ),
                },
                {"role": "user", "content": f"{context}\n\nQuestion: {question}"},
            ],
        )
        return {"answer": response.message.content}
