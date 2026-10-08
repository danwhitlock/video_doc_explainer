import json
from pathlib import Path

import pytest
from jinja2.exceptions import SecurityError, UndefinedError

from pipeline.packs import Scene, load_pack
from pipeline.render import render_scenes

PACKS_DIR = Path(__file__).resolve().parents[2] / "packs"
ALL_CUSTOMERS = [
    (pack, f"{pack[0]}-00{n}") for pack in ("mortgage", "healthcare") for n in (1, 2, 3)
]


def render(pack_name: str, customer_id: str, **value_overrides) -> dict[str, dict]:
    """Render one ground-truth customer (a test fixture only); scenes keyed by id."""
    pack = load_pack(pack_name, packs_dir=PACKS_DIR)
    customer = next(c for c in pack.customers if c.id == customer_id)
    truth_path = PACKS_DIR / pack_name / "samples" / "ground_truth" / f"{customer_id}.json"
    values = json.loads(truth_path.read_text()) | value_overrides
    scenes = render_scenes(pack.template, values, customer, pack.theme.brand)
    return {scene["id"]: scene for scene in scenes}


@pytest.mark.parametrize(("pack_name", "customer_id"), ALL_CUSTOMERS)
def test_every_ground_truth_customer_renders(pack_name, customer_id):
    scenes = render(pack_name, customer_id)

    assert "welcome" in scenes
    assert "contact" in scenes
    for scene in scenes.values():
        assert scene["narration"]
        assert "{{" not in scene["narration"]


def test_when_conditions_pick_scenes_per_customer():
    m001 = render("mortgage", "m-001")  # 90% LTV, no product fee
    assert "high-ltv" in m001
    assert "fees" not in m001

    h001 = render("healthcare", "h-001")  # local anaesthetic, no fasting
    assert "eating-normally" in h001
    assert "eating-drinking" not in h001


def test_whole_expression_visual_fields_pass_real_values():
    overpayments = render("mortgage", "m-001")["overpayments"]["visual"]
    assert overpayments["rows"] == [["Year 1", "2%"], ["Year 2", "1%"]]

    meter = render("mortgage", "m-001")["your-loan"]["visual"]["meter"]
    assert meter["value"] == 90
    assert meter["max"] == 100  # non-string values pass straight through

    items = render("healthcare", "h-003")["what-to-bring"]["visual"]["items"]
    assert isinstance(items, list)


def test_whole_floats_read_as_integers():
    # Pydantic stores numbers as floats: 10 arrives as 10.0.
    footnote = render("mortgage", "m-001", overpayment_allowance_percent=10.0)["overpayments"]
    assert footnote["visual"]["footnote"] == "Overpay up to 10% a year with no charge."

    rate = render("mortgage", "m-001", initial_rate_percent=4.89)["your-rate"]
    assert "4.89 percent" in rate["narration"]


def test_narration_whitespace_and_punctuation_are_tidy():
    for pack_name, customer_id in ALL_CUSTOMERS:
        for scene in render(pack_name, customer_id).values():
            narration = scene["narration"]
            assert "  " not in narration
            assert " ." not in narration
            assert narration == narration.strip()


def test_pack_lookup_tables_are_available():
    what_happens = render("healthcare", "h-001")["what-happens"]["narration"]

    assert "You'll be awake." in what_happens  # from anaesthetic_explained.local


def test_misspelt_field_is_an_error_not_a_gap():
    pack = load_pack("mortgage", packs_dir=PACKS_DIR)
    template = pack.template.model_copy(
        update={"scenes": [Scene(id="x", title="x", visual={}, narration="{{ d.loan_ammount }}")]}
    )

    with pytest.raises(UndefinedError, match="loan_ammount"):
        render_scenes(template, {"loan_amount": 1}, pack.customers[0], pack.theme.brand)


def test_sandbox_blocks_python_internals():
    pack = load_pack("mortgage", packs_dir=PACKS_DIR)
    narration = "{{ d.__class__.__mro__ }}"
    template = pack.template.model_copy(
        update={"scenes": [Scene(id="x", title="x", visual={}, narration=narration)]}
    )

    with pytest.raises(SecurityError):
        render_scenes(template, {}, pack.customers[0], pack.theme.brand)
