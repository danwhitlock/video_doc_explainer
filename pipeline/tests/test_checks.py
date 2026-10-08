import json
from pathlib import Path

import pytest

from pipeline.checks import (
    amortised_payment,
    build_quality_report,
    check_grounding,
    run_rules,
    values_of,
)
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


# --- date_order ---


def test_date_order_plain_dates():
    rule = pack_rule("mortgage", "expiry-after-offer")
    values = good_values("mortgage", "m-001")

    assert run_one(rule, values).status == "pass"

    reversed_dates = values | {"offer_date": "2027-03-14", "offer_expiry_date": "2026-09-14"}
    assert run_one(rule, reversed_dates).status == "fail"


def test_date_order_fails_text_that_is_not_iso():
    values = good_values("mortgage", "m-001") | {"offer_date": "next Tuesday"}

    result = run_one(pack_rule("mortgage", "expiry-after-offer"), values)

    assert result.status == "fail"
    assert "Can't read 'next Tuesday'" in result.message


def test_date_order_datetimes_and_skip_if_null():
    rule = pack_rule("healthcare", "food-before-fluids")

    assert run_one(rule, good_values("healthcare", "h-003")).status == "pass"
    # h-001 is a local anaesthetic: no fasting times, and the rule says skip_if_null.
    assert run_one(rule, good_values("healthcare", "h-001")).status == "skip"


def test_date_order_null_fails_without_skip_if_null():
    values = good_values("mortgage", "m-001") | {"offer_expiry_date": None}

    assert run_one(pack_rule("mortgage", "expiry-after-offer"), values).status == "fail"


def test_date_order_date_plus_time_pair():
    rule = pack_rule("healthcare", "fluids-before-arrival")
    values = good_values("healthcare", "h-003")  # arrives 07:00, fluids until 06:00

    result = run_one(rule, values)
    assert result.status == "pass"
    assert result.fields == ["last_clear_fluids_time", "appointment_date", "arrival_time"]

    late_fluids = values | {"last_clear_fluids_time": f"{values['appointment_date']}T07:30"}
    assert run_one(rule, late_fluids).status == "fail"


def test_date_order_equal_moments_fail():
    values = good_values("mortgage", "m-001")
    same_day = values | {"offer_expiry_date": values["offer_date"]}

    assert run_one(pack_rule("mortgage", "expiry-after-offer"), same_day).status == "fail"


# --- formula ---


def test_amortised_payment_reproduces_the_document():
    # m-001: £256,500 at 4.89% over 30 years; the offer letter says £1,359.76.
    assert amortised_payment(256500, 4.89, 30) == pytest.approx(1359.76, rel=0.01)
    assert amortised_payment(12000, 0, 1) == 1000  # 0% guard: no division by zero


def test_formula_ltv_within_absolute_tolerance():
    rule = pack_rule("mortgage", "ltv-matches-loan-and-value")
    values = good_values("mortgage", "m-001")

    assert run_one(rule, values).status == "pass"
    assert run_one(rule, values | {"ltv_percent": 80}).status == "fail"


def test_formula_payment_within_percentage_tolerance():
    rule = pack_rule("mortgage", "initial-payment-recomputes")
    values = good_values("mortgage", "m-001")

    assert run_one(rule, values).status == "pass"

    result = run_one(rule, values | {"monthly_payment_initial": 1500})
    assert result.status == "fail"
    assert "but amortised_payment gives" in result.message


def test_formula_without_target_is_true_or_false():
    rule = pack_rule("mortgage", "erc-years-cover-fixed-period")
    values = good_values("mortgage", "m-001")  # 24-month fix, 2 ERC years
    assert values["initial_period_months"] == 24

    assert run_one(rule, values).status == "pass"

    one_year = values | {"early_repayment_charges": [{"year": 1, "percent": 2}]}
    assert run_one(rule, one_year).status == "fail"


def test_formula_skips_null_input():
    values = good_values("mortgage", "m-001") | {"property_value": None}

    assert run_one(pack_rule("mortgage", "ltv-matches-loan-and-value"), values).status == "skip"


def test_formula_unknown_name_raises():
    rule = Rule(id="x", type="formula", severity="warn", formula="magic", inputs={})

    with pytest.raises(ValueError, match="Unknown formula 'magic'"):
        run_rules({}, [rule])


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


def test_grounding_skips_absence_facts_with_a_reason():
    for absent in (False, []):
        result = ground_one(evidenced(absent, None, None))
        assert result.status == "skip"
        assert result.message == "Not stated in the document (inferred from absence)"


def test_grounding_still_checks_a_false_that_has_a_quote():
    assert ground_one(evidenced(False, "An invented quote", 1)).status == "fail"


def test_grounding_fails_true_without_a_quote():
    assert ground_one(evidenced(True, None, None)).status == "fail"


def test_grounding_skips_null_values():
    assert ground_one(evidenced(None, None, None)).status == "skip"


# --- quality report ---


def report_for(values: dict) -> dict:
    """Report for these values, with every quote genuinely on page 1."""
    fields = {name: evidenced(value, f"quote for {name}", 1) for name, value in values.items()}
    pages = [" ".join(f"quote for {name}" for name in values)]
    rules = load_pack("mortgage", packs_dir=PACKS_DIR).checks.rules
    return build_quality_report(fields, pages, rules)


def test_report_has_the_briefs_fields_and_a_clean_summary():
    report = report_for(good_values("mortgage", "m-001"))

    assert set(report["results"][0]) == {"rule_id", "severity", "status", "message", "fields"}
    assert report["summary"] == {
        "pass": 12 + 24,  # every rule + one grounding result per field
        "fail": 0,
        "skip": 0,
        "errors": 0,
        "warnings": 0,
        "blocking": False,
    }


def test_error_failure_blocks_but_warning_alone_does_not():
    warning_only = report_for(good_values("mortgage", "m-001") | {"contact_phone": "999"})
    assert warning_only["summary"]["warnings"] == 1
    assert warning_only["summary"]["blocking"] is False

    error = report_for(good_values("mortgage", "m-001") | {"initial_rate_percent": 16})
    assert error["summary"]["errors"] >= 1
    assert error["summary"]["blocking"] is True
