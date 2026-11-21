"""Recurring payment / subscription detection. Owner: Vaishnavi. TODO(slice 4)."""

from __future__ import annotations


def detect_recurring(transactions: list[dict]) -> list[dict]:
    """Group debits by merchant_norm; recurring if >=2 months with similar day-of-month.

    status:
      'changed' - latest amount differs from previous by > 5% (note shows from -> to)
      'unused'  - subscription-like (gym, OTT) with no other related activity in 60 days
      'active'  - otherwise
    Returns RecurringItem dicts (see openapi.yaml). TODO(slice 4)
    """
    raise NotImplementedError
