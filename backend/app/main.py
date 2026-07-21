"""
LifeOps - FastAPI main application.
One service, one repo. Agent-consumable ASP.

Endpoints:
  GET  /                -> health + service catalog
  GET  /pricing         -> service prices (USDT)
  POST /scan            -> x402-paid document analysis (guaranteed JSON)
  GET  /tx              -> live tx log (feeds the frontend terminal)
  GET  /ics/{id}.ics    -> .ics file of a specific result (concurrency-safe)
  GET  /ics/latest.ics  -> .ics of the most recent result (demo convenience)
"""
from __future__ import annotations

import base64
import uuid
from collections import OrderedDict

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .payment import (ASSET_SYMBOL, NETWORK, NETWORK_NAME, PAY_TO,
                      PAYTO_CONFIGURED, PRICES, payment_required_header,
                      payment_requirements, price_for, recent_tx, settle)
from .pipeline import process, process_multi
from .schema import ScanRequest

app = FastAPI(
    title="LifeOps",
    version=__version__,
    description="Document to action. Deadline, money_at_risk and .ics in a single call. Agent-consumable ASP.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Result store: id -> result. Bounded LRU so memory stays flat.
# Fixes the single-slot race: concurrent users each get their own .ics URL.
_RESULTS: OrderedDict[str, dict] = OrderedDict()
_RESULTS_MAX = 200
_LATEST_ID: str | None = None


def _store_result(result: dict) -> str:
    global _LATEST_ID
    rid = uuid.uuid4().hex[:12]
    _RESULTS[rid] = result
    _RESULTS.move_to_end(rid)
    while len(_RESULTS) > _RESULTS_MAX:
        _RESULTS.popitem(last=False)
    _LATEST_ID = rid
    return rid


@app.get("/")
def root():
    return {
        "service": "LifeOps",
        "version": __version__,
        "tagline": "Paste your document, save your money.",
        "catalog": PRICES,
        "currency": ASSET_SYMBOL,
        "network": {"name": NETWORK_NAME, "chain": NETWORK},
        "pay_to": PAY_TO,
        "protocol": "x402 / A2MCP",
    }


@app.get("/health")
def health():
    """Deploy/review readiness probe. 'ready' means the payTo wallet is set."""
    return {
        "status": "ok",
        "ready_for_listing": PAYTO_CONFIGURED,
        "payto_configured": PAYTO_CONFIGURED,
        "network": NETWORK,
    }


@app.get("/pricing")
def pricing():
    return {
        "currency": ASSET_SYMBOL,
        "network": {"name": NETWORK_NAME, "chain": NETWORK},
        "services": PRICES,
        "payment_requirements": {s: payment_requirements(s) for s in PRICES},
    }


@app.post("/scan")
def scan(req: ScanRequest, x_payment: str | None = Header(default=None)):
    """
    x402 flow:
      - No X-Payment header -> 402 Payment Required + price headers.
      - Present -> settle payment, append to tx log, return guaranteed JSON.

    Services:
      scan             -> structured JSON, no .ics
      full_action_pack -> JSON + .ics
      multi_audit      -> N documents in one payload, merged audit + one .ics

    Demo convenience: header 'demo' auto-settles (live, repeatable).
    """
    service = req.service if req.service in PRICES else "full_action_pack"

    if x_payment is None:
        headers = payment_required_header(service)
        return JSONResponse(
            status_code=402,
            content={
                "error": "payment_required",
                "message": f"Payment of {price_for(service)} {ASSET_SYMBOL} on {NETWORK_NAME} required for {service}.",
                "payment_requirements": payment_requirements(service),
                "how_to_pay": "Settle via A2MCP (PAYMENT-REQUIRED header) or use X-Payment: demo for the demo flow.",
            },
            headers=headers,
        )

    # Settle payment
    tx = settle(service, req.caller, x_payment)

    # Core processing - multi_audit gets the multi-document pipeline
    if service == "multi_audit":
        result = process_multi(req.text)
    else:
        result = process(req.text, with_ics=(service != "scan"))

    rid = _store_result(result)

    return {
        "payment": tx,
        "result": result,
        "result_id": rid,
        "ics_url": f"/ics/{rid}.ics" if result.get("ics_base64") else None,
    }


@app.get("/tx")
def tx_log(limit: int = 20):
    """Live tx log - the frontend Tx Log terminal polls this."""
    return {"transactions": recent_tx(limit)}


def _ics_response(result: dict) -> Response:
    if not result.get("ics_base64"):
        raise HTTPException(status_code=404, detail="No .ics for this result.")
    raw = base64.b64decode(result["ics_base64"])
    return Response(
        content=raw,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=lifeops.ics"},
    )


@app.get("/ics/latest.ics")
def download_latest_ics():
    """Download the .ics of the most recent result (demo convenience)."""
    if _LATEST_ID is None or _LATEST_ID not in _RESULTS:
        raise HTTPException(status_code=404, detail="No .ics generated yet.")
    return _ics_response(_RESULTS[_LATEST_ID])


@app.get("/ics/{result_id}.ics")
def download_ics(result_id: str):
    """Download the .ics of a specific result - safe under concurrent users."""
    result = _RESULTS.get(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Unknown result id.")
    return _ics_response(result)
