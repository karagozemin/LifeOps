"""Production x402 v2 payment gateway for LifeOps on X Layer."""
from __future__ import annotations

import asyncio
import hashlib
import os
import sqlite3
import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol

import httpx
from x402.http import (
    OKXAuthConfig,
    OKXFacilitatorClient,
    OKXFacilitatorConfig,
)
from x402.http.utils import (
    decode_payment_signature_header,
    encode_payment_required_header,
    encode_payment_response_header,
)
from x402.schemas import (
    PaymentPayload,
    PaymentRequired,
    PaymentRequirements,
    ResourceInfo,
    SettleResponse,
)

NETWORK = "eip155:196"
NETWORK_NAME = "X Layer"
ASSET = "0x779ded0c9e1022225f8e0630b35a9b54be713736"
ASSET_SYMBOL = "USDT0"
ASSET_NAME = "USD₮0"
ASSET_VERSION = "1"
ASSET_DECIMALS = 6
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

PRICES = {
    "scan": Decimal("0.01"),
    "full_action_pack": Decimal("0.05"),
    "multi_audit": Decimal("0.20"),
}

_TX_LOG: deque[dict] = deque(maxlen=50)


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def price_for(service: str) -> Decimal:
    return PRICES[service]


def base_units(service: str) -> str:
    return str(int(price_for(service) * (10**ASSET_DECIMALS)))


class Facilitator(Protocol):
    async def verify(self, payload: PaymentPayload, requirements: PaymentRequirements): ...
    async def settle(self, payload: PaymentPayload, requirements: PaymentRequirements): ...


class ReplayStore(Protocol):
    @property
    def persistent(self) -> bool: ...

    async def reserve(self, fingerprint: str) -> bool: ...
    async def commit(self, fingerprint: str) -> None: ...
    async def release(self, fingerprint: str) -> None: ...


class ReplayStoreError(Exception):
    pass


class PaymentGatewayError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


@dataclass(frozen=True)
class VerifiedPayment:
    payload: PaymentPayload | None
    requirements: PaymentRequirements
    fingerprint: str
    payer: str | None
    demo: bool = False


class ReplayGuard:
    """Atomic replay reservation with optional cross-process SQLite storage."""

    def __init__(self, max_entries: int = 10_000, db_path: str | None = None):
        self._lock = asyncio.Lock()
        self._entries: OrderedDict[str, str] = OrderedDict()
        self._max_entries = max_entries
        self.db_path = db_path
        if db_path:
            with sqlite3.connect(db_path) as db:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS payment_replays ("
                    "fingerprint TEXT PRIMARY KEY, status TEXT NOT NULL, created_at REAL NOT NULL)"
                )

    @property
    def persistent(self) -> bool:
        return bool(self.db_path)

    async def reserve(self, fingerprint: str) -> bool:
        async with self._lock:
            if self.db_path:
                now = time.time()
                try:
                    with sqlite3.connect(self.db_path, timeout=5) as db:
                        db.execute(
                            "DELETE FROM payment_replays WHERE status = 'reserved' AND created_at < ?",
                            (now - 300,),
                        )
                        db.execute(
                            "INSERT INTO payment_replays VALUES (?, 'reserved', ?)",
                            (fingerprint, now),
                        )
                        db.execute(
                            "DELETE FROM payment_replays WHERE fingerprint IN ("
                            "SELECT fingerprint FROM payment_replays WHERE status = 'settled' "
                            "ORDER BY created_at DESC LIMIT -1 OFFSET ?)",
                            (self._max_entries,),
                        )
                    return True
                except sqlite3.IntegrityError:
                    return False
            if fingerprint in self._entries:
                return False
            self._entries[fingerprint] = "reserved"
            self._entries.move_to_end(fingerprint)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
            return True

    async def commit(self, fingerprint: str) -> None:
        async with self._lock:
            if self.db_path:
                with sqlite3.connect(self.db_path, timeout=5) as db:
                    db.execute(
                        "UPDATE payment_replays SET status = 'settled' WHERE fingerprint = ?",
                        (fingerprint,),
                    )
                return
            if fingerprint in self._entries:
                self._entries[fingerprint] = "settled"
                self._entries.move_to_end(fingerprint)

    async def release(self, fingerprint: str) -> None:
        async with self._lock:
            if self.db_path:
                with sqlite3.connect(self.db_path, timeout=5) as db:
                    db.execute(
                        "DELETE FROM payment_replays WHERE fingerprint = ? AND status = 'reserved'",
                        (fingerprint,),
                    )
                return
            if self._entries.get(fingerprint) == "reserved":
                self._entries.pop(fingerprint, None)


