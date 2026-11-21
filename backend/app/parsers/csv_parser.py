"""Parse HDFC-format CSV bank statements.

Columns: Date, Narration, Chq./Ref.No., Value Dt, Withdrawal Amt., Deposit Amt., Closing Balance

Returns a list of transaction dicts ready for the categoriser.
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation


def _clean_amount(raw: str) -> Decimal | None:
    """Parse Indian-format amount string like '22,000.00' → Decimal."""
    if not raw or not raw.strip():
        return None
    try:
        return Decimal(raw.strip().replace(",", ""))
    except InvalidOperation:
        return None


def parse_csv(content: str | bytes) -> list[dict]:
    """Parse an HDFC CSV statement → list of transaction dicts.

    Each dict: {date, raw_text, merchant, amount, type, ref_no, closing_balance}
    """
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")  # handle BOM

    rows = []
    reader = csv.DictReader(io.StringIO(content))

    for row in reader:
        narration = (row.get("Narration") or "").strip()
        if not narration:
            continue

        withdrawal = _clean_amount(row.get("Withdrawal Amt.", ""))
        deposit = _clean_amount(row.get("Deposit Amt.", ""))
        closing = _clean_amount(row.get("Closing Balance", ""))

        if withdrawal and withdrawal > 0:
            amount = float(withdrawal)
            txn_type = "debit"
        elif deposit and deposit > 0:
            amount = float(deposit)
            txn_type = "credit"
        else:
            continue

        # Parse date dd/mm/yyyy → yyyy-mm-dd
        raw_date = (row.get("Date") or "").strip()
        try:
            parts = raw_date.split("/")
            iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
        except (IndexError, ValueError):
            iso_date = raw_date

        rows.append({
            "date": iso_date,
            "raw_text": narration,
            "merchant": narration,
            "amount": amount,
            "type": txn_type,
            "ref_no": (row.get("Chq./Ref.No.") or "").strip(),
            "closing_balance": float(closing) if closing else None,
        })

    return rows
