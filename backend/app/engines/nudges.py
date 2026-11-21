"""Nudges when spending drifts off plan. Owner: Vaishnavi. TODO(slice 7)."""

from __future__ import annotations


def compute_nudges(month: str) -> list[dict]:
    """Drift = month-to-date spend vs pro-rated budget per category (profile.budgets).

    Also emit price_change / unused (from recurring) and essentials_over_income.
    Never phrase an essential category as something to cut. Returns Nudge dicts. TODO(slice 7)
    """
    raise NotImplementedError
