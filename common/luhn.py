"""Luhn checksum validation and fake test card numbers.

All numbers below are Stripe's published test cards (stripe.com/docs/testing)
or satisfy Luhn without belonging to any real issuer range. Never use real
card data in this project.
"""

STRIPE_TEST_VISA = "4242424242424242"
STRIPE_TEST_MASTERCARD = "5555555555554444"
STRIPE_TEST_AMEX = "378282246310005"
STRIPE_TEST_DECLINE_INSUFFICIENT_FUNDS = "4000000000009995"

TEST_CARD_NUMBERS = [
    STRIPE_TEST_VISA,
    STRIPE_TEST_MASTERCARD,
    STRIPE_TEST_AMEX,
    STRIPE_TEST_DECLINE_INSUFFICIENT_FUNDS,
]


def is_luhn_valid(number: str) -> bool:
    digits = [c for c in number if c.isdigit()]
    if len(digits) != len(number) or len(digits) < 2:
        return False

    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0
