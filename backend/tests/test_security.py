from __future__ import annotations

import asyncio
import time

from fastapi.testclient import TestClient

from app import main
from app.payment import ReplayGuard
from app.payment import _TX_LOG, recent_tx


def test_security_headers_are_returned():
    response = TestClient(main.app).get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["content-security-policy"].startswith("default-src 'none'")
    assert response.headers["x-request-id"]


def test_oversized_request_is_rejected_before_parsing():
    response = TestClient(main.app).post(
        "/scan",
        content=b"x" * (64 * 1024 + 1),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"] == "request_too_large"


def test_result_store_expires_sensitive_generated_output(monkeypatch):
    monkeypatch.setattr(main, "_RESULT_TTL_SECONDS", 60)
    result_id = main._store_result({"ics_base64": "value"})
    expires, result = main._RESULTS[result_id]
    main._RESULTS[result_id] = (time.monotonic() - 1, result)
    assert main._get_result(result_id) is None
    assert result_id not in main._RESULTS


def test_sqlite_replay_guard_survives_new_instances(tmp_path):
    path = str(tmp_path / "replays.sqlite3")

    async def scenario():
        first = ReplayGuard(db_path=path)
        assert await first.reserve("same-payment") is True
        await first.commit("same-payment")

        after_restart = ReplayGuard(db_path=path)
        assert await after_restart.reserve("same-payment") is False
        assert after_restart.persistent is True

    asyncio.run(scenario())


def test_public_transaction_feed_redacts_identity_fields():
    _TX_LOG.appendleft({"tx_hash": "0xabc", "payer": "0xprivate", "caller": "private-agent"})
    item = recent_tx(1)[0]
    assert item["tx_hash"] == "0xabc"
    assert "payer" not in item
    assert "caller" not in item
