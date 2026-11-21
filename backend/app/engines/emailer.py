"""Branded emails via Resend (test sender -> DEMO_EMAIL). Button-triggered only; no cron.

Email clients strip SVG/JS, so every chart is drawn with table cells + inline styles (works in
Gmail web/app, Outlook, Apple Mail). Every number is computed in Python before it gets here.
"""

from __future__ import annotations

import html
import os

APP_URL = os.environ.get("APP_URL", "https://finpulse-sandy-five.vercel.app").rstrip("/")
TEAL, TEAL_DARK, INK, MUTED, LINE, BG = "#0f766e", "#115e59", "#18181b", "#71717a", "#e4e4e7", "#f4f4f5"
RED, GREEN, AMBER, GREY = "#dc2626", "#16a34a", "#d97706", "#d4d4d8"
FONT = "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"


def _inr(n: float) -> str:
    n = float(n)
    s = f"{abs(n):,.0f}" if abs(n) >= 1000 else f"{abs(n):,.2f}".rstrip("0").rstrip(".")
    # Indian grouping: 1,23,456
    whole, _, frac = s.replace(",", "").partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        whole = f"{head},{tail}"
    return f"{'-' if n < 0 else ''}₹{whole}{'.' + frac if frac else ''}"


def _month_name(m: str) -> str:
    import calendar

    y, mo = m.split("-")
    return f"{calendar.month_name[int(mo)]} {y}"


def _esc(s: object) -> str:
    return html.escape(str(s))


def _bar(pct: float, color: str, height: int = 8) -> str:
    pct = max(0.0, min(100.0, pct))
    rest = 100 - pct
    filled = f'<td width="{pct:.1f}%" style="background:{color};height:{height}px;line-height:{height}px;font-size:0;border-radius:4px">&nbsp;</td>' if pct > 0 else ""
    empty = f'<td width="{rest:.1f}%" style="background:{BG};height:{height}px;line-height:{height}px;font-size:0">&nbsp;</td>' if rest > 0 else ""
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate;'
            f'border-radius:4px;overflow:hidden;background:{BG}"><tr>{filled}{empty}</tr></table>')


def _badge(text: str, color: str) -> str:
    return (f'<span style="display:inline-block;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600;'
            f'color:{color};background:{color}1a">{_esc(text)}</span>')


def _section(title: str, body: str) -> str:
    return (f'<tr><td style="padding:8px 24px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border:1px solid {LINE};border-radius:12px;background:#ffffff"><tr><td style="padding:16px 16px 4px;'
            f'{FONT}font-size:14px;font-weight:700;color:{INK}">{_esc(title)}</td></tr><tr><td style="padding:4px 16px 16px">'
            f'{body}</td></tr></table></td></tr>')


