from pathlib import Path

from app.engines.parse import (
    detect_kind,
    parse_csv,
    parse_pdf,
    parse_sms,
)

SAMPLES = Path(__file__).resolve().parents[2] / "frontend" / "public" / "samples"


def check_standardized_rows(rows):
    assert rows
    for row in rows:
        assert set(row) == {"date", "amount", "direction", "raw_desc"}
        assert row["direction"] in {"dr", "cr"}
        assert row["amount"] > 0
        assert row["raw_desc"]
        assert len(row["date"]) == 10


def test_csv_statement_parser():
    data = (SAMPLES / "statement_nov.csv").read_bytes()
    rows = parse_csv(data)

    assert len(rows) == 21
    check_standardized_rows(rows)


def test_sms_statement_parser(monkeypatch):
    from app.parsers import sms_parser
    monkeypatch.setattr(sms_parser, "_extract_llm", lambda text: None)
    text = (SAMPLES / "sms_nov.txt").read_text()
    rows = parse_sms(text)

    assert len(rows) == 32
    check_standardized_rows(rows)


def test_pdf_statement_parser_and_reconciliation():
    data = (SAMPLES / "statement_nov.pdf").read_bytes()
    rows, reconciliation = parse_pdf(data)

    assert len(rows) == 21
    check_standardized_rows(rows)
    assert reconciliation["ok"] is True
    assert reconciliation["opening"] == 47485.55
    assert reconciliation["closing"] == 56354.55
    assert reconciliation["computed_closing"] == 56354.55


def test_file_type_detection():
    pdf = (SAMPLES / "statement_nov.pdf").read_bytes()
    csv = (SAMPLES / "statement_nov.csv").read_bytes()
    sms = (SAMPLES / "sms_nov.txt").read_bytes()

    assert detect_kind("statement.pdf", pdf) == "pdf"
    assert detect_kind("statement.csv", csv) == "csv"
    assert detect_kind("messages.txt", sms) == "sms"
