"""Response examples copied from openapi.yaml. Stub routes return these until each slice lands.

Delete an entry once its route returns real data.
"""

TX_NETFLIX = {"id": "tx_001", "upload_id": "up_001", "date": "2026-10-05", "amount": 499,
              "direction": "dr", "raw_desc": "UPI/NETFLIX/netflix@icici", "merchant_norm": "netflix",
              "category": "Subscriptions", "cat_source": "rule", "confidence": 1.0,
              "needs_review": False}
TX_CRYPTIC = {"id": "tx_002", "upload_id": "up_001", "date": "2026-10-07", "amount": 1240,
              "direction": "dr", "raw_desc": "UPI/RAZ*PAYU8823", "merchant_norm": "raz payu8823",
              "category": "Shopping", "cat_source": "ai", "confidence": 0.42, "needs_review": True}
PROFILE = {"monthly_income": 85000, "fixed_costs": 31500, "emergency_fund": 40000,
           "email": "demo@example.com",
           "budgets": {"Dining": 3000, "Food Delivery": 4000, "Shopping": 5000}}
GOAL_EF = {"id": "goal_001", "name": "Emergency fund", "target_amount": 100000,
           "saved_amount": 40000, "target_date": "2027-06-30"}
GOAL_GOA = {"id": "goal_002", "name": "Goa trip", "target_amount": 25000, "saved_amount": 0,
            "target_date": "2027-03-31"}

EXAMPLES: dict[str, dict] = {
    "ingest": {"upload_id": "up_001", "rows": [TX_NETFLIX, TX_CRYPTIC], "auto_rate": 0.81,
               "reconciled": {"ok": True, "opening": 52310.0, "closing": 61880.5,
                              "computed_closing": 61880.5}},
    "transactions": {"items": [TX_CRYPTIC], "total": 1},
    "correct": {"rule": {"id": "rule_001", "match_type": "normalized", "pattern": "raz payu8823",
                         "category": "Groceries", "hits": 1},
                "similar_ids": ["tx_014", "tx_031"]},
    "rules_apply": {"updated": 2},
    "profile": PROFILE,
    "profile_put": {**PROFILE, "monthly_income": 90000},
    "goals": {"items": [GOAL_EF, GOAL_GOA]},
    "goal_post": GOAL_GOA,
    "recurring": {"items": [
        {"id": "rec_001", "merchant_norm": "netflix", "category": "Subscriptions", "amount": 649,
         "prev_amount": 499, "cadence": "monthly", "last_seen": "2026-11-05", "status": "changed",
         "note": "Price up 30% (499 -> 649)"},
        {"id": "rec_002", "merchant_norm": "cult.fit", "category": "Subscriptions", "amount": 1499,
         "prev_amount": 1499, "cadence": "monthly", "last_seen": "2026-11-02", "status": "unused",
         "note": "No related activity in 60 days"}]},
    "simulate": {"baseline": {"monthly_spend": 61200, "monthly_savings": 23800},
                 "scenario": {"monthly_spend": 62300, "monthly_savings": 22700},
                 "goal_dates": [{"goal_id": "goal_001", "name": "Emergency fund",
                                 "baseline_date": "2027-02-28", "scenario_date": "2027-03-31",
                                 "on_track": True}],
                 "warnings": []},
    "nudges": {"items": [{"id": "ndg_001", "kind": "drift", "category": "Food Delivery",
                          "severity": "warn", "month": "2026-11",
                          "message": "Food Delivery is at 6,850 vs a 4,000 budget with 9 days left."}]},
    "report": {"month": "2026-10", "income": 85000, "spend": 61200, "savings": 23800,
               "savings_rate": 0.28,
               "by_category": [{"category": "Rent", "amount": 22000, "budget": None},
                               {"category": "Food Delivery", "amount": 6850, "budget": 4000}],
               "recurring_changes": [{"merchant_norm": "netflix", "from": 499, "to": 649}],
               "goal_progress": [{"goal_id": "goal_001", "name": "Emergency fund", "pct": 0.4,
                                  "on_track": True}],
               "highlights": ["Savings rate 28%", "Food Delivery 71% over budget"]},
    "email": {"id": "re_abc123", "to": "demo@example.com"},
    "auto_rate": {"series": [
        {"upload_id": "up_001", "filename": "sms_oct.txt", "created_at": "2026-11-21T10:00:00Z",
         "auto_rate": 0.72},
        {"upload_id": "up_003", "filename": "sms_nov.txt", "created_at": "2026-11-21T10:05:00Z",
         "auto_rate": 0.94}]},
    "coach_events": [
        {"node": "intent_guard", "status": "ok", "tier_used": "groq", "ms": 180, "args": {},
         "result_summary": "intent=planning"},
        {"node": "simulate", "status": "ok", "tier_used": None, "ms": 12,
         "args": {"adjustments": [{"category": "Dining", "pct_change": -30}]},
         "result_summary": "savings +900/mo"}],
    "coach_answer": "Cutting dining by 30% frees about 900 a month, so the Goa trip moves to "
                    "March 2027.",
}
