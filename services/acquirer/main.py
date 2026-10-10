import httpx
from fastapi import FastAPI, HTTPException

from common.config import settings
from common.models import (
    AcquirerAuthorizeRequest,
    AuthorizeRequest,
    AuthorizeResponse,
    DeclineReason,
)

app = FastAPI(title="acquirer")

# Toy merchant directory: api_key -> merchant_id. A real acquirer underwrites
# and onboards merchants; this sim just checks the key is one we recognize.
_MERCHANTS = {
    "sk_test_demo_merchant": "merchant_demo",
}


def is_valid_merchant(api_key: str) -> bool:
    return api_key in _MERCHANTS


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "acquirer"}


@app.post("/v1/authorize", response_model=AuthorizeResponse)
def authorize(req: AcquirerAuthorizeRequest) -> AuthorizeResponse:
    if not is_valid_merchant(req.api_key):
        return AuthorizeResponse(approved=False, reason=DeclineReason.INVALID_MERCHANT)

    payload = AuthorizeRequest(card_number=req.card_number, amount_cents=req.amount_cents)
    try:
        resp = httpx.post(
            f"{settings.processor_url}/v1/authorize", json=payload.model_dump(), timeout=5.0
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="processor unreachable") from exc

    return AuthorizeResponse.model_validate(resp.json())
