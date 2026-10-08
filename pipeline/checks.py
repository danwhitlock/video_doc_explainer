"""Quality engine: runs a pack's checks.yaml rules against extracted values.

Each rule `type` maps to one generic function in RULE_CHECKS. Nothing here
knows which pack it is checking - the rules themselves carry the field names.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

from pipeline.packs import Rule
from pipeline.readability import flesch_reading_ease

Status = Literal["pass", "fail", "skip"]
Values = dict[str, Any]


@dataclass
class CheckResult:
    rule_id: str
    severity: str
    status: Status
    message: str
    fields: list[str] = field(default_factory=list)


def values_of(extracted_fields: dict[str, dict[str, Any]]) -> Values:
    """Unwrap {name: {value, evidence_quote, page}} to {name: value}."""
    return {name: wrapped["value"] for name, wrapped in extracted_fields.items()}


def run_rules(values: Values, rules: list[Rule]) -> list[CheckResult]:
    """Run every rule, in order, and return one result per rule."""
    results = []
    for rule in rules:
        check = RULE_CHECKS.get(rule.type)
        if check is None:
            raise ValueError(f"Rule {rule.id!r} has unknown type {rule.type!r}")
        status, message, fields = check(values, rule.model_extra or {})
        results.append(CheckResult(rule.id, rule.severity, status, message, fields))
    return results


# Each check takes (values, the rule's own parameters) and returns
# (status, message, fields involved).
CheckOutcome = tuple[Status, str, list[str]]


def check_required(values: Values, params: dict[str, Any]) -> CheckOutcome:
    """Fields must have a value. `fields: "*"` means all; `allow_null` exempts some."""
    names = list(values) if params["fields"] == "*" else _as_list(params["fields"])
    allowed_null = set(params.get("allow_null", []))
    missing = [name for name in names if name not in allowed_null and _is_missing(values.get(name))]
    if missing:
        return "fail", f"Missing value for: {', '.join(missing)}", missing
    return "pass", f"All {len(names)} required fields present", []


def check_range(values: Values, params: dict[str, Any]) -> CheckOutcome:
    """A number within min/max, or a list with at least min_items entries."""
    name = params["field"]
    value = values.get(name)
    if value is None:
        return "skip", f"{name} is empty; nothing to range-check", [name]

    if "min_items" in params:
        if len(value) < params["min_items"]:
            return (
                "fail",
                f"{name} has {len(value)} item(s); needs at least {params['min_items']}",
                [name],
            )
        return "pass", f"{name} has {len(value)} item(s)", [name]

    low, high = params.get("min"), params.get("max")
    if (low is not None and value < low) or (high is not None and value > high):
        return "fail", f"{name} = {value} is outside {low}–{high}", [name]
    return "pass", f"{name} = {value} is within {low}–{high}", [name]


def check_regex(values: Values, params: dict[str, Any]) -> CheckOutcome:
    """Each named field (one or a list) must match the pattern. Empty fields are skipped."""
    names = _as_list(params["field"])
    pattern = re.compile(params["pattern"])
    present = [name for name in names if values.get(name) is not None]
    if not present:
        return "skip", f"No value to check for: {', '.join(names)}", names

    bad = [name for name in present if not pattern.search(str(values[name]))]
    if bad:
        return "fail", f"Unexpected format for: {', '.join(bad)}", bad
    return "pass", f"Format OK for: {', '.join(present)}", present


def check_compare(values: Values, params: dict[str, Any]) -> CheckOutcome:
    """One field against another, e.g. total_amount_repayable > loan_amount."""
    names = [params["field"], params["other"]]
    if any(values.get(name) is None for name in names):
        return "skip", f"Can't compare {_describe(params)}: a value is empty", names
    if _holds(values, params):
        return "pass", f"{_describe(params)} holds", names
    return "fail", f"Expected {_describe(params)}", names


def check_conditional(values: Values, params: dict[str, Any]) -> CheckOutcome:
    """If the `if` condition holds, the `then` condition must too; otherwise not applicable."""
    condition, requirement = params["if"], params["then"]
    names = [condition["field"], requirement["field"]]
    if not _holds(values, condition):
        return "skip", f"Not applicable: {_describe(condition)} is not true", names
    if _holds(values, requirement):
        return "pass", f"{_describe(condition)}, and {_describe(requirement)}", names
    return "fail", f"{_describe(condition)}, so expected {_describe(requirement)}", names


def check_date_order(values: Values, params: dict[str, Any]) -> CheckOutcome:
    """`before` must be strictly earlier than `after`.

    Each side is a field holding an ISO date or datetime, or a {date, time} pair
    of fields. Null values fail unless the rule sets skip_if_null. Text that
    isn't ISO (e.g. "next Tuesday") fails - this is where `format: date` is enforced.
    """
    before_label, before_fields, before_text = _moment(values, params["before"])
    after_label, after_fields, after_text = _moment(values, params["after"])
    names = before_fields + after_fields

    if before_text is None or after_text is None:
        if params.get("skip_if_null"):
            return "skip", f"Not checked: {before_label} or {after_label} is empty", names
        return "fail", f"Missing date: {before_label} or {after_label} is empty", names

    try:
        before, after = datetime.fromisoformat(before_text), datetime.fromisoformat(after_text)
    except ValueError:
        return "fail", f"Can't read {before_text!r} or {after_text!r} as a date", names

    if before < after:
        return (
            "pass",
            f"{before_label} ({before_text}) is before {after_label} ({after_text})",
            names,
        )
    return (
        "fail",
        f"Expected {before_label} ({before_text}) before {after_label} ({after_text})",
        names,
    )


def _moment(values: Values, spec: str | dict[str, str]) -> tuple[str, list[str], str | None]:
    """Turn a field name or {date, time} spec into (label, fields, ISO text or None if empty)."""
    if isinstance(spec, str):
        value = values.get(spec)
        return spec, [spec], None if value is None else str(value)

    date, time = values.get(spec["date"]), values.get(spec["time"])
    text = None if date is None or time is None else f"{date}T{time}"
    return f"{spec['date']} + {spec['time']}", [spec["date"], spec["time"]], text


def check_formula(values: Values, params: dict[str, Any]) -> CheckOutcome:
    """Recompute a value with a named formula and compare it to `target`.

    `inputs` maps the formula's argument names to field names. With a target,
    the result must match within tolerance_abs or tolerance_pct; without one,
    the formula itself returns True/False.
    """
    name = params["formula"]
    formula = FORMULAS.get(name)
    if formula is None:
        raise ValueError(f"Unknown formula {name!r}")

    inputs = {arg: values.get(field) for arg, field in params["inputs"].items()}
    target = params.get("target")
    names = list(params["inputs"].values()) + ([target] if target else [])
    if any(value is None for value in inputs.values()) or (target and values.get(target) is None):
        return "skip", f"Can't compute {name}: an input is empty", names

    try:
        computed = formula(**inputs)
    except ZeroDivisionError:
        return "fail", f"Can't compute {name}: division by zero", names

    if target is None:
        if computed:
            return "pass", f"{name} holds", names
        return "fail", f"{name} does not hold for {inputs}", names

    actual = values[target]
    allowed = params.get("tolerance_abs", 0) or abs(computed) * params.get("tolerance_pct", 0) / 100
    if abs(actual - computed) <= allowed:
        return "pass", f"{target} = {actual} matches {name} = {computed:.2f}", names
    return (
        "fail",
        f"{target} = {actual} but {name} gives {computed:.2f} (allowed ±{allowed:.2f})",
        names,
    )


def ltv(loan: float, value: float) -> float:
    """Loan-to-value, as a percentage."""
    return loan / value * 100


def amortised_payment(principal: float, annual_rate_percent: float, years: int) -> float:
    """Monthly payment on a repayment mortgage: P * r / (1 - (1 + r) ** -n)."""
    monthly_rate = annual_rate_percent / 100 / 12
    payments = years * 12
    if monthly_rate == 0:
        return principal / payments
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -payments)


def erc_years_cover(schedule: list[dict[str, Any]], months: int) -> bool:
    """One early repayment charge entry per year of the initial rate period."""
    return len(schedule) == months / 12


FORMULAS: dict[str, Callable[..., Any]] = {
    "ltv": ltv,
    "amortised_payment": amortised_payment,
    "erc_years_cover": erc_years_cover,
}


# Shared by compare and conditional. `>` and `<` treat a null as "not true",
# because Python can't order None against a number.
OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    "==": lambda left, right: left == right,
    ">": lambda left, right: left is not None and right is not None and left > right,
    "<": lambda left, right: left is not None and right is not None and left < right,
    "in": lambda left, right: left in right,
    "not_null": lambda left, _right: left is not None,
}


def _holds(values: Values, condition: dict[str, Any]) -> bool:
    """Evaluate one {field, op, value | other}: `value` is a literal, `other` a field name."""
    operator = OPERATORS.get(condition["op"])
    if operator is None:
        raise ValueError(f"Unknown operator {condition['op']!r}")
    left = values.get(condition["field"])
    right = values.get(condition["other"]) if "other" in condition else condition.get("value")
    return operator(left, right)


def _describe(condition: dict[str, Any]) -> str:
    """Readable form of a condition, e.g. 'product_fee == 0' or 'last_food_time is set'."""
    if condition["op"] == "not_null":
        return f"{condition['field']} is set"
    right = condition["other"] if "other" in condition else condition.get("value")
    return f"{condition['field']} {condition['op']} {right}"


GROUNDING_RULE_ID = "grounding"
# warn, not error: an ungrounded field is flagged in the UI but doesn't block the
# explainer. Hard value errors are already blocked by each pack's own error rules.
GROUNDING_SEVERITY = "warn"


def check_grounding(
    extracted_fields: dict[str, dict[str, Any]], pages: list[str]
) -> list[CheckResult]:
    """Built-in hallucination guard: each evidence quote must appear on its cited page.

    Compared after collapsing whitespace and case, because PDF text is hard-wrapped
    mid-sentence. One result per field, so the UI can show a per-field badge.
    """
    normalised_pages = [_normalise(page) for page in pages]
    results = []
    for name, wrapped in extracted_fields.items():
        status, message = _ground_one(wrapped, normalised_pages)
        results.append(CheckResult(GROUNDING_RULE_ID, GROUNDING_SEVERITY, status, message, [name]))
    return results


def _ground_one(wrapped: dict[str, Any], normalised_pages: list[str]) -> tuple[Status, str]:
    if wrapped["value"] is None:
        return "skip", "No value, so no evidence to ground"

    quote, page = _normalise(wrapped["evidence_quote"] or ""), wrapped["page"]
    if not quote:
        return "fail", "Ungrounded: no evidence quote"
    if (
        page is not None
        and 1 <= page <= len(normalised_pages)
        and quote in normalised_pages[page - 1]
    ):
        return "pass", f"Quote found on page {page}"

    found_on = [number for number, text in enumerate(normalised_pages, 1) if quote in text]
    if found_on:
        return "fail", f"Ungrounded: quote found on page {found_on[0]}, not page {page}"
    return "fail", f"Ungrounded: quote not found on page {page} or any other page"


READABILITY_RULE_ID = "readability"


def check_readability(text: str, minimum: float) -> CheckResult:
    """Narration should score at least the pack's reading_ease_min (warn below)."""
    score = flesch_reading_ease(text)
    if score >= minimum:
        return CheckResult(
            READABILITY_RULE_ID,
            "warn",
            "pass",
            f"Reading ease {score} meets the target of {minimum}",
        )
    return CheckResult(
        READABILITY_RULE_ID,
        "warn",
        "fail",
        f"Reading ease {score} is below the target of {minimum}",
    )


