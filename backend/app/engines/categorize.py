"""Categorizer. Owner: Vaishnavi. TODO(slice 2).

Order (hard decision, do not reorder):
  1. exact merchant rule      (category_rules.match_type = 'exact',      pattern == raw merchant)
  2. normalized-merchant rule (category_rules.match_type = 'normalized', pattern == merchant_norm)
  3. LLM with the user's last 20 corrections as few-shot examples
  4. LLM alone
Every transaction stores cat_source (rule|ai|user) + confidence (rule=1.0, user=1.0, ai=model score).
All LLM calls go through app.services.llm.chat().
"""

from __future__ import annotations

CATEGORIES: tuple[str, ...] = (
    "Rent", "Utilities", "Groceries", "Medical", "EMI", "Insurance", "Education",
    "Dining", "Food Delivery", "Shopping", "Travel", "Entertainment", "Subscriptions",
    "Fuel", "Transfers", "Income", "Investments", "Other",
)

# Never suggested as cuts. What-if may model them rising.
ESSENTIAL: frozenset[str] = frozenset(
    {"Rent", "Utilities", "Groceries", "Medical", "EMI", "Insurance", "Education"})

REVIEW_THRESHOLD = 0.6  # ai confidence below this -> needs_review = True


def categorize(rows: list[dict]) -> list[dict]:
    """Add category, cat_source, confidence, needs_review to each normalized row.

    Input rows have: date, amount, direction, raw_desc, merchant_norm.
    Batch the rows that miss both rule lookups into ONE LLM call (JSON output).
    TODO(slice 2)
    """
    raise NotImplementedError


def learn_rule(transaction_id: str, category: str) -> tuple[dict, list[str]]:
    """Correction loop: set txn category (cat_source='user'), upsert a 'normalized' rule for its
    merchant_norm, return (rule, ids of other transactions with same merchant_norm and a different
    category) so the UI can offer retro-apply. TODO(slice 3)
    """
    raise NotImplementedError


def apply_rule(rule_id: str, transaction_ids: list[str]) -> int:
    """Retro-apply a rule to the given transactions; returns rows updated. TODO(slice 3)"""
    raise NotImplementedError
