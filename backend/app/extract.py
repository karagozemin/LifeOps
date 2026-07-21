"""
Extraction layer.
Primary: OpenAI JSON mode (when OPENAI_API_KEY is set).
Fallback: zero-dependency deterministic regex + rule engine.
=> The demo NEVER breaks. Structured output is guaranteed even without an LLM.

Hardened fallback:
  - Context-aware date selection (never mistake an issue date for a deadline).
  - Smart amount detection (ignore reference / ID / policy numbers).
  - Passport/visa 6-month validity rule (travel-aware).
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

# Keywords that mark a date as a DEADLINE (we prefer these).
_DEADLINE_CUES = [
    "expir", "expiry", "expires", "due", "ends", "end date", "deadline",
    "valid until", "valid thru", "valid through", "renew", "cancel",
    "convert", "converts", "payment due", "last day", "before",
]
# Keywords that mark a date as NOT a deadline (issue/start dates -> penalized).
_ISSUE_CUES = [
    "issued", "issue date", "start date", "purchased", "purchase date",
    "activated", "activation", "date of birth", "dob", "born", "printed",
    "from", "since", "effective",
]


def _iter_dates(text: str):
    """
    Yield (iso_date, match_start, match_end) for every date found in text.
    Supports ISO, DD.MM.YYYY, MM/DD/YYYY, 'Month DD, YYYY', 'DD Month YYYY'.
    """
    t = text.lower()

    patterns = [
        # ISO 2027-03-14
        (r"(20\d{2})-(\d{1,2})-(\d{1,2})", lambda g: (int(g[0]), int(g[1]), int(g[2]))),
        # DD.MM.YYYY (day-first for dotted)
        (r"(\d{1,2})\.(\d{1,2})\.(20\d{2})", lambda g: (int(g[2]), int(g[1]), int(g[0]))),
        # MM/DD/YYYY (month-first for slashed)
        (r"(\d{1,2})/(\d{1,2})/(20\d{2})", lambda g: (int(g[2]), int(g[0]), int(g[1]))),
        # Month DD, YYYY
        (r"([a-z]{3,9})\s+(\d{1,2}),?\s+(20\d{2})",
         lambda g: (int(g[2]), _MONTHS.get(g[0], 0), int(g[1]))),
        # DD Month YYYY
        (r"(\d{1,2})\s+([a-z]{3,9})\s+(20\d{2})",
         lambda g: (int(g[2]), _MONTHS.get(g[1], 0), int(g[0]))),
    ]

    seen = set()
    for pat, conv in patterns:
        for m in re.finditer(pat, t):
            try:
                y, mo, d = conv(m.groups())
            except (ValueError, KeyError):
                continue
            if not (1 <= mo <= 12 and 1 <= d <= 31 and 2000 <= y <= 2099):
                continue
            try:
                iso = date(y, mo, d).isoformat()
            except ValueError:
                continue
            key = (iso, m.start())
            if key in seen:
                continue
            seen.add(key)
            yield iso, m.start(), m.end()


def _context_score(text: str, start: int, end: int) -> int:
    """
    Score a date by the words around it. Deadline cues -> +, issue cues -> -.
    A window of ~40 chars before the match is inspected.
    """
    lo = max(0, start - 40)
    window = text[lo:end].lower()
    score = 0
    for cue in _DEADLINE_CUES:
        if cue in window:
            score += 3
    for cue in _ISSUE_CUES:
        if cue in window:
            score -= 4
    return score


def _all_dates(text: str) -> list[str]:
    """All parsed ISO dates (deduped, chronological)."""
    out = {iso for iso, _, _ in _iter_dates(text)}
    return sorted(out)


def _pick_deadline(text: str) -> str | None:
    """
    Choose the most likely DEADLINE date.
    Strategy:
      1. Highest context score (deadline cues nearby win, issue cues lose).
      2. On a tie, prefer a future date over a past one.
      3. On a further tie, prefer the earliest upcoming date.
    Falls back to relative 'in N days' if no explicit date exists.
    """
    candidates = list(_iter_dates(text))
    today = date.today()

    if candidates:
        scored = []
        for iso, s, e in candidates:
            d = date.fromisoformat(iso)
            is_future = d >= today
            score = _context_score(text, s, e)
            # future dates get a small baseline boost (deadlines are usually ahead)
            if is_future:
                score += 1
            scored.append((score, is_future, d, iso))

        # Best score first; then future-first; then earliest date first.
        scored.sort(key=lambda x: (-x[0], not x[1], x[2]))
        best_score = scored[0][0]

        # If nothing has a positive deadline signal, prefer the earliest FUTURE
        # date (a plain deadline with no cue is still usually ahead of us).
        if best_score <= 1:
            future = sorted([x for x in scored if x[1]], key=lambda x: x[2])
            if future:
                return future[0][3]
        return scored[0][3]

    # relative: "in 39 days" / "39 days"
    m = re.search(r"(\d+)\s*days?", text.lower())
    if m:
        return (today + timedelta(days=int(m.group(1)))).isoformat()

    return None


# ---- type detection -----------------------------------------------------

def _detect_type(text: str) -> str:
    t = text.lower()
    rules = [
        ("visa", ["visa"]),
        ("passport", ["passport"]),
        ("drivers_license", ["driver", "driving license", "driving licence", "license", "licence"]),
        ("warranty", ["warranty", "guarantee"]),
        ("subscription", ["subscription", "trial", "free trial", "auto-renew", "auto renew", "renew your plan", "monthly plan"]),
        ("bill", ["bill", "invoice", "utility", "electricity", "statement", "amount due"]),
        ("appointment", ["appointment", "booking", "reservation", "inspection"]),
    ]
    for dtype, kws in rules:
        if any(kw in t for kw in kws):
            return dtype
    return "unknown"


# ---- amount detection ---------------------------------------------------

# Reference-like tokens whose trailing numbers must NOT be read as money.
_REF_CUES = re.compile(
    r"(no\.?|number|#|ref|reference|id|policy|account|acct|passport|licen[cs]e|"
    r"card|iban|invoice\s*no|class)\s*[:#]?\s*[a-z]?\d",
    re.IGNORECASE,
)


def _amount(text: str) -> float | None:
    """
    Find the most relevant monetary amount.
    - Requires a currency signal ($, USD, dollars) so IDs/dates aren't matched.
    - Skips numbers that belong to reference/ID tokens.
    - Prefers amounts tagged 'per month'/'monthly' for subscriptions, else the
      largest currency amount (usually the headline figure).
    """
    t = text.lower()

    # Mask reference numbers so they can't be captured as money.
    masked = _REF_CUES.sub(lambda m: " " * len(m.group(0)), t)

    money_re = re.compile(
        r"(?:\$|usd|us\$)\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?|[0-9]+(?:[.,][0-9]{1,2})?)"
        r"|([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:usd|dollars?|\$)"
    )

    found: list[tuple[float, int]] = []
    for m in money_re.finditer(masked):
        raw = m.group(1) or m.group(2)
        if raw is None:
            continue
        val = _to_float(raw)
        if val is None:
            continue
        found.append((val, m.start()))

    if not found:
        return None

    # Subscription: a 'per month' figure is the real recurring charge.
    if "month" in t:
        # look for a number immediately followed by monthly wording
        m = re.search(
            r"([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:usd|dollars?)?\s*(?:/|per\s+)?month",
            masked,
        )
        if m:
            v = _to_float(m.group(1))
            if v is not None:
                return v

    # Otherwise the largest currency amount is the headline figure.
    return max(v for v, _ in found)


def _to_float(raw: str) -> float | None:
    s = raw.strip()
    # 1,234.56 -> 1234.56 ; 1.234,56 -> 1234.56 ; 19,99 -> 19.99
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):      # european 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:                                # 1,234.56
            s = s.replace(",", "")
    elif "," in s:
        # decimal comma if exactly two trailing digits, else thousands sep
        if re.search(r",\d{2}$", s):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


# ---- entity helpers -----------------------------------------------------

def _holder(text: str) -> str | None:
    m = re.search(r"(?:holder|name)\s*[:\-]\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})", text)
    return m.group(1).strip() if m else None


def _provider(text: str) -> str | None:
    m = re.search(r"(?:provider|product|service|plan|company)\s*[:\-]\s*([A-Za-z0-9][\w \-]{1,40})", text)
    if m:
        return m.group(1).strip().rstrip(".")
    # brand-like: 'StreamPlus free trial'
    m = re.search(r"\b([A-Z][a-z]+(?:Plus|Pro|Prime|Max|Go))\b", text)
    return m.group(1) if m else None


def _reference(text: str) -> str | None:
    m = re.search(r"(?:no\.?|number|ref\.?|reference|policy)\s*[:#]?\s*([A-Z0-9\-]{4,})", text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _travel_date(text: str) -> str | None:
    """Detect a planned travel date (for the passport 6-month rule)."""
    m = re.search(r"(?:travel|trip|departure|flight|fly)\D{0,20}(20\d{2}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/20\d{2}|[a-z]{3,9}\s+\d{1,2},?\s+20\d{2})", text.lower())
    if not m:
        return None
    for iso, _, _ in _iter_dates(m.group(0)):
        return iso
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

_TITLES = {
    "drivers_license": "Driver's license renewal", "passport": "Passport renewal",
    "visa": "Visa renewal", "warranty": "Warranty expiration",
    "subscription": "Subscription cancellation window", "bill": "Bill payment due",
    "appointment": "Appointment", "unknown": "Deadline",
}


def _passport_validity_obligation(text: str, expiry_iso: str) -> dict | None:
    """
    Passport/visa 6-month validity rule.
    Many destinations require the passport to stay valid for 6 months AFTER
    travel. If a travel date is present and expiry is within 6 months of it,
    surface an EARLIER effective deadline: (travel_date + 6 months).
    """
    travel = _travel_date(text)
    if not travel:
        return None
    try:
        expiry = date.fromisoformat(expiry_iso)
        tdate = date.fromisoformat(travel)
    except ValueError:
        return None

    # 6 months after travel (approximate as 182 days)
    required_valid_until = tdate + timedelta(days=182)
    if expiry >= required_valid_until:
        return None  # passport is fine for the trip

    # Passport effectively "too short" for this trip -> act before travel.
    start_by = (tdate - timedelta(days=60)).isoformat()
    days_remaining = (tdate - date.today()).days
    return {
        "title": "Passport too short for planned travel (6-month rule)",
        "due_date": travel,
        "start_action_by": start_by,
        "risk_if_missed": (
            "Entry denied at the border: the destination requires the passport "
            "to be valid for 6 months beyond the travel date. Renew before the trip."
        ),
        "money_at_risk_usd": RISK_TABLE["passport"]["base"] + 200.0,
        "days_remaining": days_remaining,
        "steps": [
            "Check the destination's passport validity requirement",
            "Book an expedited passport renewal appointment",
            "Renew before the travel date",
        ],
    }


def _fallback_extract(text: str) -> dict:
    dtype = _detect_type(text)
    due = _pick_deadline(text) or (
        date.today() + timedelta(days=RISK_TABLE[dtype]["lead_days"] + 30)
    ).isoformat()
    amount = _amount(text)
    risk = estimate_risk(dtype, amount)

    due_d = datetime.strptime(due, "%Y-%m-%d").date()
    start_by = (due_d - timedelta(days=risk["lead_days"])).isoformat()
    days_remaining = (due_d - date.today()).days

    primary = {
        "title": _TITLES[dtype],
        "due_date": due,
        "start_action_by": start_by,
        "risk_if_missed": risk["risk_if_missed"],
        "money_at_risk_usd": risk["money_at_risk_usd"],
        "days_remaining": days_remaining,
        "steps": _STEPS[dtype],
    }

    obligations = [primary]

    # Passport/visa 6-month validity rule -> may add an earlier, sharper deadline.
    if dtype in ("passport", "visa"):
        extra = _passport_validity_obligation(text, due)
        if extra:
            obligations.insert(0, extra)

    # 3 reminders anchored on the *primary* deadline.
    r1 = start_by
    r2 = (due_d - timedelta(days=max(risk["lead_days"] // 2, 1))).isoformat()
    r3 = (due_d - timedelta(days=2)).isoformat()

    return {
        "document_type": dtype,
        "entities": {
            "expiry_date": due,
            "holder": _holder(text),
            "provider": _provider(text),
            "amount_usd": amount,
            "reference": _reference(text),
        },
        "obligations": obligations,
        "reminders": [r1, r2, r3],
        "confidence": 0.82 if dtype != "unknown" else 0.5,
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
            "Dates in ISO. Choose the DEADLINE date, never an issue/start date. "
            "For passports/visas, apply the destination 6-month validity rule when a "
            "travel date is present. Personal-life scope only; corporate/technical = unknown."
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
