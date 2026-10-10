import secrets

from common.luhn import is_luhn_valid
from services.gateway.db import Token, get_session


class InvalidCardError(Exception):
    pass


def tokenize(card_number: str) -> str:
    if not is_luhn_valid(card_number):
        raise InvalidCardError("card number fails Luhn check")

    token = f"tok_{secrets.token_hex(12)}"
    with get_session() as session:
        session.add(Token(token=token, card_number=card_number))
        session.commit()
    return token


def detokenize(token: str) -> str | None:
    with get_session() as session:
        record = session.get(Token, token)
        return record.card_number if record else None
