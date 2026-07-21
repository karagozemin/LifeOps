"""
Use Case 6 - A2MCP proof.
Another agent (TravelPlanner) calls LifeOps via x402.
A real, outward-facing service: proof of agent-to-agent infrastructure.

Run:  python agent_call_demo.py
(The backend must be running on http://localhost:8000.)
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000"


def _post(path: str, payload: dict, headers: dict | None = None) -> tuple[int, dict, dict]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read()), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()), dict(e.headers)


def main():
    doc = (
        "PASSPORT - Holder: Alex Morgan. Passport No: U12345678. "
        "Expiry Date: 2026-11-05. Planned travel 2026-10-20, "
        "Schengen area (6-month validity rule)."
    )
    payload = {"text": doc, "service": "full_action_pack", "caller": "TravelPlanner-Agent-v2"}

    print("[TravelPlanner-Agent] calling LifeOps...\n")

    # 1) Unpaid call -> expect 402 + PAYMENT-REQUIRED header (A2MCP spec)
    status, body, headers = _post("/scan", payload)
    print(f"1. Unpaid call -> HTTP {status}")
    print(f"   {body.get('message', body)}")
    pr = headers.get("payment-required") or headers.get("PAYMENT-REQUIRED")
    if pr:
        import base64
        print(f"   PAYMENT-REQUIRED: {json.loads(base64.b64decode(pr))}")
    print()

    if status != 402:
        print("Expected 402 but got a different response.")
        sys.exit(1)

    # 2) Retry with x402 payment
    print("2. Settling payment via A2MCP (X Layer / USDT0)...")
    status, body, _ = _post("/scan", payload, headers={"X-Payment": "demo"})
    p = body["payment"]
    print(f"   -> HTTP {status} | tx: {p['tx_hash']} | {p['amount']} {p['asset']} on {p['network']}\n")

    result = body["result"]
    print("3. Guaranteed JSON returned by LifeOps:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\nTravelPlanner can now warn the user:")
    for ob in result["obligations"]:
        print(f"   - {ob['title']} - {ob['days_remaining']} days | at risk ${ob['money_at_risk_usd']}")
        print(f"     {ob['risk_if_missed']}")


if __name__ == "__main__":
    main()
