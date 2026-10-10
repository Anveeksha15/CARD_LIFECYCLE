import uuid

import httpx
from fastapi import APIRouter, Header, HTTPException

from common.config import settings
from common.models import (
    AcquirerAuthorizeRequest,
    AuthorizeResponse,
    PaymentIntentCreateRequest,
    PaymentIntentResponse,
    TokenizeRequest,
    TokenizeResponse,
)
from services.gateway.db import PaymentIntent, get_session
from services.gateway.vault import InvalidCardError, detokenize, tokenize

router = APIRouter()


@router.post("/v1/tokens", response_model=TokenizeResponse)
def create_token(req: TokenizeRequest) -> TokenizeResponse:
    try:
        token = tokenize(req.card_number)
    except InvalidCardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TokenizeResponse(token=token)


@router.post("/v1/payment_intents", response_model=PaymentIntentResponse)
def create_payment_intent(
    req: PaymentIntentCreateRequest,
    authorization: str = Header(..., alias="Authorization"),
) -> PaymentIntentResponse:
    api_key = authorization.removeprefix("Bearer ").strip()

    card_number = detokenize(req.token)
    if card_number is None:
        raise HTTPException(status_code=400, detail="unknown or expired token")

    intent_id = f"pi_{uuid.uuid4().hex[:16]}"

    payload = AcquirerAuthorizeRequest(
        api_key=api_key, card_number=card_number, amount_cents=req.amount_cents
    )
    try:
        resp = httpx.post(
            f"{settings.acquirer_url}/v1/authorize", json=payload.model_dump(), timeout=5.0
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="acquirer unreachable") from exc

    result = AuthorizeResponse.model_validate(resp.json())
    status = "succeeded" if result.approved else "failed"

    with get_session() as session:
        session.add(
            PaymentIntent(
                id=intent_id,
                amount_cents=req.amount_cents,
                token=req.token,
                status=status,
                decline_reason=result.reason,
            )
        )
        session.commit()

    return PaymentIntentResponse(
        id=intent_id,
        amount_cents=req.amount_cents,
        status=status,
        decline_reason=result.reason,
    )
