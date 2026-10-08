"""Retention and deletion: remove a customer's derived files, leaving a receipt.

Only pipeline outputs are deleted - source documents in packs/ are inputs and
are never touched. Each file is hashed before deletion so the receipt can be
matched against the run manifest, without keeping any of the content.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pipeline.lineage import MANIFEST_NAME, file_sha256
from pipeline.packs import Pack, load_pack

RECEIPT_NAME = "deletion_receipt.json"


def find_customer_dir(customer_id: str, out_dir: Path, packs_dir: Path | str = "packs") -> Path:
    """Locate a customer's output folder by looking the id up in every pack.

    Only ids listed in a customers.json are accepted, so a typo or a path
    like "../.." is refused before anything is deleted.
    """
    for pack in _all_packs(packs_dir):
        if any(customer.id == customer_id for customer in pack.customers):
            return Path(out_dir) / pack.config.name / customer_id
    raise ValueError(f"Unknown customer {customer_id!r}: not in any pack's customers.json")


def purge_customer(customer_dir: Path, reason: str, now: datetime | None = None) -> dict | None:
    """Delete every derived file in `customer_dir` and write a deletion receipt.

    Returns the receipt, or None if there was nothing to delete (an existing
    receipt is kept rather than overwritten with an empty one).
    """
    files = _derived_files(customer_dir)
    if not files:
        return None

    deleted = [
        {
            "file": str(path.relative_to(customer_dir)),
            "sha256": file_sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in files
    ]
    for path in files:
        path.unlink()
    _remove_empty_subfolders(customer_dir)

    receipt = {
        "pack": customer_dir.parent.name,
        "customer_id": customer_dir.name,
        "reason": reason,
        "deleted_at": (now or datetime.now(UTC)).isoformat(timespec="seconds"),
        "file_count": len(deleted),
        "files": deleted,
    }
    (customer_dir / RECEIPT_NAME).write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def describe_receipt(receipt: dict[str, Any]) -> str:
    """One line for the terminal - ids and counts only, never content."""
    return f"{receipt['pack']}/{receipt['customer_id']}: {receipt['file_count']} file(s) deleted"


def purge_expired(
    out_dir: Path, packs_dir: Path | str = "packs", now: datetime | None = None
) -> list[dict]:
    """Purge every customer whose last run is older than their pack's retention_days."""
    now = now or datetime.now(UTC)
    receipts = []
    for pack in _all_packs(packs_dir):
        retention = timedelta(days=pack.config.retention_days)
        for customer in pack.customers:
            customer_dir = Path(out_dir) / pack.config.name / customer.id
            last_run = last_run_time(customer_dir)
            if last_run is not None and now - last_run > retention:
                reason = f"expired (retention {pack.config.retention_days} days)"
                receipt = purge_customer(customer_dir, reason, now)
                if receipt:
                    receipts.append(receipt)
    return receipts


def last_run_time(customer_dir: Path) -> datetime | None:
    """When outputs were last produced: the manifest's timestamp, else the newest file."""
    manifest = customer_dir / MANIFEST_NAME
    if manifest.exists():
        return datetime.fromisoformat(json.loads(manifest.read_text())["timestamp"])
    files = _derived_files(customer_dir)
    if not files:
        return None
    newest = max(path.stat().st_mtime for path in files)
    return datetime.fromtimestamp(newest, UTC)


def _derived_files(customer_dir: Path) -> list[Path]:
    if not customer_dir.is_dir():
        return []
    return sorted(
        path for path in customer_dir.rglob("*") if path.is_file() and path.name != RECEIPT_NAME
    )


def _remove_empty_subfolders(customer_dir: Path) -> None:
    # Deepest first, so a nested empty folder is removed before its parent.
    for folder in sorted(customer_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()


def _all_packs(packs_dir: Path | str) -> Iterator[Pack]:
    for pack_dir in sorted(Path(packs_dir).iterdir()):
        if (pack_dir / "pack.yaml").exists():
            yield load_pack(pack_dir.name, packs_dir=packs_dir)
