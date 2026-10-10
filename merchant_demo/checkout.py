"""Acts as the merchant: tokenizes a card, then creates a payment_intent."""

import sys

import httpx

GATEWAY_URL = "http://localhost:8000"
API_KEY = "sk_test_demo_merchant"


def buy(card_number: str, amount_cents: int) -> None:
    token_resp = httpx.post(f"{GATEWAY_URL}/v1/tokens", json={"card_number": card_number})
    token_resp.raise_for_status()
    token = token_resp.json()["token"]
    print(f"tokenized card -> {token}")

    intent_resp = httpx.post(
        f"{GATEWAY_URL}/v1/payment_intents",
        json={"amount_cents": amount_cents, "token": token},
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    intent_resp.raise_for_status()
    print(intent_resp.json())


if __name__ == "__main__":
    card = sys.argv[1] if len(sys.argv) > 1 else "4242424242424242"
    amount = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    buy(card, amount)
