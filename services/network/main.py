import httpx
from fastapi import FastAPI, HTTPException

from common.config import settings
from common.models import AuthorizeRequest, AuthorizeResponse, NetworkAuthorizeRequest

app = FastAPI(title="network")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "network"}


@app.post("/v1/authorize", response_model=AuthorizeResponse)
def authorize(req: NetworkAuthorizeRequest) -> AuthorizeResponse:
    issuer_req = AuthorizeRequest(card_number=req.card_number, amount_cents=req.amount_cents)
    try:
        resp = httpx.post(
            f"{settings.issuer_url}/v1/authorize", json=issuer_req.model_dump(), timeout=5.0
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="issuer unreachable") from exc

    result = AuthorizeResponse.model_validate(resp.json())
    result.network = req.network
    return result
