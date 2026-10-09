"""Schema-guided extraction: document pages -> validated fields with evidence."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from pipeline.ingest import extract_pages
from pipeline.packs import customer_document, load_pack
from pipeline.providers.base import LLMProvider
from pipeline.schema_models import build_model, wrap_schema

INSTRUCTIONS = """\
You are extracting fields from the document below.
For every field, return:
- value: the value, in the type and format the field's description asks for.
- evidence_quote: a short quote copied word for word from the document that supports the value.
- page: the page number from the "=== Page N ===" marker above the quote.
Every value needs an evidence_quote and page, with one exception:
a false or an empty list that comes from the document never mentioning something may have null evidence_quote and page.
If the document does not state a field at all, set value, evidence_quote and page to null.
Do not guess or calculate values that are not written in the document."""

MAX_ATTEMPTS = 2  # the first try plus one retry with the validation errors


class ExtractionError(Exception):
    """Raised when the model's reply is still invalid after the retry."""


@dataclass
class Extraction:
    """Validated fields plus a record of how they were produced (for lineage)."""

    fields: dict[str, Any]
    provider: str
    model: str
    prompt_sha256: str
    duration_seconds: float
    attempts: int


def extract(pages: list[str], schema: dict[str, Any], provider: LLMProvider) -> Extraction:
    """Extract `schema`'s fields from `pages`, retrying once if the reply is invalid."""
    wrapped = wrap_schema(schema)
    result_model = build_model(schema)
    document = INSTRUCTIONS + "\n\n" + describe_fields(schema) + "\n\n" + format_pages(pages)

    started = time.perf_counter()
    feedback = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            reply = provider.extract(document + feedback, wrapped)
            validated = result_model.model_validate(reply)
        except (ValidationError, json.JSONDecodeError) as error:
            problems = describe_problems(error)
            feedback = (
                "\n\nYour previous reply was invalid:\n"
                + problems
                + "\nReply again, fixing these problems."
            )
            continue
        return Extraction(
            fields=validated.model_dump(mode="json"),
            provider=provider.name,
            model=provider.model,
            prompt_sha256=prompt_sha256(wrapped),
            duration_seconds=round(time.perf_counter() - started, 3),
            attempts=attempt,
        )

    raise ExtractionError(f"Reply still invalid after {MAX_ATTEMPTS} attempts:\n{problems}")


def extract_customer(
    pack_name: str,
    customer_id: str,
    provider: LLMProvider,
    packs_dir: Path | str = "packs",
) -> Extraction:
    """Load a pack, find this customer's document, and extract it.

    The one-customer unit of work that `explainer extract` (and later
    `explainer run`) calls.
    """
    pack = load_pack(pack_name, packs_dir=packs_dir)
    pages = extract_pages(customer_document(pack, customer_id, packs_dir))
    return extract(pages, pack.extraction_schema, provider)


def describe_fields(schema: dict[str, Any]) -> str:
    """List each field's name, type and description as plain prompt text.

    Ollama's `format` only constrains the reply's shape; the model never reads
    the schema (measured in 4.6c-1). So the descriptions - "ISO date", "not the
    illustrative figure" - must be in the prompt itself. Claude also sees them
    via its tool definition; giving both providers the same prompt keeps the
    comparison fair.
    """
    lines = ["Fields to extract:"]
    for name, field in schema["properties"].items():
        line = f"- {name} ({describe_type(field)})"
        if field.get("description"):
            line += f": {field['description']}"
        lines.append(line)
    return "\n".join(lines)


def describe_type(field: dict[str, Any]) -> str:
    """Short type label, e.g. "number", "string, date", "one of: a, b", "list of: year, percent"."""
    if "enum" in field:
        return "one of: " + ", ".join(str(option) for option in field["enum"])
    types = field.get("type", "any")
    if isinstance(types, list):
        # "null" just means "may be missing", which the instructions already cover.
        types = ", ".join(t for t in types if t != "null")
    if types == "array":
        items = field.get("items", {})
        if "properties" in items:
            return "list of: " + ", ".join(items["properties"])
        return "list of " + describe_type(items)
    if "format" in field:
        return f"{types}, {field['format']}"
    return types


def format_pages(pages: list[str]) -> str:
    """Join pages with numbered markers so the model can say where a quote came from."""
    return "\n\n".join(f"=== Page {number} ===\n{text}" for number, text in enumerate(pages, 1))


def prompt_sha256(wrapped_schema: dict[str, Any]) -> str:
    """Fingerprint of the prompt version: instructions + schema, not the document.

    Same for every customer; changes only when the instructions or a schema
    description change. The document gets its own hash in the lineage manifest.
    """
    canonical = INSTRUCTIONS + json.dumps(wrapped_schema, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def describe_problems(error: ValidationError | json.JSONDecodeError) -> str:
    """Turn an error into short lines the model can act on, e.g. 'loan_amount.value: ...'."""
    if isinstance(error, json.JSONDecodeError):
        return f"- the reply was not valid JSON ({error.msg})"
    return "\n".join(
        f"- {'.'.join(str(part) for part in problem['loc'])}: {problem['msg']}"
        for problem in error.errors()
    )
