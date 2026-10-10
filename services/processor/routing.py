from common.models import Network


class UnsupportedNetworkError(Exception):
    pass


def get_network(card_number: str) -> Network:
    digits = card_number.strip()

    if digits.startswith("4"):
        return Network.VISA

    if digits[:2] in {"34", "37"}:
        return Network.AMEX

    if digits[:2].isdigit() and 51 <= int(digits[:2]) <= 55:
        return Network.MASTERCARD

    if digits[:4].isdigit() and 2221 <= int(digits[:4]) <= 2720:
        return Network.MASTERCARD

    raise UnsupportedNetworkError(f"no network route for card prefix {digits[:6]}")
