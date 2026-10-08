import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from pipeline.extract import Extraction, extract_customer
from pipeline.providers import get_provider

app = typer.Typer()


@app.callback()
def main() -> None:
    """Explainer Engine: document -> narrated explainer pipeline."""


@app.command("extract")
def extract_command(
    pack: Annotated[str, typer.Option(help="Industry pack, e.g. mortgage")],
    customer: Annotated[str, typer.Option(help="Customer id, e.g. m-001")],
    out_dir: Annotated[Path, typer.Option(help="Where outputs are written")] = Path(
        "web/public/data"
    ),
) -> None:
    """Run extraction alone for one customer and print the fields."""
    extraction = extract_customer(pack, customer, get_provider())

    out_path = out_dir / pack / customer / "extraction.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(asdict(extraction), indent=2, ensure_ascii=False) + "\n")

    typer.echo(format_table(extraction))
    typer.echo(
        f"\n{extraction.provider}/{extraction.model} · {extraction.attempts} attempt(s) · "
        f"{extraction.duration_seconds}s · prompt {extraction.prompt_sha256[:12]}"
    )
    typer.echo(f"Saved to {out_path}")


def format_table(extraction: Extraction, width: int = 40) -> str:
    """One line per field: name, value, page, start of the evidence quote."""
    lines = [f"{'FIELD':<30} {'VALUE':<{width}} {'PG':>3}  EVIDENCE"]
    for name, field in extraction.fields.items():
        value = json.dumps(field["value"], ensure_ascii=False)
        quote = field["evidence_quote"] or "-"
        page = field["page"] if field["page"] is not None else "-"
        lines.append(f"{name:<30} {_clip(value, width):<{width}} {page:>3}  {_clip(quote, width)}")
    return "\n".join(lines)


def _clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


if __name__ == "__main__":
    app()
