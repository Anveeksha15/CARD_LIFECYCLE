from fastapi import FastAPI, HTTPException

from common.config import settings
from common.http import UpstreamError, post_with_retry
from common.models import (
    AuthorizeRequest,
    AuthorizeResponse,
    DeclineReason,
    NetworkAuthorizeRequest,
    ReversalRequest,
    ReversalResponse,
)
from services.processor.routing import UnsupportedNetworkError, get_network

app = FastAPI(title="processor")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "processor"}


@app.post("/v1/authorize", response_model=AuthorizeResponse)
def authorize(req: AuthorizeRequest) -> AuthorizeResponse:
    try:
        network = get_network(req.card_number)
    except UnsupportedNetworkError:
        return AuthorizeResponse(approved=False, reason=DeclineReason.UNSUPPORTED_NETWORK)

    payload = NetworkAuthorizeRequest(
        card_number=req.card_number,
        amount_cents=req.amount_cents,
        network=network,
        request_id=req.request_id,
        simulate_lost_response=req.simulate_lost_response,
    )
    try:
        resp = post_with_retry(f"{settings.network_url}/v1/authorize", payload.model_dump())
    except UpstreamError as exc:
        raise HTTPException(status_code=503, detail="network unreachable") from exc

    return AuthorizeResponse.model_validate(resp.json())


@app.post("/v1/reversals", response_model=ReversalResponse)
def reverse(req: ReversalRequest) -> ReversalResponse:
    try:
        resp = post_with_retry(
            f"{settings.network_url}/v1/reversals", req.model_dump(), max_attempts=1
        )
    except UpstreamError as exc:
        raise HTTPException(status_code=503, detail="network unreachable") from exc

    return ReversalResponse.model_validate(resp.json())
