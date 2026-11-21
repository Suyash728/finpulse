"""Rule-first transaction categorization with an LLM fallback."""

from __future__ import annotations

import json
import re

from app.services import llm

CATEGORIES: tuple[str, ...] = (
    "Rent", "Utilities", "Groceries", "Medical", "EMI", "Insurance", "Education",
    "Dining", "Food Delivery", "Shopping", "Travel", "Entertainment", "Subscriptions",
    "Fuel", "Transfers", "Income", "Investments", "Other",
)

ESSENTIAL: frozenset[str] = frozenset({
    "Rent", "Utilities", "Groceries", "Medical", "EMI", "Insurance", "Education",
})

REVIEW_THRESHOLD = 0.7


def _valid_category(value: object) -> str:
    return value if isinstance(value, str) and value in CATEGORIES else "Other"


def _parse_llm_response(content: str) -> dict[int, tuple[str, float]]:
    """Parse indexed category predictions; reject malformed or invalid predictions."""
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE)

    payload = json.loads(content)
    if not isinstance(payload, dict):
        return {}

    results = payload.get("results", [])
    if not isinstance(results, list):
        return {}

    parsed: dict[int, tuple[str, float]] = {}

    for item in results:
        try:
            index = int(item["index"])
            raw_category = item["category"]
            category = _valid_category(raw_category)
            confidence = float(item["confidence"])
            confidence = max(0.0, min(1.0, confidence))

            if category != raw_category:
                confidence = 0.0

            parsed[index] = (category, confidence)
        except (KeyError, TypeError, ValueError):
            continue

    return parsed


