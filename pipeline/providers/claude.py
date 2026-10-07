from __future__ import annotations

from typing import Any

import anthropic

EXTRACT_TOOL_NAME = "extract_fields"


class ClaudeProvider:
    """LLMProvider backed by the Claude API.

    Per CLAUDE.md, used only for hosted Q&A and the optional eval comparison -
    Ollama is the default for extraction.
    """

    def __init__(self, model: str, client: Any | None = None) -> None:
        self.name = "claude"
        self.model = model
        self._client = client or anthropic.Anthropic()

    def extract(self, text: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Ask the model to fill in `schema`'s fields from `text`.

        Uses forced tool use: the schema is the tool's input_schema, and
        tool_choice forces Claude to call it, so the reply is guaranteed to
        be a structured argument set rather than prose we'd have to parse.
        """
        response = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=(
                "Extract the fields described by the tool's schema from the document text. "
                "Only use information present in the text."
            ),
            messages=[{"role": "user", "content": text}],
            tools=[
                {
                    "name": EXTRACT_TOOL_NAME,
                    "description": "Record the extracted fields.",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": EXTRACT_TOOL_NAME},
        )
        for block in response.content:
            if block.type == "tool_use":
                return block.input
        raise ValueError("Claude did not return a tool_use block")

    def answer(self, question: str, passages: list[dict[str, Any]]) -> dict[str, Any]:
        """Answer `question` using only the given passages, cited by id."""
        context = "\n\n".join(f"[{passage['id']}] {passage['text']}" for passage in passages)
        response = self._client.messages.create(
            model=self.model,
            max_tokens=300,
            system=(
                "Answer the question using only the passages below. "
                "If the passages don't contain the answer, say so."
            ),
            messages=[{"role": "user", "content": f"{context}\n\nQuestion: {question}"}],
        )
        for block in response.content:
            if block.type == "text":
                return {"answer": block.text}
        raise ValueError("Claude did not return a text block")
