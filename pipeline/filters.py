"""Formatting filters available to every pack's template.yaml.

Plain functions, registered with Jinja by render.py via FILTERS, so each can be
tested on its own. Output is customer-facing UK English.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def gbp(amount: float) -> str:
    """1359.76 -> '£1,359.76'. Negative amounts read '-£5.00'."""
    return _money(amount, Decimal("0.01"), "{:,.2f}")


def gbp0(amount: float) -> str:
    """627497.65 -> '£627,498' (rounded to whole pounds)."""
    return _money(amount, Decimal(1), "{:,.0f}")


def _money(amount: float, step: Decimal, pattern: str) -> str:
    # Half-up via Decimal: Python's round() uses banker's rounding (2.5 -> 2),
    # which is wrong for money shown to a customer.
    rounded = Decimal(str(amount)).quantize(step, rounding=ROUND_HALF_UP)
    sign = "-" if rounded < 0 else ""
    return f"{sign}£{pattern.format(abs(rounded))}"


def pct(value: float) -> str:
    """4.89 -> '4.89 percent', 2.0 -> '2 percent' (spoken-friendly)."""
    return f"{_number(value)} percent"


def long_date(iso_date: str) -> str:
    """'2028-10-31' -> '31 October 2028'."""
    day = date.fromisoformat(iso_date)
    return f"{day.day} {day:%B %Y}"


def weekday_date(iso_date: str) -> str:
    """'2026-11-04' -> 'Wednesday 4 November'."""
    day = date.fromisoformat(iso_date)
    return f"{day:%A} {day.day} {day:%B}"


def years_months(months: int) -> str:
    """24 -> '2 years', 18 -> '1 year and 6 months', 6 -> '6 months'."""
    years, remainder = divmod(int(months), 12)
    parts = [_plural(years, "year")] if years else []
    if remainder or not years:
        parts.append(_plural(remainder, "month"))
    return " and ".join(parts)


def time_12h(hh_mm: str) -> str:
    """'13:00' -> '1pm', '08:30' -> '8:30am', '00:00' -> '12am'."""
    moment = time.fromisoformat(hh_mm)
    hour = moment.hour % 12 or 12
    minutes = f":{moment.minute:02d}" if moment.minute else ""
    return f"{hour}{minutes}{'am' if moment.hour < 12 else 'pm'}"


def day_phrase(iso_datetime: str, ref_date: str) -> str:
    """A time relative to the appointment day.

    ('2026-11-04T11:00', '2026-11-04') -> '11am on the day'
    ('2026-11-03T09:00', '2026-11-04') -> '9am the day before'
    anything else -> '9am on Monday 2 November'
    """
    moment = datetime.fromisoformat(iso_datetime)
    days_before = (date.fromisoformat(ref_date) - moment.date()).days
    clock = time_12h(f"{moment:%H:%M}")
    if days_before == 0:
        return f"{clock} on the day"
    if days_before == 1:
        return f"{clock} the day before"
    return f"{clock} on {weekday_date(moment.date().isoformat())}"


def lower_first(text: str) -> str:
    """'Colonoscopy' -> 'colonoscopy', but acronyms stay: 'MRI scan' -> 'MRI scan'."""
    if not text or (len(text) > 1 and text[1].isupper()):
        return text
    return text[0].lower() + text[1:]


def join_and(items: list[str]) -> str:
    """['a', 'b', 'c'] -> 'a, b and c'."""
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


def table_rows(items: list[dict[str, Any]], *cell_formats: str) -> list[list[str]]:
    """Turn a list of records into table rows, one format string per column.

    ([{'year': 1, 'percent': 2}], 'Year {year}', '{percent}%') -> [['Year 1', '2%']]
    The pack's template says what each column looks like, so the engine needn't know.
    """
    return [[cell.format(**item) for cell in cell_formats] for item in items]


def _number(value: float) -> str:
    """Up to 2 decimal places, without trailing zeros: 2.0 -> '2', 4.50 -> '4.5'."""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


FILTERS = {
    "gbp": gbp,
    "gbp0": gbp0,
    "pct": pct,
    "long_date": long_date,
    "weekday_date": weekday_date,
    "years_months": years_months,
    "time_12h": time_12h,
    "day_phrase": day_phrase,
    "lower_first": lower_first,
    "join_and": join_and,
    "table_rows": table_rows,
}
