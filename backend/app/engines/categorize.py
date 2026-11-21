"""Rule-first transaction categorization with an LLM fallback."""

from __future__ import annotations

import json
import math
import re
from collections import Counter

from app.services import llm

CATEGORIES: tuple[str, ...] = (
    "Rent", "Utilities", "Groceries", "Medical", "EMI", "Insurance", "Education",
    "Dining", "Food Delivery", "Shopping", "Travel", "Entertainment", "Subscriptions",
    "Fuel", "Transfers", "Income", "Investments", "Other",
)

_CATEGORY_SET = frozenset(CATEGORIES)

ESSENTIAL: frozenset[str] = frozenset({
    "Rent", "Utilities", "Groceries", "Medical", "EMI", "Insurance", "Education",
})

REVIEW_THRESHOLD = 0.7


def _valid_category(value: object) -> str:
    """Return a valid category or Other for invalid values."""
    return value if isinstance(value, str) and value in _CATEGORY_SET else "Other"


def _extract_response_text(response: object) -> str | None:
    """Safely extract text content from str, dict, or SDK response objects."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        for key in ("text", "content"):
            val = response.get(key)
            if isinstance(val, str):
                return val
        return None
    for attr in ("text", "content"):
        val = getattr(response, attr, None)
        if isinstance(val, str):
            return val
    return None


def _parse_llm_response(content: str | None) -> dict[int, tuple[str, float]]:
    """Parse indexed category predictions; reject malformed or invalid predictions."""
    if not isinstance(content, str):
        return {}

    content = content.strip()
    content = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        content,
        flags=re.IGNORECASE,
    )

    if not content:
        return {}

    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {}

    if isinstance(payload, list):
        results = payload
    elif isinstance(payload, dict):
        results = payload.get("results", [])
    else:
        return {}

    if not isinstance(results, list):
        return {}

    parsed: dict[int, tuple[str, float]] = {}

    for item in results:
        if not isinstance(item, dict):
            continue

        try:
            raw_index = item["index"]

            if isinstance(raw_index, bool):
                continue
            elif isinstance(raw_index, int):
                index = raw_index
            elif isinstance(raw_index, float):
                if not raw_index.is_integer():
                    continue
                index = int(raw_index)
            elif isinstance(raw_index, str):
                index = int(raw_index.strip())
            else:
                continue

            raw_category = item["category"]
            category = _valid_category(raw_category)

            raw_confidence = item["confidence"]
            if isinstance(raw_confidence, bool):
                continue

            confidence = float(raw_confidence)
            if not math.isfinite(confidence):
                continue

            confidence = max(0.0, min(1.0, confidence))

            if category != raw_category:
                confidence = 0.0

            parsed[index] = (category, confidence)

        except (KeyError, TypeError, ValueError, OverflowError):
            continue

    return parsed


def _increment_rule_hits(client, hit_counts: Counter[str], current_hits: dict[str, int]) -> None:
    """Best-effort increment of hits on matched category rules."""
    for rule_id, delta in hit_counts.items():
        if not rule_id or delta <= 0:
            continue
        try:
            new_hits = (current_hits.get(rule_id) or 0) + delta
            client.table("category_rules").update({"hits": new_hits}).eq("id", rule_id).execute()
        except Exception:
            pass


def categorize(rows: list[dict]) -> list[dict]:
    """Categorize rows using exact rules, normalized rules, then one batched LLM call."""
    if not rows:
        return []

    from app.db import get_client

    client = get_client()

    rules_response = (
        client.table("category_rules")
        .select("id,match_type,pattern,category,hits")
        .execute()
    )
    rules = rules_response.data or []

    # Map pattern -> (category, rule_id)
    exact_rules: dict[str, tuple[str, str]]
