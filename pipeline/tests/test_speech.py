import json
from pathlib import Path

import pytest

from pipeline.packs import load_pack
from pipeline.render import render_scenes
from pipeline.speech import to_speech

PACKS_DIR = Path(__file__).resolve().parents[2] / "packs"
RULES = {"phone_numbers": "digits", "symbols": {"%": " percent"}}


def test_phone_number_matches_the_template_comment():
    speech = to_speech("Call us on 01632 960412 today.", RULES)

    assert speech == "Call us on oh one six three two, nine six oh, four one two today."


def test_phone_number_keeps_its_written_groups():
    speech = to_speech("Ring 020 7946 0000.", RULES)

    assert speech == "Ring oh two oh, seven nine four six, oh oh oh oh."


def test_unspaced_phone_number():
    assert to_speech("01632960412", RULES) == "oh one six three two, nine six oh, four one two"


def test_percent_symbol_is_spoken():
    assert to_speech("Overpay up to 10% a year.", RULES) == "Overpay up to 10 percent a year."


@pytest.mark.parametrize(
    "text",
    [
        "Your fixed rate ends in 2028.",
        "Please arrive at 8:30am.",
        "Quote reference FBS-2026-104381.",
        "Your loan is £256,500.",
        "Hospital number 0123456.",  # too short to be a UK phone number
    ],
)
def test_other_numbers_are_left_alone(text):
    assert to_speech(text, RULES) == text


def test_unknown_rules_are_errors():
    with pytest.raises(ValueError, match="Unknown speech rule 'emoji'"):
        to_speech("Hi", {"emoji": "words"})
    with pytest.raises(ValueError, match="Unsupported speech rule phone_numbers: 'words'"):
        to_speech("Hi", {"phone_numbers": "words"})


def test_render_adds_speech_and_keeps_narration_as_written():
    pack = load_pack("mortgage", packs_dir=PACKS_DIR)
    values = json.loads((PACKS_DIR / "mortgage/samples/ground_truth/m-001.json").read_text())

    scenes = render_scenes(pack.template, values, pack.customers[0], pack.theme.brand)
    contact = next(scene for scene in scenes if scene["id"] == "contact")

    assert "01632 960412" in contact["narration"]
    assert "oh one six three two, nine six oh, four one two" in contact["speech"]
    assert "01632" not in contact["speech"]
