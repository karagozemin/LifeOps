"""
Pure-Python .ics (iCalendar) generator. Zero external dependencies.
Emits a VEVENT for every obligation and reminder, returns base64.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone


def _fold(line: str) -> str:
    """RFC5545 75-octet line folding."""
    if len(line) <= 75:
        return line
    out, chunk = [], line
    while len(chunk) > 75:
        out.append(chunk[:75])
        chunk = " " + chunk[75:]
    out.append(chunk)
    return "\r\n".join(out)


def _dt(date_iso: str) -> str:
    """YYYY-MM-DD -> YYYYMMDD (all-day event)."""
    return date_iso.replace("-", "")


def build_ics(obligations: list[dict], reminders: list[str], title_prefix: str = "LifeOps") -> str:
    """Build .ics from obligations + reminders, return a base64 string."""
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LifeOps//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for i, ob in enumerate(obligations):
        due = _dt(ob["due_date"])
        uid = f"lifeops-ob-{i}-{now}@lifeops"
        lines += [
            "BEGIN:VEVENT",
            _fold(f"UID:{uid}"),
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{due}",
            _fold(f"SUMMARY:{ob['title']} (deadline)"),
            _fold(f"DESCRIPTION:{ob['risk_if_missed']} | At risk: ${ob['money_at_risk_usd']}"),
            "BEGIN:VALARM",
            "TRIGGER:-P7D",
            "ACTION:DISPLAY",
            _fold(f"DESCRIPTION:{ob['title']} - 7 days left"),
            "END:VALARM",
            "END:VEVENT",
        ]

    for j, rem in enumerate(reminders):
        uid = f"lifeops-rem-{j}-{now}@lifeops"
        lines += [
            "BEGIN:VEVENT",
            _fold(f"UID:{uid}"),
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{_dt(rem)}",
            _fold(f"SUMMARY:{title_prefix} reminder"),
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    raw = "\r\n".join(lines).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")
