"""What-if simulator. Owner: Vaishnavi. TODO(slice 6).

All arithmetic happens here, never in the LLM.
"""

from __future__ import annotations


def baseline(month: str | None = None) -> dict:
    """Average monthly spend per category over the loaded months + income + savings. TODO(slice 6)"""
    raise NotImplementedError


def simulate(adjustments: list[dict]) -> dict:
    """Apply [{category, pct_change | abs_change}] to the baseline.

    Returns {baseline, scenario, goal_dates[], warnings[]}; goal_dates = month when
    saved_amount + monthly_savings * n >= target_amount, baseline vs scenario.
    Warnings: essentials > income -> plain-language warning (point to income or a human advisor).
    Essentials may go UP here; the coach must never propose cutting them. TODO(slice 6)
    """
    raise NotImplementedError
