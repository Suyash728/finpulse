import json
from types import SimpleNamespace

import pytest

from app.engines import categorize as categorizer


class FakeQuery:
    def __init__(self, table, responses):
        self.table_name = table
        self.responses = responses
        self.filters = []

    def select(self, *_args):
        return self

    def eq(self, *args):
        self.filters.append(args)
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args):
        return self

    def execute(self):
        return SimpleNamespace(data=self.responses.get(self.table_name, []))


class FakeClient:
    def __init__(self, responses):
        self.responses = responses

    def table(self, name):
        return FakeQuery(name, self.responses)


@pytest.fixture
def sample_rows():
    return [
        {
            "date": "2026-11-01",
            "amount": 649,
            "direction": "dr",
            "raw_desc": "UPI/NETFLIX/netflix@icici",
            "merchant_norm": "netflix",
        },
        {
            "date": "2026-11-02",
            "amount": 500,
            "direction": "dr",
            "raw_desc": "UPI/DMART/dmart@ybl",
            "merchant_norm": "dmart",
        },
    ]


def test_exact_rule_has_priority_over_normalized_rule(monkeypatch, sample_rows):
    client = FakeClient({
        "category_rules": [
            {"match_type": "exact", "pattern": sample_rows[0]["raw_desc"], "category": "Shopping"},
            {"match_type": "normalized", "pattern": "netflix", "category": "Subscriptions"},
            {"match_type": "normalized", "pattern": "dmart", "category": "Groceries"},
        ],
    })
    monkeypatch.setattr("app.db.get_client", lambda: client)

    def unexpected_llm(*_args, **_kwargs):
        pytest.fail("LLM should not run when rules match every transaction")

    monkeypatch.setattr(categorizer.llm, "chat", unexpected_llm)

    result = categorizer.categorize(sample_rows)

    assert [row["category"] for row in result] == ["Shopping", "Groceries"]
    assert all(row["cat_source"] == "rule" for row in result)
    assert all(row["confidence"] == 1.0 for row in result)
    assert all(not row["needs_review"] for row in result)


def test_llm_receives_correction_examples_and_batches_rows(
    monkeypatch, sample_rows
):
    client = FakeClient({
        "category_rules": [],
        "transactions": [
            {
                "raw_desc": "UPI/SWIGGY",
                "merchant_norm": "swiggy",
                "category": "Food Delivery",
            }
        ],
    })
    monkeypatch.setattr("app.db.get_client", lambda: client)

    calls = []

    def fake_chat(messages, **kwargs):
        calls.append((messages, kwargs))
        return SimpleNamespace(
            text=json.dumps({
                "results": [
                    {"index": 0, "category": "Subscriptions", "confidence": 0.95},
                    {"index": 1, "category": "Groceries", "confidence": 0.65},
                ]
            })
        )

    monkeypatch.setattr(categorizer.llm, "chat", fake_chat)

    result = categorizer.categorize(sample_rows)

    assert len(calls) == 1
    assert "swiggy" in calls[0][0][1]["content"]
    assert len(json.loads(calls[0][0][1]["content"])["transactions"]) == 2
    assert result[0]["cat_source"] == "ai"
    assert result[0]["category"] == "Subscriptions"
    assert result[0]["confidence"] == 0.95
    assert result[0]["needs_review"] is False
    assert result[1]["category"] == "Groceries"
    assert result[1]["needs_review"] is True


def test_llm_failure_sends_rows_to_review(monkeypatch, sample_rows):
    monkeypatch.setattr(
        "app.db.get_client",
        lambda: FakeClient({"category_rules": [], "transactions": []}),
    )

    def fail(*_args, **_kwargs):
        raise categorizer.llm.AllTiersFailed("offline")

    monkeypatch.setattr(categorizer.llm, "chat", fail)

    result = categorizer.categorize(sample_rows)

    assert all(row["category"] == "Other" for row in result)
    assert all(row["confidence"] == 0.0 for row in result)
    assert all(row["needs_review"] for row in result)


def test_empty_input_does_not_connect_to_database(monkeypatch):
    def unexpected_db():
        pytest.fail("Database should not be accessed for empty input")

    monkeypatch.setattr("app.db.get_client", unexpected_db)

    assert categorizer.categorize([]) == []


def test_review_threshold_is_point_seven():
    assert categorizer.REVIEW_THRESHOLD == 0.7


def test_invalid_llm_category_is_sent_to_review(monkeypatch, sample_rows):
    monkeypatch.setattr(
        "app.db.get_client",
        lambda: FakeClient({"category_rules": [], "transactions": []}),
    )
    monkeypatch.setattr(
        categorizer.llm,
        "chat",
        lambda *_args, **_kwargs: SimpleNamespace(
            text='{"results":[{"index":0,"category":"FakeCategory","confidence":0.99}]}'
        ),
    )

    result = categorizer.categorize(sample_rows)

    assert result[0]["category"] == "Other"
    assert result[0]["confidence"] == 0.0
    assert result[0]["needs_review"] is True


@pytest.mark.parametrize("content", ['[]', '"invalid"', '123'])
def test_malformed_llm_json_structure_sends_rows_to_review(
    monkeypatch, sample_rows, content
):
    monkeypatch.setattr(
        "app.db.get_client",
        lambda: FakeClient({"category_rules": [], "transactions": []}),
    )
    monkeypatch.setattr(
        categorizer.llm,
        "chat",
        lambda *_args, **_kwargs: SimpleNamespace(text=content),
    )

    result = categorizer.categorize(sample_rows)

    assert all(row["category"] == "Other" for row in result)
    assert all(row["confidence"] == 0.0 for row in result)
    assert all(row["needs_review"] for row in result)
