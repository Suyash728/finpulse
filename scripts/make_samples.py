# /// script
# requires-python = ">=3.12"
# dependencies = ["fpdf2>=2.8"]
# ///
"""Generate deterministic demo data into backend/samples/.

Accounts (so loading everything never double-counts):
  sms_*.txt            HDFC / SBI / ICICI UPI + card SMS (day-to-day spending)
  statement_*.csv      Kotak salary account (salary, rent, EMI, bills, SIP) - messy export
  statement_nov.pdf    SAME Kotak account as statement_nov.csv, with opening/closing balance:
                       demo of PDF ingest + reconciliation; rows dedupe against the CSV.

Story: salary 85,000; rent 22,000; Netflix 499 (Oct) -> 649 (Nov); cult.fit 1,499/month with no
related activity (unused); heavy Swiggy/Zomato, worse in Nov (drift); cryptic merchants the AI gets
wrong in Oct (user corrects) and that reappear in Nov (learned rules fire).

Run:  cd backend && uv run python ../scripts/make_samples.py   (fpdf2 is a backend dev dep)
  or: uv run scripts/make_samples.py                         (PEP 723 inline deps)
  or: python scripts/make_samples.py                          (skips the PDF if fpdf2 missing)
"""

from __future__ import annotations

import csv
import io
import random
from datetime import date
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "backend" / "samples"

# Cryptic merchants -> what the user will correct them to (ground truth, NOT in the samples).
CRYPTIC = {
    "UPI/RAZ*PAYU8823": "Groceries",      # local kirana via Razorpay
    "POS 4471 MUMBAI": "Dining",          # restaurant card swipe
    "VPA ksh.store@okicici": "Medical",   # neighbourhood pharmacy
    "UPI/PAYTM*QR8812": "Fuel",           # petrol pump QR
    "IMPS/P2A/RMKCLASSES": "Education",   # tuition fees
}


def ref(rng: random.Random) -> str:
    return str(rng.randint(10**11, 10**12 - 1))


# ---------------------------------------------------------------- SMS
def sms_hdfc_upi(d: date, amt: float, payee: str, rng) -> str:
    return (f"Sent Rs.{amt:.2f} From HDFC Bank A/C *4521 To {payee} On {d:%d/%m/%y} "
            f"Ref {ref(rng)} Not You? Call 18002586161/SMS BLOCK UPI to 7308080808")


def sms_hdfc_card(d: date, amt: float, merchant: str, rng) -> str:
    return (f"Rs.{amt:.2f} spent on HDFC Bank Card x9012 at {merchant} on "
            f"{d:%Y-%m-%d}:{rng.randint(8, 22):02d}:{rng.randint(0, 59):02d}:11. "
            f"Avl Lmt: Rs.{rng.randint(80000, 150000):,}.00")


def sms_sbi(d: date, amt: float, payee: str, rng) -> str:
    return (f"Dear UPI user A/C X8832 debited by {amt:g} on date {d:%d%b%y} trf to {payee} "
            f"Refno {ref(rng)}. If not u? call 1800111109. -SBI")


def sms_icici(d: date, amt: float, payee: str, rng) -> str:
    return (f"ICICI Bank Acct XX219 debited for Rs {amt:.2f} on {d:%d-%b-%y}; {payee} credited. "
            f"UPI:{ref(rng)}. Call 18002662 for dispute. SMS BLOCK 219 to 9215676766.")


def sms_credit(d: date, amt: float, vpa: str, name: str, rng) -> str:
    return (f"Rs.{amt:.2f} credited to HDFC Bank A/c XX4521 on {d:%d-%m-%y} by VPA {vpa} "
            f"({name}) (UPI Ref No {ref(rng)})")


NOISE = [
    "123456 is your OTP for txn of Rs.2,499.00 at AMAZON. Valid 5 mins. Do not share. -HDFC Bank",
    "Get a pre-approved Personal Loan up to Rs 5,00,000 at 10.5% p.a. Apply now: hdfcbk.io/x1 T&C",
]


