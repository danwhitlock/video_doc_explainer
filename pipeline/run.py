"""The full pipeline for one customer, or every customer in a pack.

ingest -> extract -> check -> render (only if nothing blocking) -> quality report
-> chunks -> manifest. Each stage is timed for the manifest.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from pipeline.checks import check_readability, quality_results, summarise, values_of
from pipeline.extract import ExtractionError, extract
from pipeline.ingest import chunk_pages, extract_pages
from pipeline.lineage import build_manifest, write_manifest
from pipeline.packs import Pack, customer_document
from pipeline.providers.base import LLMProvider
from pipeline.render import CAPTIONS_NAME, SCENES_NAME, render_scenes, write_render_outputs

Outcome = Literal["rendered", "blocked", "failed"]


@dataclass
class RunResult:
    customer_id: str
    outcome: Outcome
    errors: int = 0
    warnings: int = 0
    seconds: float = 0.0
    message: str = ""


def run_pack(
    pack: Pack,
    provider: LLMProvider,
    out_dir: Path,
    customer_ids: list[str] | None = None,
    packs_dir: Path | str = "packs",
) -> list[RunResult]:
    """Run each customer (all of them by default). One failing doesn't stop the rest."""
    ids = customer_ids or [customer.id for customer in pack.customers]
    return [run_customer(pack, customer_id, provider, out_dir, packs_dir) for customer_id in ids]


def run_customer(
    pack: Pack,
    customer_id: str,
    provider: LLMProvider,
    out_dir: Path,
    packs_dir: Path | str = "packs",
) -> RunResult:
    started = time.perf_counter()
    stage_seconds: dict[str, float] = {}
    pdf_path = customer_document(pack, customer_id, packs_dir)
    customer = next(c for c in pack.customers if c.id == customer_id)
    customer_dir = out_dir / pack.config.name / customer_id

    with _timed(stage_seconds, "ingest"):
        pages = extract_pages(pdf_path)
        chunks = chunk_pages(pages)

    try:
        with _timed(stage_seconds, "extract"):
            extraction = extract(pages, pack.extraction_schema, provider)
    except ExtractionError as error:
        # Nothing new is trustworthy, so leave this customer's previous outputs alone.
        return RunResult(customer_id, "failed", seconds=_since(started), message=str(error))

    customer_dir.mkdir(parents=True, exist_ok=True)
    outputs = [_write_json(customer_dir / "extraction.json", asdict(extraction))]

    with _timed(stage_seconds, "check"):
        results = quality_results(extraction.fields, pages, pack.checks.rules)
        blocking = summarise(results)["summary"]["blocking"]

    if blocking:
        _remove_stale_render_outputs(customer_dir)
    else:
        with _timed(stage_seconds, "render"):
            values = values_of(extraction.fields)
            scenes = render_scenes(pack.template, values, customer, pack.theme.brand)
            narration = " ".join(scene["narration"] for scene in scenes)
            results.append(check_readability(narration, pack.config.reading_ease_min))
            outputs += write_render_outputs(customer_dir, scenes, pack.config.name, customer_id)

    report = summarise(results)
    outputs.append(_write_json(customer_dir / "quality_report.json", report))
    chunk_records = [{"id": f"chunk-{n}", **asdict(chunk)} for n, chunk in enumerate(chunks, 1)]
    outputs.append(_write_json(customer_dir / "chunks.json", chunk_records))

    manifest = build_manifest(
        pack=pack.config,
        customer_id=customer_id,
        input_path=pdf_path,
        extraction=extraction,
        stage_seconds=stage_seconds,
        check_summary=report["summary"],
        output_paths=outputs,
    )
    write_manifest(customer_dir, manifest)

    summary = report["summary"]
    return RunResult(
        customer_id,
        "blocked" if blocking else "rendered",
        errors=summary["errors"],
        warnings=summary["warnings"],
        seconds=_since(started),
    )


@contextmanager
def _timed(stage_seconds: dict[str, float], stage: str) -> Iterator[None]:
    started = time.perf_counter()
    yield
    stage_seconds[stage] = round(time.perf_counter() - started, 3)


def _since(started: float) -> float:
    return round(time.perf_counter() - started, 1)


def _write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return path


def _remove_stale_render_outputs(customer_dir: Path) -> None:
    """A blocked run must not leave an earlier run's explainer on show."""
    for name in (SCENES_NAME, CAPTIONS_NAME):
        (customer_dir / name).unlink(missing_ok=True)
