import hashlib
import json
from pathlib import Path

from pipeline.extract import Extraction
from pipeline.lineage import build_manifest, file_sha256, write_manifest
from pipeline.packs import load_pack

PACKS_DIR = Path(__file__).resolve().parents[2] / "packs"

EXTRACTION = Extraction(
    fields={"customer_name": {"value": "Ms Priya Raman", "evidence_quote": "Dear", "page": 1}},
    provider="ollama",
    model="qwen2.5:7b",
    prompt_sha256="ab" * 32,
    duration_seconds=176.3,
    attempts=1,
)
SUMMARY = {"pass": 35, "fail": 1, "skip": 0, "errors": 0, "warnings": 1, "blocking": False}


def make_manifest(tmp_path: Path, **overrides) -> dict:
    pdf = tmp_path / "m-001.pdf"
    pdf.write_bytes(b"%PDF fake document")
    output = tmp_path / "extraction.json"
    output.write_text(json.dumps({"fields": EXTRACTION.fields}))
    arguments = {
        "pack": load_pack("mortgage", packs_dir=PACKS_DIR).config,
        "customer_id": "m-001",
        "input_path": pdf,
        "extraction": EXTRACTION,
        "stage_seconds": {"ingest": 0.4, "extract": 176.3, "check": 0.1},
        "check_summary": SUMMARY,
        "output_paths": [output],
    }
    return build_manifest(**(arguments | overrides))


def test_file_sha256_matches_hashlib_and_changes_with_one_byte(tmp_path):
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"hello")
    assert file_sha256(path) == hashlib.sha256(b"hello").hexdigest()

    path.write_bytes(b"hellO")
    assert file_sha256(path) != hashlib.sha256(b"hello").hexdigest()


def test_manifest_has_every_field_the_brief_lists(tmp_path):
    manifest = make_manifest(tmp_path)

    assert set(manifest) == {
        "run_id",
        "timestamp",
        "pack",
        "customer_id",
        "input",
        "extraction",
        "stage_seconds",
        "checks",
        "outputs",
    }
    assert manifest["pack"] == {"name": "mortgage", "schema_version": "1.0.0"}
    assert manifest["input"] == {
        "file": "m-001.pdf",
        "sha256": hashlib.sha256(b"%PDF fake document").hexdigest(),
    }
    assert manifest["extraction"] == {
        "provider": "ollama",
        "model": "qwen2.5:7b",
        "prompt_sha256": "ab" * 32,
        "attempts": 1,
    }
    assert manifest["checks"]["blocking"] is False
    assert len(manifest["run_id"]) == 32


def test_outputs_are_hashed_by_name(tmp_path):
    manifest = make_manifest(tmp_path)

    expected = file_sha256(tmp_path / "extraction.json")
    assert manifest["outputs"] == {"extraction.json": expected}


def test_manifest_never_contains_the_customer_name(tmp_path):
    # The extraction and the output file both contain the name; the manifest must not.
    manifest = make_manifest(tmp_path)

    assert "Priya" not in json.dumps(manifest)


def test_run_id_and_timestamp_can_be_fixed(tmp_path):
    manifest = make_manifest(tmp_path, run_id="run-1", timestamp="2026-10-08T12:00:00+00:00")

    assert manifest["run_id"] == "run-1"
    assert manifest["timestamp"] == "2026-10-08T12:00:00+00:00"


def test_write_manifest_saves_json(tmp_path):
    manifest = make_manifest(tmp_path)

    path = write_manifest(tmp_path, manifest)

    assert path.name == "manifest.json"
    assert json.loads(path.read_text()) == manifest
