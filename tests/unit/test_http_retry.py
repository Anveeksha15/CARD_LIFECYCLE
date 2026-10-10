import httpx
import pytest
import respx

from common.http import UpstreamError, post_with_retry

URL = "http://upstream.test/v1/authorize"


@respx.mock
def test_succeeds_after_transient_failures():
    route = respx.post(URL)
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(503),
        httpx.Response(200, json={"approved": True}),
    ]

    resp = post_with_retry(URL, {"amount_cents": 100}, max_attempts=3, backoff_base=0.01)

    assert resp.status_code == 200
    assert route.call_count == 3


@respx.mock
def test_raises_after_exhausting_attempts():
    respx.post(URL).mock(return_value=httpx.Response(503))

    with pytest.raises(UpstreamError):
        post_with_retry(URL, {"amount_cents": 100}, max_attempts=2, backoff_base=0.01)
