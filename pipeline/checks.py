"""Quality engine: runs a pack's checks.yaml rules against extracted values.

Each rule `type` maps to one generic function in RULE_CHECKS. Nothing here
knows which pack it is checking - the rules themselves carry the field names.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from pipeline.packs import Rule

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


RULE_CHECKS: dict[str, Callable[[Values, dict[str, Any]], CheckOutcome]] = {
    "required": check_required,
    "range": check_range,
    "regex": check_regex,
}


def _as_list(value: str | list[str]) -> list[str]:
    return value if isinstance(value, list) else [value]


def _normalise(text: str) -> str:
    return " ".join(text.split()).casefold()


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())
