from types import SimpleNamespace

import pytest

from pipeline.providers.base import LLMProvider
from pipeline.providers.claude import ClaudeProvider


class FakeMessages:
    """Stands in for anthropic.Anthropic().messages - records calls, returns canned content blocks."""

    def __init__(self, content: list) -> None:
        self.content = content
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(content=self.content)


class FakeAnthropicClient:
    def __init__(self, content: list) -> None:
        self.messages = FakeMessages(content)


def test_claude_provider_satisfies_protocol():
    client = FakeAnthropicClient([SimpleNamespace(type="tool_use", input={})])
    provider = ClaudeProvider(model="claude-haiku-4-5", client=client)

    assert isinstance(provider, LLMProvider)


def test_extract_forces_tool_choice_and_returns_tool_input():
    schema = {"type": "object", "properties": {"loan_amount": {"type": "number"}}}
    tool_block = SimpleNamespace(type="tool_use", input={"loan_amount": 256500})
    client = FakeAnthropicClient([tool_block])
    provider = ClaudeProvider(model="claude-haiku-4-5", client=client)

    result = provider.extract("Loan amount: 256,500", schema)

    assert result == {"loan_amount": 256500}
    call = client.messages.calls[0]
    assert call["tools"][0]["input_schema"] == schema
    assert call["tool_choice"] == {"type": "tool", "name": "extract_fields"}


def test_extract_raises_if_no_tool_use_block_returned():
    client = FakeAnthropicClient([SimpleNamespace(type="text", text="I can't do that")])
    provider = ClaudeProvider(model="claude-haiku-4-5", client=client)

    with pytest.raises(ValueError):
        provider.extract("some text", {})


def test_answer_includes_passages_and_question_in_the_prompt():
    text_block = SimpleNamespace(type="text", text="The fixed rate ends on 31 October 2028.")
    client = FakeAnthropicClient([text_block])
    provider = ClaudeProvider(model="claude-haiku-4-5", client=client)
    passages = [{"id": "m-001-p1-c2", "text": "Your fixed rate ends on 31 October 2028."}]

    result = provider.answer("When does my fixed rate end?", passages)

    assert result == {"answer": "The fixed rate ends on 31 October 2028."}
    sent_prompt = client.messages.calls[0]["messages"][-1]["content"]
    assert "31 October 2028" in sent_prompt
    assert "When does my fixed rate end?" in sent_prompt
