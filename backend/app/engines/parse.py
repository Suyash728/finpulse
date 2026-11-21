"""Statement parsers -> list of raw rows. Owner: Vaishnavi.

Every parser returns rows shaped:
  {"date": date, "amount": float (>0), "direction": "dr"|"cr", "raw_desc": str}
"""

from __future__ import annotations


def parse_sms(text: str) -> list[dict]:
    """Parse pasted bank/UPI SMS (HDFC/SBI/ICICI styles, one message per line or blank-line block).
    Regex for amount (Rs./INR/₹), debited/credited, date, merchant/VPA. Skip OTP/promos. TODO(slice 1)
    """
    raise NotImplementedError


def parse_csv(data: bytes) -> list[dict]:
    """Messy CSV via pandas: detect header row, map columns (Txn Date/Value Date/Narration/
    Withdrawal Amt./Deposit Amt./Dr/Cr...), parse mixed date formats (dayfirst). TODO(slice 1)
    """
    raise NotImplementedError


def parse_pdf(data: bytes) -> tuple[list[dict], dict]:
    """pdfplumber table extraction. Returns (rows, reconciled) where reconciled =
    {ok, opening, closing, computed_closing}: opening + credits - debits == closing. TODO(slice 5)
    """
    raise NotImplementedError


def detect_kind(filename: str, data: bytes) -> str:
    """'pdf' | 'csv' | 'sms' by extension, then sniffing. TODO(slice 1)"""
    raise NotImplementedError
