"""What-if simulator. All arithmetic here, never in the LLM."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from app.engines.categorize import ESSENTIAL

NOT_SPEND = {"Transfers", "Investments", "Income"}


def baseline(month: str | None = None) -> dict:
    """Average monthly debit per category over the months present in the data."""
    from app.engines.ledger import all_transactions, get_profile

    tx = [t for t in all_transactions() if t["direction"] == "dr" and t["category"] not in NOT_SPEND]
    months = {t["date"][:7] for t in tx} or {"x"}
    per_cat: dict[str, float] = defaultdict(float)
    for t in tx:
        per_cat[t["category"]] += t["amount"]
    avg = {c: round(v / len(months), 2) for c, v in per_cat.items()}
    return {"income": get_profile()["monthly_income"], "by_category": avg}


def _goal_dates(goals: list[dict], savings: float, start: date) -> list[date | None]:
    """Fund goals one after another (target-date order) from monthly savings; day precision."""
    out, cursor = [], start
    for g in goals:
        need = max(0.0, g["target_amount"] - g["saved_amount"])
        if savings <= 0:
            out.append(None)
            continue
        cursor = cursor + timedelta(days=round(need / savings * 30.44))
        out.append(cursor)
    return out


def simulate(adjustments: list[dict]) -> dict:
    from app.engines.ledger import get_goals

    base = baseline()
    income, cats = base["income"], dict(base["by_category"])
    s_income, s_cats = income, dict(cats)
    for a in adjustments:
        c, pct, absd = a["category"], a.get("pct_change"), a.get("abs_change")
        if c == "Income":
            s_income = s_income * (1 + (pct or 0) / 100) + (absd or 0)
            continue
        cur = s_cats.get(c, 0.0)
        s_cats[c] = max(0.0, cur * (1 + (pct or 0) / 100) + (absd or 0))
    spend, s_spend = round(sum(cats.values()), 2), round(sum(s_cats.values()), 2)
    sav, s_sav = round(income - spend, 2), round(s_income - s_spend, 2)
    goals = get_goals()["items"]
    today = date.today()
    b_dates, s_dates = _goal_dates(goals, sav, today), _goal_dates(goals, s_sav, today)
    goal_dates = []
    for g, bd, sd in zip(goals, b_dates, s_dates, strict=True):
        goal_dates.append({"goal_id": g["id"], "name": g["name"],
                           "baseline_date": bd.isoformat() if bd else g["target_date"],
                           "scenario_date": sd.isoformat() if sd else g["target_date"],
                           "on_track": bool(sd and sd.isoformat() <= g["target_date"])})
    warnings = []
    ess = round(sum(v for c, v in s_cats.items() if c in ESSENTIAL), 2)
    if ess > s_income:
        warnings.append(f"Essentials (₹{ess:,.0f}/mo) are more than income (₹{s_income:,.0f}/mo).")
    if s_sav <= 0:
        warnings.append("At this level you save nothing each month, so goals can't be reached.")
    return {"baseline": {"monthly_spend": spend, "monthly_savings": sav},
            "scenario": {"monthly_spend": s_spend, "monthly_savings": s_sav},
            "goal_dates": goal_dates, "warnings": warnings}
