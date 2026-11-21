"""Storage layer: ingest -> Supabase, transactions list, auto-rate, profile + goals (seeded on first read)."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from datetime import date

from app.db import get_client
from app.engines.categorize import categorize
from app.engines.normalize import normalize_merchant
from app.engines.parse import detect_kind, parse_csv, parse_pdf, parse_sms

# ---- tiny read cache: one /report used to re-read the same tables 4-5 times. Cleared on every write.
_CACHE: dict[str, tuple[float, object]] = {}
_LOCK = threading.Lock()
TTL = 60.0


def _cached(key: str, fn: Callable[[], object]):
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < TTL:
        return hit[1]
    val = fn()
    with _LOCK:
        _CACHE[key] = (now, val)
    return val


def invalidate() -> None:
    with _LOCK:
        _CACHE.clear()


TX_FIELDS = "id,upload_id,date,amount,direction,raw_desc,merchant_norm,category,cat_source,confidence,needs_review"


AUTO_CONFIDENCE = 0.9  # AI labels below this go to "Needs review" and don't count as automatic


def _is_auto(t: dict) -> bool:
    """'Auto' = needed no human fix: a rule, or a confident AI label."""
    return t["cat_source"] == "rule" or (t["cat_source"] == "ai" and float(t["confidence"]) >= AUTO_CONFIDENCE)


def _next_month(m: str) -> str:
    y, mo = map(int, m.split("-"))
    return f"{y + (mo == 12)}-{(mo % 12) + 1:02d}"


def ingest(kind: str, filename: str | None, *, text: str | None = None, data: bytes | None = None) -> dict:
    reconciled = None
    if kind == "sms" or (data is not None and detect_kind(filename or "", data) == "sms"):
        kind, rows = "sms", parse_sms(text if text is not None else data.decode("utf-8", "ignore"))
    elif detect_kind(filename or "", data) == "pdf":
        kind = "pdf"
        rows, reconciled = parse_pdf(data)
    else:
        kind, rows = "csv", parse_csv(data)
    if not rows:
        raise ValueError("No transactions found in this input")
    for r in rows:
        r["merchant_norm"] = normalize_merchant(r.get("merchant") or r["raw_desc"])
    rows = categorize(rows)
    auto = sum(_is_auto(r) for r in rows)
    client = get_client()
    upload = client.table("uploads").insert({
        "kind": kind, "filename": filename, "rows_total": len(rows), "rows_auto": auto,
        "auto_rate": round(auto / len(rows), 4), "reconciled": reconciled,
    }).execute().data[0]
    records = [{
        "upload_id": upload["id"], "date": r["date"], "amount": r["amount"], "direction": r["direction"],
        "raw_desc": r["raw_desc"], "merchant_norm": r["merchant_norm"], "category": r["category"],
        "cat_source": r["cat_source"], "confidence": round(float(r["confidence"]), 3),
        "needs_review": r["cat_source"] == "ai" and float(r["confidence"]) < AUTO_CONFIDENCE,
        "dedupe_key": f'{r["date"]}|{r["amount"]:.2f}|{r["direction"]}|{r["raw_desc"][:120]}',
    } for r in rows]
    # Same statement as CSV and PDF -> duplicates skipped by dedupe_key.
    client.table("transactions").upsert(records, on_conflict="dedupe_key", ignore_duplicates=True).execute()
    invalidate()
    saved = client.table("transactions").select(TX_FIELDS).eq("upload_id", upload["id"]).order("date").execute().data
    return {"upload_id": upload["id"], "rows": saved, "auto_rate": round(auto / len(rows), 4),
            "reconciled": reconciled, "duplicates_skipped": len(records) - len(saved)}


def list_transactions(month: str | None = None, category: str | None = None,
                      needs_review: bool | None = None) -> dict:
    q = get_client().table("transactions").select(TX_FIELDS)
    if month:
        q = q.gte("date", f"{month}-01").lt("date", f"{_next_month(month)}-01")
    if category:
        q = q.eq("category", category)
    if needs_review is not None:
        q = q.eq("needs_review", needs_review)
    items = q.order("date", desc=True).limit(2000).execute().data
    for t in items:
        t["amount"] = float(t["amount"])
        t["confidence"] = float(t["confidence"])
    return {"items": items, "total": len(items)}


def auto_rate_series() -> dict:
    """Live per-upload rate: rows that needed no human fix (user-corrected rows count as misses)."""
    client = get_client()
    ups = client.table("uploads").select("id,filename,kind,created_at").order("created_at").execute().data
    txs = client.table("transactions").select("upload_id,cat_source,confidence").execute().data
    out = []
    for u in ups:
        rows = [t for t in txs if t["upload_id"] == u["id"]]
        if rows:
            out.append({"upload_id": u["id"], "filename": u["filename"] or u["kind"], "created_at": u["created_at"],
                        "auto_rate": round(sum(_is_auto(t) for t in rows) / len(rows), 4)})
    return {"series": out}


def all_transactions() -> list[dict]:
    def load():
        rows = get_client().table("transactions").select(TX_FIELDS).order("date").limit(10000).execute().data
        for t in rows:
            t["amount"] = float(t["amount"])
        return rows

    return _cached("tx", load)  # type: ignore[return-value]


def latest_month() -> str:
    tx = all_transactions()
    return max(t["date"] for t in tx)[:7] if tx else date.today().strftime("%Y-%m")


def available_months() -> list[str]:
    return sorted({t["date"][:7] for t in all_transactions()}, reverse=True)


# ---------------- profile + goals
PROFILE_FIELDS = "monthly_income,fixed_costs,emergency_fund,email,budgets"


def seed_profile_goals(force: bool = False) -> None:
    from app.seed import GOALS, PROFILE

    client = get_client()
    row = client.table("profile").select(PROFILE_FIELDS).eq("id", 1).execute().data
    if force or not row or float(row[0]["monthly_income"] or 0) == 0:
        client.table("profile").upsert({"id": 1, **PROFILE, "email": os.environ.get("DEMO_EMAIL")}).execute()
    if force or not client.table("goals").select("id").limit(1).execute().data:
        client.table("goals").insert(GOALS).execute()


def get_profile() -> dict:
    def load():
        seed_profile_goals()
        p = get_client().table("profile").select(PROFILE_FIELDS).eq("id", 1).execute().data[0]
        for k in ("monthly_income", "fixed_costs", "emergency_fund"):
            p[k] = float(p[k] or 0)
        return p

    return dict(_cached("profile", load))  # type: ignore[arg-type]


def put_profile(fields: dict) -> dict:
    upd = {k: v for k, v in fields.items() if v is not None}
    if upd:
        get_client().table("profile").update(upd).eq("id", 1).execute()
        invalidate()
    return get_profile()


def get_goals() -> dict:
    return {"items": [dict(g) for g in _cached("goals", _load_goals)]}  # type: ignore[union-attr]


def _load_goals() -> list[dict]:
    seed_profile_goals()
    items = get_client().table("goals").select("id,name,target_amount,saved_amount,target_date") \
        .order("target_date").execute().data
    today = date.today()
    for g in items:
        g["target_amount"], g["saved_amount"] = float(g["target_amount"]), float(g["saved_amount"])
        td = date.fromisoformat(g["target_date"])
        months = max(1, (td.year - today.year) * 12 + td.month - today.month)
        g["monthly_needed"] = round(max(0.0, g["target_amount"] - g["saved_amount"]) / months, 2)
    return items


def add_goal(g: dict) -> dict:
    date.fromisoformat(g["target_date"])
    row = get_client().table("goals").insert({k: g[k] for k in ("name", "target_amount", "saved_amount", "target_date")}) \
        .execute().data[0]
    row["target_amount"], row["saved_amount"] = float(row["target_amount"]), float(row["saved_amount"])
    invalidate()
    return row


def reset_demo() -> None:
    """Wipe demo data and re-seed profile + goals."""
    client = get_client()
    zero = "00000000-0000-0000-0000-000000000000"
    for t in ("transactions", "category_rules", "nudges", "recurring", "goals", "uploads"):
        client.table(t).delete().neq("id", zero).execute()
    seed_profile_goals(force=True)
    from app.demo_history import build_history

    uploads, txns, rules = build_history()  # Oct 2025 - Sep 2026, already categorised
    client.table("uploads").insert(uploads).execute()
    for i in range(0, len(txns), 400):
        client.table("transactions").insert(txns[i:i + 400]).execute()
    client.table("category_rules").insert(rules).execute()
    invalidate()
