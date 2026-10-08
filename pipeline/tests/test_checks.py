import json
from pathlib import Path

import pytest

from pipeline.checks import check_grounding, run_rules, values_of
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


# --- compare ---


def test_compare_passes_fails_and_skips():
    rule = pack_rule("mortgage", "total-exceeds-loan")
    values = good_values("mortgage", "m-001")

    assert run_one(rule, values).status == "pass"

    result = run_one(rule, values | {"total_amount_repayable": 1000})
    assert result.status == "fail"
    assert result.message == "Expected total_amount_repayable > loan_amount"

    assert run_one(rule, values | {"loan_amount": None}).status == "skip"


# --- conditional ---


def test_conditional_greater_than_another_field():
    rule = pack_rule("mortgage", "follow-on-payment-higher-when-rate-higher")
    values = good_values("mortgage", "m-001")

    assert run_one(rule, values).status == "pass"
    assert run_one(rule, values | {"monthly_payment_follow_on": 900}).status == "fail"


def test_conditional_equals_a_literal():
    rule = pack_rule("mortgage", "no-fee-means-not-added")
    values = good_values("mortgage", "m-001") | {"product_fee": 0}

    assert run_one(rule, values | {"product_fee_added_to_loan": False}).status == "pass"
    assert run_one(rule, values | {"product_fee_added_to_loan": True}).status == "fail"


def test_conditional_in_skips_when_not_applicable():
    rule = pack_rule("healthcare", "escort-for-sedation-or-general")
    values = good_values("healthcare", "h-001")  # local anaesthetic
    assert values["anaesthetic_type"] == "local"

    assert run_one(rule, values).status == "skip"

    sedation = values | {"anaesthetic_type": "sedation"}
    assert run_one(rule, sedation | {"escort_required": True}).status == "pass"
    assert run_one(rule, sedation | {"escort_required": False}).status == "fail"


def test_conditional_not_null():
    rule = pack_rule("healthcare", "fasting-for-general-anaesthetic")
    values = good_values("healthcare", "h-003")  # general anaesthetic
    assert values["anaesthetic_type"] == "general"

    assert run_one(rule, values).status == "pass"

    result = run_one(rule, values | {"last_food_time": None})
    assert result.status == "fail"
    assert result.message == "anaesthetic_type == general, so expected last_food_time is set"


def test_conditional_unknown_operator_raises():
    rule = Rule(
        id="odd",
        type="conditional",
        severity="warn",
        **{"if": {"field": "a", "op": "~=", "value": 1}, "then": {"field": "b", "op": "not_null"}},
    )

    with pytest.raises(ValueError, match="Unknown operator '~='"):
        run_rules({"a": 1, "b": 2}, [rule])


# --- engine ---


def test_unknown_rule_type_raises():
    rule = Rule(id="mystery", type="telepathy", severity="warn")

    with pytest.raises(ValueError, match="unknown type 'telepathy'"):
        run_rules({}, [rule])


# --- grounding ---

PAGES = [
    "Amount of loan £256,500.00\nValue of the property\n£285,000.00\nYear 1 2% of the amount repaid",
    "Year 2 1% of the amount repaid\nCall us on 01632 960412",
]


def evidenced(value, quote, page):
    return {"value": value, "evidence_quote": quote, "page": page}


def ground_one(wrapped):
    (result,) = check_grounding({"field": wrapped}, PAGES)
    return result


def test_grounding_passes_across_line_breaks_and_case():
    result = ground_one(evidenced(285000, "VALUE OF THE PROPERTY £285,000.00", 1))

    assert result.status == "pass"
    assert result.rule_id == "grounding"
    assert result.fields == ["field"]


def test_grounding_fails_an_invented_quote():
    result = ground_one(evidenced(250000, "Amount of loan £250,000.00", 1))

    assert result.status == "fail"
    assert "not found on page 1 or any other page" in result.message


def test_grounding_fails_wrong_page_and_says_where_it_is():
    result = ground_one(evidenced("01632 960412", "Call us on 01632 960412", 1))

    assert result.status == "fail"
    assert "found on page 2, not page 1" in result.message


def test_grounding_fails_a_quote_spanning_two_pages():
    # Like the m-001 early repayment table, which runs across the page break.
    quote = "Year 1 2% of the amount repaid Year 2 1% of the amount repaid"

    assert ground_one(evidenced([2, 1], quote, 1)).status == "fail"


def test_grounding_fails_out_of_range_page_and_missing_quote():
    assert ground_one(evidenced(256500, "Amount of loan £256,500.00", 9)).status == "fail"
    assert ground_one(evidenced(256500, None, 1)).status == "fail"


def test_grounding_skips_null_values():
    assert ground_one(evidenced(None, None, None)).status == "skip"
