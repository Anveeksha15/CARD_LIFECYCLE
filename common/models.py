from enum import StrEnum

from pydantic import BaseModel, Field


class Network(StrEnum):
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"


class DeclineReason(StrEnum):
    INSUFFICIENT_FUNDS = "insufficient_funds"
    CARD_BLOCKED = "card_blocked"
    CARD_NOT_FOUND = "card_not_found"
    UNSUPPORTED_NETWORK = "unsupported_network"


class AuthorizeRequest(BaseModel):
    card_number: str
    amount_cents: int = Field(gt=0)


class NetworkAuthorizeRequest(AuthorizeRequest):
    network: Network


class AuthorizeResponse(BaseModel):
    approved: bool
    reason: DeclineReason | None = None
    network: Network | None = None