class UpstashReplayGuard:
    """Atomic cross-instance replay protection using Upstash Redis REST."""

    def __init__(
        self,
        url: str,
        token: str,
        *,
        ttl_seconds: int = 604_800,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.url = url.rstrip("/")
        self.token = token
        self.ttl_seconds = max(300, ttl_seconds)
        self._transport = transport

    @property
    def persistent(self) -> bool:
        return True

    def _key(self, fingerprint: str) -> str:
        return f"lifeops:payment-replay:{fingerprint}"

    async def _command(self, *parts: str):
        try:
            async with httpx.AsyncClient(
                base_url=self.url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5,
                transport=self._transport,
            ) as client:
                response = await client.post("/", json=list(parts))
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ReplayStoreError("Persistent replay store is unavailable.") from exc
        if payload.get("error"):
            raise ReplayStoreError("Persistent replay store rejected the operation.")
        return payload.get("result")

    async def reserve(self, fingerprint: str) -> bool:
        result = await self._command(
            "SET",
            self._key(fingerprint),
            "reserved",
            "NX",
            "EX",
            str(self.ttl_seconds),
        )
        return result == "OK"

    async def commit(self, fingerprint: str) -> None:
        # The reservation already has the full replay TTL. Keeping it unchanged
        # avoids turning a completed payment into an error on a transient write.
        return None

    async def release(self, fingerprint: str) -> None:
        script = (
            "if redis.call('get', KEYS[1]) == 'reserved' then "
            "return redis.call('del', KEYS[1]) else return 0 end"
        )
        await self._command("EVAL", script, "1", self._key(fingerprint))


def default_replay_guard() -> ReplayStore:
    upstash_url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
    upstash_token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
    if upstash_url and upstash_token:
        return UpstashReplayGuard(upstash_url, upstash_token)
    return ReplayGuard(db_path=os.getenv("LIFEOPS_REPLAY_DB", "").strip() or None)


class PaymentGateway:
    def __init__(
        self,
        *,
        pay_to: str | None = None,
        okx_base_url: str | None = None,
        okx_api_key: str | None = None,
        okx_secret_key: str | None = None,
        okx_passphrase: str | None = None,
        facilitator: Facilitator | None = None,
        demo_mode: bool | None = None,
        replay_guard: ReplayStore | None = None,
    ):
        self.pay_to = (pay_to or os.getenv("LIFEOPS_PAYTO", ZERO_ADDRESS)).strip()
        self.okx_base_url = okx_base_url or os.getenv("OKX_BASE_URL", "https://web3.okx.com")
        self.demo_mode = _env_flag("LIFEOPS_DEMO_MODE") if demo_mode is None else demo_mode
        self._facilitator = facilitator
        credentials = {
            "api_key": okx_api_key or os.getenv("OKX_API_KEY", ""),
            "secret_key": okx_secret_key or os.getenv("OKX_SECRET_KEY", ""),
            "passphrase": okx_passphrase or os.getenv("OKX_PASSPHRASE", ""),
        }
        if self._facilitator is None and all(credentials.values()):
            self._facilitator = OKXFacilitatorClient(
                OKXFacilitatorConfig(
                    auth=OKXAuthConfig(**credentials),
                    base_url=self.okx_base_url,
                    sync_settle=True,
                )
            )
        self._replays = replay_guard or default_replay_guard()

    @property
    def payto_configured(self) -> bool:
        return self.pay_to.lower() != ZERO_ADDRESS and len(self.pay_to) == 42

    @property
    def facilitator_configured(self) -> bool:
        return self._facilitator is not None

    @property
    def ready_for_listing(self) -> bool:
        return (
            self.payto_configured
            and self.facilitator_configured
            and self._replays.persistent
            and not self.demo_mode
        )

    @property
    def replay_persistent(self) -> bool:
        return self._replays.persistent

    def requirements(self, service: str) -> PaymentRequirements:
        return PaymentRequirements(
            scheme="exact",
            network=NETWORK,
            asset=ASSET,
            amount=base_units(service),
            payTo=self.pay_to,
            maxTimeoutSeconds=60,
            extra={"name": ASSET_NAME, "version": ASSET_VERSION},
        )

    def challenge(self, service: str, resource_url: str) -> PaymentRequired:
        return PaymentRequired(
            x402Version=2,
            error="Payment required",
            resource=ResourceInfo(
                url=resource_url,
                description=f"LifeOps {service} document analysis",
                mimeType="application/json",
                serviceName="LifeOps",
            ),
            accepts=[self.requirements(service)],
        )

    def challenge_headers(self, service: str, resource_url: str) -> dict[str, str]:
        return {
            "PAYMENT-REQUIRED": encode_payment_required_header(
                self.challenge(service, resource_url)
            ),
            "Cache-Control": "no-store",
        }

    async def _release_reservation(self, fingerprint: str) -> None:
        try:
            await self._replays.release(fingerprint)
        except ReplayStoreError:
            # Retaining a reservation is safer than allowing a replay. Do not
            # mask the facilitator or business error that caused the release.
            pass

    async def verify(
        self,
        service: str,
        payment_signature: str | None,
        legacy_payment: str | None,
    ) -> VerifiedPayment:
        requirements = self.requirements(service)

        if self.demo_mode and (payment_signature == "demo" or legacy_payment == "demo"):
            fingerprint = hashlib.sha256(
                f"demo:{service}:{datetime.now(timezone.utc).isoformat()}".encode()
            ).hexdigest()
            return VerifiedPayment(None, requirements, fingerprint, "demo", demo=True)

        if legacy_payment is not None:
            raise PaymentGatewayError(
                400,
                "legacy_payment_header",
                "X-Payment is not accepted. Use the x402 v2 PAYMENT-SIGNATURE header.",
            )
        if not payment_signature:
            raise PaymentGatewayError(402, "payment_required", "Payment is required.")
        if not self.facilitator_configured:
            raise PaymentGatewayError(
                503,
                "payment_service_unavailable",
                "The payment facilitator is not configured.",
            )

        try:
            payload = decode_payment_signature_header(payment_signature)
        except Exception as exc:
            raise PaymentGatewayError(
                400, "invalid_payment_signature", "PAYMENT-SIGNATURE is malformed."
            ) from exc

        if not isinstance(payload, PaymentPayload) or payload.x402_version != 2:
            raise PaymentGatewayError(400, "unsupported_x402_version", "x402 v2 is required.")
        if payload.accepted != requirements:
            raise PaymentGatewayError(
                402,
                "payment_requirements_mismatch",
                "The signed payment does not match this service's requirements.",
            )

        fingerprint = hashlib.sha256(payment_signature.encode()).hexdigest()
        try:
            reserved = await self._replays.reserve(fingerprint)
        except ReplayStoreError as exc:
            raise PaymentGatewayError(
                503,
                "replay_store_unavailable",
                "Payment replay protection is temporarily unavailable.",
            ) from exc
        if not reserved:
            raise PaymentGatewayError(409, "payment_replayed", "This payment was already used.")

        try:
            verification = await self._facilitator.verify(payload, requirements)
        except Exception as exc:
            await self._release_reservation(fingerprint)
            raise PaymentGatewayError(
                502, "payment_verification_failed", "The facilitator could not verify payment."
            ) from exc

        if not verification.is_valid:
            await self._release_reservation(fingerprint)
            reason = verification.invalid_reason or "Payment verification failed."
            raise PaymentGatewayError(402, "payment_invalid", reason)

        return VerifiedPayment(
            payload, requirements, fingerprint, verification.payer, demo=False
        )

    async def settle(self, verified: VerifiedPayment, service: str, caller: str) -> tuple[dict, str]:
        if verified.demo:
            digest = hashlib.sha256(
                f"demo:{verified.fingerprint}:{caller}".encode()
            ).hexdigest()
            response = SettleResponse(
                success=True,
                transaction=f"demo-{digest[:24]}",
                network=NETWORK,
                payer="demo",
                amount=base_units(service),
            )
            mode = "demo"
        else:
            try:
                response = await self._facilitator.settle(
                    verified.payload, verified.requirements
                )
            except Exception as exc:
                await self._release_reservation(verified.fingerprint)
                raise PaymentGatewayError(
                    502, "payment_settlement_failed", "The facilitator could not settle payment."
                ) from exc
            if not response.success:
                await self._release_reservation(verified.fingerprint)
                reason = response.error_reason or "Payment settlement failed."
                raise PaymentGatewayError(402, "payment_not_settled", reason)
            await self._replays.commit(verified.fingerprint)
            mode = "x402"

        tx = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "service": service,
            "caller": caller,
            "payer": response.payer or verified.payer,
            "amount": float(price_for(service)),
            "amount_base_units": base_units(service),
            "asset": ASSET_SYMBOL,
            "network": NETWORK_NAME,
            "chain": response.network,
            "tx_hash": response.transaction,
            "status": "settled",
            "mode": mode,
            "protocol": "x402 v2 / A2MCP",
        }
        _TX_LOG.appendleft(tx)
        return tx, encode_payment_response_header(response)

    async def abandon(self, verified: VerifiedPayment) -> None:
        """Release a verified reservation when business processing fails."""
        if not verified.demo:
            await self._release_reservation(verified.fingerprint)


def recent_tx(limit: int = 20) -> list[dict]:
    public = []
    for transaction in list(_TX_LOG)[: max(0, min(limit, 50))]:
        item = transaction.copy()
        item.pop("payer", None)
        item.pop("caller", None)
        public.append(item)
    return public


payment_gateway = PaymentGateway()
