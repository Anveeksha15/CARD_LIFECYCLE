import random

import fakeredis
import pytest
from fastapi.testclient import TestClient

import services.fraud.main as fraud_main
import services.gateway.fraud as gateway_fraud
import services.gateway.routes as gateway_routes
from common.config import settings
from common.http import UpstreamError
from common.luhn import complete_luhn
from services.gateway.db import FraudCheck, get_session

AUTH_HEADERS = {"Authorization": "Bearer sk_test_demo_merchant"}


@pytest.fixture
def fraud_on(monkeypatch, service_clients, fraud_model_prefix):
    """Turn the flag on and route the gateway's fraud calls to a real, in-process fraud
    service (fakeredis for its windows)."""
    monkeypatch.setattr(settings, "fraud_check_enabled", True)
    monkeypatch.setattr(settings, "fraud_model_path", str(fraud_model_prefix))
    monkeypatch.setattr(fraud_main, "_redis", fakeredis.FakeRedis(decode_responses=True))
    with TestClient(fraud_main.app) as fraud_client:
        service_clients[settings.fraud_url] = fraud_client
        yield


@pytest.fixture
def acquirer_calls(monkeypatch):
    calls = []
    routed = gateway_routes.post_with_retry

    def counting(url, json, **kwargs):
        if url.startswith(f"{settings.acquirer_url}/v1/authorize"):
            calls.append(json["card_number"])
        return routed(url, json, **kwargs)

    monkeypatch.setattr(gateway_routes, "post_with_retry", counting)
    return calls


def _pay(client, card_number, amount_cents, **customer):
    token = client.post("/v1/tokens", json={"card_number": card_number}).json()["token"]
    resp = client.post(
        "/v1/payment_intents",
        json={"amount_cents": amount_cents, "token": token, **customer},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    return resp.json()


def _fraud_row(intent_id):
    with get_session() as session:
        return session.get(FraudCheck, intent_id)


def test_flag_off_never_calls_fraud_service(gateway_client, monkeypatch):
    def must_not_be_called(*args, **kwargs):
        raise AssertionError("fraud service called with the flag off")

    monkeypatch.setattr(gateway_fraud, "score", must_not_be_called)
    body = _pay(gateway_client, "4242424242424242", 1500)
    assert body["status"] == "succeeded"
    assert body["fraud_decision"] is None
    assert _fraud_row(body["id"]) is None


def test_normal_payment_is_scored_and_allowed(gateway_client, fraud_on):
    body = _pay(
        gateway_client, "4242424242424242", 4200,
        customer_ip="198.51.100.7", customer_email="shopper@example.com",
    )
    assert body["status"] == "succeeded"
    assert body["fraud_decision"] == "allow"
    row = _fraud_row(body["id"])
    assert row is not None and row.decision == "allow"


def test_card_testing_burst_is_blocked_before_the_acquirer(
    gateway_client, fraud_on, acquirer_calls
):
    rng = random.Random(0)
    results = [
        _pay(
            gateway_client,
            complete_luhn("424242" + f"{rng.randrange(10**9):09d}"),
            100,
            customer_ip="203.0.113.66",
            customer_email="tester@example.com",
        )
        for _ in range(15)
    ]
    blocked = [r for r in results if r["decline_reason"] == "fraud_suspected"]
    assert results[-1]["decline_reason"] == "fraud_suspected"
    assert len(blocked) >= 10
    assert all(r["status"] == "failed" and r["fraud_decision"] == "block" for r in blocked)
    # Blocked attempts never reach the acquirer.
    assert len(acquirer_calls) == len(results) - len(blocked)


def test_fraud_service_down_fails_open(gateway_client, fraud_on, monkeypatch):
    routed = gateway_fraud.post_with_retry

    def fraud_down(url, json, **kwargs):
        if url.startswith(settings.fraud_url):
            raise UpstreamError("fraud service timed out")
        return routed(url, json, **kwargs)

    monkeypatch.setattr(gateway_fraud, "post_with_retry", fraud_down)
    body = _pay(gateway_client, "4242424242424242", 1500, customer_ip="198.51.100.8")
    assert body["status"] == "succeeded"
    assert body["fraud_decision"] is None
    assert _fraud_row(body["id"]) is None
