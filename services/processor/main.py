import httpx
from fastapi import FastAPI, HTTPException

from common.config import settings
from common.models import (
    AuthorizeRequest,
    AuthorizeResponse,
    DeclineReason,
    NetworkAuthorizeRequest,
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
        card_number=req.card_number, amount_cents=req.amount_cents, network=network
    )
    try:
        resp = httpx.post(
            f"{settings.network_url}/v1/authorize", json=payload.model_dump(), timeout=5.0
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="network unreachable") from exc

    return AuthorizeResponse.model_validate(resp.json())
