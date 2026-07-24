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


def estimate_risk(
    doc_type: str,
    amount_usd: float | None = None,
    late_fee_percent: float | None = None,
) -> dict:
    """Return a conservative risk estimate with an explicit calculation basis."""
    profile = RISK_TABLE.get(doc_type, RISK_TABLE["unknown"])
    money = profile["base"]
    basis = f"LifeOps category benchmark for {doc_type.replace('_', ' ')}"
    is_estimate = True

    if amount_usd is not None:
        if doc_type == "subscription":
            money = round(amount_usd, 2)
            basis = f"Next disclosed subscription charge: ${money:.2f}"
            is_estimate = False
        elif doc_type == "bill":
            if late_fee_percent is not None:
                money = round(amount_usd * late_fee_percent / 100, 2)
                basis = f"Disclosed late fee: ${amount_usd:.2f} x {late_fee_percent:g}%"
                is_estimate = False
            else:
                basis = "Late-fee benchmark; no fee rate was found in the document"
        elif doc_type == "warranty":
            money = round(amount_usd, 2)
            basis = f"Disclosed replacement value: ${money:.2f}"
            is_estimate = False
        elif doc_type in ("passport", "visa", "drivers_license"):
            money = round(amount_usd, 2)
            basis = f"Disclosed amount exposed by the missed deadline: ${money:.2f}"
            is_estimate = False

    if doc_type == "unknown":
        money = 0.0
        basis = "No supported document type or monetary consequence detected"

    return {
        "money_at_risk_usd": money,
        "lead_days": profile["lead_days"],
        "risk_if_missed": profile["risk"],
        "risk_basis": basis,
        "money_at_risk_is_estimate": is_estimate,
    }
