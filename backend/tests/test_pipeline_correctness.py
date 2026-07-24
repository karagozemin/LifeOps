from __future__ import annotations

import base64
from datetime import date, timedelta

from app.extract import _add_months
from app.ics import build_ics
from app.pipeline import _normalize, process


def test_text_without_a_deadline_does_not_fabricate_one():
    result = process("This is a personal note about buying groceries tomorrow.")
    assert result["document_type"] == "unknown"
    assert result["obligations"] == []
    assert result["total_money_at_risk_usd"] == 0
    assert result["ics_base64"] == ""
    assert "deadline_not_found" in result["warnings"]


def test_issue_date_is_not_selected_over_expiry_date():
    result = process(
        "Driver license issued 2024-01-10. The license expires 2027-03-14."
    )
    assert result["obligations"][0]["due_date"] == "2027-03-14"
    assert result["entities"]["expiry_date"] == "2027-03-14"


def test_bill_risk_uses_disclosed_fee_not_an_invented_penalty():
    result = process("Electricity bill due 07/29/2026. Amount 45 USD. A 5% late fee applies.")
    obligation = result["obligations"][0]
    assert obligation["money_at_risk_usd"] == 2.25
    assert obligation["money_at_risk_is_estimate"] is False
    assert obligation["risk_basis"] == "Disclosed late fee: $45.00 x 5%"


def test_subscription_risk_is_the_next_charge_not_twelve_months():
    result = process("StreamPlus trial ends in 3 days and converts to 19.99 USD per month.")
    assert result["total_money_at_risk_usd"] == 19.99


def test_passport_travel_risk_is_not_double_counted():
    result = process(
        "Passport expiry 2026-11-05. Planned travel: 2026-10-20, "
        "destination Schengen area (6-month validity rule)."
    )
    assert len(result["obligations"]) == 2
    assert result["total_money_at_risk_usd"] == 300
    assert sum(item["money_at_risk_usd"] for item in result["obligations"]) == 300


def test_six_month_rule_uses_calendar_months():
    assert _add_months(date(2026, 8, 31), 6) == date(2027, 2, 28)


def test_overdue_status_and_past_reminders_are_explicit():
    yesterday = date.today() - timedelta(days=1)
    result = process(f"Electricity bill due {yesterday.isoformat()}, amount 20 USD.")
    assert result["obligations"][0]["status"] == "overdue"
    assert result["reminders"] == []
    assert "deadline_overdue" in result["warnings"]


def test_evidence_quotes_are_verbatim_source_text():
    text = "Warranty ends on 2027-09-01. Device value is 120 USD."
    result = process(text)
    assert result["evidence"]
    normalized = " ".join(text.split())
    assert all(item["source_text"] in normalized for item in result["evidence"])


def test_normalizer_rejects_hallucinated_evidence_and_bad_dates():
    normalized = _normalize(
        {
            "document_type": "made_up_type",
            "obligations": [{"due_date": "tomorrow", "money_at_risk_usd": -50}],
            "evidence": [{"field": "deadline", "value": "tomorrow", "source_text": "Not in source"}],
            "confidence": 4,
        },
        "Actual source",
    )
    assert normalized["document_type"] == "unknown"
    assert normalized["obligations"] == []
    assert normalized["evidence"] == []
    assert normalized["confidence"] == 1
    assert "invalid_deadline" in normalized["warnings"]


def test_ics_escapes_text_and_folds_by_utf8_octets():
    title = "Renew, verify; and review \\ " + "İstanbul " * 12
    encoded = build_ics(
        [{
            "title": title,
            "due_date": "2027-03-14",
            "risk_if_missed": "Line one\nLine two, with semicolon;",
            "money_at_risk_usd": 10,
        }],
        [],
    )
    raw = base64.b64decode(encoded)
    text = raw.decode("utf-8")
    assert "Renew\\, verify\\; and review \\\\" in text
    assert "Line one\\nLine two\\, with semicolon\\;" in text
    assert raw.endswith(b"\r\n")
    assert all(len(line) <= 75 for line in raw.split(b"\r\n") if line)
