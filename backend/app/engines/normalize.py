"""Merchant normalization. Pure functions, no I/O.

"UPI/RAZ*PAYU8823" -> "raz payu", "swiggy@icici" -> "swiggy", "NETFLIX.COM" -> "netflix".
Same merchant in Oct and Nov (SMS, CSV or PDF) must map to the same string so learned rules fire.
"""

from __future__ import annotations

import re

_ALIASES = [  # (regex on lowercase text, canonical name)
    (r"swiggy\s*instamart", "swiggy instamart"), (r"swiggy", "swiggy"), (r"zomato", "zomato"),
    (r"netflix", "netflix"), (r"spotify", "spotify"), (r"cult\s*\.?\s*fit|cultfit", "cultfit"),
    (r"amazon\s*pay|amazon", "amazon"), (r"flipkart", "flipkart"), (r"myntra", "myntra"),
    (r"\buber\b|uber\.india", "uber"), (r"\bola\b|olacabs", "ola"), (r"bigbasket", "bigbasket"),
    (r"blinkit", "blinkit"), (r"dmart", "dmart"), (r"pvr", "pvr inox"), (r"bookmyshow|\bbms@", "bookmyshow"),
    (r"irctc", "irctc"), (r"apollo", "apollo pharmacy"), (r"hpcl", "hpcl"), (r"airtel", "airtel"),
    (r"\bjio\b", "jio"), (r"adanielec|adani\s*elec", "adani electricity"), (r"bescom", "bescom"),
    (r"mahanagar\s*gas", "mahanagar gas"), (r"tata\s*play", "tata play"), (r"bajajfin", "bajaj finance"),
    (r"lic\s+of\s+india", "lic"), (r"hdfc\s*ergo", "hdfc ergo"), (r"icici\s*pru", "icici pru mf"),
    (r"croma", "croma"), (r"reliance\s*digital", "reliance digital"), (r"salary", "salary"),
]
_PREFIX = re.compile(
    r"^(?:upi|pos|neft|imps|rtgs|ach\s*d-?|ach|nach|ecs|bil|bbps|vpa|to|by|ref|txn|p2a|p2m|dr|cr)\b[\s/:*.-]*",
    re.IGNORECASE)
_CITY = re.compile(r"\b(?:mumbai|bangalore|bengaluru|blr|delhi|pune|navi|andheri|bandra|thane|in)\b")


_SMS_PAYEE = re.compile(
    r"(?:\btrf\s+to|\bto|\bat|\bby\s+vpa|;)\s+(.+?)(?:\s+(?:on|ref|refno|credited|\(upi)\b|[.;]\s|$)",
    re.IGNORECASE)


def sms_payee(text: str) -> str | None:
    """Payee from a full bank SMS ("Sent Rs.1240 ... To UPI/RAZ*PAYU8823 On ...")."""
    if len(text) < 40 or not re.search(r"\b(?:rs\.?|inr|debited|credited|spent|sent)\b", text, re.IGNORECASE):
        return None
    vpa = re.search(r"\bby\s+vpa\s+(\S+)", text, re.IGNORECASE)  # credits: payer VPA
    if vpa:
        return vpa.group(1)
    m = _SMS_PAYEE.search(text)
    return m.group(1).strip() if m else None


def normalize_merchant(raw_desc: str) -> str:
    """Lowercase, alias known brands, strip channel prefixes / refs / digits / city words."""
    s = (sms_payee(raw_desc or "") or raw_desc or "").lower().strip()
    for pat, name in _ALIASES:
        if re.search(pat, s):
            return name
    prev = None
    while prev != s:  # strip stacked prefixes: "UPI/P2A/..."
        prev, s = s, _PREFIX.sub("", s).strip()
    s = s.split("@")[0]  # VPA handle -> local part
    s = re.sub(r"[*/_|,;:()-]+", " ", s)
    cleaned = _CITY.sub(" ", re.sub(r"\d{3,}", " ", s))
    cleaned = re.sub(r"\b(?:ltd|pvt|limited|india|pl)\b", " ", cleaned)
    words: list[str] = []
    for w in (w.strip(".") for w in cleaned.split()):  # "ksh.store ksh.store" -> "ksh.store"
        if w and w not in words:
            words.append(w)
    cleaned = " ".join(words).strip(" .")
    if len(cleaned) >= 2:
        return cleaned[:60]
    return re.sub(r"\s+", " ", s).strip(" .")[:60] or "unknown"
