"""Email via Resend (test sender -> DEMO_EMAIL). Button-triggered only; no cron."""

from __future__ import annotations

import html
import os


def render_html(kind: str, payload: dict) -> str:
    if kind == "nudges":
        items = "".join(f"<li style='margin:6px 0'>{html.escape(n['message'])}</li>" for n in payload["items"])
        body = f"<h2 style='margin:0 0 8px'>Your FinPulse nudges</h2><ul style='padding-left:18px'>{items or '<li>All good this month.</li>'}</ul>"
    else:
        r = payload
        rows = "".join(f"<tr><td style='padding:4px 8px'>{html.escape(c['category'])}</td>"
                       f"<td style='padding:4px 8px;text-align:right'>₹{c['amount']:,.0f}</td></tr>" for c in r["by_category"][:8])
        hl = "".join(f"<li>{html.escape(h)}</li>" for h in r["highlights"])
        body = (f"<h2 style='margin:0 0 8px'>FinPulse · {r['month']} review</h2>"
                f"<p>Income ₹{r['income']:,.0f} · Spent ₹{r['spend']:,.0f} · Saved ₹{r['savings']:,.0f} "
                f"({round(r['savings_rate'] * 100)}%)</p><ul>{hl}</ul><table>{rows}</table>")
    return (f"<div style='font-family:system-ui,sans-serif;max-width:560px;color:#111'>{body}"
            "<p style='color:#666;font-size:12px'>Educational coach. Not investment advice.</p></div>")


def send(kind: str, month: str | None = None) -> dict:
    import resend

    from app.engines.ledger import get_profile
    from app.engines.nudges import compute_nudges
    from app.engines.report import monthly_report

    resend.api_key = os.environ["RESEND_API_KEY"]
    to = os.environ.get("DEMO_EMAIL") or get_profile().get("email")
    if not to:
        raise ValueError("No DEMO_EMAIL configured")
    if kind == "nudges":
        payload = {"items": compute_nudges(month)}
        subject = f"FinPulse · {len(payload['items'])} nudges"
    else:
        from app.engines.ledger import all_transactions

        m = month or max(t["date"] for t in all_transactions())[:7]
        payload = monthly_report(m)
        subject = f"FinPulse · {m} review"
    r = resend.Emails.send({"from": os.environ.get("EMAIL_FROM", "onboarding@resend.dev"), "to": [to],
                            "subject": subject, "html": render_html(kind, payload)})
    return {"id": r["id"] if isinstance(r, dict) else getattr(r, "id", ""), "to": to}
