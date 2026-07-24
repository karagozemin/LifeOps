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
import os
import time
import uuid
from collections import OrderedDict, defaultdict, deque

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .payment import (
    ASSET_SYMBOL,
    NETWORK,
    NETWORK_NAME,
    PRICES,
    PaymentGatewayError,
    payment_gateway,
    recent_tx,
)
from .pipeline import process, process_multi
from .schema import ScanRequest

app = FastAPI(
    title="LifeOps",
    version=__version__,
    description="Document to action. Deadline, money_at_risk and .ics in a single call. Agent-consumable ASP.",
)

_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "LIFEOPS_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "PAYMENT-SIGNATURE", "X-Payment"],
    expose_headers=["PAYMENT-REQUIRED", "PAYMENT-RESPONSE", "X-Request-ID"],
)

_MAX_REQUEST_BYTES = 64 * 1024
_RATE_LIMIT = max(1, int(os.getenv("LIFEOPS_RATE_LIMIT_PER_MINUTE", "60")))
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def security_and_limits(request: Request, call_next):
    request_id = uuid.uuid4().hex
    if request.url.path in {"/scan", "/preview"}:
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > _MAX_REQUEST_BYTES:
            return JSONResponse(
                status_code=413,
                content={"error": "request_too_large", "message": "Request body exceeds 64 KiB."},
                headers={"X-Request-ID": request_id},
            )

        client_key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = _RATE_BUCKETS[client_key]
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= _RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limit_exceeded", "message": "Too many scan requests."},
                headers={"Retry-After": "60", "X-Request-ID": request_id},
            )
        bucket.append(now)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Result store: id -> result. Bounded LRU so memory stays flat.
# Fixes the single-slot race: concurrent users each get their own .ics URL.
_RESULTS: OrderedDict[str, tuple[float, dict]] = OrderedDict()
_RESULTS_MAX = 200
_RESULT_TTL_SECONDS = max(60, int(os.getenv("LIFEOPS_RESULT_TTL_SECONDS", "1800")))
_LATEST_ID: str | None = None


def _store_result(result: dict) -> str:
    global _LATEST_ID
    rid = uuid.uuid4().hex[:12]
    _RESULTS[rid] = (time.monotonic() + _RESULT_TTL_SECONDS, result)
    _RESULTS.move_to_end(rid)
    while len(_RESULTS) > _RESULTS_MAX:
        _RESULTS.popitem(last=False)
    _LATEST_ID = rid
    return rid


def _get_result(result_id: str) -> dict | None:
    entry = _RESULTS.get(result_id)
    if entry is None:
        return None
    expires_at, result = entry
    if expires_at <= time.monotonic():
        _RESULTS.pop(result_id, None)
        return None
    _RESULTS.move_to_end(result_id)
    return result


@app.get("/")
def root():
    return {
        "service": "LifeOps",
        "version": __version__,
        "tagline": "Paste your document, save your money.",
        "catalog": {service: float(price) for service, price in PRICES.items()},
        "currency": ASSET_SYMBOL,
        "network": {"name": NETWORK_NAME, "chain": NETWORK},
        "pay_to": payment_gateway.pay_to,
        "protocol": "x402 v2 / A2MCP",
    }


@app.get("/health")
def health():
    """Deploy/review readiness probe for the production payment path."""
    return {
        "status": "ok",
        "ready_for_listing": payment_gateway.ready_for_listing,
        "payto_configured": payment_gateway.payto_configured,
        "facilitator_configured": payment_gateway.facilitator_configured,
        "replay_persistent": payment_gateway.replay_persistent,
        "demo_mode": payment_gateway.demo_mode,
        "network": NETWORK,
    }


@app.get("/pricing")
def pricing():
    return {
        "currency": ASSET_SYMBOL,
        "network": {"name": NETWORK_NAME, "chain": NETWORK},
        "services": {service: float(price) for service, price in PRICES.items()},
        "payment_requirements": {
            service: payment_gateway.requirements(service).model_dump(
                by_alias=True, exclude_none=True
            )
            for service in PRICES
        },
    }


@app.post("/scan")
async def scan(
    req: ScanRequest,
    request: Request,
    payment_signature: str | None = Header(default=None, alias="PAYMENT-SIGNATURE"),
    x_payment: str | None = Header(default=None, alias="X-Payment"),
):
    """
    x402 flow:
      - No PAYMENT-SIGNATURE -> standard x402 v2 challenge.
      - Valid signature -> facilitator verify, process, then settle.

    Services:
      scan             -> structured JSON, no .ics
      full_action_pack -> JSON + .ics
      multi_audit      -> N documents in one payload, merged audit + one .ics

    Demo payment only exists when LIFEOPS_DEMO_MODE=true.
    """
    service = req.service
    if service not in PRICES:
        raise HTTPException(status_code=422, detail=f"Unknown service: {service}")

    resource_url = str(request.url)
    try:
        verified = await payment_gateway.verify(service, payment_signature, x_payment)
    except PaymentGatewayError as exc:
        headers = {"Cache-Control": "no-store"}
        if exc.status_code == 402:
            headers.update(payment_gateway.challenge_headers(service, resource_url))
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message},
            headers=headers,
        )

    # Core processing - multi_audit gets the multi-document pipeline
    try:
        if service == "multi_audit":
            result = process_multi(req.text)
        else:
            result = process(req.text, with_ics=(service != "scan"))
    except Exception:
        await payment_gateway.abandon(verified)
        raise

    try:
        tx, payment_response = await payment_gateway.settle(
            verified, service, req.caller
        )
    except PaymentGatewayError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message},
            headers={"Cache-Control": "no-store"},
        )

    rid = _store_result(result)

    return JSONResponse(
        content={
            "payment": tx,
            "result": result,
            "result_id": rid,
            "ics_url": f"/ics/{rid}.ics" if result.get("ics_base64") else None,
        },
        headers={"PAYMENT-RESPONSE": payment_response, "Cache-Control": "no-store"},
    )


@app.post("/preview")
def preview(req: ScanRequest):
    """Rate-limited web preview; paid agent traffic remains on /scan."""
    if os.getenv("LIFEOPS_PREVIEW_ENABLED", "true").lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=404, detail="Preview is disabled.")
    if req.service not in PRICES:
        raise HTTPException(status_code=422, detail=f"Unknown service: {req.service}")

    if req.service == "multi_audit":
        result = process_multi(req.text)
    else:
        result = process(req.text, with_ics=(req.service != "scan"))
    rid = _store_result(result)
    return JSONResponse(
        content={
            "result": result,
            "result_id": rid,
            "ics_url": f"/ics/{rid}.ics" if result.get("ics_base64") else None,
            "preview": True,
        },
        headers={"Cache-Control": "no-store", "X-LifeOps-Preview": "true"},
    )


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
    result = _get_result(_LATEST_ID) if _LATEST_ID is not None else None
    if result is None:
        raise HTTPException(status_code=404, detail="No .ics generated yet.")
    return _ics_response(result)


@app.get("/ics/{result_id}.ics")
def download_ics(result_id: str):
    """Download the .ics of a specific result - safe under concurrent users."""
    result = _get_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Unknown result id.")
    return _ics_response(result)
