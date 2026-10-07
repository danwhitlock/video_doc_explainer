from pathlib import Path

import pytest

from pipeline.packs import load_pack

PACKS_DIR = Path(__file__).resolve().parents[2] / "packs"


@pytest.mark.parametrize("pack_name", ["mortgage", "healthcare"])
def test_load_pack_reads_all_six_files(pack_name: str):
    pack = load_pack(pack_name, packs_dir=PACKS_DIR)

    assert pack.config.name == pack_name
    assert len(pack.customers) == 3
    assert len(pack.checks.rules) > 0
    assert len(pack.template.scenes) > 0
    assert pack.theme.color["primary"].startswith("#")
    assert "properties" in pack.extraction_schema


def test_load_pack_keeps_extra_rule_fields():
    pack = load_pack("mortgage", packs_dir=PACKS_DIR)

    rate_rule = next(rule for rule in pack.checks.rules if rule.id == "rate-plausible")
    assert rate_rule.type == "range"
    assert rate_rule.severity == "error"
    assert rate_rule.model_extra["field"] == "initial_rate_percent"
    assert rate_rule.model_extra["min"] == 0.5


def test_load_pack_keeps_pack_specific_template_extras():
    # healthcare's template.yaml has a top-level `anaesthetic_explained` lookup
    # that mortgage's doesn't - the loader must not hardcode either pack's keys
    pack = load_pack("healthcare", packs_dir=PACKS_DIR)

    assert "anaesthetic_explained" in pack.template.model_extra
    assert "local" in pack.template.model_extra["anaesthetic_explained"]


def test_load_pack_parses_customer_prefs():
    pack = load_pack("mortgage", packs_dir=PACKS_DIR)

    priya = next(c for c in pack.customers if c.id == "m-001")
    assert priya.preferred_name == "Priya"
    assert priya.prefs["captions"] is True


def test_load_pack_parses_scene_conditions():
    pack = load_pack("mortgage", packs_dir=PACKS_DIR)

    high_ltv = next(s for s in pack.template.scenes if s.id == "high-ltv")
    assert high_ltv.when == "d.ltv_percent > 85"
    welcome = next(s for s in pack.template.scenes if s.id == "welcome")
    assert welcome.when is None
