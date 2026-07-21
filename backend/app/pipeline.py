"""
Core pipeline: extract -> normalize -> money -> .ics -> guaranteed schema.
Wires all parts together and returns a dict conforming to LifeOpsResult.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from .extract import extract
from .ics import build_ics
from .money import estimate_risk
from .schema import LifeOpsResult


def _safe_days_remaining(due: str) -> int:
    try:
        d = datetime.strptime(due, "%Y-%m-%d").date()
        return (d - date.today()).days
    except Exception:
        return 0


def _normalize(raw: dict) -> dict:
    """Force LLM or fallback output into the guaranteed schema + fill gaps."""
    dtype = raw.get("document_type", "unknown")
    entities = raw.get("entities", {}) or {}
    amount = entities.get("amount_usd")

    obligations = raw.get("obligations") or []
    fixed_obs = []
    total_risk = 0.0

    for ob in obligations:
        due = ob.get("due_date") or entities.get("expiry_date") or date.today().isoformat()
        risk = estimate_risk(dtype, amount)

        money = ob.get("money_at_risk_usd")
        if money is None:
            money = risk["money_at_risk_usd"]

        start_by = ob.get("start_action_by")
        if not start_by:
            try:
                dd = datetime.strptime(due, "%Y-%m-%d").date()
                start_by = (dd - timedelta(days=risk["lead_days"])).isoformat()
            except Exception:
                start_by = due

        fixed = {
            "title": ob.get("title") or "Deadline",
            "due_date": due,
            "start_action_by": start_by,
            "risk_if_missed": ob.get("risk_if_missed") or risk["risk_if_missed"],
            "money_at_risk_usd": float(money),
            "days_remaining": ob.get("days_remaining") if ob.get("days_remaining") is not None else _safe_days_remaining(due),
            "steps": ob.get("steps") or [],
        }
        total_risk += fixed["money_at_risk_usd"]
        fixed_obs.append(fixed)

    reminders = raw.get("reminders") or []

    return {
        "document_type": dtype,
        "entities": {
            "expiry_date": entities.get("expiry_date"),
            "holder": entities.get("holder"),
            "provider": entities.get("provider"),
            "amount_usd": amount,
            "reference": entities.get("reference"),
        },
        "obligations": fixed_obs,
        "reminders": reminders,
        "total_money_at_risk_usd": round(total_risk, 2),
        "confidence": float(raw.get("confidence", 0.7)),
    }


def process(text: str, with_ics: bool = True) -> dict:
    """Full run: text -> guaranteed LifeOpsResult dict."""
    raw = extract(text)
    norm = _normalize(raw)

    if with_ics and norm["obligations"]:
        norm["ics_base64"] = build_ics(norm["obligations"], norm["reminders"])
    else:
        norm["ics_base64"] = ""

    # Enforce the schema guarantee one final time via Pydantic
    result = LifeOpsResult(**norm)
    return result.model_dump()
