import json

import redis

from common.config import settings

_PROCESSING_TTL_SECONDS = 60
_RESULT_TTL_SECONDS = 24 * 60 * 60

_redis = redis.from_url(settings.redis_url, decode_responses=True)


class IdempotencyInProgress(Exception):
    pass


def claim(key: str) -> dict | None:
    """Claim an idempotency key.

    Returns None if this caller now owns the key and should perform the
    operation. Returns the previously stored result dict if the key was
    already completed. Raises IdempotencyInProgress if another request with
    the same key is still being processed.
    """
    acquired = _redis.set(key, "processing", nx=True, ex=_PROCESSING_TTL_SECONDS)
    if acquired:
        return None

    value = _redis.get(key)
    if value == "processing":
        raise IdempotencyInProgress(key)
    return json.loads(value)


def store_result(key: str, result: dict) -> None:
    _redis.set(key, json.dumps(result), ex=_RESULT_TTL_SECONDS)
