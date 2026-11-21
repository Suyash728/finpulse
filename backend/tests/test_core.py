"""Offline tests: router fallback order + graph interrupt/resume with a stubbed LLM."""

import time

from fastapi.testclient import TestClient

from app.services import llm


def test_privacy_mode_is_local_only():
    assert llm.tier_order(privacy_mode=True) == ("local",)
    assert llm.tier_order() == ("groq", "gemini", "local")


def test_router_falls_through_missing_keys(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("VLLM_BASE_URL", "http://127.0.0.1:9/v1")  # nothing listens
    try:
        llm.chat([{"role": "user", "content": "hi"}])
    except llm.AllTiersFailed as e:
        msg = str(e)
        assert "groq: no GROQ_API_KEY" in msg and "gemini: no GEMINI_API_KEY" in msg
        assert "local:" in msg
    else:
        raise AssertionError("expected AllTiersFailed")


def test_graph_interrupt_and_resume(monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda *a, **k: llm.LLMResult("stub", "stub", "stub", 1))
    from app.main import app

    c = TestClient(app)
    assert c.get("/health").json()["success"]
    run_id = c.post("/runs", json={"input": "x"}).json()["data"]["run_id"]
    for _ in range(50):
        evs = c.get(f"/runs/{run_id}").json()["data"]["events"]
        if any(e["status"] == "interrupted" for e in evs):
            break
        time.sleep(0.05)
    assert [e["node"] for e in evs][:4] == ["planner", "planner", "tools", "tools"]
    assert c.post(f"/runs/{run_id}/resume", json={"approve": True}).json()["success"]
    for _ in range(50):
        state = c.get(f"/runs/{run_id}").json()["data"]["state"]
        if state.get("result"):
            break
        time.sleep(0.05)
    assert state["result"] == "action executed"
