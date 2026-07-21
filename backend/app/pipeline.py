"""
Core pipeline: extract -> normalize -> money -> .ics -> guaranteed schema.
Wires all parts together and returns a dict conforming to LifeOpsResult.

Also implements multi_audit: split a pasted bundle into individual documents,
run the full pipeline on each, and merge into a single audit result with one
combined .ics and an aggregated total_money_at_risk_usd.
"""
from __future__ import annotations

import re
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


# ---- multi_audit --------------------------------------------------------

# Explicit separators an agent/user can put between documents.
_EXPLICIT_SEP = re.compile(r"\n\s*(?:-{3,}|={3,}|\*{3,}|#{3,})\s*\n")


def split_documents(text: str) -> list[str]:
    """
    Split a pasted bundle into individual documents.
      1. Explicit separators (---, ===, ***, ###) always win.
      2. Otherwise, blank-line paragraphs are treated as candidate docs
         (very short fragments are merged into the previous block so a
         stray one-liner doesn't become its own 'document').
      3. Single-block text -> one document.
    """
    text = text.strip()
    if not text:
        return []

    parts = [p.strip() for p in _EXPLICIT_SEP.split(text) if p.strip()]
    if len(parts) > 1:
        return parts

    # Fallback: blank-line separated blocks
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) <= 1:
        return [text]

    merged: list[str] = []
    for b in blocks:
        # a fragment under 40 chars is most likely a continuation, not a doc
        if merged and len(b) < 40:
            merged[-1] = merged[-1] + "\n" + b
        else:
            merged.append(b)
    return merged


def process_multi(text: str) -> dict:
    """
    multi_audit: N documents in -> ONE merged audit out.
    - Each document runs through the full pipeline independently.
    - Obligations are merged and sorted by urgency (days_remaining asc).
    - money_at_risk is summed across all documents.
    - A single combined .ics covers every obligation + reminder.
    """
    docs = split_documents(text)

    if len(docs) <= 1:
        # Single doc -> behave exactly like full_action_pack (never worse).
        return process(text)

    all_obs: list[dict] = []
    all_rems: list[str] = []
    confidences: list[float] = []
    doc_types: list[str] = []

    for doc in docs:
        raw = extract(doc)
        norm = _normalize(raw)
        # Tag each obligation with its source document type for clarity.
        dtype = norm["document_type"]
        for ob in norm["obligations"]:
            ob["title"] = f"[{dtype}] {ob['title']}"
        all_obs.extend(norm["obligations"])
        all_rems.extend(norm["reminders"])
        confidences.append(norm["confidence"])
        doc_types.append(dtype)

    # Most urgent first - this is the audit's headline ordering.
    all_obs.sort(key=lambda o: o["days_remaining"])
    # Dedupe + sort reminders chronologically.
    all_rems = sorted(set(all_rems))

    total = round(sum(o["money_at_risk_usd"] for o in all_obs), 2)

    merged = {
        "document_type": "multi",
        "entities": {
            "expiry_date": all_obs[0]["due_date"] if all_obs else None,
            "holder": None,
            "provider": ", ".join(dict.fromkeys(doc_types)),  # unique, ordered
            "amount_usd": None,
            "reference": f"{len(docs)} documents audited",
        },
        "obligations": all_obs,
        "reminders": all_rems,
        "total_money_at_risk_usd": total,
        "confidence": round(min(confidences), 2) if confidences else 0.5,
        "documents_scanned": len(docs),
        "ics_base64": build_ics(all_obs, all_rems) if all_obs else "",
    }

    result = LifeOpsResult(**merged)
    return result.model_dump()