def build_sms(year: int, month: int, nov: bool, rng: random.Random) -> list[str]:
    def d(day: int) -> date:
        return date(year, month, day)

    msgs: list[tuple[date, str]] = []
    add = lambda day, s: msgs.append((d(day), s))

    # Subscriptions
    add(5, sms_hdfc_card(d(5), 649.0 if nov else 499.0, "NETFLIX.COM", rng))
    add(2, sms_hdfc_card(d(2), 1499.0, "CULTFIT HEALTHIFYME", rng))
    add(11, sms_hdfc_card(d(11), 119.0, "SPOTIFY INDIA", rng))
    # Food delivery: heavy, worse in Nov (drift)
    n_food = 16 if nov else 11
    max_day = 20 if nov else 30
    for _ in range(n_food):
        day = rng.randint(1, max_day)
        who = rng.choice(["Swiggy", "Zomato"])
        payee = "swiggy@icici" if who == "Swiggy" else "zomato-order@ptybl"
        amt = round(rng.uniform(280, 720), 2)
        add(day, rng.choice([sms_hdfc_upi, sms_icici])(d(day), amt, payee, rng))
    # Groceries
    for day, payee in [(3, "bigbasket@hdfcbank"), (12, "blinkit@axisbank"), (24, "DMART AVENUE")]:
        if nov and day > 20:
            day = 19
        amt = round(rng.uniform(900, 2100), 2)
        add(day, sms_sbi(d(day), amt, payee, rng) if "@" in payee
            else sms_hdfc_card(d(day), amt, payee, rng))
    # Travel / shopping / dining
    for day in (4, 9, 15) if nov else (4, 9, 15, 22, 27):
        add(day, sms_hdfc_upi(d(day), round(rng.uniform(180, 420), 2), "uber.india@axisbank", rng))
    add(8, sms_hdfc_card(d(8), round(rng.uniform(1200, 2600), 2), "AMAZON PAY INDIA", rng))
    add(16, sms_icici(d(16), round(rng.uniform(800, 1900), 2), "myntra@ybl", rng))
    add(13, sms_hdfc_card(d(13), round(rng.uniform(900, 1600), 2), "SOCIAL BANDRA", rng))
    add(18, sms_sbi(d(18), round(rng.uniform(400, 700), 2), "pvrinox@hdfcbank", rng))
    # Cryptic merchants (Oct: AI guesses wrong; Nov: learned rules fire)
    add(7, sms_hdfc_upi(d(7), 1240.0, "UPI/RAZ*PAYU8823", rng))
    add(14, sms_hdfc_card(d(14), 1860.0, "POS 4471 MUMBAI", rng))
    add(10, sms_icici(d(10), 645.0, "VPA ksh.store@okicici", rng))
    add(17, sms_sbi(d(17), 2000.0, "UPI/PAYTM*QR8812", rng))
    add(6, sms_hdfc_upi(d(6), 3500.0, "IMPS/P2A/RMKCLASSES", rng))
    if not nov:
        add(26, sms_hdfc_upi(d(26), 980.0, "UPI/RAZ*PAYU8823", rng))
        add(28, sms_hdfc_card(d(28), 1320.0, "POS 4471 MUMBAI", rng))
    # Credits
    add(20 if nov else 21, sms_credit(d(20 if nov else 21), 1500.0, "rahul.k@okaxis",
                                      "RAHUL KUMAR", rng))
    add(12, sms_credit(d(12), 349.0, "amazonrefunds@apl", "AMAZON SELLER SERVICES", rng))

    msgs.sort(key=lambda m: m[0])
    lines = [m[1] for m in msgs]
    lines.insert(len(lines) // 3, NOISE[0])
    lines.insert(2 * len(lines) // 3, NOISE[1])
    return lines


# ---------------------------------------------------------------- statement (Kotak salary a/c)
def statement_rows(year: int, month: int, nov: bool) -> list[tuple[date, str, float, str]]:
    """(date, narration, amount, 'Dr'|'Cr')."""
    m = month
    rows = [
        (date(year, m, 1), "NEFT/ACME TECHNOLOGIES PVT LTD/SALARY OCT" if not nov
         else "NEFT/ACME TECHNOLOGIES PVT LTD/SALARY NOV", 85000.0, "Cr"),
        (date(year, m, 2), "NEFT/R SHARMA/RENT", 22000.0, "Dr"),
        (date(year, m, 5), "ACH D-BAJAJFIN-PL0098812", 4500.0, "Dr"),
        (date(year, m, 7), "NEFT/BBPS/ADANIELEC/1029384", 1840.0 if not nov else 1610.0, "Dr"),
        (date(year, m, 8), "BIL/AIRTEL POSTPAID/9820XXXX", 799.0, "Dr"),
        (date(year, m, 10), "ACH D-ICICI PRU MF SIP", 5000.0, "Dr"),
        (date(year, m, 3), "IMPS/TRF TO HDFC XX4521/SELF", 20000.0, "Dr"),
        (date(year, m, 12), "ATM WDL/KOTAK ATM ANDHERI", 3000.0, "Dr"),
        (date(year, m, 14), "BIL/MAHANAGAR GAS", 640.0, "Dr"),
        (date(year, m, 15), "UPI/HPCL PETROL PUMP/hpcl@ybl", 1800.0, "Dr"),
        (date(year, m, 16), "INT.PD/SB INTEREST", 212.0 if not nov else 198.0, "Cr"),
        (date(year, m, 18), "UPI/APOLLO PHARMACY/apollo@hdfcbank", 780.0, "Dr"),
        (date(year, m, 19), "BIL/TATA PLAY DTH", 350.0, "Dr"),
        (date(year, m, 6), "UPI/RAZ*PAYU8823", 860.0, "Dr"),
        (date(year, m, 11), "POS 4471 MUMBAI", 1150.0, "Dr"),
    ]
    if not nov:
        rows += [
            (date(year, m, 20), "ACH D-LIC OF INDIA PREMIUM", 3200.0, "Dr"),
            (date(year, m, 22), "UPI/DMART/dmart@ybl", 2340.0, "Dr"),
            (date(year, m, 23), "UPI/IRCTC/irctc@sbi", 1645.0, "Dr"),
            (date(year, m, 24), "IMPS/P2A/RMKCLASSES", 3500.0, "Dr"),
            (date(year, m, 25), "UPI/ZOMATO/zomato-order@ptybl", 520.0, "Dr"),
            (date(year, m, 26), "NEFT/MOM/TRANSFER", 5000.0, "Dr"),
            (date(year, m, 27), "UPI/RELIANCE DIGITAL", 2899.0, "Dr"),
            (date(year, m, 28), "UPI/PAYTM*QR8812", 1500.0, "Dr"),
            (date(year, m, 29), "BIL/BESCOM WATER", 300.0, "Dr"),
            (date(year, m, 29), "UPI/SWIGGY INSTAMART/swiggy@icici", 845.0, "Dr"),
            (date(year, m, 30), "CASH DEP/CDM ANDHERI", 2000.0, "Cr"),
            (date(year, m, 31), "UPI/BOOKMYSHOW/bms@icici", 760.0, "Dr"),
            (date(year, m, 31), "VPA ksh.store@okicici", 410.0, "Dr"),
            (date(year, m, 30), "UPI/CROMA/croma@hdfcbank", 1299.0, "Dr"),
            (date(year, m, 21), "NEFT/HDFC ERGO HEALTH", 1000.0, "Dr"),
        ]
    else:
        rows += [
            (date(year, m, 4), "UPI/DMART/dmart@ybl", 2120.0, "Dr"),
            (date(year, m, 9), "IMPS/P2A/RMKCLASSES", 3500.0, "Dr"),
            (date(year, m, 13), "UPI/PAYTM*QR8812", 1700.0, "Dr"),
            (date(year, m, 17), "VPA ksh.store@okicici", 520.0, "Dr"),
            (date(year, m, 20), "NEFT/MOM/TRANSFER", 5000.0, "Dr"),
            (date(year, m, 20), "NEFT/HDFC ERGO HEALTH", 1000.0, "Dr"),
        ]
    rows.sort(key=lambda r: r[0])
    return rows


def fmt_date(d: date, i: int) -> str:
    """Mixed formats on purpose."""
    return [f"{d:%d/%m/%Y}", f"{d:%d-%b-%y}", f"{d:%d %b %Y}", f"{d:%Y-%m-%d}"][i % 4]


def with_balance(rows, opening: float):
    bal, out = opening, []
    for r in rows:
        bal += r[2] if r[3] == "Cr" else -r[2]
        out.append((*r, round(bal, 2)))
    return out, round(bal, 2)


OPENING = {"oct": 48210.55}


def csv_oct(rows) -> str:
    buf = io.StringIO()
    buf.write("Kotak Mahindra Bank\nAccount Statement\nAccount No:,XXXXXX7781\n"
              "Period:,01-10-2026 to 31-10-2026\n\n")
    w = csv.writer(buf)
    w.writerow(["Sl. No.", "Txn Date", "Value Date", "Narration", "Chq / Ref No.",
                "Withdrawal Amt.", "Deposit Amt.", "Balance"])
    for i, (d, desc, amt, drcr, bal) in enumerate(rows):
        a = f"{amt:,.2f}"
        w.writerow([i + 1, fmt_date(d, i), f"{d:%d/%m/%Y}", desc, f"REF{100000 + i}",
                    a if drcr == "Dr" else "", a if drcr == "Cr" else "", f"{bal:,.2f}"])
    buf.write("\n** This is a computer generated statement **\n")
    return buf.getvalue()


def csv_nov(rows) -> str:
    buf = io.StringIO()
    buf.write("KOTAK MAHINDRA BANK LTD - SAVINGS ACCOUNT XXXXXX7781\n\n")
    w = csv.writer(buf)
    w.writerow(["Tran Date", "Particulars", "Amount (INR)", "Dr / Cr", "Balance (INR)"])
    for i, (d, desc, amt, drcr, bal) in enumerate(rows):
        w.writerow([fmt_date(d, i + 1), f"  {desc} ", f"{amt:,.2f}", drcr.upper(), f"{bal:,.2f}"])
    buf.write("Opening Balance and Closing Balance as per bank records\n")
    return buf.getvalue()


def pdf_nov(rows, opening: float, closing: float, path: Path) -> bool:
    try:
        from fpdf import FPDF
    except ImportError:
        print("skip statement_nov.pdf (install fpdf2: run via `cd backend && uv run python ...`)")
        return False
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Kotak Mahindra Bank - Statement of Account", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 5, "Account: XXXXXX7781   Period: 01-Nov-2026 to 20-Nov-2026",
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Opening Balance: {opening:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    with pdf.table(col_widths=(22, 88, 25, 25, 30),
                   text_align=("LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT")) as t:
        t.row(["Date", "Description", "Debit", "Credit", "Balance"])
        for d, desc, amt, drcr, bal in rows:
            a = f"{amt:,.2f}"
            t.row([f"{d:%d-%m-%Y}", desc, a if drcr == "Dr" else "", a if drcr == "Cr" else "",
                   f"{bal:,.2f}"])
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, f"Closing Balance: {closing:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))
    return True


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    (OUT / "sms_oct.txt").write_text("\n\n".join(build_sms(2026, 10, False, rng)) + "\n")
    (OUT / "sms_nov.txt").write_text("\n\n".join(build_sms(2026, 11, True, rng)) + "\n")

    oct_rows, oct_close = with_balance(statement_rows(2026, 10, False), OPENING["oct"])
    nov_rows, nov_close = with_balance(statement_rows(2026, 11, True), oct_close)
    (OUT / "statement_oct.csv").write_text(csv_oct(oct_rows))
    (OUT / "statement_nov.csv").write_text(csv_nov(nov_rows))
    pdf_nov(nov_rows, oct_close, nov_close, OUT / "statement_nov.pdf")

    for f in sorted(OUT.iterdir()):
        print(f"{f.name:22} {f.stat().st_size:>7} bytes")


if __name__ == "__main__":
    main()
