import json

from fastapi import FastAPI, HTTPException, Request

from common.config import settings
from common.signing import verify_signature

app = FastAPI(title="merchant-demo-webhook-receiver")

_received_events: list[dict] = []


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "merchant-demo"}


@app.get("/events")
def events() -> list[dict]:
    return _received_events


@app.post("/webhook")
async def webhook(request: Request) -> dict:
    body = await request.body()
    signature = request.headers.get("X-Signature", "")
    if not verify_signature(body, signature, settings.webhook_secret):
        raise HTTPException(status_code=400, detail="invalid signature")

    event = json.loads(body)
    _received_events.append(event)
    print(f"received webhook: {event}")
    return {"received": True}
