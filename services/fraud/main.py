import time
from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI, Request

from common.config import settings
from common.models import (
    FraudDecision,
    FraudOutcomeRequest,
    FraudScoreRequest,
    FraudScoreResponse,
)
from services.fraud.features import Tx, observe, record_outcome
from services.fraud.model import FraudModel

_redis = redis.from_url(settings.redis_url, decode_responses=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = FraudModel.load(settings.fraud_model_path)
    yield


app = FastAPI(title="fraud", lifespan=lifespan)


def decide(risk: float, block_threshold: float) -> FraudDecision:
    if risk >= block_threshold:
        return FraudDecision.BLOCK
    if risk >= settings.fraud_review_threshold:
        return FraudDecision.REVIEW
    return FraudDecision.ALLOW


@app.get("/health")
def health(request: Request) -> dict:
    model: FraudModel = request.app.state.model
    return {"status": "ok", "service": "fraud", "model": model.name, "threshold": model.threshold}


@app.post("/v1/score", response_model=FraudScoreResponse)
def score(req: FraudScoreRequest, request: Request) -> FraudScoreResponse:
    model: FraudModel = request.app.state.model
    tx = Tx(req.event_id, req.card_fingerprint, req.bin, req.ip, req.email)
    # Records this attempt before scoring it, so a blocked attempt still counts.
    features = observe(_redis, tx, now=time.time())
    risk = model.predict(features, req.amount_cents)
    return FraudScoreResponse(
        risk=risk, decision=decide(risk, model.threshold), model=model.name, features=features
    )


@app.post("/v1/outcome")
def outcome(req: FraudOutcomeRequest) -> dict:
    tx = Tx(req.event_id, req.card_fingerprint, req.bin, req.ip, req.email)
    record_outcome(_redis, tx, now=time.time(), declined=req.declined)
    return {"recorded": True}
