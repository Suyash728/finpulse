"""Deterministic demo data: 12 months of history (Nov 2025 – Oct 2026) + the Nov 2026 statement (1–22 Nov).

One merchant catalog feeds both, so merchant names in the October upload match the rules the
user "learned" over the year. History is inserted already categorised by POST /admin/reset-demo;
the November statement (three weeks in, one week left) is a messy HDFC-style CSV the presenter uploads on camera.
"""

from __future__ import annotations

import calendar
import random
import uuid
from datetime import UTC, date, datetime, timedelta

from app.engines.normalize import normalize_merchant

HISTORY_START = (2025, 11)
HISTORY_MONTHS = 12
DEMO_MONTH = (2026, 11)
DEMO_CUTOFF_DAY = 22  # statement downloaded on 22 Nov: three weeks in, one week left

# (narration, category, direction, (min, max) amount, (min, max) count per month, day range)
FIXED = [
    ("NEFT CR-ACME TECHNOLOGIES PVT LTD-SALARY", "Income", "cr", (85000, 85000), (1, 1), (1, 1)),
    ("NEFT DR-R SHARMA-RENT", "Rent", "dr", (22000, 22000), (1, 1), (2, 3)),
    ("ACH D- BAJAJ FINANCE LTD-PL0098812", "EMI", "dr", (4500, 4500), (1, 1), (5, 5)),
    ("ACH D- ICICI PRU MF SIP", "Investments", "dr", (5000, 5000), (1, 1), (10, 10)),
    ("BIL/AIRTEL POSTPAID/9820XXXX", "Utilities", "dr", (799, 799), (1, 1), (8, 8)),
    ("BIL/MAHANAGAR GAS", "Utilities", "dr", (480, 720), (1, 1), (14, 15)),
    ("UPI-NETFLIX.COM-netflix@icici", "Subscriptions", "dr", (499, 499), (1, 1), (5, 5)),
    ("UPI-SPOTIFY INDIA-spotify@hdfcbank", "Subscriptions", "dr", (119, 119), (1, 1), (11, 11)),
    ("BIL/TATA PLAY DTH", "Subscriptions", "dr", (350, 350), (1, 1), (19, 19)),
    ("NEFT DR-MOM-TRANSFER", "Transfers", "dr", (5000, 5000), (1, 1), (26, 26)),
]
VARIABLE = [
    ("UPI-SWIGGY-swiggy@icici", "Food Delivery", (240, 620), (4, 6)),
    ("UPI-ZOMATO-zomato-order@ptybl", "Food Delivery", (260, 580), (2, 4)),
    ("UPI-BIGBASKET-bigbasket@hdfcbank", "Groceries", (900, 1700), (1, 2)),
    ("UPI-BLINKIT-blinkit@axisbank", "Groceries", (280, 850), (2, 3)),
    ("POS DMART AVENUE THANE", "Groceries", (1400, 2400), (1, 1)),
    ("UPI-STARBUCKS-starbucks@ybl", "Dining", (320, 680), (1, 2)),
    ("POS MAINLAND CHINA ANDHERI", "Dining", (1100, 2200), (0, 1)),
    ("UPI-UBER INDIA-uber.india@axisbank", "Travel", (160, 440), (3, 5)),
    ("UPI-HPCL PETROL PUMP-hpcl@ybl", "Fuel", (1500, 2100), (1, 2)),
    ("UPI-AMAZON PAY-amazonpay@apl", "Shopping", (450, 2600), (1, 2)),
    ("UPI-MYNTRA-myntra@ybl", "Shopping", (700, 2200), (0, 1)),
    ("UPI-APOLLO PHARMACY-apollo@hdfcbank", "Medical", (250, 900), (0, 1)),
    ("UPI-BOOKMYSHOW-bms@icici", "Entertainment", (380, 900), (0, 1)),
    # Cryptic merchants the user corrected early in the year -> learned rules.
    ("UPI-RAZ*PAYU8823-payu@razorpay", "Groceries", (600, 1400), (1, 2)),
    ("POS 4471 MUMBAI", "Dining", (900, 1800), (0, 1)),
    ("UPI-KSH.STORE-ksh.store@okicici", "Medical", (300, 700), (0, 1)),
    ("UPI-PAYTM*QR8812-paytmqr@paytm", "Fuel", (1200, 2000), (0, 1)),
]
CRYPTIC = {"UPI-RAZ*PAYU8823-payu@razorpay", "POS 4471 MUMBAI", "UPI-KSH.STORE-ksh.store@okicici",
           "UPI-PAYTM*QR8812-paytmqr@paytm"}

