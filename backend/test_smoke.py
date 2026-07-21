"""
Zero-dependency smoke test - exercises the pipeline directly, no server.
Run:  python test_smoke.py
Goal: prove the deterministic fallback yields a guaranteed schema without an LLM.
"""
from __future__ import annotations

import base64

from app.pipeline import process
from app.schema import LifeOpsResult

CASES = {
    "license": "Driver's License. Expiry Date: March 14, 2027.",
    "warranty": "Headphone warranty ends in 39 days. Device value 120 USD.",
    "subscription": "StreamPlus trial converts to a 19.99 USD monthly plan in 3 days.",
    "bill": "Electricity bill due 07/22/2026, amount 45.00 USD, 5% late fee.",
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

    print(f"\nPASS: {ok}/{len(CASES)} scenarios produced a guaranteed schema + valid .ics (no LLM).")


if __name__ == "__main__":
    main()
