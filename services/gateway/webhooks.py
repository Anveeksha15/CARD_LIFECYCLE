import json

import httpx

from common.config import settings
from common.signing import sign_payload


def send_webhook(url: str, event: dict) -> None:
    """Best-effort webhook delivery. No retry queue - see docs/decisions.md."""
    payload = json.dumps(event).encode()
    signature = sign_payload(payload, settings.webhook_secret)
    try:
        httpx.post(
            url,
            content=payload,
            headers={"Content-Type": "application/json", "X-Signature": signature},
            timeout=5.0,
        )
    except httpx.HTTPError:
        pass
