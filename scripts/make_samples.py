# /// script
# requires-python = ">=3.12"
# dependencies = ["fpdf2>=2.8"]
# ///
"""Write the November 2026 demo statement (1-22 Nov) (messy HDFC-style CSV + PDF) to backend/samples/ and
frontend/public/samples/. History (Nov 2025 - Oct 2026) is loaded by POST /admin/reset-demo from the
same catalog in backend/app/demo_history.py, so merchant names match the learned rules.

Run: cd backend && uv run python ../scripts/make_samples.py
"""

from __future__ import annotations

import csv
import io
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.demo_history import demo_statement_rows  # noqa: E402

OUT = ROOT / "backend" / "samples"
PUBLIC = ROOT / "frontend" / "public" / "samples"
NAME = "hdfc_statement_nov_2026"
OPENING = 152_340.55


def fmt_date(d: date, i: int) -> str:
    return [f"{d:%d/%m/%y}", f"{d:%d/%m/%Y}", f"{d:%d-%b-%y}", f"{d:%d %b %Y}"][i % 4]  # messy on purpose


def with_balance(rows: list[dict]) -> tuple[list[dict], float]:
    bal = OPENING
    for r in rows:
        bal += r["amount"] if r["direction"] == "cr" else -r["amount"]
        r["balance"] = round(bal, 2)
    return rows, round(bal, 2)


def write_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    buf.write("HDFC BANK Ltd.\nStatement of account\nAccount No :,50100XXXXXX4521\n"
              "Statement From :,01/11/2026,To :,22/11/2026\n\n")
    w = csv.writer(buf)
    w.writerow(["Date", "Narration", "Chq./Ref.No.", "Value Dt", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"])
    for i, r in enumerate(rows):
        d = date.fromisoformat(r["date"])
        amt = f"{r['amount']:,.2f}"
        w.writerow([fmt_date(d, i), r["raw_desc"], f"{4100000000 + i * 7919:010d}", f"{d:%d/%m/%y}",
                    amt if r["direction"] == "dr" else "", amt if r["direction"] == "cr" else "", f"{r['balance']:,.2f}"])
    buf.write("\n*** End of statement. Generated for demo purposes (synthetic data). ***\n")
    return buf.getvalue()


def write_pdf(rows: list[dict], closing: float, path: Path) -> bool:
    try:
        from fpdf import FPDF
    except ImportError:
        print("skip PDF (fpdf2 not installed)")
        return False
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=8)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "HDFC Bank - Statement of Account", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 5, "Account: 50100XXXXXX4521   Period: 01-Nov-2026 to 22-Nov-2026", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Opening Balance: {OPENING:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Closing Balance: {closing:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", size=7)
    with pdf.table(col_widths=(20, 92, 24, 24, 30), text_align=("LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT"),
                   line_height=3.4, padding=0.6) as t:
        t.row(["Date", "Description", "Debit", "Credit", "Balance"])
        for r in rows:
            a = f"{r['amount']:,.2f}"
            t.row([f"{date.fromisoformat(r['date']):%d-%m-%Y}", r["raw_desc"][:58], a if r["direction"] == "dr" else "",
                   a if r["direction"] == "cr" else "", f"{r['balance']:,.2f}"])
    pdf.output(str(path))
    return True


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for old in list(OUT.glob("*")) + list(PUBLIC.glob("*")):  # previous Oct/Nov samples conflict with history
        old.unlink()
    rows, closing = with_balance(demo_statement_rows())
    (OUT / f"{NAME}.csv").write_text(write_csv(rows))
    write_pdf(rows, closing, OUT / f"{NAME}.pdf")
    for f in OUT.iterdir():
        shutil.copy(f, PUBLIC / f.name)
    print(f"{len(rows)} rows, closing {closing:,.2f}")
    for f in sorted(OUT.iterdir()):
        print(f"  {f.relative_to(ROOT)}  {f.stat().st_size} bytes")


if __name__ == "__main__":
    main()
