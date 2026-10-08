import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from pipeline.checks import build_quality_report
from pipeline.extract import Extraction, extract_customer
from pipeline.ingest import extract_pages
from pipeline.packs import customer_document, load_pack
from pipeline.providers import get_provider
from pipeline.purge import (
    RECEIPT_NAME,
    describe_receipt,
    find_customer_dir,
    purge_customer,
    purge_expired,
)

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


@app.command("check")
def check_command(
    pack: Annotated[str, typer.Option(help="Industry pack, e.g. mortgage")],
    customer: Annotated[str, typer.Option(help="Customer id, e.g. m-001")],
    out_dir: Annotated[Path, typer.Option(help="Where outputs are read and written")] = Path(
        "web/public/data"
    ),
) -> None:
    """Run quality checks on a saved extraction. Exits 1 if any error-severity check fails."""
    customer_dir = out_dir / pack / customer
    extraction = json.loads((customer_dir / "extraction.json").read_text())
    loaded = load_pack(pack)
    # Grounding needs the page text, which deliberately isn't stored in extraction.json.
    pages = extract_pages(customer_document(loaded, customer))

    report = build_quality_report(extraction["fields"], pages, loaded.checks.rules)
    (customer_dir / "quality_report.json").write_text(json.dumps(report, indent=2) + "\n")

    for severity in ("error", "warn"):
        for result in report["results"]:
            if result["status"] == "fail" and result["severity"] == severity:
                fields = ", ".join(result["fields"])
                typer.echo(
                    f"{severity.upper():<5} {result['rule_id']} [{fields}]: {result['message']}"
                )
    summary = report["summary"]
    typer.echo(
        f"\n{summary['pass']} passed · {summary['skip']} skipped · "
        f"{summary['errors']} error(s) · {summary['warnings']} warning(s) · "
        f"blocking: {str(summary['blocking']).lower()}"
    )
    typer.echo(f"Saved to {customer_dir / 'quality_report.json'}")
    if summary["blocking"]:
        raise typer.Exit(code=1)


@app.command("purge")
def purge_command(
    customer: Annotated[str | None, typer.Option(help="Purge this customer's outputs")] = None,
    expired: Annotated[
        bool, typer.Option("--expired", help="Purge every run older than its pack's retention")
    ] = False,
    out_dir: Annotated[Path, typer.Option(help="Where outputs live")] = Path("web/public/data"),
) -> None:
    """Delete derived files and write a deletion receipt. Source documents are never touched."""
    if (customer is None) == (not expired):
        raise typer.BadParameter("Use exactly one of --customer <id> or --expired")

    if expired:
        receipts = purge_expired(out_dir)
        for receipt in receipts:
            typer.echo(f"Purged {describe_receipt(receipt)}")
        typer.echo(f"{len(receipts)} customer(s) past retention purged")
        return

    try:
        customer_dir = find_customer_dir(customer, out_dir)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--customer") from error
    receipt = purge_customer(customer_dir, reason="requested")
    if receipt is None:
        typer.echo(f"Nothing to purge for {customer}")
        return
    typer.echo(f"Purged {describe_receipt(receipt)}")
    typer.echo(f"Receipt: {customer_dir / RECEIPT_NAME}")


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
