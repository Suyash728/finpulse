"""Parse Indian bank SMS alerts (HDFC/ICICI/SBI-style).

Uses regex patterns to extract: amount, account, date, merchant/VPA, ref.
Falls back to LLM extraction for unrecognised formats.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from app.services import llm


# ── Regex patterns for common Indian bank SMS formats ──────────────────
_AMOUNT_RE = re.compile(
    r"Rs\.?\s*([\d,]+\.?\d*)", re.IGNORECASE
)
_ACCT_RE = re.compile(
    r"(?:A/c|Acct?|a/c)\s*(?:No\.?)?\s*(?:XX?|X+)(\d{3,4})", re.IGNORECASE
)
_DATE_RE = re.compile(
    r"on\s+(\d{1,2}[-/]\w{3,4}[-/]\d{2,4})", re.IGNORECASE
)
_VPA_RE = re.compile(
    r"(?:VPA|to)\s+(\S+@\S+)", re.IGNORECASE
)
_REF_RE = re.compile(
    r"(?:UPI\s*Ref|Ref)\s*[:\s]?\s*(\d{6,})", re.IGNORECASE
)
_DEBIT_RE = re.compile(
    r"debit(?:ed)?", re.IGNORECASE
)
_CREDIT_RE = re.compile(
    r"credit(?:ed)?", re.IGNORECASE
)


def _parse_date(raw: str) -> str:
    """Try to parse dd-Mon-yy or dd-mm-yyyy → ISO date string."""
    for fmt in ("%d-%b-%y", "%d-%B-%y", "%d-%m-%Y", "%d/%m/%Y",
                "%d-%b-%Y", "%d-%m-%y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _extract_regex(text: str) -> dict | None:
    """Try to extract transaction from SMS using regex. Returns dict or None."""
    amounts = _AMOUNT_RE.findall(text)
    if not amounts:
        return None

    # First amount is the transaction amount
    amount_str = amounts[0].replace(",", "")
    try:
        amount = float(amount_str)
    except ValueError:
        return None

    # Determine type
    if _DEBIT_RE.search(text):
        txn_type = "debit"
    elif _CREDIT_RE.search(text):
        txn_type = "credit"
    else:
        txn_type = "debit"  # default for Indian bank SMS

    # Date
    date_match = _DATE_RE.search(text)
    date_str = _parse_date(date_match.group(1)) if date_match else ""

    # Merchant / VPA
    vpa_match = _VPA_RE.search(text)
    merchant = vpa_match.group(1) if vpa_match else ""

    # Ref
    ref_match = _REF_RE.search(text)
    ref_no = ref_match.group(1) if ref_match else ""

    # Account
    acct_match = _ACCT_RE.search(text)
    account = acct_match.group(1) if acct_match else ""

    return {
        "date": date_str,
        "raw_text": text.strip(),
        "merchant": merchant or text[:80].strip(),
        "amount": amount,
        "type": txn_type,
        "ref_no": ref_no,
        "closing_balance": None,
        "account_suffix": account,
    }


def _extract_llm(text: str) -> dict | None:
    """Use LLM to extract transaction from an SMS that regex couldn't parse."""
    prompt = (
        "Extract the transaction from this Indian bank SMS. "
        "Return ONLY valid JSON with keys: amount (number), type ('debit' or 'credit'), "
        "date (YYYY-MM-DD), merchant (string), ref_no (string or null). "
        "If not a transaction SMS, return {\"skip\": true}.\n\n"
        f"SMS: {text}"
    )
    try:
        result = llm.chat(
            [{"role": "user", "content": prompt}],
            temperature=0,
        )
        # Extract JSON from response
        raw = result.text.strip()
        # Try to find JSON in the response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
        else:
            return None

        if data.get("skip"):
            return None

        return {
            "date": str(data.get("date", "")),
            "raw_text": text.strip(),
            "merchant": str(data.get("merchant", text[:80])),
            "amount": float(data["amount"]),
            "type": data.get("type", "debit"),
            "ref_no": str(data.get("ref_no", "")),
            "closing_balance": None,
        }
    except Exception:
        return None


def parse_sms(content: str) -> list[dict]:
    """Parse one or more SMS messages from text content.

    Supports formats:
    - Multiple SMS separated by '--- SMS N ---' headers
    - Each SMS on separate lines (double newline separated)
    - Single SMS
    """
    # Split on SMS delimiters
    parts = re.split(r"---\s*SMS\s*\d+\s*---", content, flags=re.IGNORECASE)

    if len(parts) <= 1:
        # Try splitting on double newlines
        parts = [p.strip() for p in content.strip().split("\n\n") if p.strip()]

    if not parts:
        parts = [content.strip()]

    transactions = []
    for part in parts:
        text = part.strip()
        if not text or len(text) < 20:
            continue

        # Try regex first
        result = _extract_regex(text)
        if result is None:
            # Fall back to LLM
            result = _extract_llm(text)

        if result is not None:
            transactions.append(result)

    return transactions
