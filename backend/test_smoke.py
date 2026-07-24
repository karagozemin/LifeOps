"""
Zero-dependency smoke test - exercises the pipeline directly, no server.
Run:  python test_smoke.py
Goal: prove the deterministic fallback yields a guaranteed schema without an LLM.
"""
from __future__ import annotations

import base64

from app.pipeline import process, process_multi
from app.schema import LifeOpsResult

CASES = {
    "license": "Driver's License. Expiry Date: March 14, 2027.",
    "warranty": "Headphone warranty ends in 39 days. Device value 120 USD.",
    "subscription": "StreamPlus trial converts to a 19.99 USD monthly plan in 3 days.",
    "bill": "Electricity bill due 07/29/2026, amount 45.00 USD, 5% late fee.",
    "passport": "Passport expiry 2026-11-05, Schengen travel 2026-10-20.",
}


def main():
    ok = 0
    for name, text in CASES.items():
        result = process(text)
        # Schema guarantee: Pydantic validation
        LifeOpsResult(**result)
        ob = result["obligations"][0]
        ics_ok = bool(result["ics_base64"]) and base64.b64decode(result["ics_base64"]).startswith(b"BEGIN:VCALENDAR")
        print(f"OK  {name:12s} | type={result['document_type']:16s} "
              f"| due={ob['due_date']} | risk=${ob['money_at_risk_usd']:<7} "
              f"| .ics={'OK' if ics_ok else 'MISSING'} | conf={result['confidence']}")
        assert ics_ok, f"{name}: .ics not generated"
        ok += 1

    # ---- multi_audit: 3 documents in one payload -> ONE merged audit ----
    bundle = "\n---\n".join([
        CASES["passport"],
        CASES["subscription"],
        CASES["bill"],
    ])
    multi = process_multi(bundle)
    LifeOpsResult(**multi)
    assert multi["document_type"] == "multi", "multi_audit: wrong document_type"
    assert multi["documents_scanned"] == 3, f"multi_audit: expected 3 docs, got {multi['documents_scanned']}"
    assert len(multi["obligations"]) >= 3, "multi_audit: obligations not merged"
    # urgency ordering: most urgent first
    days = [o["days_remaining"] for o in multi["obligations"]]
    assert days == sorted(days), "multi_audit: obligations not sorted by urgency"
    # aggregated risk = sum of parts
    total = round(sum(o["money_at_risk_usd"] for o in multi["obligations"]), 2)
    assert multi["total_money_at_risk_usd"] == total, "multi_audit: total risk mismatch"
    ics_ok = base64.b64decode(multi["ics_base64"]).startswith(b"BEGIN:VCALENDAR")
    assert ics_ok, "multi_audit: combined .ics not generated"
    print(f"OK  multi_audit  | docs={multi['documents_scanned']} "
          f"| obligations={len(multi['obligations'])} "
          f"| total_risk=${multi['total_money_at_risk_usd']} | .ics=OK")
    ok += 1

    print(f"\nPASS: {ok}/{len(CASES) + 1} scenarios produced a guaranteed schema + valid .ics (no LLM).")


if __name__ == "__main__":
    main()
