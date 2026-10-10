from fastapi import FastAPI, HTTPException

from common.config import settings
from common.http import UpstreamError, post_with_retry
from common.models import (
    AuthorizeRequest,
    AuthorizeResponse,
    NetworkAuthorizeRequest,
    ReversalRequest,
    ReversalResponse,
)

app = FastAPI(title="network")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "network"}


@app.post("/v1/authorize", response_model=AuthorizeResponse)
def authorize(req: NetworkAuthorizeRequest) -> AuthorizeResponse:
    issuer_req = AuthorizeRequest(
        card_number=req.card_number,
        amount_cents=req.amount_cents,
        request_id=req.request_id,
        simulate_lost_response=req.simulate_lost_response,
    )
    try:
        resp = post_with_retry(f"{settings.issuer_url}/v1/authorize", issuer_req.model_dump())
    except UpstreamError as exc:
        raise HTTPException(status_code=503, detail="issuer unreachable") from exc

    result = AuthorizeResponse.model_validate(resp.json())
    result.network = req.network
    return result


@app.post("/v1/reversals", response_model=ReversalResponse)
def reverse(req: ReversalRequest) -> ReversalResponse:
    try:
        resp = post_with_retry(
            f"{settings.issuer_url}/v1/reversals", req.model_dump(), max_attempts=1
        )
    except UpstreamError as exc:
        raise HTTPException(status_code=503, detail="issuer unreachable") from exc

    return ReversalResponse.model_validate(resp.json())
