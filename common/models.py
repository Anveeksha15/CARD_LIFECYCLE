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
    INVALID_MERCHANT = "invalid_merchant"


class AuthorizeRequest(BaseModel):
    card_number: str
    amount_cents: int = Field(gt=0)


class NetworkAuthorizeRequest(AuthorizeRequest):
    network: Network


class AcquirerAuthorizeRequest(AuthorizeRequest):
    api_key: str


class AuthorizeResponse(BaseModel):
    approved: bool
    reason: DeclineReason | None = None
    network: Network | None = None


class TokenizeRequest(BaseModel):
    card_number: str


class TokenizeResponse(BaseModel):
    token: str


class PaymentIntentCreateRequest(BaseModel):
    amount_cents: int = Field(gt=0)
    token: str


class PaymentIntentResponse(BaseModel):
    id: str
    amount_cents: int
    status: str
    decline_reason: DeclineReason | None = None