def categorize(rows: list[dict]) -> list[dict]:
    """Categorize rows using exact rules, normalized rules, then one batched LLM call."""
    if not rows:
        return []

    from app.db import get_client

    client = get_client()

    rules_response = (
        client.table("category_rules")
        .select("match_type,pattern,category")
        .execute()
    )
    rules = rules_response.data or []

    exact_rules = {
        rule["pattern"]: rule["category"]
        for rule in rules
        if rule.get("match_type") == "exact"
        and rule.get("category") in CATEGORIES
    }
    normalized_rules = {
        rule["pattern"]: rule["category"]
        for rule in rules
        if rule.get("match_type") == "normalized"
        and rule.get("category") in CATEGORIES
    }

    output: list[dict | None] = [None] * len(rows)
    pending: list[tuple[int, dict]] = []

    for index, row in enumerate(rows):
        raw_desc = row.get("raw_desc", "")
        merchant_norm = row.get("merchant_norm", "")

        category = exact_rules.get(raw_desc)
        if category is None:
            category = normalized_rules.get(merchant_norm)

        if category is not None:
            output[index] = {
                **row,
                "category": category,
                "cat_source": "rule",
                "confidence": 1.0,
                "needs_review": False,
            }
        else:
            pending.append((index, row))

    if not pending:
        return [item for item in output if item is not None]

    correction_response = (
        client.table("transactions")
        .select("raw_desc,merchant_norm,category")
        .eq("cat_source", "user")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    corrections = correction_response.data or []

    examples = [
        {
            "raw_desc": item.get("raw_desc", ""),
            "merchant_norm": item.get("merchant_norm", ""),
            "category": item.get("category", ""),
        }
        for item in corrections
        if item.get("category") in CATEGORIES
    ]

    transactions = [
        {
            "index": index,
            "raw_desc": row.get("raw_desc", ""),
            "merchant_norm": row.get("merchant_norm", ""),
            "direction": row.get("direction", ""),
            "amount": row.get("amount", 0),
        }
        for index, row in pending
    ]

    messages = [
        {
            "role": "system",
            "content": (
                "You categorize personal finance transactions. "
                f"Choose exactly one category from: {', '.join(CATEGORIES)}. "
                "Use the user's correction examples as their preferences. "
                "Return only valid JSON in this shape: "
                '{"results":[{"index":0,"category":"Groceries","confidence":0.92}]}. '
                "Confidence must be a number between 0 and 1. "
                "Do not invent transaction details."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {"correction_examples": examples, "transactions": transactions},
                ensure_ascii=False,
            ),
        },
    ]

    predictions: dict[int, tuple[str, float]] = {}

    try:
        response = llm.chat(
            messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        predictions = _parse_llm_response(response.text)
    except (llm.AllTiersFailed, ValueError, TypeError, KeyError):
        # Unknown predictions remain visible in the review queue.
        pass

    for index, row in pending:
        category, confidence = predictions.get(index, ("Other", 0.0))
        output[index] = {
            **row,
            "category": category,
            "cat_source": "ai",
            "confidence": confidence,
            "needs_review": confidence < REVIEW_THRESHOLD,
        }

    return [item for item in output if item is not None]


def learn_rule(transaction_id: str, category: str) -> tuple[dict, list[str]]:
    """Save a normalized user correction and return similar transaction IDs."""
    if category not in CATEGORIES:
        raise ValueError(f"Invalid category: {category}")

    from app.db import get_client

    client = get_client()

    response = (
        client.table("transactions")
        .select("id,raw_desc,merchant_norm")
        .eq("id", transaction_id)
        .limit(1)
        .execute()
    )
    transactions = response.data or []
    if not transactions:
        raise ValueError("Transaction not found")

    transaction = transactions[0]
    merchant_norm = transaction.get("merchant_norm", "").strip()
    if not merchant_norm:
        raise ValueError("Transaction has no normalized merchant")

    client.table("transactions").update({
        "category": category,
        "cat_source": "user",
        "confidence": 1.0,
        "needs_review": False,
    }).eq("id", transaction_id).execute()

    rule_response = (
        client.table("category_rules")
        .upsert(
            {
                "match_type": "normalized",
                "pattern": merchant_norm,
                "category": category,
                "created_from_txn": transaction_id,
            },
            on_conflict="match_type,pattern",
        )
        .execute()
    )

    rule_rows = rule_response.data or []
    if rule_rows:
        rule = rule_rows[0]
    else:
        lookup = (
            client.table("category_rules")
            .select("id,match_type,pattern,category,hits")
            .eq("match_type", "normalized")
            .eq("pattern", merchant_norm)
            .limit(1)
            .execute()
        )
        rule_rows = lookup.data or []
        if not rule_rows:
            raise RuntimeError("Rule was not returned after saving")
        rule = rule_rows[0]

    similar_response = (
        client.table("transactions")
        .select("id,category")
        .eq("merchant_norm", merchant_norm)
        .neq("id", transaction_id)
        .execute()
    )
    similar_ids = [
        item["id"]
        for item in (similar_response.data or [])
        if item.get("id") and item.get("category") != category
    ]

    return rule, similar_ids


def apply_rule(rule_id: str, transaction_ids: list[str]) -> int:
    """Apply a saved rule only to selected transactions matching its pattern."""
    if not transaction_ids:
        return 0

    from app.db import get_client

    client = get_client()

    rule_response = (
        client.table("category_rules")
        .select("id,match_type,pattern,category")
        .eq("id", rule_id)
        .limit(1)
        .execute()
    )
    rules = rule_response.data or []
    if not rules:
        raise ValueError("Rule not found")

    rule = rules[0]
    match_type = rule.get("match_type")
    pattern = rule.get("pattern")
    category = rule.get("category")

    if match_type not in ("exact", "normalized") or category not in CATEGORIES:
        raise ValueError("Invalid saved rule")

    selected_response = (
        client.table("transactions")
        .select("id,raw_desc,merchant_norm")
        .in_("id", transaction_ids)
        .execute()
    )

    matching_ids = [
        item["id"]
        for item in (selected_response.data or [])
        if item.get("id")
        and (
            item.get("raw_desc") == pattern
            if match_type == "exact"
            else item.get("merchant_norm") == pattern
        )
    ]

    if not matching_ids:
        return 0

    update_response = (
        client.table("transactions")
        .update({
            "category": category,
            "cat_source": "rule",
            "confidence": 1.0,
            "needs_review": False,
        })
        .in_("id", matching_ids)
        .select("id")
        .execute()
    )

    return len(update_response.data or [])
