"""Real TravelPlanner -> LifeOps x402 payment demo using Onchain OS."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_URL = os.getenv("LIFEOPS_API_BASE", "http://127.0.0.1:8000").rstrip("/")


def _cli() -> str:
    found = shutil.which("onchainos")
    fallback = Path.home() / ".local" / "bin" / "onchainos"
    if found:
        return found
    if fallback.is_file():
        return str(fallback)
    raise RuntimeError("onchainos CLI was not found. Install OKX Onchain OS first.")


def _invoke(arguments: list[str], expected_codes: set[int] = {0}) -> tuple[int, dict]:
    completed = subprocess.run(arguments, text=True, capture_output=True, check=False)
    output = completed.stdout.strip() or completed.stderr.strip()
    try:
        envelope = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Onchain OS returned non-JSON output: {output[:300]}") from exc
    if completed.returncode not in expected_codes:
        raise RuntimeError(envelope.get("error") or output)
    return completed.returncode, envelope


def _field(data: dict, *names: str):
    for name in names:
        if name in data:
            return data[name]
    return None


def main() -> None:
    document = (
        "PASSPORT - Holder: Alex Morgan. Passport No: U12345678. "
        "Expiry Date: 2026-11-05. Planned travel 2026-10-20, "
        "Schengen area (6-month validity rule)."
    )
    parameters = [
        "--param", f"text={document}",
        "--param", "service=full_action_pack",
        "--param", "caller=TravelPlanner-Agent-v2",
    ]
    binary = _cli()

    print("TravelPlanner -> LifeOps")
    print("1. Requesting an unsigned x402 quote...")
    _, quote_envelope = _invoke([
        binary, "payment", "quote", f"{BASE_URL}/scan", "--method", "POST", *parameters
    ])
    quote = quote_envelope.get("data", {})
    payment_id = _field(quote, "paymentId", "payment_id")
    if not payment_id:
        raise RuntimeError(f"Quote did not return a paymentId: {quote}")

    print(json.dumps(quote, ensure_ascii=False, indent=2))
    print("\n2. Preparing the payment confirmation...")
    pay_command = [binary, "payment", "pay", "--payment-id", str(payment_id)]
    code, confirmation = _invoke(pay_command, expected_codes={0, 2})
    if code == 2:
        message = confirmation.get("message") or confirmation.get("data", {}).get("message")
        print(message or "Payment confirmation required.")
        answer = input("Type YES to sign and pay, or anything else to cancel: ").strip()
        if answer != "YES":
            print("Cancelled before signing. No payment was sent.")
            return
        _, paid_envelope = _invoke([*pay_command, "--yes"])
    else:
        paid_envelope = confirmation

    paid = paid_envelope.get("data", {})
    if paid.get("status") != "success":
        raise RuntimeError(f"Payment did not complete: {json.dumps(paid, ensure_ascii=False)}")

    print("\n3. Real settlement receipt")
    print(json.dumps(_field(paid, "decodedReceipt", "decoded_receipt"), ensure_ascii=False, indent=2))
    print(f"Transaction: {_field(paid, 'txHash', 'tx_hash')}")

    merchant = paid.get("result", {})
    result = merchant.get("result", {}) if isinstance(merchant, dict) else {}
    print("\n4. Guaranteed LifeOps JSON")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result:
        raise RuntimeError("The paid merchant response did not contain a LifeOps result.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, KeyboardInterrupt) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
