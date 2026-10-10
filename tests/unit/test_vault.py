import pytest

from services.gateway.vault import InvalidCardError, detokenize, tokenize


def test_tokenize_detokenize_roundtrip():
    token = tokenize("4242424242424242")
    assert token.startswith("tok_")
    assert detokenize(token) == "4242424242424242"


def test_unknown_token_returns_none():
    assert detokenize("tok_doesnotexist") is None


def test_invalid_card_rejected():
    with pytest.raises(InvalidCardError):
        tokenize("4242424242424241")
