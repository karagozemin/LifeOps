"""
Pure-Python .ics (iCalendar) generator. Zero external dependencies.
Emits a VEVENT for every obligation and reminder, returns base64.
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone


def _fold(line: str) -> str:
    """RFC5545 75-octet line folding."""
    output: list[str] = []
    current = ""
    prefix = ""
    for char in line:
        if len((prefix + current + char).encode("utf-8")) > 75 and current:
            output.append(prefix + current)
            current = char
            prefix = " "
        else:
            current += char
    output.append(prefix + current)
    return "\r\n".join(output)


def _escape(value: object) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


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
        uid_seed = f"{ob['title']}:{ob['due_date']}:{i}".encode("utf-8")
        uid = f"lifeops-ob-{hashlib.sha256(uid_seed).hexdigest()[:20]}@lifeops"
        lines += [
            "BEGIN:VEVENT",
            _fold(f"UID:{uid}"),
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{due}",
            _fold(f"SUMMARY:{_escape(ob['title'])} (deadline)"),
            _fold(f"DESCRIPTION:{_escape(ob['risk_if_missed'])} | At risk: ${ob['money_at_risk_usd']}"),
            "BEGIN:VALARM",
            "TRIGGER:-P7D",
            "ACTION:DISPLAY",
            _fold(f"DESCRIPTION:{_escape(ob['title'])} - 7 days left"),
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
            _fold(f"SUMMARY:{_escape(title_prefix)} reminder"),
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    raw = ("\r\n".join(lines) + "\r\n").encode("utf-8")
    return base64.b64encode(raw).decode("ascii")
