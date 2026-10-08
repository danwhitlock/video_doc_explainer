import pytest

from pipeline.checks import check_readability
from pipeline.readability import count_syllables, flesch_reading_ease

# From the m-001 offer letter, section 2.
PDF_RATE_PARAGRAPH = (
    "Your mortgage starts on a fixed rate of 4.89% for 24 months, until 31 October 2028. "
    "After that, it will move to our Standard Variable Rate (SVR), currently 7.49%, "
    "for the rest of the term."
)
# The same facts, written the way the narration should be.
PLAIN_REWRITE = (
    "Your fixed rate lasts two years. After that, your rate goes up. Your payment will be higher."
)


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("cat", 1),
        ("the", 1),
        ("fee", 1),
        ("rate", 1),  # silent final e
        ("whale", 1),  # "-le" after a vowel is silent too
        ("table", 2),  # "-le" after a consonant is a syllable
        ("mortgage", 2),
        ("payment", 2),
        ("explained", 2),  # silent -ed
        ("wanted", 2),  # -ed after t is spoken
        ("repayment", 3),
        ("1,359.76", 6),  # numbers: one per digit
    ],
)
def test_count_syllables(word, expected):
    assert count_syllables(word) == expected


def test_very_simple_text_scores_above_100():
    assert flesch_reading_ease("The cat sat on the mat.") == pytest.approx(116.1)


def test_pdf_paragraph_scores_below_plain_english_and_rewrite_above():
    assert flesch_reading_ease(PDF_RATE_PARAGRAPH) < 60
    assert flesch_reading_ease(PLAIN_REWRITE) > 90


def test_decimal_point_does_not_split_a_sentence():
    one_sentence = "You pay £1,359.76 a month."
    two_sentences = "You pay £1,359 a month. You pay 76 more."

    # Splitting at the "." in 1,359.76 would make the first look like two short sentences.
    assert flesch_reading_ease(one_sentence) < flesch_reading_ease(two_sentences)


def test_text_with_no_words_raises():
    with pytest.raises(ValueError):
        flesch_reading_ease("... !!!")


def test_check_readability_passes_or_warns_around_the_minimum():
    passed = check_readability(PLAIN_REWRITE, minimum=60)
    assert passed.status == "pass"
    assert passed.rule_id == "readability"
    assert passed.severity == "warn"

    warned = check_readability(PDF_RATE_PARAGRAPH, minimum=60)
    assert warned.status == "fail"
    assert "below the target of 60" in warned.message
