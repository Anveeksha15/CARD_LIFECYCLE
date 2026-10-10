import services.settlement.worker as worker
from common.config import settings
from services.settlement.ledger import entries_for, init_db

AUTH_HEADERS = {"Authorization": "Bearer sk_test_demo_merchant"}


class _FakeHttpx:
    """Delegates worker.py's httpx.get/.post calls to the gateway TestClient,
    without touching the real, shared httpx module used elsewhere.
    """

    def __init__(self, client):
        self.get = client.get
        self.post = client.post


def test_worker_settles_eligible_intent(gateway_client, monkeypatch):
    init_db()
    monkeypatch.setattr(settings, "settlement_delay_seconds", 0)
    monkeypatch.setattr(worker, "httpx", _FakeHttpx(gateway_client))

    token = gateway_client.post(
        "/v1/tokens", json={"card_number": "4242424242424242"}
    ).json()["token"]
    intent = gateway_client.post(
        "/v1/payment_intents",
        json={"amount_cents": 1000, "token": token},
        headers=AUTH_HEADERS,
    ).json()
    assert intent["status"] == "succeeded"
    assert intent["settled"] is False

    settled_count = worker.run_once()
    assert settled_count >= 1

    unsettled_ids = {
        i["id"]
        for i in gateway_client.get("/v1/payment_intents", params={"unsettled": "true"}).json()
    }
    assert intent["id"] not in unsettled_ids

    entries = entries_for(intent["id"])
    assert len(entries) == 6
    debits = sum(e.amount_cents for e in entries if e.direction == "debit")
    credits = sum(e.amount_cents for e in entries if e.direction == "credit")
    # Three balanced movements (issuer->acquirer, acquirer->merchant,
    # acquirer->fee) each move amount_cents total, so debits == credits == 2x.
    assert debits == credits == 2 * 1000
