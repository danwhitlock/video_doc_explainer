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
