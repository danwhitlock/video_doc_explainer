import json
import re
from itertools import pairwise
from pathlib import Path

import pytest

from pipeline.packs import load_pack
from pipeline.readability import split_sentences
from pipeline.render import (
    WORDS_PER_SECOND,
    captions_vtt,
    render_scenes,
    scenes_document,
    write_render_outputs,
)

PACKS_DIR = Path(__file__).resolve().parents[2] / "packs"
TIMESTAMP = r"\d{2}:\d{2}:\d{2}\.\d{3}"


def scene(scene_id: str, narration: str) -> dict:
    return {"id": scene_id, "title": "", "visual": {}, "narration": narration, "speech": narration}


SCENES = [
    scene("welcome", "Hi Priya. This video explains your offer."),  # 7 words
    scene("your-rate", "You pay £1,359.76 a month. It is fixed for two years."),  # 11 words
]


def m001_scenes() -> list[dict]:
    pack = load_pack("mortgage", packs_dir=PACKS_DIR)
    values = json.loads((PACKS_DIR / "mortgage/samples/ground_truth/m-001.json").read_text())
    return render_scenes(pack.template, values, pack.customers[0], pack.theme.brand)


def cue_times(vtt: str) -> list[tuple[float, float]]:
    def seconds(stamp: str) -> float:
        hours, minutes, secs = stamp.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(secs)

    pairs = re.findall(rf"({TIMESTAMP}) --> ({TIMESTAMP})", vtt)
    return [(seconds(start), seconds(end)) for start, end in pairs]


def test_durations_and_start_times():
    document = scenes_document(SCENES, "mortgage", "m-001")

    first, second = document["scenes"]
    assert document["words_per_second"] == WORDS_PER_SECOND
    assert first["start_seconds"] == 0
    assert first["duration_seconds"] == pytest.approx(7 / 2.6, abs=0.01)
    assert second["start_seconds"] == pytest.approx(7 / 2.6, abs=0.01)
    assert document["total_seconds"] == pytest.approx(18 / 2.6, abs=0.01)
    assert second["speech"] == SCENES[1]["speech"]  # rendered fields are kept


def test_vtt_format_and_one_cue_per_sentence():
    vtt = captions_vtt(SCENES)

    assert vtt.startswith("WEBVTT\n\n")
    assert re.search(rf"^{TIMESTAMP} --> {TIMESTAMP}$", vtt, re.MULTILINE)
    cue_ids = re.findall(r"^([a-z-]+-\d+)$", vtt, re.MULTILINE)
    assert cue_ids == ["welcome-1", "welcome-2", "your-rate-1", "your-rate-2"]


def test_decimal_point_does_not_split_a_cue():
    assert "You pay £1,359.76 a month." in captions_vtt(SCENES).splitlines()


def test_cues_are_continuous_and_end_exactly_at_the_total():
    scenes = m001_scenes()
    times = cue_times(captions_vtt(scenes))
    exact_total = sum(len(s["narration"].split()) for s in scenes) / WORDS_PER_SECOND

    assert times[0][0] == 0
    for (_, previous_end), (next_start, _) in pairwise(times):
        assert next_start == previous_end  # no gaps, no overlaps
    # VTT shows milliseconds; scenes.json rounds total_seconds to 2 dp.
    assert times[-1][1] == pytest.approx(exact_total, abs=0.0005)
    total = scenes_document(scenes, "mortgage", "m-001")["total_seconds"]
    assert total == pytest.approx(exact_total, abs=0.005)


def test_split_sentences_keeps_punctuation():
    assert split_sentences("Hi Priya. You pay £1,359.76 a month!") == [
        "Hi Priya.",
        "You pay £1,359.76 a month!",
    ]


def test_outputs_contain_only_what_the_template_used(tmp_path):
    # The extraction has "Ms Priya Raman"; the template only uses the preferred name.
    paths = write_render_outputs(tmp_path, m001_scenes(), "mortgage", "m-001")

    assert [path.name for path in paths] == ["scenes.json", "captions.vtt"]
    for path in paths:
        text = path.read_text()
        assert "Priya" in text
        assert "Raman" not in text
