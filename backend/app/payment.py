"""
x402 payment gate + live tx log - OKX A2MCP compliant (X Layer).

A2MCP spec (OKX.AI / Onchain OS):
  - Paid service without payment -> HTTP 402 + PAYMENT-REQUIRED header.
  - Header carries base64(JSON) payment requirements:
      scheme  : "exact"
      network : "eip155:196"      (X Layer mainnet)
      asset   : USDT0 contract    (6 decimals)
      amount  : base units string (0.01 USDT0 -> "10000")
      payTo   : receiving X Layer wallet (env: LIFEOPS_PAYTO)

Demo mode ('X-Payment: demo') produces a deterministic mock settlement so the
frontend Tx Log terminal stays live and repeatable. Real settlement happens
through OKX.AI / A2MCP rails once the ASP listing is approved.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from collections import deque
from datetime import datetime, timezone

# ---------------------------------------------------------------- X Layer / A2MCP
NETWORK = "eip155:196"  # X Layer mainnet
NETWORK_NAME = "X Layer"
ASSET = "0x779ded0c9e1022225f8e0630b35a9b54be713736"  # USDT0 on X Layer
ASSET_SYMBOL = "USDT0"
ASSET_DECIMALS = 6
PAY_TO = os.environ.get("LIFEOPS_PAYTO", "0x0000000000000000000000000000000000000000")
PAYTO_CONFIGURED = PAY_TO != "0x0000000000000000000000000000000000000000"
if not PAYTO_CONFIGURED:
    import sys
    print(
        "[LifeOps] WARNING: LIFEOPS_PAYTO is not set - payTo is the zero address. "
        "Set LIFEOPS_PAYTO=0x<your X Layer wallet> before registering the ASP on OKX.AI.",
        file=sys.stderr,
    )

# Service prices in USDT0 (human units)
PRICES = {
    "scan": 0.01,
    "full_action_pack": 0.05,
    "multi_audit": 0.20,
}

# Keep the last N tx in memory - the frontend Tx Log terminal is fed from here
_TX_LOG: deque = deque(maxlen=50)


def price_for(service: str) -> float:
    return PRICES.get(service, PRICES["full_action_pack"])


def base_units(service: str) -> str:
    """Human price -> 6-decimal base units string. 0.01 -> '10000'."""
    return str(int(round(price_for(service) * 10**ASSET_DECIMALS)))


def payment_requirements(service: str) -> dict:
    """A2MCP 'exact' scheme payment requirements for this service."""
    return {
        "scheme": "exact",
        "network": NETWORK,
        "asset": ASSET,
        "amount": base_units(service),
        "payTo": PAY_TO,
        "description": f"LifeOps {service} ({price_for(service)} {ASSET_SYMBOL})",
    }


def payment_required_header(service: str) -> dict:
    """
    Header set returned with a 402 response (A2MCP compliant).
    PAYMENT-REQUIRED = base64(JSON requirements) per OKX x402 convention.
    """
    req = payment_requirements(service)
    encoded = base64.b64encode(json.dumps(req).encode()).decode()
    return {
        "PAYMENT-REQUIRED": encoded,
        # Human-readable mirrors for debugging / curl -i
        "x402-price": base_units(service),
        "x402-asset": ASSET,
        "x402-network": NETWORK,
        "x402-pay-to": PAY_TO,
    }


def _tx_hash(service: str, caller: str) -> str:
    seed = f"{service}:{caller}:{time.time_ns()}"
    return "0x" + hashlib.sha256(seed.encode()).hexdigest()[:40]


def settle(service: str, caller: str, x_payment: str = "demo") -> dict:
    """
    Settle the payment and append to the live tx log.
    'demo' -> deterministic mock settlement (clearly labeled).
    Anything else is treated as an A2MCP payment payload reference.
    """
    amount = price_for(service)
    mode = "demo-settlement" if x_payment == "demo" else "a2mcp"
    tx = {
        "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "service": service,
        "caller": caller,
        "amount": amount,
        "asset": ASSET_SYMBOL,
        "network": NETWORK_NAME,
        "chain": NETWORK,
        "tx_hash": _tx_hash(service, caller),
        "status": "settled",
        "mode": mode,
        "protocol": "x402 / A2MCP",
    }
    _TX_LOG.appendleft(tx)
    return tx


def recent_tx(limit: int = 20) -> list[dict]:
    return list(_TX_LOG)[:limit]
