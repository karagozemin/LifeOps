from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.payment import ReplayStoreError, UpstashReplayGuard


def test_upstash_reservation_is_atomic_and_releasable():
    keys: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        command = json.loads(request.content)
        if command[0] == "SET":
            key = command[1]
            if key in keys:
                return httpx.Response(200, json={"result": None})
            keys[key] = command[2]
            return httpx.Response(200, json={"result": "OK"})
        if command[0] == "EVAL":
            key = command[-1]
            removed = int(keys.pop(key, None) is not None)
            return httpx.Response(200, json={"result": removed})
        raise AssertionError(f"Unexpected command: {command}")

    guard = UpstashReplayGuard(
        "https://example.upstash.io",
        "test-token",
        transport=httpx.MockTransport(handler),
    )

    async def exercise() -> None:
        assert guard.persistent is True
        assert await guard.reserve("abc") is True
        assert await guard.reserve("abc") is False
        await guard.release("abc")
        assert await guard.reserve("abc") is True

    asyncio.run(exercise())


def test_upstash_failure_does_not_fall_back_to_memory():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    guard = UpstashReplayGuard(
        "https://example.upstash.io",
        "test-token",
        transport=httpx.MockTransport(handler),
    )

    async def exercise() -> None:
        with pytest.raises(ReplayStoreError):
            await guard.reserve("abc")

    asyncio.run(exercise())