# Seasonal one-offs: (year, month) -> [(narration, category, amount, day)]
SEASONAL = {
    (2025, 11): [("UPI-TANISHQ-tanishq@hdfcbank", "Shopping", 18500, 18), ("UPI-RELIANCE DIGITAL-rdigital@icici", "Shopping", 12999, 17),
                 ("UPI-AMAZON PAY-amazonpay@apl", "Shopping", 4200, 16)],
    (2025, 12): [("UPI-INDIGO-indigo@icici", "Travel", 8650, 12), ("UPI-MAKEMYTRIP-mmt@icici", "Travel", 11800, 13)],
    (2026, 1): [("ACH D- LIC OF INDIA PREMIUM", "Insurance", 3200, 20)],
    (2026, 3): [("NEFT DR-HDFC ERGO HEALTH", "Insurance", 12000, 22), ("NEFT CR-ACME TECHNOLOGIES-BONUS", "Income", 20000, 28)],
    (2026, 4): [("ACH D- LIC OF INDIA PREMIUM", "Insurance", 3200, 20)],
    (2026, 5): [("UPI-IRCTC-irctc@sbi", "Travel", 2380, 9)],
    (2026, 7): [("ACH D- LIC OF INDIA PREMIUM", "Insurance", 3200, 20), ("UPI-CROMA-croma@hdfcbank", "Shopping", 6499, 24)],
    (2026, 8): [("NEFT DR-KRISHNA TUTORIALS-FEES", "Education", 3500, 6)],
    (2026, 10): [("ACH D- LIC OF INDIA PREMIUM", "Insurance", 3200, 20)],
}
GYM_FROM = (2026, 4)  # cult.fit membership starts in April and is never used
GYM = ("UPI-CULTFIT HEALTHIFYME-cultfit@axisbank", "Subscriptions", 1499, 2)

# November 2026 statement (1-22 Nov): food-delivery drift, Netflix price rise, Diwali (8 Nov), and NEW
# cryptic merchants to fix live.
NEW_CRYPTIC = [  # (narration, true category, amounts, days)
    ("UPI-BHARATPE*90812345-bharatpe.90812345@icici", "Groceries", [640, 820, 455], [4, 15, 21]),
    ("POS 7781 PUNE HWY", "Dining", [1180, 960], [11, 19]),
    ("UPI-Q48219876@ybl", "Medical", [390, 720], [9, 20]),
    ("NEFT DR-KRISHNA TUTORIALS-NOV", "Education", [3500], [6]),
]
DIWALI = [("UPI-AMAZON PAY-amazonpay@apl", "Shopping", 2999, 6), ("UPI-HALDIRAMS-haldirams@ybl", "Dining", 1640, 7)]


def _months(start: tuple[int, int], n: int):
    y, m = start
    for _ in range(n):
        yield y, m
        y, m = (y + (m == 12), m % 12 + 1)


