from sqlmodel import Session

from common.config import settings
from services.gateway.db import PaymentIntent, get_session
from services.issuer.accounts import Authorization, _engine

AUTH_HEADERS = {"Authorization": "Bearer sk_test_demo_merchant"}


def test_lost_response_triggers_reversal(gateway_client, monkeypatch):
    # The issuer still runs its real simulate_lost_response sleep (see
    # tests/integration/conftest.py) - shrink it so the test stays fast.
    monkeypatch.setattr(settings, "simulate_lost_response_delay_seconds", 0.05)

    token_resp = gateway_client.post("/v1/tokens", json={"card_number": "4242424242424242"})
    token = token_resp.json()["token"]

    resp = gateway_client.post(
        "/v1/payment_intents",
        json={"amount_cents": 1000, "token": token},
        headers={**AUTH_HEADERS, "X-Simulate-Lost-Response": "true"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["decline_reason"] == "upstream_timeout"

    with get_session() as session:
        intent = session.get(PaymentIntent, body["id"])
        request_id = intent.request_id

    # The issuer approved and persisted the authorization before "losing" the
    # response - confirm it was found and reversed using the request_id the
    # gateway generated, even though it never saw the approval come back.
    with Session(_engine) as session:
        record = session.get(Authorization, request_id)

    assert record is not None
    assert record.status == "reversed"
