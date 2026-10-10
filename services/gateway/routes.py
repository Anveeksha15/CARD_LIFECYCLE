import uuid

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from common.config import settings
from common.http import UpstreamError, post_with_retry
from common.models import (
    AcquirerAuthorizeRequest,
    AuthorizeResponse,
    DeclineReason,
    PaymentIntentCreateRequest,
    PaymentIntentResponse,
    ReversalRequest,
    TokenizeRequest,
    TokenizeResponse,
)
from services.gateway.db import PaymentIntent, get_session
from services.gateway.idempotency import IdempotencyInProgress, claim, store_result
from services.gateway.vault import InvalidCardError, detokenize, tokenize
from services.gateway.webhooks import send_webhook

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
    background_tasks: BackgroundTasks,
    authorization: str = Header(..., alias="Authorization"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    simulate_lost_response: bool = Header(False, alias="X-Simulate-Lost-Response"),
) -> PaymentIntentResponse:
    api_key = authorization.removeprefix("Bearer ").strip()

    idem_redis_key = f"idempotency:{api_key}:{idempotency_key}" if idempotency_key else None
    if idem_redis_key:
        try:
            cached = claim(idem_redis_key)
        except IdempotencyInProgress as exc:
            raise HTTPException(
                status_code=409,
                detail="a request with this idempotency key is already being processed",
            ) from exc
        if cached is not None:
            return PaymentIntentResponse(**cached)

    card_number = detokenize(req.token)
    if card_number is None:
        raise HTTPException(status_code=400, detail="unknown or expired token")

    intent_id = f"pi_{uuid.uuid4().hex[:16]}"
    request_id = uuid.uuid4().hex

    payload = AcquirerAuthorizeRequest(
        api_key=api_key,
        card_number=card_number,
        amount_cents=req.amount_cents,
        request_id=request_id,
        simulate_lost_response=simulate_lost_response,
    )

    try:
        resp = post_with_retry(f"{settings.acquirer_url}/v1/authorize", payload.model_dump())
        result = AuthorizeResponse.model_validate(resp.json())
    except UpstreamError:
        # We don't know whether the issuer approved before the response was
        # lost - best-effort reverse whatever it may have recorded for this
        # request_id, then surface it to the merchant as a plain failure.
        try:
            post_with_retry(
                f"{settings.acquirer_url}/v1/reversals",
                ReversalRequest(request_id=request_id).model_dump(),
                max_attempts=1,
            )
        except UpstreamError:
            pass
        result = AuthorizeResponse(approved=False, reason=DeclineReason.UPSTREAM_TIMEOUT)

    status = "succeeded" if result.approved else "failed"

    with get_session() as session:
        session.add(
            PaymentIntent(
                id=intent_id,
                amount_cents=req.amount_cents,
                token=req.token,
                status=status,
                decline_reason=result.reason,
                request_id=request_id,
            )
        )
        session.commit()

    response = PaymentIntentResponse(
        id=intent_id,
        amount_cents=req.amount_cents,
        status=status,
        decline_reason=result.reason,
    )

    if idem_redis_key:
        store_result(idem_redis_key, response.model_dump(mode="json"))

    background_tasks.add_task(
        send_webhook,
        settings.merchant_webhook_url,
        {
            "type": "payment_intent.succeeded" if result.approved else "payment_intent.failed",
            "id": intent_id,
            "amount_cents": req.amount_cents,
            "status": status,
            "decline_reason": result.reason,
        },
    )

    return response
