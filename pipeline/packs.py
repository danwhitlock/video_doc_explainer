from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict


class PackConfig(BaseModel):
    """Parsed `pack.yaml`: identity, document type and demo-wide settings."""

    name: str
    display_name: str
    industry: str
    brand: str
    document_type: str
    schema_version: str
    retention_days: int
    reading_ease_min: int
    visual_types: list[str]
    suggested_questions: list[str]


class Rule(BaseModel):
    """One quality rule from `checks.yaml`.

    Rule types (required, range, regex, compare, date_order, formula,
    conditional, sum_check) each carry different extra fields - checks.py
    (not built yet) is what interprets them. Loading only needs `id`, `type`
    and `severity`; everything else is kept as-is via `model_extra`.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    severity: str


class ChecksConfig(BaseModel):
    """Parsed `checks.yaml`."""

    rules: list[Rule]


class Scene(BaseModel):
    """One scene from `template.yaml`."""

    id: str
    title: str
    visual: dict[str, Any]
    narration: str
    when: str | None = None


class TemplateConfig(BaseModel):
    """Parsed `template.yaml`.

    Packs can add their own top-level narration lookup tables (e.g.
    healthcare's `anaesthetic_explained`) - `model_extra` keeps those
    available to render.py without a schema change.
    """

    model_config = ConfigDict(extra="allow")

    speech: dict[str, Any]
    scenes: list[Scene]


class ContrastPair(BaseModel):
    """One colour-pair requirement checked by `npm run check:themes`."""

    fg: str
    bg: str
    min: float


class ThemeConfig(BaseModel):
    """Parsed `theme.json`.

    Brand/color/font/shape/motion/voice are consumed directly as CSS custom
    properties by the web app, so they're kept as loosely-typed dicts here
    rather than re-declaring every colour and font name.
    """

    brand: dict[str, Any]
    color: dict[str, str]
    font: dict[str, str]
    shape: dict[str, Any]
    motion: dict[str, Any]
    voice: dict[str, Any]
    tone: str
    contrast_pairs: list[ContrastPair]


class Customer(BaseModel):
    """One entry from `customers.json`."""

    id: str
    preferred_name: str
    document: str
    persona: str
    prefs: dict[str, Any]


class Pack(BaseModel):
    """Everything the engine needs to run one industry pack."""

    config: PackConfig
    extraction_schema: dict[str, Any]  # JSON Schema; used as-is by extract.py
    checks: ChecksConfig
    template: TemplateConfig
    theme: ThemeConfig
    customers: list[Customer]


def load_pack(name: str, packs_dir: Path | str = "packs") -> Pack:
    """Load one industry pack's config files into a typed `Pack`."""
    pack_dir = Path(packs_dir) / name

    with open(pack_dir / "pack.yaml") as f:
        config = PackConfig.model_validate(yaml.safe_load(f))

    with open(pack_dir / "schema.json") as f:
        extraction_schema = json.load(f)

    with open(pack_dir / "checks.yaml") as f:
        checks = ChecksConfig.model_validate(yaml.safe_load(f))

    with open(pack_dir / "template.yaml") as f:
        template = TemplateConfig.model_validate(yaml.safe_load(f))

    with open(pack_dir / "theme.json") as f:
        theme = ThemeConfig.model_validate(json.load(f))

    with open(pack_dir / "customers.json") as f:
        customers = [Customer.model_validate(c) for c in json.load(f)]

    return Pack(
        config=config,
        extraction_schema=extraction_schema,
        checks=checks,
        template=template,
        theme=theme,
        customers=customers,
    )
