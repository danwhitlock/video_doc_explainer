import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pipeline import cli
from pipeline.lineage import file_sha256
from pipeline.purge import find_customer_dir, purge_customer, purge_expired

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKS_DIR = REPO_ROOT / "packs"
NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def make_outputs(out_dir: Path, pack: str = "mortgage", customer: str = "m-001", run_at=None):
    """Fake derived files for one customer, including a nested audio folder."""
    customer_dir = out_dir / pack / customer
    (customer_dir / "audio").mkdir(parents=True)
    (customer_dir / "extraction.json").write_text('{"fields": {}}')
    (customer_dir / "audio" / "scene-1.mp3").write_bytes(b"fake audio")
    if run_at is not None:
        manifest = {"timestamp": run_at.isoformat()}
        (customer_dir / "manifest.json").write_text(json.dumps(manifest))
    return customer_dir


def test_purge_deletes_files_and_receipt_lists_their_hashes(tmp_path):
    customer_dir = make_outputs(tmp_path)
    expected_hash = file_sha256(customer_dir / "extraction.json")

    receipt = purge_customer(customer_dir, reason="requested", now=NOW)

    assert [path.name for path in customer_dir.iterdir()] == ["deletion_receipt.json"]
    assert receipt["file_count"] == 2
    assert receipt["reason"] == "requested"
    assert receipt["deleted_at"] == "2026-10-08T12:00:00+00:00"
    assert {"file": "extraction.json", "sha256": expected_hash, "bytes": 14} in receipt["files"]
    saved = json.loads((customer_dir / "deletion_receipt.json").read_text())
    assert saved == receipt


def test_source_pdf_is_never_touched(tmp_path):
    pdf = PACKS_DIR / "mortgage" / "samples" / "m-001.pdf"
    before = file_sha256(pdf)

    purge_customer(make_outputs(tmp_path), reason="requested")

    assert file_sha256(pdf) == before


@pytest.mark.parametrize("customer_id", ["m-999", "../..", "mortgage"])
def test_unknown_or_path_like_customer_is_refused(tmp_path, customer_id):
    make_outputs(tmp_path)

    with pytest.raises(ValueError, match="Unknown customer"):
        find_customer_dir(customer_id, tmp_path, packs_dir=PACKS_DIR)

    assert (tmp_path / "mortgage" / "m-001" / "extraction.json").exists()


def test_find_customer_dir_searches_every_pack(tmp_path):
    found = find_customer_dir("h-002", tmp_path, packs_dir=PACKS_DIR)

    assert found == tmp_path / "healthcare" / "h-002"


def test_expired_purges_old_runs_and_keeps_recent_ones(tmp_path):
    # Mortgage retention is 30 days.
    old = make_outputs(tmp_path, customer="m-001", run_at=NOW - timedelta(days=31))
    recent = make_outputs(tmp_path, customer="m-002", run_at=NOW - timedelta(days=29))

    receipts = purge_expired(tmp_path, packs_dir=PACKS_DIR, now=NOW)

    assert [receipt["customer_id"] for receipt in receipts] == ["m-001"]
    assert receipts[0]["reason"] == "expired (retention 30 days)"
    assert not (old / "extraction.json").exists()
    assert (recent / "extraction.json").exists()


def test_repurge_keeps_the_original_receipt(tmp_path):
    customer_dir = make_outputs(tmp_path)
    first = purge_customer(customer_dir, reason="requested", now=NOW)

    assert purge_customer(customer_dir, reason="requested") is None
    assert json.loads((customer_dir / "deletion_receipt.json").read_text()) == first


@pytest.mark.parametrize("args", [[], ["--customer", "m-001", "--expired"]])
def test_cli_needs_exactly_one_of_customer_or_expired(tmp_path, args):
    result = CliRunner().invoke(cli.app, ["purge", "--out-dir", str(tmp_path), *args])

    assert result.exit_code != 0
    assert "exactly one of --customer" in result.output


def test_cli_purges_a_customer(monkeypatch, tmp_path):
    monkeypatch.chdir(REPO_ROOT)  # packs/ is found relative to the repo root
    make_outputs(tmp_path)

    result = CliRunner().invoke(
        cli.app, ["purge", "--customer", "m-001", "--out-dir", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    assert "Purged mortgage/m-001: 2 file(s) deleted" in result.output
    assert (tmp_path / "mortgage" / "m-001" / "deletion_receipt.json").exists()


def test_cli_refuses_unknown_customer_cleanly(monkeypatch, tmp_path):
    monkeypatch.chdir(REPO_ROOT)

    result = CliRunner().invoke(
        cli.app, ["purge", "--customer", "../..", "--out-dir", str(tmp_path)]
    )

    assert result.exit_code == 2  # usage error, not a crash
    assert "Unknown customer '../..'" in result.output
