AUTH_HEADERS = {"Authorization": "Bearer sk_test_demo_merchant"}


def _tokenize(gateway_client, card_number: str) -> str:
    resp = gateway_client.post("/v1/tokens", json={"card_number": card_number})
    assert resp.status_code == 200
    return resp.json()["token"]


def test_approved_payment_intent(gateway_client):
    token = _tokenize(gateway_client, "4242424242424242")
    resp = gateway_client.post(
        "/v1/payment_intents",
        json={"amount_cents": 1500, "token": token},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "succeeded"
    assert body["decline_reason"] is None


def test_insufficient_funds_decline(gateway_client):
    token = _tokenize(gateway_client, "4000000000009995")
    resp = gateway_client.post(
        "/v1/payment_intents",
        json={"amount_cents": 500, "token": token},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["decline_reason"] == "insufficient_funds"


def test_card_blocked_decline(gateway_client):
    token = _tokenize(gateway_client, "4000000000000002")
    resp = gateway_client.post(
        "/v1/payment_intents",
        json={"amount_cents": 500, "token": token},
        headers=AUTH_HEADERS,
    )
    assert resp.json()["decline_reason"] == "card_blocked"


def test_invalid_merchant_decline(gateway_client):
    token = _tokenize(gateway_client, "4242424242424242")
    resp = gateway_client.post(
        "/v1/payment_intents",
        json={"amount_cents": 500, "token": token},
        headers={"Authorization": "Bearer sk_test_not_a_real_merchant"},
    )
    assert resp.json()["decline_reason"] == "invalid_merchant"


def test_unknown_token_rejected(gateway_client):
    resp = gateway_client.post(
        "/v1/payment_intents",
        json={"amount_cents": 500, "token": "tok_doesnotexist"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400
