"""Parse HDFC- and Kotak-style Indian bank CSV statements."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation


def _clean_amount(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    try:
        return Decimal(raw.strip().replace(",", "").replace("₹", ""))
    except (InvalidOperation, AttributeError):
        return None


def _parse_date(raw: str) -> str:
    raw = raw.strip()
    formats = (
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
        "%d-%b-%y", "%d-%b-%Y",
        "%d %b %Y", "%d %B %Y",
        "%d/%m/%y", "%d-%m-%y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _find_header(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        lowered = line.lower()
        has_date = "date" in lowered
        has_description = any(x in lowered for x in ("narration", "particulars"))
        has_amount = any(x in lowered for x in ("withdrawal", "amount (inr)", "deposit"))
        if has_date and has_description and has_amount:
            return index
    return None


def parse_csv(content: str | bytes) -> list[dict]:
    """Return rows with date, raw_text, merchant, amount, type, ref_no and closing_balance."""
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig", errors="replace")

    lines = content.splitlines()
    header_index = _find_header(lines)
    if header_index is None:
        return []

    reader = csv.DictReader(io.StringIO("\n".join(lines[header_index:])))
    transactions = []

    for row in reader:
        row = {
            (key or "").strip().lower(): (value or "").strip()
            for key, value in row.items()
        }

        narration = row.get("narration") or row.get("particulars") or ""
        if not narration:
            continue

        raw_date = row.get("date") or row.get("tran date") or row.get("value date") or ""
        iso_date = _parse_date(raw_date)
        if not iso_date:
            continue

        withdrawal = _clean_amount(row.get("withdrawal amt.") or row.get("withdrawal amount"))
        deposit = _clean_amount(row.get("deposit amt.") or row.get("deposit amount"))
        balance = _clean_amount(row.get("closing balance") or row.get("balance (inr)"))

        if withdrawal is not None and withdrawal > 0:
            amount, txn_type = withdrawal, "debit"
        elif deposit is not None and deposit > 0:
            amount, txn_type = deposit, "credit"
        else:
            combined = _clean_amount(row.get("amount (inr)") or row.get("amount"))
            direction = (row.get("dr / cr") or row.get("dr/cr") or row.get("type") or "").lower()

            if combined is None or combined <= 0:
                continue
            if direction in ("dr", "debit", "withdrawal"):
                amount, txn_type = combined, "debit"
            elif direction in ("cr", "credit", "deposit"):
                amount, txn_type = combined, "credit"
            else:
                continue

        transactions.append({
            "date": iso_date,
            "raw_text": narration,
            "merchant": narration,
            "amount": float(amount),
            "type": txn_type,
            "ref_no": row.get("chq./ref.no.") or row.get("ref no") or "",
            "closing_balance": float(balance) if balance is not None else None,
        })

    return transactions
