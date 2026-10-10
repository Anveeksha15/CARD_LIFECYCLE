from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.models import AuthorizeRequest, AuthorizeResponse
from services.issuer.accounts import get_account, init_db
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
    return decide(account, req.amount_cents)
