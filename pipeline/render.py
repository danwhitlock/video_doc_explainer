"""Render a pack's template.yaml into scenes for one customer.

Each scene comes out as {id, title, visual, narration, speech}. Scenes whose `when:`
is false are left out. Visuals stay structured data for React, never HTML.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from pipeline.filters import FILTERS
from pipeline.packs import Customer, TemplateConfig
from pipeline.readability import split_sentences
from pipeline.speech import to_speech

# A string that is exactly one {{ expression }} and nothing else.
_WHOLE_EXPRESSION = re.compile(r"\s*\{\{((?:(?!\{\{|\}\}).)*)\}\}\s*", re.DOTALL)
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([.,;:!?])")
WORDS_PER_SECOND = 2.6  # estimate until real audio durations exist
SCENES_NAME = "scenes.json"
CAPTIONS_NAME = "captions.vtt"


def make_environment() -> SandboxedEnvironment:
    """Jinja set up for pack templates.

    StrictUndefined: a misspelt field is an error, not a silent gap in narration.
    Sandboxed: templates are config, so they can't reach Python internals.
    No autoescape: output is data for React (which escapes on display), not HTML.
    """
    env = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)
    env.filters.update(FILTERS)
    return env


def build_context(
    template: TemplateConfig, values: dict[str, Any], customer: Customer, brand: dict[str, Any]
) -> dict[str, Any]:
    """Names available to every template string: d, p, brand, plus any lookup
    tables the pack's template declares (e.g. healthcare's anaesthetic_explained)."""
    return {
        **(template.model_extra or {}),
        "d": _tidy_numbers(values),
        "p": customer.model_dump(),
        "brand": brand,
    }


def render_scenes(
    template: TemplateConfig, values: dict[str, Any], customer: Customer, brand: dict[str, Any]
) -> list[dict[str, Any]]:
    """Render every scene whose `when:` holds, in template order."""
    env = make_environment()
    context = build_context(template, values, customer, brand)
    scenes = []
    for scene in template.scenes:
        if scene.when and not env.compile_expression(scene.when)(**context):
            continue
        narration = _clean(env.from_string(scene.narration).render(context))
        scenes.append(
            {
                "id": scene.id,
                "title": env.from_string(scene.title).render(context),
                "visual": _render_visual(env, scene.visual, context),
                "narration": narration,  # captions + transcript, as written
                "speech": to_speech(narration, template.speech),  # what TTS reads
            }
        )
    return scenes


def scenes_document(
    scenes: list[dict[str, Any]], pack_name: str, customer_id: str
) -> dict[str, Any]:
    """scenes.json: the rendered scenes with estimated start times and durations."""
    words_so_far = 0
    timed = []
    for scene in scenes:
        words = len(scene["narration"].split())
        timed.append(
            scene
            | {
                "start_seconds": round(words_so_far / WORDS_PER_SECOND, 2),
                "duration_seconds": round(words / WORDS_PER_SECOND, 2),
            }
        )
        words_so_far += words
    return {
        "pack": pack_name,
        "customer_id": customer_id,
        "words_per_second": WORDS_PER_SECOND,
        "total_seconds": round(words_so_far / WORDS_PER_SECOND, 2),
        "scenes": timed,
    }


def captions_vtt(scenes: list[dict[str, Any]]) -> str:
    """WebVTT with one cue per sentence, timed continuously across scenes.

    Times come from a running word total, rounded only for display, so small
    rounding errors can't add up into captions drifting out of sync.
    Cue ids name their scene (e.g. "your-loan-2") for the player.
    """
    lines = ["WEBVTT", ""]
    words_so_far = 0
    for scene in scenes:
        for number, sentence in enumerate(split_sentences(scene["narration"]), 1):
            words = len(sentence.split())
            start = _vtt_time(words_so_far / WORDS_PER_SECOND)
            end = _vtt_time((words_so_far + words) / WORDS_PER_SECOND)
            lines += [f"{scene['id']}-{number}", f"{start} --> {end}", sentence, ""]
            words_so_far += words
    return "\n".join(lines)


def write_render_outputs(
    customer_dir: Path, scenes: list[dict[str, Any]], pack_name: str, customer_id: str
) -> list[Path]:
    """Write scenes.json and captions.vtt; return their paths for the manifest."""
    customer_dir.mkdir(parents=True, exist_ok=True)
    scenes_path = customer_dir / SCENES_NAME
    document = scenes_document(scenes, pack_name, customer_id)
    scenes_path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    captions_path = customer_dir / CAPTIONS_NAME
    captions_path.write_text(captions_vtt(scenes))
    return [scenes_path, captions_path]


def _vtt_time(seconds: float) -> str:
    """75.5 -> '00:01:15.500'."""
    total_ms = round(seconds * 1000)
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def _render_visual(env: SandboxedEnvironment, node: Any, context: dict[str, Any]) -> Any:
    """Walk the visual's dicts and lists, rendering every string in it.

    A string that is exactly one {{ expression }} is evaluated, so its real
    value (a list, a number) is passed through rather than its text form.
    """
    if isinstance(node, dict):
        return {key: _render_visual(env, value, context) for key, value in node.items()}
    if isinstance(node, list):
        return [_render_visual(env, item, context) for item in node]
    if not isinstance(node, str):
        return node
    whole = _WHOLE_EXPRESSION.fullmatch(node)
    if whole:
        return env.compile_expression(whole.group(1))(**context)
    return env.from_string(node).render(context)


def _clean(text: str) -> str:
    """Collapse whitespace and remove stray spaces before punctuation left by template loops."""
    return _SPACE_BEFORE_PUNCTUATION.sub(r"\1", " ".join(text.split()))


def _tidy_numbers(value: Any) -> Any:
    """Whole floats become ints (10.0 -> 10) so text reads '10%', not '10.0%'.

    Pydantic stores every JSON `number` as a float; real decimals are untouched.
    """
    if isinstance(value, dict):
        return {key: _tidy_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_tidy_numbers(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value