def month_rows(y: int, m: int, *, demo: bool = False) -> list[dict]:
    """Raw rows for one month: {date, raw_desc, amount, direction, category}."""
    rng = random.Random(y * 100 + m)
    dim = calendar.monthrange(y, m)[1]
    last = DEMO_CUTOFF_DAY if demo else dim  # partial month for the on-camera statement
    rows: list[dict] = []

    def add(desc, cat, amt, day, direction="dr"):
        rows.append({"date": date(y, m, min(day, dim)).isoformat(), "raw_desc": desc, "amount": round(float(amt), 2),
                     "direction": direction, "category": cat})

    for desc, cat, direction, (lo, hi), (cmin, cmax), (d0, d1) in FIXED:
        amt = rng.randint(lo, hi)
        if desc.startswith("BIL/MAHANAGAR") and m in (4, 5, 6):
            amt += 180  # summer
        if demo and "NETFLIX" in desc:
            amt = 649  # price rise
        for _ in range(rng.randint(cmin, cmax)):
            day = rng.randint(d0, d1)
            if day <= last:
                add(desc, cat, amt, day, direction)
    # electricity: summer peak
    add("BIL/BBPS/ADANI ELECTRICITY", "Utilities", {4: 2480, 5: 2720, 6: 2350}.get(m, rng.randint(1350, 1850)), 7)
    if (y, m) >= GYM_FROM:
        add(GYM[0], GYM[1], GYM[2], GYM[3])
    for desc, cat, (lo, hi), (cmin, cmax) in VARIABLE:
        n = rng.randint(cmin, cmax)
        if demo:
            n = round(n * last / dim)  # only 22 of 30 days have happened
            if cat == "Food Delivery":
                n += 3  # the drift the nudge should catch
        for _ in range(n):
            add(desc, cat, rng.randint(lo * 100, hi * 100) / 100, rng.randint(1, last))
    for desc, cat, amt, day in SEASONAL.get((y, m), []):
        add(desc, cat, amt, day, "cr" if cat == "Income" else "dr")
    if m in (12, 3, 6, 9):
        add("INT.PD-SB INTEREST", "Income", rng.randint(180, 320), dim)
    if demo:
        for desc, cat, amounts, days in NEW_CRYPTIC:
            for amt, day in zip(amounts, days, strict=True):
                add(desc, cat, amt, day)
        for desc, cat, amt, day in DIWALI:
            add(desc, cat, amt, day)
        add("UPI-UBER INDIA-uber.india@axisbank", "Travel", 286, last)  # statement ends on the 22nd
    rows.sort(key=lambda r: (r["date"], r["direction"] != "cr"))
    return rows


def build_history() -> tuple[list[dict], list[dict], list[dict]]:
    """(uploads, transactions, rules) ready to insert. Auto-rate climbs ~62% -> ~93% over the year."""
    uploads, txns, rule_cats = [], [], {}
    months = list(_months(HISTORY_START, HISTORY_MONTHS))
    for i, (y, m) in enumerate(months):
        rows = month_rows(y, m)
        rng = random.Random(f"src-{y}-{m}")
        target_auto = 0.62 + 0.31 * i / (len(months) - 1)
        n_user = round((1 - target_auto) * len(rows))
        # Corrections fall on cryptic merchants first, then a random spread of others.
        order = sorted(range(len(rows)), key=lambda k: (rows[k]["raw_desc"] not in CRYPTIC, rng.random()))
        user_idx = set(order[:n_user])
        up_id = str(uuid.uuid4())
        next_m = date(y + (m == 12), m % 12 + 1, 1)
        uploads.append({"id": up_id, "kind": "csv" if i % 3 else "sms", "filename": f"hdfc_{y}_{m:02d}.csv",
                        "rows_total": len(rows), "rows_auto": len(rows) - n_user,
                        "auto_rate": round((len(rows) - n_user) / len(rows), 4), "reconciled": None,
                        "created_at": datetime(next_m.year, next_m.month, 1, 3, 30, tzinfo=UTC).isoformat()})
        for k, r in enumerate(rows):
            norm = normalize_merchant(r["raw_desc"])
            src = "user" if k in user_idx else "rule"
            txns.append({**r, "id": str(uuid.uuid4()), "upload_id": up_id, "merchant_norm": norm, "cat_source": src,
                         "confidence": 1.0, "needs_review": False,
                         "dedupe_key": f'{r["date"]}|{r["amount"]:.2f}|{r["direction"]}|{r["raw_desc"][:120]}|{k}'})
            rule_cats[norm] = r["category"]
    hits: dict[str, int] = {}
    for t in txns:
        hits[t["merchant_norm"]] = hits.get(t["merchant_norm"], 0) + 1
    rules = [{"match_type": "normalized", "pattern": p, "category": c, "hits": hits[p]} for p, c in rule_cats.items()]
    return uploads, txns, rules


def demo_statement_rows() -> list[dict]:
    """November 2026 rows (1-22 Nov) for the on-camera upload (no categories: the app must work them out)."""
    return [{k: r[k] for k in ("date", "raw_desc", "amount", "direction")} for r in month_rows(*DEMO_MONTH, demo=True)]


def last_history_day() -> date:
    y, m = list(_months(HISTORY_START, HISTORY_MONTHS))[-1]
    return date(y, m, calendar.monthrange(y, m)[1]) + timedelta(days=0)
