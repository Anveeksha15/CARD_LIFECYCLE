AUTH_HEADERS = {"Authorization": "Bearer sk_test_demo_merchant"}


def test_replayed_idempotency_key_returns_same_intent(gateway_client):
    token_resp = gateway_client.post("/v1/tokens", json={"card_number": "5555555555554444"})
    token = token_resp.json()["token"]

    headers = {**AUTH_HEADERS, "Idempotency-Key": "test-idem-key-1"}
    body = {"amount_cents": 2000, "token": token}

    first = gateway_client.post("/v1/payment_intents", json=body, headers=headers)
    second = gateway_client.post("/v1/payment_intents", json=body, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_concurrent_in_progress_key_is_rejected(gateway_client, monkeypatch):
    from services.gateway import routes as gateway_routes
    from services.gateway.idempotency import IdempotencyInProgress

    def raise_in_progress(key):
        raise IdempotencyInProgress(key)

    monkeypatch.setattr(gateway_routes, "claim", raise_in_progress)

    token_resp = gateway_client.post("/v1/tokens", json={"card_number": "4242424242424242"})
    token = token_resp.json()["token"]

    resp = gateway_client.post(
        "/v1/payment_intents",
        json={"amount_cents": 500, "token": token},
        headers={**AUTH_HEADERS, "Idempotency-Key": "in-flight-key"},
    )
    assert resp.status_code == 409
