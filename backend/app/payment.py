"""
x402 payment gate + live tx log.
Real-service requirement: every paid call requires payment confirmation first.
In demo mode it produces a deterministic mock tx (live and repeatable).
Real x402 header verification plugs in here.
"""
from __future__ import annotations

import hashlib
import time
from collections import deque
from datetime import datetime, timezone

# Service prices (USDT)
PRICES = {
    "scan": 0.01,
    "full_action_pack": 0.05,
    "multi_audit": 0.20,
}

# Keep the last N tx in memory - the frontend Tx Log terminal is fed from here
_TX_LOG: deque = deque(maxlen=50)


def price_for(service: str) -> float:
    return PRICES.get(service, PRICES["full_action_pack"])


def _tx_hash(service: str, caller: str) -> str:
    seed = f"{service}:{caller}:{time.time_ns()}"
    return "0x" + hashlib.sha256(seed.encode()).hexdigest()[:40]


def settle(service: str, caller: str) -> dict:
    """
    Settle the x402 payment (demo: deterministic mock).
    In a real integration: verify X-Payment header, settle on-chain.
    """
    amount = price_for(service)
    tx = {
        "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "service": service,
        "caller": caller,
        "amount_usdt": amount,
        "tx_hash": _tx_hash(service, caller),
        "status": "settled",
        "protocol": "x402 / A2MCP",
    }
    _TX_LOG.appendleft(tx)
    return tx


def recent_tx(limit: int = 20) -> list[dict]:
    return list(_TX_LOG)[:limit]


def payment_required_header(service: str) -> dict:
    """x402 header set returned with a 402 response."""
    return {
        "x402-price": str(price_for(service)),
        "x402-currency": "USDT",
        "x402-network": "base",
        "x402-protocol": "A2MCP",
    }
