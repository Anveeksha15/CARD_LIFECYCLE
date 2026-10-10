"""End-to-end demo against an already-running stack (docker compose up --build -d).

Walks through everything the project promises: a payment traveling through all
five services, a decline, a retried request that doesn't double-charge, and
settlement landing later.
"""

import time
import uuid

import httpx

from common.config import settings
from merchant_demo.checkout import GATEWAY_URL, buy


def main() -> None:
    print("=== 1. Happy path (Visa) ===")
    approved = buy("4242424242424242", 1500)

    print("\n=== 2. Decline (insufficient funds) ===")
    buy("4000000000009995", 500)

    print("\n=== 3. Idempotent replay (same Idempotency-Key twice) ===")
    # Unique per run so repeat demos don't replay a cached result from Redis
    # left over from an earlier run - the within-run replay is what matters.
    idempotency_key = f"demo-idem-key-{uuid.uuid4().hex[:8]}"
    first = buy("5555555555554444", 2000, idempotency_key=idempotency_key)
    second = buy("5555555555554444", 2000, idempotency_key=idempotency_key)
    assert first["id"] == second["id"], "replay should return the same payment_intent"
    print(f"confirmed: both calls returned {first['id']} - no double charge")

    wait_seconds = settings.settlement_delay_seconds + 2
    print(f"\n=== 4. Waiting {wait_seconds}s for settlement to land ===")
    time.sleep(wait_seconds)

    unsettled_ids = {
        intent["id"]
        for intent in httpx.get(
            f"{GATEWAY_URL}/v1/payment_intents", params={"unsettled": "true"}
        ).json()
    }
    if approved["id"] in unsettled_ids:
        print(f"{approved['id']} is still unsettled - give the settlement worker more time")
    else:
        print(f"{approved['id']} has settled - check settlement.db inside the settlement "
              "container for its ledger entries")


if __name__ == "__main__":
    main()
