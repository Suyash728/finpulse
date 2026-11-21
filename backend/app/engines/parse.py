"""Statement parsers -> standardized transaction rows."""

from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

from app.parsers.csv_parser import parse_csv as _parse_csv
from app.parsers.pdf_parser import parse_pdf as _parse_pdf
from app.parsers.sms_parser import parse_sms as _parse_sms


def _standardize(rows: list[dict]) -> list[dict]:
    """Convert parser-specific rows to the common backend contract."""
    result = []

    for row in rows:
        amount = float(row.get("amount") or 0)
        txn_type = str(row.get("type") or "").lower()

        if amount <= 0 or txn_type not in ("debit", "credit"):
            continue

        raw_date = str(row.get("date") or "").strip()
        try:
            parsed_date = date.fromisoformat(raw_date).isoformat()
        except ValueError:
            continue

        description = (
            row.get("raw_text")
            or row.get("merchant")
            or ""
        ).strip()

        if not description:
            continue

        result.append({
            "date": parsed_date,
            "amount": round(amount, 2),
            "direction": "dr" if txn_type == "debit" else "cr",
            "raw_desc": description,
        })

    return result


def parse_sms(text: str) -> list[dict]:
    """Parse SMS alerts and return standardized transaction rows."""
    return _standardize(_parse_sms(text))


def parse_csv(data: bytes) -> list[dict]:
    """Parse a bank CSV and return standardized transaction rows."""
    return _standardize(_parse_csv(data))


def parse_pdf(data: bytes) -> tuple[list[dict], dict]:
    """Parse a PDF statement and calculate its balance reconciliation."""
    parsed = _parse_pdf(BytesIO(data))
    rows = _standardize(parsed.get("transactions", []))

    opening = parsed.get("opening_balance")
    closing = parsed.get("closing_balance")

    computed = None
    if opening is not None:
        credits = sum(r["amount"] for r in rows if r["direction"] == "cr")
        debits = sum(r["amount"] for r in rows if r["direction"] == "dr")
        computed = round(float(opening) + credits - debits, 2)

    ok = (
        computed is not None
        and closing is not None
        and abs(computed - float(closing)) < 0.01
    )

    reconciled = {
        "ok": ok,
        "opening": opening,
        "closing": closing,
        "computed_closing": computed,
    }

    return rows, reconciled


def detect_kind(filename: str, data: bytes) -> str:
    """Identify PDF, CSV or SMS input."""
    suffix = Path(filename or "").suffix.lower()

    if suffix == ".pdf" or data.startswith(b"%PDF"):
        return "pdf"

    if suffix == ".csv":
        return "csv"

    if suffix in (".txt", ".sms"):
        return "sms"

    sample = data[:4096].decode("utf-8-sig", errors="replace").lower()

    if (
        "narration" in sample
        or "particulars" in sample
        or "withdrawal amt" in sample
    ) and ("," in sample or "\t" in sample):
        return "csv"

    return "sms"
