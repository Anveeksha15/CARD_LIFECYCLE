"""Runs the real service chain in-process by routing common.http.post_with_retry's
call sites to each service's own FastAPI TestClient instead of real network calls.
A background thread + future.result(timeout=...) is used so that a slow handler
(the issuer's simulate_lost_response sleep) genuinely times out here the same way
a real httpx call would, including abandoning the still-running handler - this is
what makes the reversal scenario reproducible without Docker.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError

import pytest
from fastapi.testclient import TestClient

import services.acquirer.main as acquirer_main
import services.gateway.routes as gateway_routes
import services.issuer.main as issuer_main
import services.network.main as network_main
import services.processor.main as processor_main
from common.config import settings
from common.http import UpstreamError
from services.gateway.main import app as gateway_app

_EXECUTOR = ThreadPoolExecutor(max_workers=8)


@pytest.fixture
def gateway_client():
    return TestClient(gateway_app)


@pytest.fixture
def service_clients():
    return {
        settings.acquirer_url: TestClient(acquirer_main.app),
        settings.processor_url: TestClient(processor_main.app),
        settings.network_url: TestClient(network_main.app),
        settings.issuer_url: TestClient(issuer_main.app),
    }


@pytest.fixture(autouse=True)
def route_post_with_retry(monkeypatch, service_clients):
    def fake_post_with_retry(url, json, *, timeout=None, max_attempts=None, backoff_base=None):
        timeout = settings.request_timeout_seconds if timeout is None else timeout
        max_attempts = settings.max_retry_attempts if max_attempts is None else max_attempts
        backoff_base = settings.retry_backoff_base_seconds if backoff_base is None else backoff_base

        base_url, client = next(
            (b, c) for b, c in service_clients.items() if url.startswith(b)
        )
        path = url[len(base_url) :]

        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            future = _EXECUTOR.submit(client.post, path, json=json)
            try:
                resp = future.result(timeout=timeout)
                if resp.status_code < 500:
                    return resp
                last_exc = Exception(f"status {resp.status_code}")
            except FutureTimeoutError as exc:
                last_exc = exc

            if attempt < max_attempts:
                time.sleep(backoff_base * (2 ** (attempt - 1)))

        raise UpstreamError(f"failed to reach {url} after {max_attempts} attempts") from last_exc

    monkeypatch.setattr(acquirer_main, "post_with_retry", fake_post_with_retry)
    monkeypatch.setattr(processor_main, "post_with_retry", fake_post_with_retry)
    monkeypatch.setattr(network_main, "post_with_retry", fake_post_with_retry)
    monkeypatch.setattr(gateway_routes, "post_with_retry", fake_post_with_retry)
