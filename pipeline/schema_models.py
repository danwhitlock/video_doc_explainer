"""Turn a pack's schema.json into what extraction needs.

`wrap_schema` builds the JSON Schema the model is asked to fill in, where every
field becomes {value, evidence_quote, page}. `build_model` builds a Pydantic
model with the same shape, used to validate the reply. Both work from whatever
schema is loaded, so no pack-specific code is needed.

Only shape and type are checked here - business rules (ranges, cross-field
sums, date formats) belong to checks.py.
"""

from __future__ import annotations

import copy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, create_model, model_validator

_JSON_TO_PYTHON = {"string": str, "number": float, "integer": int, "boolean": bool}

EVIDENCE_QUOTE_SCHEMA = {
    "type": ["string", "null"],
    "description": (
        "A short quote copied word for word from the document that supports the value. "
        "Null only if value is null."
    ),
}
PAGE_SCHEMA = {
    "type": ["integer", "null"],
    "description": "Page number the evidence quote is on. Null only if value is null.",
}


def wrap_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON Schema where each field is {value, evidence_quote, page}.

    The field's original definition (type, enum, description) becomes the
    schema of `value`, so hints like "not the illustrative figure" still
    reach the model.
    """
    properties = {
        name: {
            "type": "object",
            "properties": {
                "value": copy.deepcopy(field),
                "evidence_quote": EVIDENCE_QUOTE_SCHEMA,
                "page": PAGE_SCHEMA,
            },
            "required": ["value", "evidence_quote", "page"],
            "additionalProperties": False,
        }
        for name, field in schema["properties"].items()
    }
    return {
        "title": schema.get("title", "Extraction"),
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


class EvidencedField(BaseModel):
    """Base for each wrapped field; `build_model` adds a typed `value`."""

    model_config = ConfigDict(extra="forbid")

    evidence_quote: str | None
    page: int | None

    @model_validator(mode="after")
    def _evidence_required_for_a_value(self) -> EvidencedField:
        # A value with no quote can't be traced back to the document - that's
        # exactly the untraceable output this project exists to prevent.
        if self.value is not None and (not self.evidence_quote or self.page is None):
            raise ValueError("a non-null value needs an evidence_quote and a page")
        return self


def build_model(schema: dict[str, Any]) -> type[BaseModel]:
    """Return a Pydantic model that validates a reply to `wrap_schema(schema)`."""
    fields = {
        name: (
            create_model(
                f"{name}_field",
                __base__=EvidencedField,
                value=(_python_type(field, name), ...),
            ),
            ...,
        )
        for name, field in schema["properties"].items()
    }
    return create_model(
        "ExtractionResult",
        __config__=ConfigDict(extra="forbid"),
        **fields,
    )


def _python_type(field: dict[str, Any], name: str) -> Any:
    """Map one JSON Schema field definition to a Python type annotation."""
    types = field["type"] if isinstance(field["type"], list) else [field["type"]]
    nullable = "null" in types
    (json_type,) = [t for t in types if t != "null"]

    if "enum" in field:
        python_type = Literal[tuple(field["enum"])]
    elif json_type == "array":
        python_type = list[_python_type(field["items"], f"{name}_item")]
    elif json_type == "object":
        required = set(field.get("required", []))
        python_type = create_model(
            name,
            __config__=ConfigDict(extra="forbid"),
            **{
                prop: (_python_type(spec, prop), ... if prop in required else None)
                for prop, spec in field["properties"].items()
            },
        )
    else:
        python_type = _JSON_TO_PYTHON[json_type]

    return python_type | None if nullable else python_type
