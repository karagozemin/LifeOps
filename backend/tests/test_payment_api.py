from __future__ import annotations

from fastapi.testclient import TestClient
from x402.http.utils import (
    decode_payment_required_header,
    decode_payment_response_header,
    encode_payment_signature_header,
)
from x402.schemas import PaymentPayload, SettleResponse, VerifyResponse

from app import main
from app.payment import NETWORK, PaymentGateway

PAY_TO = "0x1111111111111111111111111111111111111111"


class FakeFacilitator:
    def __init__(self, *, valid: bool = True, settled: bool = True):
        self.valid = valid
        self.settled = settled
        self.verify_calls = 0
        self.settle_calls = 0

    async def verify(self, payload, requirements):
        self.verify_calls += 1
        return VerifyResponse(
            isValid=self.valid,
            invalidReason=None if self.valid else "bad_signature",
            payer="0x2222222222222222222222222222222222222222",
        )

    async def settle(self, payload, requirements):
        self.settle_calls += 1
        return SettleResponse(
            success=self.settled,
            errorReason=None if self.settled else "settlement_reverted",
            payer="0x2222222222222222222222222222222222222222",
            transaction="0x" + "a" * 64,
            network=NETWORK,
            amount=requirements.amount,
        )


def install_gateway(monkeypatch, *, facilitator=None, demo_mode=False):
    gateway = PaymentGateway(
        pay_to=PAY_TO,
        facilitator=facilitator,
        demo_mode=demo_mode,
    )
    monkeypatch.setattr(main, "payment_gateway", gateway)
    return gateway


def signature_for(gateway: PaymentGateway, service: str = "scan") -> str:
    payload = PaymentPayload(
        x402Version=2,
        accepted=gateway.requirements(service),
        payload={"signature": "0x1234", "authorization": {"nonce": "1"}},
    )
    return encode_payment_signature_header(payload)


def post(client: TestClient, headers=None, service="scan"):
    return client.post(
        "/scan",
        json={"text": "Warranty expires 2027-03-14. Value 120 USD.", "service": service},
        headers=headers or {},
    )


def test_unpaid_request_returns_standard_v2_challenge(monkeypatch):
    gateway = install_gateway(monkeypatch, facilitator=FakeFacilitator())
    response = post(TestClient(main.app))

    assert response.status_code == 402
    challenge = decode_payment_required_header(response.headers["PAYMENT-REQUIRED"])
    assert challenge.x402_version == 2
    assert challenge.resource.url == "http://testserver/scan"
    assert challenge.accepts == [gateway.requirements("scan")]
    assert response.headers["cache-control"] == "no-store"


def test_malformed_signature_is_rejected(monkeypatch):
    install_gateway(monkeypatch, facilitator=FakeFacilitator())
    response = post(TestClient(main.app), {"PAYMENT-SIGNATURE": "not-base64"})
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_payment_signature"


def test_legacy_header_is_never_payment_in_production(monkeypatch):
    install_gateway(monkeypatch, facilitator=FakeFacilitator(), demo_mode=False)
    response = post(TestClient(main.app), {"X-Payment": "anything"})
    assert response.status_code == 400
    assert response.json()["error"] == "legacy_payment_header"


def test_requirements_mismatch_is_rejected(monkeypatch):
    gateway = install_gateway(monkeypatch, facilitator=FakeFacilitator())
    signature = signature_for(gateway, "full_action_pack")
    response = post(TestClient(main.app), {"PAYMENT-SIGNATURE": signature}, "scan")
    assert response.status_code == 402
    assert response.json()["error"] == "payment_requirements_mismatch"


def test_verified_payment_is_settled_and_receipted(monkeypatch):
    facilitator = FakeFacilitator()
    gateway = install_gateway(monkeypatch, facilitator=facilitator)
    response = post(
        TestClient(main.app),
        {"PAYMENT-SIGNATURE": signature_for(gateway)},
    )

    assert response.status_code == 200
    assert response.json()["payment"]["tx_hash"] == "0x" + "a" * 64
    receipt = decode_payment_response_header(response.headers["PAYMENT-RESPONSE"])
    assert receipt.success is True
    assert receipt.network == NETWORK
    assert facilitator.verify_calls == facilitator.settle_calls == 1


def test_settlement_failure_does_not_return_business_result(monkeypatch):
    facilitator = FakeFacilitator(settled=False)
    gateway = install_gateway(monkeypatch, facilitator=facilitator)
    response = post(
        TestClient(main.app),
        {"PAYMENT-SIGNATURE": signature_for(gateway)},
    )
    assert response.status_code == 402
    assert response.json()["error"] == "payment_not_settled"
    assert "result" not in response.json()


def test_same_payment_cannot_be_replayed(monkeypatch):
    gateway = install_gateway(monkeypatch, facilitator=FakeFacilitator())
    signature = signature_for(gateway)
    client = TestClient(main.app)

    assert post(client, {"PAYMENT-SIGNATURE": signature}).status_code == 200
    replay = post(client, {"PAYMENT-SIGNATURE": signature})
    assert replay.status_code == 409
    assert replay.json()["error"] == "payment_replayed"


def test_demo_only_works_when_explicitly_enabled(monkeypatch):
    install_gateway(monkeypatch, facilitator=None, demo_mode=False)
    disabled = post(TestClient(main.app), {"X-Payment": "demo"})
    assert disabled.status_code == 400

    install_gateway(monkeypatch, facilitator=None, demo_mode=True)
    enabled = post(TestClient(main.app), {"X-Payment": "demo"})
    assert enabled.status_code == 200
    assert enabled.json()["payment"]["mode"] == "demo"
    assert enabled.json()["payment"]["tx_hash"].startswith("demo-")


def test_unknown_service_is_rejected(monkeypatch):
    install_gateway(monkeypatch, facilitator=FakeFacilitator())
    response = post(TestClient(main.app), service="not-a-service")
    assert response.status_code == 422


def test_empty_input_is_rejected_before_payment(monkeypatch):
    facilitator = FakeFacilitator()
    install_gateway(monkeypatch, facilitator=facilitator)
    response = TestClient(main.app).post(
        "/scan", json={"text": "   ", "service": "scan"}
    )
    assert response.status_code == 422
    assert facilitator.verify_calls == facilitator.settle_calls == 0


def test_preview_is_explicit_and_never_claims_payment(monkeypatch):
    facilitator = FakeFacilitator()
    install_gateway(monkeypatch, facilitator=facilitator)
    response = TestClient(main.app).post(
        "/preview",
        json={"text": "Warranty ends 2027-09-01. Value 120 USD.", "service": "full_action_pack"},
    )
    assert response.status_code == 200
    assert response.headers["x-lifeops-preview"] == "true"
    assert response.json()["preview"] is True
    assert "payment" not in response.json()
    assert facilitator.verify_calls == facilitator.settle_calls == 0
