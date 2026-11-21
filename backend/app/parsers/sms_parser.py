"""Parse Indian bank SMS alerts without treating OTPs or promotions as transactions."""

from __future__ import annotations

import json
import re
from datetime import datetime

from app.services import llm

_AMOUNT_RE = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
_ACCT_RE = re.compile(r"(?:A/c|Acct?)\s*(?:No\.?)?\s*(?:XX?|X+)(\d{3,4})", re.IGNORECASE)
_VPA_RE = re.compile(r"(?:VPA|to)\s+([A-Z0-9._-]+@[A-Z0-9.-]+)", re.IGNORECASE)
_REF_RE = re.compile(r"(?:UPI\s*Ref|Ref)\s*[:\s]?\s*(\d{6,})", re.IGNORECASE)

_DATE_PATTERNS = (
    re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"),
    re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b"),
    re.compile(
        r"\b\d{1,2}[-/ ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*[-/ ]\d{2,4}\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b\d{1,2}(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\d{2,4}\b",
        re.IGNORECASE,
    ),
)

_DATE_FORMATS = (
    "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%d-%b-%y", "%d-%b-%Y", "%d %b %Y", "%d %B %Y",
    "%d%b%y", "%d%b%Y",
)

_SKIP_RE = re.compile(
    r"\b(?:OTP|one.time.password|pre-approved|personal loan|"
    r"apply now|loan offer|valid for \d+ mins?)\b",
    re.IGNORECASE,
)

_DEBIT_RE = re.compile(
    r"\b(?:debit(?:ed)?|sent|spent)\b", re.IGNORECASE
)
_CREDIT_RE = re.compile(
    r"\bcredit(?:ed)?\b", re.IGNORECASE
)
_TRANSACTION_HINT_RE = re.compile(
    r"\b(?:debit(?:ed)?|credit(?:ed)?|sent|spent on|"
    r"withdrawn|transferred|purchase)\b",
    re.IGNORECASE,
)


def _parse_date(raw: str) -> str:
    raw = raw.strip().replace(",", "")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _extract_date(text: str) -> str:
    for pattern in _DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            parsed = _parse_date(match.group(0))
            if parsed:
                return parsed
    return ""


def _direction(text: str) -> str:
    if _DEBIT_RE.search(text):
        return "debit"
    if _CREDIT_RE.search(text):
        return "credit"
    return ""


def _extract_regex(text: str) -> dict | None:
    if _SKIP_RE.search(text):
        return None

    txn_type = _direction(text)
    if not txn_type:
        return None

    amount_match = _AMOUNT_RE.search(text)
    if not amount_match:
        return None

    try:
        amount = float(amount_match.group(1).replace(",", ""))
    except ValueError:
        return None

    if amount <= 0:
        return None

    date_str = _extract_date(text)
    if not date_str:
        return None

    vpa_match = _VPA_RE.search(text)
    card_merchant = re.search(r"\bat\s+(.+?)(?:\s+on\s+|[.;]|$)", text, re.IGNORECASE)
    merchant = (
        vpa_match.group(1) if vpa_match
        else card_merchant.group(1).strip() if card_merchant
        else text[:80].strip()
    )

    ref_match = _REF_RE.search(text)
    acct_match = _ACCT_RE.search(text)

    return {
        "date": date_str,
        "raw_text": text.strip(),
        "merchant": merchant,
        "amount": amount,
        "type": txn_type,
        "ref_no": ref_match.group(1) if ref_match else "",
        "closing_balance": None,
        "account_suffix": acct_match.group(1) if acct_match else "",
    }


def _extract_llm(text: str) -> dict | None:
    if _SKIP_RE.search(text) or not _TRANSACTION_HINT_RE.search(text):
        return None

    prompt = (
        "Extract a real completed bank transaction from this SMS. "
        "Return ONLY JSON with amount (number), type ('debit' or 'credit'), "
        "date (YYYY-MM-DD), merchant (string), ref_no (string or null). "
        "If this is not a completed transaction, return {\"skip\": true}.\n\n"
        f"SMS: {text}"
    )

    try:
        result = llm.chat(
            [{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = result.text.strip()
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start < 0 or end <= start:
            return None

        data = json.loads(raw[start:end])
        if data.get("skip"):
            return None

        amount = float(data["amount"])
        txn_type = data["type"]
        date_str = _parse_date(str(data.get("date", "")))

        if amount <= 0 or txn_type not in ("debit", "credit") or not date_str:
            return None

        return {
            "date": date_str,
            "raw_text": text.strip(),
            "merchant": str(data.get("merchant") or text[:80]),
            "amount": amount,
            "type": txn_type,
            "ref_no": str(data.get("ref_no") or ""),
            "closing_balance": None,
        }
    except Exception:  # noqa: BLE001 - LLM fallback is best-effort
        return None


def parse_sms(content: str) -> list[dict]:
    """Parse SMS blocks; skip OTPs, promotions and messages without a clear direction."""
    parts = re.split(r"---\s*SMS\s*\d+\s*---", content, flags=re.IGNORECASE)

    if len(parts) <= 1:
        parts = [p.strip() for p in content.strip().split("\n\n") if p.strip()]

    if not parts:
        parts = [content.strip()]

    transactions = []
    for part in parts:
        text = part.strip()
        if len(text) < 20 or _SKIP_RE.search(text):
            continue

        result = _extract_regex(text)
        if result is None:
            result = _extract_llm(text)

        if result is not None:
            transactions.append(result)

    return transactions
