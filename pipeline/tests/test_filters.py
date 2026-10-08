import pytest

from pipeline.filters import (
    FILTERS,
    day_phrase,
    gbp,
    gbp0,
    join_and,
    long_date,
    lower_first,
    pct,
    table_rows,
    time_12h,
    weekday_date,
    years_months,
)

# Examples are taken from the two templates' header comments where they exist.


def test_gbp():
    assert gbp(1359.76) == "£1,359.76"
    assert gbp(0) == "£0.00"
    assert gbp(-5) == "-£5.00"


def test_gbp0_rounds_to_whole_pounds():
    assert gbp0(627497.65) == "£627,498"
    assert gbp0(256500) == "£256,500"


def test_money_rounds_half_up_not_bankers():
    # Python's round(2.5) == 2; a customer document should say £3.
    assert gbp0(2.5) == "£3"
    assert gbp0(3.5) == "£4"
    assert gbp(0.125) == "£0.13"


def test_pct():
    assert pct(4.89) == "4.89 percent"
    assert pct(2.0) == "2 percent"
    assert pct(7.5) == "7.5 percent"


def test_long_date_and_weekday_date():
    assert long_date("2028-10-31") == "31 October 2028"
    assert long_date("2027-03-04") == "4 March 2027"  # no leading zero
    assert weekday_date("2026-11-04") == "Wednesday 4 November"


@pytest.mark.parametrize(
    ("months", "expected"),
    [
        (24, "2 years"),
        (12, "1 year"),
        (18, "1 year and 6 months"),
        (6, "6 months"),
        (1, "1 month"),
        (0, "0 months"),
    ],
)
def test_years_months(months, expected):
    assert years_months(months) == expected


@pytest.mark.parametrize(
    ("hh_mm", "expected"),
    [("13:00", "1pm"), ("08:30", "8:30am"), ("12:00", "12pm"), ("00:00", "12am")],
)
def test_time_12h(hh_mm, expected):
    assert time_12h(hh_mm) == expected


def test_day_phrase():
    assert day_phrase("2026-11-03T09:00", "2026-11-04") == "9am the day before"
    assert day_phrase("2026-11-04T11:00", "2026-11-04") == "11am on the day"
    assert day_phrase("2026-11-02T18:30", "2026-11-04") == "6:30pm on Monday 2 November"


def test_lower_first_keeps_acronyms():
    assert lower_first("Colonoscopy") == "colonoscopy"
    assert lower_first("MRI scan") == "MRI scan"
    assert lower_first("A") == "a"
    assert lower_first("") == ""


def test_join_and():
    assert join_and(["a", "b", "c"]) == "a, b and c"
    assert join_and(["a", "b"]) == "a and b"
    assert join_and(["a"]) == "a"
    assert join_and([]) == ""


def test_table_rows():
    schedule = [{"year": 1, "percent": 2}, {"year": 2, "percent": 1}]

    rows = table_rows(schedule, "Year {year}", "{percent}%")

    assert rows == [["Year 1", "2%"], ["Year 2", "1%"]]


def test_every_filter_named_in_the_templates_is_registered():
    named_in_headers = {
        "gbp",
        "gbp0",
        "pct",
        "long_date",
        "years_months",
        "time_12h",
        "day_phrase",
        "weekday_date",
        "lower_first",
        "join_and",
        "table_rows",
    }

    assert named_in_headers <= set(FILTERS)