def _shell(subtitle: str, preheader: str, body_rows: str, cta_label: str, cta_path: str) -> str:
    logo = f"{APP_URL}/icons/icon-192.png"
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only"><title>FinPulse</title></head>
<body style="margin:0;padding:0;background:{BG}">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{_esc(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG}"><tr><td align="center" style="padding:24px 8px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:{BG}">
<tr><td style="padding:0 24px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"
  style="background:{TEAL};background-image:linear-gradient(135deg,{TEAL},{TEAL_DARK});border-radius:14px">
  <tr><td style="padding:20px 20px">
    <table role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td style="padding-right:12px"><img src="{logo}" width="40" height="40" alt="FinPulse" style="display:block;border-radius:10px;border:2px solid rgba(255,255,255,.35)"></td>
      <td style="{FONT}color:#ffffff"><div style="font-size:20px;font-weight:800;letter-spacing:-.3px">FinPulse</div>
        <div style="font-size:13px;opacity:.9">{_esc(subtitle)}</div></td>
    </tr></table>
  </td></tr></table></td></tr>
{body_rows}
<tr><td align="center" style="padding:20px 24px 8px">
  <a href="{APP_URL}{cta_path}" style="{FONT}display:inline-block;background:{TEAL};color:#ffffff;text-decoration:none;
  font-weight:700;font-size:14px;padding:12px 22px;border-radius:10px">{_esc(cta_label)} →</a></td></tr>
<tr><td style="padding:12px 24px 24px;{FONT}font-size:11px;line-height:16px;color:{MUTED};text-align:center">
  FinPulse is an educational coach. It never recommends specific stocks, funds or crypto.<br>
  Every figure is computed from your transactions, not guessed by AI. · Demo data, synthetic.</td></tr>
</table></td></tr></table></body></html>"""


# ---------------------------------------------------------------- report email
def _report_html(r: dict, recurring: list[dict]) -> str:
    month = _month_name(r["month"])
    prev = r.get("prev_spend") or 0
    spend_delta = round((r["spend"] - prev) / prev * 100) if prev else None
    tiles = [("Income", _inr(r["income"]), None), ("Spent", _inr(r["spend"]),
             (f"{'+' if spend_delta > 0 else ''}{spend_delta}% vs last month", RED if spend_delta > 0 else GREEN) if spend_delta is not None else None),
             ("Saved", _inr(r["savings"]), None), ("Savings rate", f"{round(r['savings_rate'] * 100)}%", None)]
    cells = ""
    for i, (label, value, sub) in enumerate(tiles):
        sub_html = f'<div style="margin-top:4px">{_badge(sub[0], sub[1])}</div>' if sub else ""
        cells += (f'<td width="50%" style="padding:6px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
                  f'style="border:1px solid {LINE};border-radius:12px;background:#fff"><tr><td style="padding:12px 14px;{FONT}">'
                  f'<div style="font-size:12px;color:{MUTED}">{label}</div><div style="font-size:20px;font-weight:800;color:{INK}">{value}</div>'
                  f'{sub_html}</td></tr></table></td>')
        if i % 2 == 1:
            cells += "</tr><tr>"
    kpis = (f'<tr><td style="padding:8px 18px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
            f'{cells}</tr></table></td></tr>')
    headline = (f'<tr><td style="padding:16px 24px 4px;{FONT}"><div style="font-size:22px;font-weight:800;color:{INK}">'
                f'You kept {round(r["savings_rate"] * 100)}% of your income in {month}.</div>'
                f'<div style="font-size:13px;color:{MUTED};margin-top:4px">Here is where {_inr(r["spend"])} went.</div></td></tr>')

    cats = [c for c in r["by_category"]][:8]
    top = max([1.0] + [max(c["amount"], c.get("budget") or 0) for c in cats])
    rows = ""
    for c in cats:
        over = c.get("budget") and c["amount"] > c["budget"]
        color = RED if over else TEAL
        right = f'<b style="color:{RED if over else INK}">{_inr(c["amount"])}</b>' + (
            f'<span style="color:{MUTED}"> / {_inr(c["budget"])}</span>' if c.get("budget") else "")
        rows += (f'<tr><td style="padding:6px 0 2px;{FONT}font-size:13px;color:{INK}">{_esc(c["category"])}</td>'
                 f'<td align="right" style="padding:6px 0 2px;{FONT}font-size:13px">{right}</td></tr>'
                 f'<tr><td colspan="2" style="padding:0 0 4px">{_bar(c["amount"] / top * 100, color)}</td></tr>')
    where = f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>'

    cmp_rows = ""
    cmp_cats = [c for c in r["by_category"] if c["category"] != "Other"][:6]
    ctop = max([1.0] + [max(c["amount"], c.get("prev_amount") or 0) for c in cmp_cats])
    for c in cmp_cats:
        ch = c.get("change_pct")
        badge = _badge(f"{'+' if ch > 0 else ''}{round(ch)}%", RED if ch > 0 else GREEN) if ch is not None else _badge("new", MUTED)
        cmp_rows += (f'<tr><td width="34%" style="padding:6px 8px 6px 0;{FONT}font-size:12px;color:{INK}">{_esc(c["category"])}</td>'
                     f'<td style="padding:6px 0">{_bar((c.get("prev_amount") or 0) / ctop * 100, GREY, 6)}'
                     f'<div style="height:3px;line-height:3px;font-size:0">&nbsp;</div>{_bar(c["amount"] / ctop * 100, TEAL, 6)}</td>'
                     f'<td width="18%" align="right" style="padding:6px 0 6px 8px">{badge}</td></tr>')
    legend = (f'<div style="{FONT}font-size:11px;color:{MUTED};padding-bottom:6px">'
              f'<span style="color:{GREY}">■</span> {_month_name(r["prev_month"])} {_inr(prev)} &nbsp; '
              f'<span style="color:{TEAL}">■</span> {month} {_inr(r["spend"])}</div>') if r.get("prev_month") else ""
    compare = f'{legend}<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{cmp_rows}</table>'

    ins = ""
    for it in r.get("insights", []):
        color = RED if it["tone"] == "bad" else GREEN
        badge = f' {_badge(f"{abs(round(it["delta_pct"]))}%", color)}' if it.get("delta_pct") is not None else ""
        ins += (f'<tr><td width="14" valign="top" style="padding:8px 0;{FONT}color:{color};font-size:14px">●</td>'
                f'<td style="padding:8px 0 8px 6px;{FONT}font-size:13px;line-height:19px;color:{INK};border-bottom:1px solid {BG}">'
                f'{_esc(it["text"])}{badge}</td></tr>')
    insights = f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{ins}</table>'

    subs = ""
    for s in [x for x in recurring if x["status"] != "active"]:
        tag = _badge("Price up", AMBER) if s["status"] == "changed" else _badge("Unused", MUTED)
        amount = (f'{_inr(s["prev_amount"])} → <b>{_inr(s["amount"])}</b>' if s["status"] == "changed"
                  else f'<b>{_inr(s["amount"])}</b>/mo')
        subs += (f'<tr><td style="padding:8px 0;{FONT}font-size:13px;color:{INK};border-bottom:1px solid {BG}">'
                 f'<b>{_esc(s["merchant_norm"].title())}</b> {tag}<div style="font-size:12px;color:{MUTED}">{_esc(s.get("note", ""))}</div></td>'
                 f'<td align="right" style="padding:8px 0;{FONT}font-size:13px;color:{INK};border-bottom:1px solid {BG}">{amount}</td></tr>')
    subscriptions = f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{subs}</table>' if subs else ""

    goals = ""
    for g in r.get("goal_progress", []):
        color = GREEN if g["on_track"] else RED
        goals += (f'<tr><td style="padding:6px 0 2px;{FONT}font-size:13px;color:{INK}">{_esc(g["name"])}</td>'
                  f'<td align="right" style="padding:6px 0 2px;{FONT}font-size:12px;color:{color}">{round(g["pct"] * 100)}% · '
                  f'{"on track" if g["on_track"] else "behind"}</td></tr><tr><td colspan="2">{_bar(g["pct"] * 100, TEAL)}</td></tr>')
    goals_html = f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{goals}</table>' if goals else ""

    p = r.get("projection") or {}
    proj = ""
    if p.get("budget_total"):
        ok = p["on_track"]
        proj = (f'<div style="{FONT}font-size:13px;color:{INK};line-height:20px">'
                f'{_badge("Within budget" if ok else "Over budget", GREEN if ok else RED)}<br>'
                f'Spent <b>{_inr(p["projected"])}</b> against a <b>{_inr(p["budget_total"])}</b> monthly budget · '
                f'average <b>{_inr(p["avg_per_day"])}</b> a day.</div>')

    body = headline + kpis + _section("Where your money went", where) + _section("This month vs last month", compare)
    body += _section("Insights", insights)
    if subscriptions:
        body += _section("Subscriptions to review", subscriptions)
    if goals_html:
        body += _section("Goal progress", goals_html)
    if proj:
        body += _section("Budget check", proj)
    pre = f"{month}: spent {_inr(r['spend'])}, saved {_inr(r['savings'])} ({round(r['savings_rate'] * 100)}%)."
    return _shell(f"{month} · Monthly review", pre, body, "Open your full report", "/report")


# ---------------------------------------------------------------- nudges email
def _nudges_html(items: list[dict]) -> str:
    color = {"alert": RED, "warn": AMBER, "info": MUTED}
    label = {"drift": "Budget drift", "price_change": "Price change", "unused": "Unused", "essentials_over_income": "Essentials"}
    rows = ""
    for n in items:
        c = color.get(n["severity"], MUTED)
        rows += (f'<tr><td width="4" style="background:{c};border-radius:2px">&nbsp;</td>'
                 f'<td style="padding:10px 12px;{FONT}"><div>{_badge(label.get(n["kind"], n["kind"]), c)}</div>'
                 f'<div style="font-size:14px;line-height:20px;color:{INK};margin-top:4px">{_esc(n["message"])}</div></td></tr>'
                 f'<tr><td colspan="2" style="height:8px;font-size:0;line-height:8px">&nbsp;</td></tr>')
    if not rows:
        rows = f'<tr><td style="{FONT}font-size:14px;color:{INK}">All good: nothing has drifted off plan.</td></tr>'
    headline = (f'<tr><td style="padding:16px 24px 4px;{FONT}"><div style="font-size:22px;font-weight:800;color:{INK}">'
                f'{len(items)} thing{"s" if len(items) != 1 else ""} need{"s" if len(items) == 1 else ""} your attention</div>'
                f'<div style="font-size:13px;color:{MUTED};margin-top:4px">Spending drift and subscription changes FinPulse spotted.</div></td></tr>')
    body = headline + _section("Nudges", f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>')
    return _shell("Your nudges", f"{len(items)} nudges from FinPulse", body, "Open FinPulse", "/")


def render_html(kind: str, payload: dict) -> str:
    if kind == "nudges":
        return _nudges_html(payload["items"])
    return _report_html(payload, payload.get("_recurring", []))


def build(kind: str, month: str | None = None) -> tuple[str, str]:
    """(subject, html) for a kind; used by send() and the preview script."""
    from app.engines.ledger import all_transactions, latest_month
    from app.engines.nudges import compute_nudges
    from app.engines.recurring import detect_recurring
    from app.engines.report import monthly_report

    if kind == "nudges":
        items = compute_nudges(month)
        return f"FinPulse · {len(items)} nudges for you", render_html("nudges", {"items": items})
    m = month or latest_month()
    payload = monthly_report(m)
    payload["_recurring"] = detect_recurring(all_transactions())
    return f"FinPulse · Your {_month_name(m)} review", render_html("report", payload)


def send(kind: str, month: str | None = None) -> dict:
    import resend

    from app.engines.ledger import get_profile

    resend.api_key = os.environ["RESEND_API_KEY"]
    to = os.environ.get("DEMO_EMAIL") or get_profile().get("email")
    if not to:
        raise ValueError("No DEMO_EMAIL configured")
    subject, body = build(kind, month)
    r = resend.Emails.send({"from": os.environ.get("EMAIL_FROM", "FinPulse <onboarding@resend.dev>"), "to": [to],
                            "subject": subject, "html": body})
    return {"id": r["id"] if isinstance(r, dict) else getattr(r, "id", ""), "to": to}
