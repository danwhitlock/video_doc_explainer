import json

import pytest

from pipeline.extract import ExtractionError, describe_fields, extract, prompt_sha256
from pipeline.schema_models import wrap_schema

SCHEMA = {
    "type": "object",
    "properties": {
        "loan_amount": {"type": "number", "description": "Loan in pounds."},
        "term_years": {"type": "integer", "description": "Term in years."},
    },
    "required": ["loan_amount", "term_years"],
}

GOOD_REPLY = {
    "loan_amount": {"value": 256500, "evidence_quote": "Loan amount £256,500", "page": 1},
    "term_years": {"value": 30, "evidence_quote": "over 30 years", "page": 2},
}

BAD_REPLY = {
    "loan_amount": {"value": "lots", "evidence_quote": "Loan amount £256,500", "page": 1},
    "term_years": {"value": 30, "evidence_quote": "over 30 years", "page": 2},
}

PAGES = ["Loan amount £256,500", "Repayable over 30 years"]


class FakeProvider:
    """Plays back scripted replies in order and records the text it was sent.

    A reply that is an exception instance is raised instead of returned,
    to simulate a provider failing to parse the model's output.
    """

    name = "fake"
    model = "fake-model-1"

    def __init__(self, replies: list) -> None:
        self.replies = list(replies)
        self.texts: list[str] = []

    def extract(self, text, schema):
        self.texts.append(text)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def answer(self, question, passages):
        raise NotImplementedError


def test_sends_page_markers_to_the_provider():
    provider = FakeProvider([GOOD_REPLY])

    extract(PAGES, SCHEMA, provider)

    assert "=== Page 1 ===\nLoan amount £256,500" in provider.texts[0]
    assert "=== Page 2 ===\nRepayable over 30 years" in provider.texts[0]


def test_sends_every_field_description_to_the_provider():
    # Ollama's `format` never reaches the model's prompt (4.6c-1), so the
    # descriptions must be in the text itself.
    provider = FakeProvider([GOOD_REPLY])

    extract(PAGES, SCHEMA, provider)

    assert "- loan_amount (number): Loan in pounds." in provider.texts[0]
    assert "- term_years (integer): Term in years." in provider.texts[0]


def test_field_list_shows_format_enum_and_list_items():
    schema = {
        "properties": {
            "offer_date": {"type": "string", "format": "date", "description": "ISO date."},
            "repayment_type": {"type": "string", "enum": ["capital and interest", "interest only"],
                               "description": "Repayment method."},
            "erc": {"type": "array", "description": "Charges by year.",
                    "items": {"type": "object", "properties": {"year": {}, "percent": {}}}},
            "conditions": {"type": "array", "items": {"type": "string"}, "description": "Conditions."},
        }
    }

    lines = describe_fields(schema).splitlines()

    assert "- offer_date (string, date): ISO date." in lines
    assert "- repayment_type (one of: capital and interest, interest only): Repayment method." in lines
    assert "- erc (list of: year, percent): Charges by year." in lines
    assert "- conditions (list of string): Conditions." in lines


def test_field_list_drops_null_from_nullable_types():
    schema = {"properties": {"hours": {"type": ["number", "null"], "description": "Hours."}}}

    assert "- hours (number): Hours." in describe_fields(schema)


def test_good_first_reply_takes_one_attempt_and_records_metadata():
    provider = FakeProvider([GOOD_REPLY])

    result = extract(PAGES, SCHEMA, provider)

    assert result.fields == GOOD_REPLY
    assert result.attempts == 1
    assert result.provider == "fake"
    assert result.model == "fake-model-1"
    assert len(result.prompt_sha256) == 64
    assert result.duration_seconds >= 0


def test_bad_then_good_retries_with_the_errors():
    provider = FakeProvider([BAD_REPLY, GOOD_REPLY])

    result = extract(PAGES, SCHEMA, provider)

    assert result.attempts == 2
    assert "Your previous reply was invalid" not in provider.texts[0]
    assert "- loan_amount.value: Input should be a valid number" in provider.texts[1]


def test_bad_twice_raises():
    provider = FakeProvider([BAD_REPLY, BAD_REPLY])

    with pytest.raises(ExtractionError, match="loan_amount.value"):
        extract(PAGES, SCHEMA, provider)


def test_unreadable_json_is_retried():
    not_json = json.JSONDecodeError("Expecting value", "oops", 0)
    provider = FakeProvider([not_json, GOOD_REPLY])

    result = extract(PAGES, SCHEMA, provider)

    assert result.attempts == 2
    assert "the reply was not valid JSON (Expecting value)" in provider.texts[1]


def test_prompt_hash_ignores_the_document_but_tracks_the_schema():
    first = extract(["Document A"], SCHEMA, FakeProvider([GOOD_REPLY])).prompt_sha256
    second = extract(["Document B"], SCHEMA, FakeProvider([GOOD_REPLY])).prompt_sha256
    assert first == second

    edited = json.loads(json.dumps(SCHEMA))
    edited["properties"]["loan_amount"]["description"] = "Loan in pounds, including fees."
    assert prompt_sha256(wrap_schema(edited)) != first
