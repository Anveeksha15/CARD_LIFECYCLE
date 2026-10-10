import time
from datetime import UTC, datetime

import httpx

from common.config import settings
from services.settlement.ledger import init_db, record_settlement


def run_once() -> int:
    resp = httpx.get(
        f"{settings.gateway_url}/v1/payment_intents",
        params={"unsettled": "true"},
        timeout=5.0,
    )
    resp.raise_for_status()

    now = datetime.now(UTC)
    settled_count = 0

    for candidate in resp.json():
        created_at = datetime.fromisoformat(candidate["created_at"])
        if (now - created_at).total_seconds() < settings.settlement_delay_seconds:
            continue

        amount_cents = candidate["amount_cents"]
        fee_cents = amount_cents * settings.settlement_fee_bps // 10000
        record_settlement(candidate["id"], amount_cents, fee_cents)

        httpx.post(
            f"{settings.gateway_url}/v1/payment_intents/{candidate['id']}/settle", timeout=5.0
        )
        settled_count += 1

    return settled_count


def main() -> None:
    init_db()
    print("settlement worker started")
    while True:
        try:
            settled_count = run_once()
            if settled_count:
                print(f"settled {settled_count} payment intent(s)")
        except httpx.HTTPError as exc:
            print(f"settlement poll failed: {exc}")
        time.sleep(settings.settlement_poll_interval_seconds)


if __name__ == "__main__":
    main()
