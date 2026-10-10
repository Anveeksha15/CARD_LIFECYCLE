import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.config import settings
from common.models import AuthorizeRequest, AuthorizeResponse, ReversalRequest, ReversalResponse
from services.issuer.accounts import (
    get_account,
    init_db,
    record_authorization,
    reverse_authorization,
)
from services.issuer.rules import decide


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="issuer", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "issuer"}


@app.post("/v1/authorize", response_model=AuthorizeResponse)
def authorize(req: AuthorizeRequest) -> AuthorizeResponse:
    account = get_account(req.card_number)
    result = decide(account, req.amount_cents)

    if result.approved:
        record_authorization(req.request_id, req.card_number, req.amount_cents)
        if req.simulate_lost_response:
            time.sleep(settings.simulate_lost_response_delay_seconds)

    return result


@app.post("/v1/reversals", response_model=ReversalResponse)
def reverse(req: ReversalRequest) -> ReversalResponse:
    return ReversalResponse(reversed=reverse_authorization(req.request_id))
