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

_SUPPORTED_TYPES = {
    "drivers_license", "passport", "visa", "warranty", "subscription",
    "bill", "appointment", "unknown",
}


def _safe_days_remaining(due: str) -> int:
    try:
        d = datetime.strptime(due, "%Y-%m-%d").date()
        return (d - date.today()).days
    except Exception:
        return 0


def _parse_iso(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _normalize(raw: dict, source_text: str = "") -> dict:
    """Force LLM or fallback output into the guaranteed schema + fill gaps."""
    dtype = str(raw.get("document_type", "unknown"))
    if dtype not in _SUPPORTED_TYPES:
        dtype = "unknown"
    entities = raw.get("entities", {}) or {}
    amount = entities.get("amount_usd")

    obligations = raw.get("obligations") or []
    if not isinstance(obligations, list):
        obligations = []
    fixed_obs = []
    total_risk = 0.0
    raw_warnings = raw.get("warnings") or []
    warnings = list(dict.fromkeys(raw_warnings if isinstance(raw_warnings, list) else []))

    for ob in obligations:
        if not isinstance(ob, dict):
            continue
        due = ob.get("due_date") or entities.get("expiry_date")
        due_date = _parse_iso(due)
        if due_date is None:
            if "invalid_deadline" not in warnings:
                warnings.append("invalid_deadline")
            continue
        due = due_date.isoformat()
        risk = estimate_risk(dtype, amount)

        # LLM output never determines money. A value is accepted only together
        # with the deterministic risk basis produced by our rule engine.
        money = ob.get("money_at_risk_usd") if ob.get("risk_basis") else None
        try:
            money = max(0.0, float(money)) if money is not None else risk["money_at_risk_usd"]
        except (TypeError, ValueError):
            money = risk["money_at_risk_usd"]

        start_by_date = _parse_iso(ob.get("start_action_by"))
        if start_by_date is None:
            start_by_date = due_date - timedelta(days=risk["lead_days"])
        days_remaining = (due_date - date.today()).days
        status = "overdue" if days_remaining < 0 else "due_soon" if days_remaining <= 14 else "upcoming"

        fixed = {
            "title": ob.get("title") or "Deadline",
            "due_date": due,
            "start_action_by": start_by_date.isoformat(),
            "risk_if_missed": ob.get("risk_if_missed") or risk["risk_if_missed"],
            "money_at_risk_usd": money,
            "days_remaining": days_remaining,
            "steps": ob.get("steps") or [],
            "status": status,
            "risk_basis": ob.get("risk_basis") or risk["risk_basis"],
            "money_at_risk_is_estimate": ob.get(
                "money_at_risk_is_estimate", risk["money_at_risk_is_estimate"]
            ),
        }
        total_risk += fixed["money_at_risk_usd"]
        fixed_obs.append(fixed)

    reminders = sorted({
        parsed.isoformat()
        for value in (raw.get("reminders") or [])
        if (parsed := _parse_iso(value)) is not None and parsed >= date.today()
    })

    evidence = []
    normalized_source = " ".join(source_text.split())
    for item in raw.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        quote = " ".join(str(item.get("source_text", "")).split())
        if not quote or (normalized_source and quote not in normalized_source):
            continue
        evidence.append({
            "field": str(item.get("field", "unknown")),
            "value": str(item.get("value", "")),
            "source_text": quote,
        })

    try:
        confidence = float(raw.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5

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
        "confidence": min(1.0, max(0.0, confidence)),
        "evidence": evidence,
        "warnings": warnings,
        "extraction_mode": raw.get("extraction_mode", "deterministic")
        if raw.get("extraction_mode") in {"deterministic", "llm"}
        else "deterministic",
    }


def process(text: str, with_ics: bool = True) -> dict:
    """Full run: text -> guaranteed LifeOpsResult dict."""
    raw = extract(text)
    norm = _normalize(raw, text)

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
    all_evidence: list[dict] = []
    all_warnings: list[str] = []
    extraction_modes: list[str] = []

    for doc in docs:
        raw = extract(doc)
        norm = _normalize(raw, doc)
        # Tag each obligation with its source document type for clarity.
        dtype = norm["document_type"]
        for ob in norm["obligations"]:
            ob["title"] = f"[{dtype}] {ob['title']}"
        all_obs.extend(norm["obligations"])
        all_rems.extend(norm["reminders"])
        confidences.append(norm["confidence"])
        doc_types.append(dtype)
        all_evidence.extend(norm["evidence"])
        all_warnings.extend(norm["warnings"])
        extraction_modes.append(norm["extraction_mode"])

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
        "evidence": all_evidence,
        "warnings": list(dict.fromkeys(all_warnings)),
        "extraction_mode": (
            "hybrid" if len(set(extraction_modes)) > 1
            else extraction_modes[0] if extraction_modes
            else "deterministic"
        ),
        "ics_base64": build_ics(all_obs, all_rems) if all_obs else "",
    }

    result = LifeOpsResult(**merged)
    return result.model_dump()
