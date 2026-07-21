"""
LifeOps - FastAPI main application.
One service, one repo. Agent-consumable ASP.

Endpoints:
  GET  /                -> health + service catalog
  GET  /pricing         -> service prices (USDT)
  POST /scan            -> x402-paid document analysis (guaranteed JSON)
  GET  /tx              -> live tx log (feeds the frontend terminal)
  GET  /ics/{...}       -> .ics file of the latest result (downloadable)
"""
from __future__ import annotations

import base64

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .payment import (PRICES, payment_required_header, price_for, recent_tx,
                      settle)
from .pipeline import process
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

# Store the most recent result for .ics download
_LAST_RESULT: dict = {}


@app.get("/")
def root():
    return {
        "service": "LifeOps",
        "version": __version__,
        "tagline": "Paste your document, save your money.",
        "catalog": PRICES,
        "protocol": "x402 / A2MCP",
    }


@app.get("/pricing")
def pricing():
    return {"currency": "USDT", "services": PRICES}


@app.post("/scan")
def scan(req: ScanRequest, x_payment: str | None = Header(default=None)):
    """
    x402 flow:
      - No X-Payment header -> 402 Payment Required + price headers.
      - Present -> settle payment, append to tx log, return guaranteed JSON.

    Demo convenience: header 'demo' auto-settles (live, repeatable).
    """
    service = req.service if req.service in PRICES else "full_action_pack"

    if x_payment is None:
        headers = payment_required_header(service)
        return JSONResponse(
            status_code=402,
            content={
                "error": "payment_required",
                "message": f"Payment of {price_for(service)} USDT required for {service}.",
                "how_to_pay": "Send an x402 payment via the X-Payment header (demo: 'demo').",
            },
            headers=headers,
        )

    # Settle payment
    tx = settle(service, req.caller)

    # Core processing
    result = process(req.text, with_ics=(service != "scan"))

    global _LAST_RESULT
    _LAST_RESULT = result

    return {
        "payment": tx,
        "result": result,
    }


@app.get("/tx")
def tx_log(limit: int = 20):
    """Live tx log - the frontend Tx Log terminal polls this."""
    return {"transactions": recent_tx(limit)}


@app.get("/ics/latest.ics")
def download_ics():
    """Download the .ics file of the latest analysis result."""
    if not _LAST_RESULT or not _LAST_RESULT.get("ics_base64"):
        raise HTTPException(status_code=404, detail="No .ics generated yet.")
    raw = base64.b64decode(_LAST_RESULT["ics_base64"])
    return Response(
        content=raw,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=lifeops.ics"},
    )
