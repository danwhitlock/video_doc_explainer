import json
from pathlib import Path

from typer.testing import CliRunner

from pipeline import cli

REPO_ROOT = Path(__file__).resolve().parents[2]


class FakeProvider:
    """Returns a valid mortgage reply built from ground truth (as a test fixture only)."""

    name = "fake"
    model = "fake-model-1"

    def extract(self, text, schema):
        truth_path = REPO_ROOT / "packs/mortgage/samples/ground_truth/m-001.json"
        truth = json.loads(truth_path.read_text())
        return {
            name: {"value": value, "evidence_quote": "quoted text", "page": 1}
            for name, value in truth.items()
        }

    def answer(self, question, passages):
        raise NotImplementedError


def test_extract_command_prints_fields_and_writes_json(monkeypatch, tmp_path):
    monkeypatch.chdir(REPO_ROOT)  # the pack is found relative to the repo root
    monkeypatch.setattr(cli, "get_provider", lambda: FakeProvider())

    result = CliRunner().invoke(
        cli.app,
        ["extract", "--pack", "mortgage", "--customer", "m-001", "--out-dir", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert "loan_amount" in result.output
    assert "fake/fake-model-1 · 1 attempt(s)" in result.output

    saved = json.loads((tmp_path / "mortgage" / "m-001" / "extraction.json").read_text())
    assert saved["model"] == "fake-model-1"
    assert saved["fields"]["loan_amount"]["value"] == 256500


def test_extract_command_rejects_unknown_customer(monkeypatch, tmp_path):
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setattr(cli, "get_provider", lambda: FakeProvider())

    result = CliRunner().invoke(
        cli.app,
        ["extract", "--pack", "mortgage", "--customer", "m-999", "--out-dir", str(tmp_path)],
    )

    assert result.exit_code != 0
    assert "No customer 'm-999'" in str(result.exception)


def write_extraction(out_dir: Path, overrides: dict | None = None) -> None:
    fields = FakeProvider().extract("", {})
    for name, value in (overrides or {}).items():
        fields[name]["value"] = value
    customer_dir = out_dir / "mortgage" / "m-001"
    customer_dir.mkdir(parents=True)
    (customer_dir / "extraction.json").write_text(json.dumps({"fields": fields}))


def run_check(out_dir: Path):
    return CliRunner().invoke(
        cli.app, ["check", "--pack", "mortgage", "--customer", "m-001", "--out-dir", str(out_dir)]
    )


def test_check_command_writes_report_and_exits_0_without_errors(monkeypatch, tmp_path):
    monkeypatch.chdir(REPO_ROOT)
    write_extraction(tmp_path)

    result = run_check(tmp_path)

    # The fake's "quoted text" isn't in the PDF, so grounding warns - but warnings don't block.
    assert result.exit_code == 0, result.output
    assert "WARN  grounding [loan_amount]" in result.output
    assert "blocking: false" in result.output
    report = json.loads((tmp_path / "mortgage" / "m-001" / "quality_report.json").read_text())
    assert report["summary"]["blocking"] is False


def test_check_command_exits_1_when_blocking(monkeypatch, tmp_path):
    monkeypatch.chdir(REPO_ROOT)
    write_extraction(tmp_path, {"initial_rate_percent": 16})

    result = run_check(tmp_path)

    assert result.exit_code == 1
    assert "ERROR rate-plausible [initial_rate_percent]" in result.output
