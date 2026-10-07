from types import SimpleNamespace

import pytest

from pipeline.providers.base import LLMProvider
from pipeline.providers.ollama import OllamaProvider


class FakeOllamaClient:
    """Stands in for ollama.Client - records calls, returns a canned response."""

    def __init__(self, response_content: str) -> None:
        self.response_content = response_content
        self.calls: list[dict] = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(message=SimpleNamespace(content=self.response_content))


def test_ollama_provider_satisfies_protocol():
    provider = OllamaProvider(model="qwen2.5:7b", client=FakeOllamaClient("{}"))

    assert isinstance(provider, LLMProvider)


def test_extract_sends_schema_as_format_and_parses_json_response():
    client = FakeOllamaClient('{"loan_amount": 256500}')
    provider = OllamaProvider(model="qwen2.5:7b", client=client)
    schema = {"type": "object", "properties": {"loan_amount": {"type": "number"}}}

    result = provider.extract("Loan amount: 256,500", schema)

    assert result == {"loan_amount": 256500}
    assert client.calls[0]["model"] == "qwen2.5:7b"
    assert client.calls[0]["format"] == schema


def test_extract_raises_on_malformed_json():
    client = FakeOllamaClient("not valid json")
    provider = OllamaProvider(model="qwen2.5:7b", client=client)

    with pytest.raises(ValueError):  # json.JSONDecodeError is a ValueError subclass
        provider.extract("some text", {})


def test_answer_includes_passages_and_question_in_the_prompt():
    client = FakeOllamaClient("The fixed rate ends on 31 October 2028.")
    provider = OllamaProvider(model="qwen2.5:7b", client=client)
    passages = [{"id": "m-001-p1-c2", "text": "Your fixed rate ends on 31 October 2028."}]

    result = provider.answer("When does my fixed rate end?", passages)

    assert result == {"answer": "The fixed rate ends on 31 October 2028."}
    sent_prompt = client.calls[0]["messages"][-1]["content"]
    assert "31 October 2028" in sent_prompt
    assert "When does my fixed rate end?" in sent_prompt
