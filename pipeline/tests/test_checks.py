import json
from pathlib import Path

import pytest

from pipeline.checks import run_rules, values_of
from pipeline.packs import Rule, load_pack

PACKS_DIR = Path(__file__).resolve().parents[2] / "packs"


def pack_rule(pack_name: str, rule_id: str) -> Rule:
    """A rule exactly as it ships in the pack's checks.yaml."""
    rules = load_pack(pack_name, packs_dir=PACKS_DIR).checks.rules
    return next(rule for rule in rules if rule.id == rule_id)


def good_values(pack_name: str, customer_id: str) -> dict:
    """Correct values; ground truth is only a test fixture here, never read by the pipeline."""
    path = PACKS_DIR / pack_name / "samples" / "ground_truth" / f"{customer_id}.json"
    return json.loads(path.read_text())


def run_one(rule: Rule, values: dict):
    (result,) = run_rules(values, [rule])
    return result


def test_values_of_unwraps_evidence():
    wrapped = {"loan_amount": {"value": 256500, "evidence_quote": "£256,500", "page": 1}}

    assert values_of(wrapped) == {"loan_amount": 256500}


def test_result_carries_rule_id_and_severity():
    result = run_one(pack_rule("mortgage", "rate-plausible"), good_values("mortgage", "m-001"))

    assert result.rule_id == "rate-plausible"
    assert result.severity == "error"


# --- required ---


def test_required_passes_when_all_present():
    result = run_one(pack_rule("mortgage", "all-required"), good_values("mortgage", "m-001"))

    assert result.status == "pass"


def test_required_fails_naming_the_missing_field():
    values = good_values("mortgage", "m-001") | {"product_name": "  "}

    result = run_one(pack_rule("mortgage", "all-required"), values)

    assert result.status == "fail"
    assert result.fields == ["product_name"]


def test_required_respects_allow_null():
    # h-001 is a local anaesthetic: no fasting times, so those fields are null.
    values = good_values("healthcare", "h-001")
    assert values["last_food_time"] is None

    assert run_one(pack_rule("healthcare", "all-required"), values).status == "pass"

    values["patient_name"] = None
    assert run_one(pack_rule("healthcare", "all-required"), values).fields == ["patient_name"]


# --- range ---


def test_range_passes_inside_and_fails_outside():
    rule = pack_rule("mortgage", "rate-plausible")
    values = good_values("mortgage", "m-001")

    assert run_one(rule, values).status == "pass"
    assert run_one(rule, values | {"initial_rate_percent": 16}).status == "fail"


def test_range_min_items():
    rule = pack_rule("healthcare", "has-warning-signs")
    values = good_values("healthcare", "h-001")

    assert run_one(rule, values).status == "pass"
    assert run_one(rule, values | {"warning_signs": []}).status == "fail"


def test_range_skips_null():
    values = good_values("mortgage", "m-001") | {"term_years": None}

    assert run_one(pack_rule("mortgage", "term-plausible"), values).status == "skip"


# --- regex ---


def test_regex_single_field():
    rule = pack_rule("mortgage", "phone-format")
    values = good_values("mortgage", "m-001")

    assert run_one(rule, values).status == "pass"
    assert run_one(rule, values | {"contact_phone": "020 7946 0000"}).status == "fail"


def test_regex_list_of_fields_names_the_bad_one():
    rule = pack_rule("healthcare", "phone-format")
    values = good_values("healthcare", "h-001")
    assert run_one(rule, values).status == "pass"

    result = run_one(rule, values | {"out_of_hours_phone": "999"})

    assert result.status == "fail"
    assert result.fields == ["out_of_hours_phone"]


# --- engine ---


def test_unknown_rule_type_raises():
    rule = Rule(id="mystery", type="telepathy", severity="warn")

    with pytest.raises(ValueError, match="unknown type 'telepathy'"):
        run_rules({}, [rule])
