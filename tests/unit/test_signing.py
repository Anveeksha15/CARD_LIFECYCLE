import time

from common.signing import sign_payload, verify_signature

SECRET = "test-secret"


def test_roundtrip_verifies():
    payload = b'{"id": "evt_1"}'
    header = sign_payload(payload, SECRET)
    assert verify_signature(payload, header, SECRET)


def test_tampered_payload_fails():
    payload = b'{"id": "evt_1"}'
    header = sign_payload(payload, SECRET)
    assert not verify_signature(b'{"id": "evt_2"}', header, SECRET)


def test_wrong_secret_fails():
    payload = b'{"id": "evt_1"}'
    header = sign_payload(payload, SECRET)
    assert not verify_signature(payload, header, "wrong-secret")


def test_stale_timestamp_fails():
    payload = b'{"id": "evt_1"}'
    old_timestamp = int(time.time()) - 600
    header = sign_payload(payload, SECRET, timestamp=old_timestamp)
    assert not verify_signature(payload, header, SECRET, tolerance_seconds=300)


def test_malformed_header_fails():
    assert not verify_signature(b"{}", "not-a-valid-header", SECRET)
