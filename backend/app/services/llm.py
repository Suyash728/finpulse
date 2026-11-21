"""3-tier LLM router. EVERY model call in this repo goes through `chat()`.

Tier 1 Groq (3 s timeout) -> on 429/timeout/error -> Tier 2 Gemini Flash-Lite
-> on failure, no network, or privacy_mode -> Tier 3 local vLLM.
All three speak the OpenAI chat format, so one client class covers them.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from functools import cache

from openai import OpenAI, OpenAIError


@dataclass(frozen=True)
class Tier:
    name: str
    base_url: str
    key_env: str
    model: str
    timeout: float


def _tiers() -> dict[str, Tier]:
    e = os.environ.get
    return {
        "groq": Tier("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY",
                     e("GROQ_MODEL", "openai/gpt-oss-120b"), float(e("GROQ_TIMEOUT", "3"))),
        "gemini": Tier("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/",
                       "GEMINI_API_KEY", e("GEMINI_MODEL", "gemini-3.5-flash-lite"), 20.0),
        # vLLM on this desktop listens on :8001 (SGLang owns :8000).
        "local": Tier("local", e("VLLM_BASE_URL", "http://localhost:8001/v1"), "VLLM_API_KEY",
                      e("VLLM_MODEL", "nvidia/Qwen3-14B-NVFP4"), 120.0),
    }


# Hero call only (20 req/day free): pass model=HERO_MODEL with tiers=("gemini",).
HERO_MODEL = os.environ.get("GEMINI_HERO_MODEL", "gemini-3.8-flash")


@cache
def _client(base_url: str, key: str, timeout: float) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=key, timeout=timeout, max_retries=0)


@dataclass
class LLMResult:
    text: str
    tier: str
    model: str
    ms: int
    message: object = None  # raw message (tool_calls etc.)


class AllTiersFailed(RuntimeError):
    pass


def tier_order(privacy_mode: bool = False) -> tuple[str, ...]:
    if privacy_mode or os.environ.get("PRIVACY_MODE") == "1":
        return ("local",)
    return ("groq", "gemini", "local")


def chat(messages: list[dict], *, privacy_mode: bool = False, tiers: tuple[str, ...] | None = None,
         model: str | None = None, **kwargs) -> LLMResult:
    """Return the first successful completion. kwargs pass through (tools, temperature...)."""
    errors: list[str] = []
    all_tiers = _tiers()
    for name in tiers or tier_order(privacy_mode):
        t = all_tiers[name]
        key = os.environ.get(t.key_env) or ("EMPTY" if name == "local" else "")
        if not key:
            errors.append(f"{name}: no {t.key_env}")
            continue
        if name == "local" and os.environ.get("LOCAL_THINKING") != "1":
            # Qwen3 thinks by default (~10 s/call); off = demo-speed answers.
            kwargs.setdefault("extra_body", {"chat_template_kwargs": {"enable_thinking": False}})
        start = time.perf_counter()
        try:
            resp = _client(t.base_url, key, t.timeout).chat.completions.create(
                model=model or t.model, messages=messages, **kwargs)
        except OpenAIError as exc:  # 429, timeout, DNS, refused, 5xx -> next tier
            errors.append(f"{name}: {type(exc).__name__}: {exc}"[:200])
            continue
        msg = resp.choices[0].message
        return LLMResult(msg.content or "", name, model or t.model,
                         int((time.perf_counter() - start) * 1000), msg)
    raise AllTiersFailed("; ".join(errors))