def build_quality_report(
    extracted_fields: dict[str, dict[str, Any]], pages: list[str], rules: list[Rule]
) -> dict[str, Any]:
    """Run the pack's rules plus grounding and summarise them for quality_report.json."""
    return summarise(quality_results(extracted_fields, pages, rules))


def quality_results(
    extracted_fields: dict[str, dict[str, Any]], pages: list[str], rules: list[Rule]
) -> list[CheckResult]:
    """Every pack rule, then one grounding result per field."""
    return run_rules(values_of(extracted_fields), rules) + check_grounding(extracted_fields, pages)


def summarise(results: list[CheckResult]) -> dict[str, Any]:
    """Counts plus `blocking`, which is true when any error-severity check failed:
    rendering is skipped for that customer. Warnings render but are shown in the UI."""
    failed = [result for result in results if result.status == "fail"]
    errors = sum(result.severity == "error" for result in failed)
    return {
        "summary": {
            "pass": sum(result.status == "pass" for result in results),
            "fail": len(failed),
            "skip": sum(result.status == "skip" for result in results),
            "errors": errors,
            "warnings": len(failed) - errors,
            "blocking": errors > 0,
        },
        "results": [asdict(result) for result in results],
    }


RULE_CHECKS: dict[str, Callable[[Values, dict[str, Any]], CheckOutcome]] = {
    "required": check_required,
    "range": check_range,
    "regex": check_regex,
    "compare": check_compare,
    "conditional": check_conditional,
    "date_order": check_date_order,
    "formula": check_formula,
}


def _as_list(value: str | list[str]) -> list[str]:
    return value if isinstance(value, list) else [value]


def _normalise(text: str) -> str:
    return " ".join(text.split()).casefold()


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())
