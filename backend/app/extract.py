"""
Extraction layer.
Primary: OpenAI JSON mode (when OPENAI_API_KEY is set).
Fallback: zero-dependency deterministic regex + rule engine.
=> The demo NEVER breaks. Structured output is guaranteed even without an LLM.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta

from .money import RISK_TABLE, estimate_risk

# ---- date helpers -------------------------------------------------------

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def _parse_date(text: str) -> str | None:
    """Extract the first meaningful date from text as ISO (YYYY-MM-DD)."""
    t = text.lower()

    # ISO: 2027-03-14
    m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", t)
    if m:
        y, mo, d = map(int, m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}"

    # MM/DD/YYYY or DD.MM.YYYY (assume day-first for dotted, month-first for slashed)
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(20\d{2})", t)
    if m:
        d, mo, y = map(int, m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}"
    m = re.search(r"(\d{1,2})/(\d{1,2})/(20\d{2})", t)
    if m:
        mo, d, y = map(int, m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}"

    # "March 14, 2027" / "14 Mar 2027"
    m = re.search(r"([a-z]+)\s+(\d{1,2}),?\s+(20\d{2})", t)
    if m and _MONTHS.get(m.group(1)):
        mo = _MONTHS[m.group(1)]
        d = int(m.group(2))
        y = int(m.group(3))
        return f"{y:04d}-{mo:02d}-{d:02d}"
    m = re.search(r"(\d{1,2})\s+([a-z]+)\s+(20\d{2})", t)
    if m and _MONTHS.get(m.group(2)):
        d = int(m.group(1))
        mo = _MONTHS[m.group(2)]
        y = int(m.group(3))
        return f"{y:04d}-{mo:02d}-{d:02d}"

    # "in 39 days" / "39 days"
    m = re.search(r"(\d+)\s*days?", t)
    if m:
        delta = int(m.group(1))
        target = date.today() + timedelta(days=delta)
        return target.isoformat()

    return None


def _detect_type(text: str) -> str:
    t = text.lower()
    rules = [
        ("visa", ["visa"]),
        ("passport", ["passport"]),
        ("drivers_license", ["driver", "driving license", "driving licence", "license", "licence"]),
        ("warranty", ["warranty", "guarantee"]),
        ("subscription", ["subscription", "trial", "free trial", "auto-renew", "renew your plan"]),
        ("bill", ["bill", "invoice", "utility", "electricity", "statement", "amount due"]),
        ("appointment", ["appointment", "booking", "reservation"]),
    ]
    for dtype, kws in rules:
        if any(kw in t for kw in kws):
            return dtype
    return "unknown"


def _amount(text: str) -> float | None:
    m = re.search(r"\$?\s*(\d+[.,]?\d*)\s*(usd|dollars?|\$)?", text.lower())
    if m and m.group(2):
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    return None


# ---- deterministic fallback --------------------------------------------

_STEPS = {
    "drivers_license": ["Prepare photo and medical report", "Book an appointment at the licensing office", "Pay the fee and complete the renewal"],
    "passport": ["Get a biometric photo", "Book an appointment", "Pay the fee and apply"],
    "visa": ["Gather the required documents", "Book a consulate appointment", "Submit application + biometrics"],
    "warranty": ["Locate your receipt", "Open a service claim", "Hand in the device"],
    "subscription": ["Open account settings", "Click the cancel link", "Save the cancellation confirmation"],
    "bill": ["Check the invoice amount", "Make the payment", "Save the receipt"],
    "appointment": ["Prepare the required paperwork", "Plan your transport", "Arrive on time"],
    "unknown": ["Review the document", "Add the deadline to your calendar", "Take the required action"],
}


def _fallback_extract(text: str) -> dict:
    dtype = _detect_type(text)
    due = _parse_date(text) or (date.today() + timedelta(days=RISK_TABLE[dtype]["lead_days"] + 30)).isoformat()
    amount = _amount(text)
    risk = estimate_risk(dtype, amount)

    due_d = datetime.strptime(due, "%Y-%m-%d").date()
    start_by = (due_d - timedelta(days=risk["lead_days"])).isoformat()
    days_remaining = (due_d - date.today()).days

    title_map = {
        "drivers_license": "Driver's license renewal", "passport": "Passport renewal",
        "visa": "Visa renewal", "warranty": "Warranty expiration",
        "subscription": "Subscription cancellation window", "bill": "Bill payment due",
        "appointment": "Appointment", "unknown": "Deadline",
    }

    obligation = {
        "title": title_map[dtype],
        "due_date": due,
        "start_action_by": start_by,
        "risk_if_missed": risk["risk_if_missed"],
        "money_at_risk_usd": risk["money_at_risk_usd"],
        "days_remaining": days_remaining,
        "steps": _STEPS[dtype],
    }

    # 3 reminders: start_by, midpoint, due-2days
    r1 = start_by
    r2 = (due_d - timedelta(days=max(risk["lead_days"] // 2, 1))).isoformat()
    r3 = (due_d - timedelta(days=2)).isoformat()

    return {
        "document_type": dtype,
        "entities": {
            "expiry_date": due,
            "holder": None,
            "provider": None,
            "amount_usd": amount,
            "reference": None,
        },
        "obligations": [obligation],
        "reminders": [r1, r2, r3],
        "confidence": 0.78 if dtype != "unknown" else 0.5,
    }


# ---- LLM path (optional) -----------------------------------------------

def _llm_extract(text: str) -> dict | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        today = date.today().isoformat()
        sys = (
            "You are a personal-life document analysis engine. Return JSON ONLY. "
            f"Today is {today}. Fields: document_type (drivers_license|passport|visa|warranty|"
            "subscription|bill|appointment|unknown), entities{expiry_date,holder,provider,"
            "amount_usd,reference}, obligations[{title,due_date,start_action_by,risk_if_missed,"
            "money_at_risk_usd,days_remaining,steps[]}], reminders[], confidence(0-1). "
            "Dates in ISO. Personal-life scope only; corporate/technical document = unknown."
        )
        resp = client.chat.completions.create(
            model=os.getenv("LIFEOPS_MODEL", "gpt-4o-mini"),
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": sys},
                      {"role": "user", "content": text}],
            temperature=0,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception:
        # If the LLM fails, silently fall back - the demo never breaks
        return None


def extract(text: str) -> dict:
    """Main entry: try the LLM, otherwise deterministic fallback."""
    return _llm_extract(text) or _fallback_extract(text)
