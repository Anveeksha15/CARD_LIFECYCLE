from common.luhn import (
    STRIPE_TEST_AMEX,
    STRIPE_TEST_DECLINE_INSUFFICIENT_FUNDS,
    STRIPE_TEST_GENERIC_DECLINE,
    STRIPE_TEST_MASTERCARD,
    STRIPE_TEST_VISA,
)
from services.issuer.accounts import init_db, upsert_account


def main() -> None:
    init_db()
    upsert_account(STRIPE_TEST_VISA, status="active", balance_cents=500_000)
    upsert_account(STRIPE_TEST_MASTERCARD, status="active", balance_cents=250_000)
    upsert_account(STRIPE_TEST_AMEX, status="active", balance_cents=1_000_000)
    upsert_account(STRIPE_TEST_DECLINE_INSUFFICIENT_FUNDS, status="active", balance_cents=0)
    upsert_account(STRIPE_TEST_GENERIC_DECLINE, status="blocked", balance_cents=100_000)
    print("Seeded issuer accounts.")


if __name__ == "__main__":
    main()
