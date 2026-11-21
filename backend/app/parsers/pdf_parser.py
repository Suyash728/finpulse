"""Parse HDFC-style bank statement PDFs using pdfplumber.

Extracts the transaction table + opening/closing balance from the header.
Reconciles extracted rows against the stated closing balance.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

import pdfplumber


def _clean_amount(raw: str | None) -> float | None:
    if not raw or not raw.strip():
        return None
    try:
        return float(Decimal(raw.strip().replace(",", "")))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(raw: str) -> str:
    """Convert dd/mm/yyyy → yyyy-mm-dd."""
    try:
        parts = raw.strip().split("/")
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except (IndexError, ValueError):
        return raw.strip()


def _extract_header_balances(text: str) -> dict:
    """Extract opening/closing balance from PDF header text."""
    result = {}
    ob_match = re.search(r"Opening\s+Balance[:\s]*Rs\.?\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
    cb_match = re.search(r"Closing\s+Balance[:\s]*Rs\.?\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
    if ob_match:
        result["opening_balance"] = _clean_amount(ob_match.group(1))
    if cb_match:
        result["closing_balance"] = _clean_amount(cb_match.group(1))
    return result


def parse_pdf(file_bytes: bytes) -> dict:
    """Parse an HDFC PDF statement.

    Returns: {
        "transactions": [...],
        "opening_balance": float | None,
        "closing_balance": float | None,
        "reconciled": bool,
        "mismatch": float | None  # difference if not reconciled
    }
    """
    all_rows = []
    header_text = ""

    with pdfplumber.open(file_bytes) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if not header_text:
                header_text = text

            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                for row in table:
                    if not row or len(row) < 7:
                        continue
                    # Skip header row
                    if row[0] and "Date" in str(row[0]):
                        continue
                    all_rows.append(row)

    # Extract header balances
    balances = _extract_header_balances(header_text)

    # Parse transaction rows
    # Expected columns: Date, Narration, Chq./Ref.No., Value Dt, Withdrawal, Deposit, Closing Balance
    transactions = []
    for row in all_rows:
        try:
            date_raw = str(row[0] or "").strip()
            if not date_raw or not re.match(r"\d{2}/\d{2}/\d{4}", date_raw):
                continue

            narration = str(row[1] or "").strip()
            ref_no = str(row[2] or "").strip()
            withdrawal = _clean_amount(str(row[4] or ""))
            deposit = _clean_amount(str(row[5] or ""))
            closing = _clean_amount(str(row[6] or ""))

            if withdrawal and withdrawal > 0:
                amount = withdrawal
                txn_type = "debit"
            elif deposit and deposit > 0:
                amount = deposit
                txn_type = "credit"
            else:
                continue

            transactions.append({
                "date": _parse_date(date_raw),
                "raw_text": narration,
                "merchant": narration,
                "amount": amount,
                "type": txn_type,
                "ref_no": ref_no,
                "closing_balance": closing,
            })
        except (IndexError, ValueError):
            continue

    # Reconcile: check if last transaction's closing balance matches header
    reconciled = False
    mismatch = None
    if transactions and balances.get("closing_balance") is not None:
        last_closing = transactions[-1].get("closing_balance")
        expected = balances["closing_balance"]
        if last_closing is not None:
            diff = round(abs(last_closing - expected), 2)
            reconciled = diff < 0.01
            if not reconciled:
                mismatch = diff

    return {
        "transactions": transactions,
        "opening_balance": balances.get("opening_balance"),
        "closing_balance": balances.get("closing_balance"),
        "reconciled": reconciled,
        "mismatch": mismatch,
    }
