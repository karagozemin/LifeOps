"""
money_at_risk rule engine.
Computes the monetary cost of missing a deadline, based on document type.
Rule-based baseline + adjustment from any extracted amount.
"""
from __future__ import annotations

# Per-document-type baseline risk (USD) and default lead-time window (days)
RISK_TABLE = {
    "drivers_license": {"base": 150.0, "lead_days": 45,
                        "risk": "Fines for driving on an expired license + loss of driving ability"},
    "passport": {"base": 300.0, "lead_days": 60,
                 "risk": "Trip cancellation + expedited passport renewal fees"},
    "visa": {"base": 500.0, "lead_days": 60,
             "risk": "Entry denial + forfeited flights and accommodation"},
    "warranty": {"base": 120.0, "lead_days": 30,
                 "risk": "Falling out of warranty and paying full replacement cost"},
    "subscription": {"base": 20.0, "lead_days": 3,
                     "risk": "Unwanted automatic charge"},
    "bill": {"base": 25.0, "lead_days": 5,
             "risk": "Late-payment interest + service interruption"},
    "appointment": {"base": 50.0, "lead_days": 3,
                    "risk": "Missed appointment + rescheduling penalty"},
    "unknown": {"base": 50.0, "lead_days": 14,
                "risk": "Risk of missing a deadline"},
}


def estimate_risk(doc_type: str, amount_usd: float | None = None) -> dict:
    """Return a risk profile from document type + optional amount."""
    profile = RISK_TABLE.get(doc_type, RISK_TABLE["unknown"])
    money = profile["base"]

    if amount_usd is not None:
        if doc_type == "subscription":
            # Unwanted annual charge risk ~ 12 months
            money = round(amount_usd * 12, 2)
        elif doc_type == "bill":
            # 5% late fee + baseline interruption risk
            money = round(amount_usd * 0.05 + profile["base"], 2)
        elif doc_type == "warranty":
            # Out of warranty = the device itself
            money = round(amount_usd, 2)

    return {
        "money_at_risk_usd": money,
        "lead_days": profile["lead_days"],
        "risk_if_missed": profile["risk"],
    }
