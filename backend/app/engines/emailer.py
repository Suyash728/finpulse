"""Email via Resend (test sender -> DEMO_EMAIL). Button-triggered only; no cron. Owner: Vaishnavi.

Env: RESEND_API_KEY, EMAIL_FROM (e.g. onboarding@resend.dev), DEMO_EMAIL.
"""

from __future__ import annotations


def render_html(kind: str, payload: dict) -> str:
    """Minimal inline-styled HTML for 'nudges' or 'report'. TODO(slice 9)"""
    raise NotImplementedError


def send(kind: str, month: str | None = None) -> dict:
    """Build payload (compute_nudges / monthly_report), render, send with resend.Emails.send(
    {"from": EMAIL_FROM, "to": [DEMO_EMAIL], "subject": ..., "html": ...}). Returns {id, to}.
    TODO(slice 9)
    """
    raise NotImplementedError
