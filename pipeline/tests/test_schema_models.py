import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pipeline.packs import load_pack
from pipeline.schema_models import build_model, wrap_schema

PACKS_DIR = Path(__file__).resolve().parents[2] / "packs"


def schema_for(pack_name: str) -> dict:
    return load_pack(pack_name, packs_dir=PACKS_DIR).extraction_schema


def valid_reply(pack_name: str, customer_id: str) -> dict:
    """A correct, fully evidenced reply. Ground truth is only used here as a
    realistic test fixture - the pipeline itself never reads it."""
    truth_path = PACKS_DIR / pack_name / "samples" / "ground_truth" / f"{customer_id}.json"
    truth = json.loads(truth_path.read_text())
    return {
        name: {
            "value": value,
            "evidence_quote": None if value is None else "quoted text",
            "page": None if value is None else 1,
        }
        for name, value in truth.items()
    }


@pytest.mark.parametrize("pack_name", ["mortgage", "healthcare"])
def test_wrap_schema_wraps_every_field_and_keeps_descriptions(pack_name):
    schema = schema_for(pack_name)

    wrapped = wrap_schema(schema)

    assert set(wrapped["properties"]) == set(schema["properties"])
    assert wrapped["required"] == list(schema["properties"])
    for name, field in schema["properties"].items():
        wrapped_field = wrapped["properties"][name]
        assert wrapped_field["required"] == ["value", "evidence_quote", "page"]
        assert wrapped_field["properties"]["value"] == field


def test_wrap_schema_does_not_modify_the_pack_schema():
    schema = schema_for("mortgage")
    before = json.dumps(schema, sort_keys=True)

    wrap_schema(schema)["properties"]["loan_amount"]["properties"]["value"]["type"] = "string"

    assert json.dumps(schema, sort_keys=True) == before


@pytest.mark.parametrize(
    ("pack_name", "customer_id"), [("mortgage", "m-001"), ("healthcare", "h-001")]
)
def test_valid_reply_passes(pack_name, customer_id):
    model = build_model(schema_for(pack_name))

    result = model.model_validate(valid_reply(pack_name, customer_id))

    assert result.model_dump().keys() == valid_reply(pack_name, customer_id).keys()


def test_wrong_type_fails_naming_the_field():
    model = build_model(schema_for("mortgage"))
    reply = valid_reply("mortgage", "m-001")
    reply["loan_amount"]["value"] = "lots"

    with pytest.raises(ValidationError, match="loan_amount.value"):
        model.model_validate(reply)


def test_value_outside_enum_fails():
    model = build_model(schema_for("mortgage"))
    reply = valid_reply("mortgage", "m-001")
    reply["repayment_type"]["value"] = "offset"

    with pytest.raises(ValidationError, match="repayment_type.value"):
        model.model_validate(reply)


def test_null_allowed_only_where_schema_says_so():
    healthcare = build_model(schema_for("healthcare"))
    reply = valid_reply("healthcare", "h-001")
    reply["escort_hours"] = {"value": None, "evidence_quote": None, "page": None}
    healthcare.model_validate(reply)

    mortgage = build_model(schema_for("mortgage"))
    reply = valid_reply("mortgage", "m-001")
    reply["loan_amount"] = {"value": None, "evidence_quote": None, "page": None}
    with pytest.raises(ValidationError, match="loan_amount.value"):
        mortgage.model_validate(reply)


def test_value_without_evidence_fails():
    model = build_model(schema_for("mortgage"))
    reply = valid_reply("mortgage", "m-001")
    reply["loan_amount"]["evidence_quote"] = None

    with pytest.raises(ValidationError, match="needs an evidence_quote"):
        model.model_validate(reply)


def test_nested_array_items_are_validated():
    model = build_model(schema_for("mortgage"))
    reply = valid_reply("mortgage", "m-001")
    reply["early_repayment_charges"]["value"] = [{"year": 1}]  # missing "percent"

    with pytest.raises(ValidationError, match="early_repayment_charges.value.0.percent"):
        model.model_validate(reply)


def test_missing_field_fails():
    model = build_model(schema_for("mortgage"))
    reply = valid_reply("mortgage", "m-001")
    del reply["contact_phone"]

    with pytest.raises(ValidationError, match="contact_phone"):
        model.model_validate(reply)
