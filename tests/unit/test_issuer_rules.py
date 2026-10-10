from common.models import DeclineReason
from services.issuer.accounts import Account
from services.issuer.rules import decide


def test_card_not_found():
    result = decide(None, 1000)
    assert not result.approved
    assert result.reason == DeclineReason.CARD_NOT_FOUND


def test_card_blocked():
    account = Account(card_number="4000000000000002", status="blocked", balance_cents=100_000)
    result = decide(account, 1000)
    assert not result.approved
    assert result.reason == DeclineReason.CARD_BLOCKED


def test_insufficient_funds():
    account = Account(card_number="4242424242424242", status="active", balance_cents=500)
    result = decide(account, 1000)
    assert not result.approved
    assert result.reason == DeclineReason.INSUFFICIENT_FUNDS


def test_approved():
    account = Account(card_number="4242424242424242", status="active", balance_cents=5000)
    result = decide(account, 1000)
    assert result.approved
    assert result.reason is None
