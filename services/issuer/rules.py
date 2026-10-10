from common.models import AuthorizeResponse, DeclineReason
from services.issuer.accounts import Account


def decide(account: Account | None, amount_cents: int) -> AuthorizeResponse:
    if account is None:
        return AuthorizeResponse(approved=False, reason=DeclineReason.CARD_NOT_FOUND)
    if account.status == "blocked":
        return AuthorizeResponse(approved=False, reason=DeclineReason.CARD_BLOCKED)
    if account.balance_cents < amount_cents:
        return AuthorizeResponse(approved=False, reason=DeclineReason.INSUFFICIENT_FUNDS)
    return AuthorizeResponse(approved=True)
