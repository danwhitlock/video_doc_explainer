import json
from pathlib import Path

from typer.testing import CliRunner

from pipeline import cli
from pipeline.lineage import file_sha256
from pipeline.packs import load_pack
from pipeline.run import run_customer, run_pack

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKS_DIR = REPO_ROOT / "packs"
ALL_FILES = {
    "extraction.json",
    "quality_report.json",
    "scenes.json",
    "captions.vtt",
    "chunks.json",
    "manifest.json",
}


class FakeProvider:
    """Replies with each customer's ground truth (a test fixture only).

    The customer is recognised by their offer reference in the document text.
    `overrides` change values; `invalid_for` makes one customer's reply invalid.
    """

    name = "fake"
    model = "fake-model-1"

    def __init__(self, overrides: dict | None = None, invalid_for: str | None = None):
        self.overrides = overrides or {}
        self.invalid_for = invalid_for
        truth_dir = PACKS_DIR / "mortgage" / "samples" / "ground_truth"
        self.truth = {path.stem: json.loads(path.read_text()) for path in truth_dir.glob("*.json")}

    def extract(self, text, schema):
        customer_id, values = next(
            (cid, values) for cid, values in self.truth.items() if values["offer_reference"] in text
        )
        if customer_id == self.invalid_for:
            return {"not": "valid"}
        values = values | self.overrides
        return {
            name: {"value": value, "evidence_quote": "quoted text", "page": 1}
            for name, value in values.items()
        }

    def answer(self, question, passages):
        raise NotImplementedError


def mortgage():
    return load_pack("mortgage", packs_dir=PACKS_DIR)


def test_good_customer_writes_every_output_and_manifest_hashes_them(tmp_path):
    result = run_customer(mortgage(), "m-001", FakeProvider(), tmp_path, PACKS_DIR)

    customer_dir = tmp_path / "mortgage" / "m-001"
    assert result.outcome == "rendered"
    assert {path.name for path in customer_dir.iterdir()} == ALL_FILES

    manifest = json.loads((customer_dir / "manifest.json").read_text())
    assert set(manifest["outputs"]) == ALL_FILES - {"manifest.json"}
    for name, digest in manifest["outputs"].items():
        assert file_sha256(customer_dir / name) == digest
    assert set(manifest["stage_seconds"]) == {"ingest", "extract", "check", "render"}


def test_report_includes_readability_and_chunks_have_ids(tmp_path):
    run_customer(mortgage(), "m-001", FakeProvider(), tmp_path, PACKS_DIR)
    customer_dir = tmp_path / "mortgage" / "m-001"

    report = json.loads((customer_dir / "quality_report.json").read_text())
    readability = [r for r in report["results"] if r["rule_id"] == "readability"]
    assert readability[0]["status"] == "pass"

    chunks = json.loads((customer_dir / "chunks.json").read_text())
    assert chunks[0]["id"] == "chunk-1"
    assert {"page", "start", "end", "text"} <= set(chunks[0])


def test_blocking_error_skips_render_and_removes_a_stale_explainer(tmp_path):
    run_customer(mortgage(), "m-001", FakeProvider(), tmp_path, PACKS_DIR)
    customer_dir = tmp_path / "mortgage" / "m-001"
    assert (customer_dir / "scenes.json").exists()  # yesterday's explainer

    implausible_rate = FakeProvider(overrides={"initial_rate_percent": 16})
    result = run_customer(mortgage(), "m-001", implausible_rate, tmp_path, PACKS_DIR)

    assert result.outcome == "blocked"
    assert result.errors >= 1
    assert not (customer_dir / "scenes.json").exists()
    assert not (customer_dir / "captions.vtt").exists()
    manifest = json.loads((customer_dir / "manifest.json").read_text())
    assert manifest["checks"]["blocking"] is True
    assert "scenes.json" not in manifest["outputs"]


def test_failed_extraction_does_not_stop_the_others(tmp_path):
    results = run_pack(mortgage(), FakeProvider(invalid_for="m-002"), tmp_path, packs_dir=PACKS_DIR)

    outcomes = {result.customer_id: result.outcome for result in results}
    assert outcomes == {"m-001": "rendered", "m-002": "failed", "m-003": "rendered"}
    assert not (tmp_path / "mortgage" / "m-002").exists()  # nothing untrustworthy written
    failed = next(result for result in results if result.outcome == "failed")
    assert "still invalid" in failed.message


def run_cli(monkeypatch, tmp_path, provider, *args):
    monkeypatch.chdir(REPO_ROOT)  # packs/ is found relative to the repo root
    monkeypatch.setattr(cli, "get_provider", lambda: provider)
    return CliRunner().invoke(
        cli.app, ["run", "--pack", "mortgage", *args, "--out-dir", str(tmp_path)]
    )


def test_cli_all_runs_every_customer_and_exits_0(monkeypatch, tmp_path):
    result = run_cli(monkeypatch, tmp_path, FakeProvider(), "--all")

    assert result.exit_code == 0, result.output
    for customer_id in ("m-001", "m-002", "m-003"):
        assert f"{customer_id}    rendered" in result.output


def test_cli_exits_1_when_any_customer_is_blocked_or_failed(monkeypatch, tmp_path):
    result = run_cli(monkeypatch, tmp_path, FakeProvider(invalid_for="m-002"), "--all")

    assert result.exit_code == 1
    assert "m-002    failed" in result.output


def test_cli_rejects_unknown_customer(monkeypatch, tmp_path):
    result = run_cli(monkeypatch, tmp_path, FakeProvider(), "--customer", "m-999")

    assert result.exit_code == 2
    assert "'m-999' is not in mortgage" in result.output
