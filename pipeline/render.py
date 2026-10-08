"""Render a pack's template.yaml into scenes for one customer.

Each scene comes out as {id, title, visual, narration, speech}. Scenes whose `when:`
is false are left out. Visuals stay structured data for React, never HTML.
"""

from __future__ import annotations

import re
from typing import Any

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from pipeline.filters import FILTERS
from pipeline.packs import Customer, TemplateConfig
from pipeline.speech import to_speech

# A string that is exactly one {{ expression }} and nothing else.
_WHOLE_EXPRESSION = re.compile(r"\s*\{\{((?:(?!\{\{|\}\}).)*)\}\}\s*", re.DOTALL)
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([.,;:!?])")


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
