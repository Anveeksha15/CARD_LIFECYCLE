from services.gateway.fraud import build_request, fingerprint


def test_fingerprint_is_stable_and_card_specific():
    assert fingerprint("4242424242424242") == fingerprint("4242424242424242")
    assert fingerprint("4242424242424242") != fingerprint("5555555555554444")
    assert "4242424242424242" not in fingerprint("4242424242424242")


def test_request_hides_secrets_and_isolates_missing_email():
    req = build_request("4242424242424242", 100, "1.2.3.4", None, "pi_1", "sk_test_secret")
    assert req.bin == "424242"
    assert "sk_test_secret" not in req.model_dump_json()
    assert "4242424242424242" not in req.model_dump_json()
    other = build_request("4242424242424242", 100, "1.2.3.4", None, "pi_2", "sk_test_secret")
    assert req.email != other.email
