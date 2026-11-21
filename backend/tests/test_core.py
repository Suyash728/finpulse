"""Offline tests: router fallback order + every stub route honours the envelope."""

import time

import pytest
from fastapi.testclient import TestClient

from app.engines.categorize import CATEGORIES, ESSENTIAL
from app.main import app
from app.services import llm

c = TestClient(app)


def test_privacy_mode_is_local_only():
    assert llm.tier_order(privacy_mode=True) == ("local",)
    assert llm.tier_order() == ("groq", "gemini", "local")


def test_router_falls_through_missing_keys(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("VLLM_BASE_URL", "http://127.0.0.1:9/v1")  # nothing listens
    with pytest.raises(llm.AllTiersFailed) as e:
        llm.chat([{"role": "user", "content": "hi"}])
    msg = str(e.value)
    assert "groq: no GROQ_API_KEY" in msg and "gemini: no GEMINI_API_KEY" in msg and "local:" in msg


def test_essentials_subset_of_categories():
    assert ESSENTIAL <= set(CATEGORIES) and len(CATEGORIES) == 18


@pytest.mark.parametrize("method,path,body", [
    ("get", "/health", None),
    ("post", "/ingest", {"kind": "sms", "text": "Rs.499 debited to NETFLIX"}),
    ("get", "/transactions?month=2026-10&needs_review=true", None),
    ("post", "/transactions/tx_002/correct", {"category": "Groceries"}),
    ("post", "/rules/apply", {"rule_id": "rule_001", "transaction_ids": ["tx_014"]}),
    ("get", "/profile", None),
    ("put", "/profile", {"monthly_income": 90000}),
    ("get", "/goals", None),
    ("post", "/goals", {"name": "Goa trip", "target_amount": 25000, "target_date": "2027-03-31"}),
    ("get", "/recurring", None),
    ("post", "/simulate", {"adjustments": [{"category": "Dining", "pct_change": -30}]}),
    ("get", "/nudges", None),
    ("get", "/report/2026-10", None),
    ("post", "/email/send", {"kind": "report", "month": "2026-10"}),
    ("get", "/stats/auto-rate", None),
])
def test_stub_routes_envelope(method, path, body):
    r = getattr(c, method)(path, **({"json": body} if body else {}))
    j = r.json()
    assert r.status_code == 200 and j["success"] is True and j["error"] is None


def test_ingest_multipart():
    r = c.post("/ingest", files={"file": ("a.csv", b"Date,Narration\n", "text/csv")})
    assert r.json()["success"]


def test_coach_run_emits_trace():
    run_id = c.post("/coach", json={"message": "Can I afford Goa?"}).json()["data"]["run_id"]
    for _ in range(50):
        d = c.get(f"/coach/{run_id}").json()["data"]
        if d["answer"]:
            break
        time.sleep(0.05)
    assert d["events"][0]["node"] == "intent_guard"
    assert {"node", "status", "tier_used", "ms", "args", "result_summary"} <= set(d["events"][1])
