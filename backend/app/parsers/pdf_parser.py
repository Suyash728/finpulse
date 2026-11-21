"""Parse HDFC- and Kotak-style Indian bank statement PDFs."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from io import BytesIO

import pdfplumber


def _clean_amount(raw: str | None) -> float | None:
    if not raw or not str(raw).strip():
        return None
    try:
        return float(Decimal(str(raw).strip().replace(",", "").replace("₹", "")))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(raw: str) -> str:
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        from datetime import datetime
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _extract_header_balances(text: str) -> dict:
    result = {}
    for key, label in (("opening_balance", "Opening"), ("closing_balance", "Closing")):
        match = re.search(
            rf"{label}\s+Balance\s*:\s*(?:Rs\.?\s*)?[₹]?\s*([\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )
        if match:
            result[key] = _clean_amount(match.group(1))
    return result


def parse_pdf(file_bytes) -> dict:
    """Return transactions, opening/closing balances and reconciliation details."""
    all_rows = []
    header_text = ""

    with pdfplumber.open(file_bytes) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if not header_text:
                header_text = text

            for table in page.extract_tables() or []:
                if not table:
                    continue
                for row in table:
                    if row:
                        all_rows.append(row)

    balances = _extract_header_balances(header_text)
    transactions = []

    for row in all_rows:
        cells = [str(cell or "").strip() for cell in row]

        if cells[0].lower() == "date":
            continue

        # HDFC: Date, Narration, Ref, Value Date, Withdrawal, Deposit, Balance
        if len(cells) >= 7 and _parse_date(cells[0]):
            txn_date = _parse_date(cells[0])
            narration = cells[1]
            debit = _clean_amount(cells[4])
            credit = _clean_amount(cells[5])
            closing = _clean_amount(cells[6])

        # Kotak: Date, Description, Debit, Credit, Balance
        elif len(cells) >= 5 and _parse_date(cells[0]):
            txn_date = _parse_date(cells[0])
            narration = cells[1]
            debit = _clean_amount(cells[2])
            credit = _clean_amount(cells[3])
            closing = _clean_amount(cells[4])
        else:
            continue

        if debit is not None and debit > 0:
            amount, txn_type = debit, "debit"
        elif credit is not None and credit > 0:
            amount, txn_type = credit, "credit"
        else:
            continue

        if not narration:
            continue

        transactions.append({
            "date": txn_date,
            "raw_text": narration,
            "merchant": narration,
            "amount": amount,
            "type": txn_type,
            "ref_no": "",
            "closing_balance": closing,
        })

    opening = balances.get("opening_balance")
    closing = balances.get("closing_balance")
    computed = None

    if opening is not None:
        credits = sum(row["amount"] for row in transactions if row["type"] == "credit")
        debits = sum(row["amount"] for row in transactions if row["type"] == "debit")
        computed = round(opening + credits - debits, 2)

    ok = (
        computed is not None
        and closing is not None
        and abs(computed - closing) < 0.01
    )

    return {
        "transactions": transactions,
        "opening_balance": opening,
        "closing_balance": closing,
        "reconciled": ok,
        "mismatch": None if ok or computed is None or closing is None
        else round(abs(computed - closing), 2),
    }
