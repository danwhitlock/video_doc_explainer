"""Run manifest: what produced a customer's outputs, and proof they haven't changed.

The manifest identifies the input by hash and customer id only - never the
customer's name or any document text - so it can be shared for audit without
revealing what the document says.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pipeline.extract import Extraction
from pipeline.packs import PackConfig

MANIFEST_NAME = "manifest.json"
_READ_SIZE = 64 * 1024


def file_sha256(path: Path) -> str:
    """SHA-256 of a file's bytes, read in chunks so large PDFs don't fill memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_READ_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    *,
    pack: PackConfig,
    customer_id: str,
    input_path: Path,
    extraction: Extraction,
    stage_seconds: dict[str, float],
    check_summary: dict[str, Any],
    output_paths: list[Path],
    run_id: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Assemble the manifest. Only metadata is taken from `extraction`, never its fields."""
    return {
        "run_id": run_id or uuid.uuid4().hex,
        "timestamp": timestamp or datetime.now(UTC).isoformat(timespec="seconds"),
        "pack": {"name": pack.name, "schema_version": pack.schema_version},
        "customer_id": customer_id,
        "input": {"file": input_path.name, "sha256": file_sha256(input_path)},
        "extraction": {
            "provider": extraction.provider,
            "model": extraction.model,
            "prompt_sha256": extraction.prompt_sha256,
            "attempts": extraction.attempts,
        },
        "stage_seconds": stage_seconds,
        "checks": check_summary,
        "outputs": {path.name: file_sha256(path) for path in output_paths},
    }


def write_manifest(customer_dir: Path, manifest: dict[str, Any]) -> Path:
    path = customer_dir / MANIFEST_NAME
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path
