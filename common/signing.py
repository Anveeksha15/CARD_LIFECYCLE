"""HMAC sign/verify for webhooks, mirroring Stripe's t=<ts>,v1=<hmac> scheme."""

import hashlib
import hmac
import time


def sign_payload(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    timestamp = int(time.time()) if timestamp is None else timestamp
    signed_payload = f"{timestamp}.{payload.decode()}"
    signature = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def verify_signature(
    payload: bytes, header: str, secret: str, tolerance_seconds: int = 300
) -> bool:
    try:
        parts = dict(part.split("=", 1) for part in header.split(","))
        timestamp = int(parts["t"])
        expected_signature = parts["v1"]
    except (KeyError, ValueError):
        return False

    if abs(time.time() - timestamp) > tolerance_seconds:
        return False

    signed_payload = f"{timestamp}.{payload.decode()}"
    computed_signature = hmac.new(
        secret.encode(), signed_payload.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_signature, expected_signature)
