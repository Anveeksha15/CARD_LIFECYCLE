import uuid

from services.settlement.ledger import entries_for, init_db, record_settlement


def test_record_settlement_is_balanced():
    init_db()
    pi_id = f"pi_test_{uuid.uuid4().hex[:8]}"
    record_settlement(pi_id, amount_cents=1000, fee_cents=29)

    entries = entries_for(pi_id)
    assert len(entries) == 6

    debits = sum(e.amount_cents for e in entries if e.direction == "debit")
    credits = sum(e.amount_cents for e in entries if e.direction == "credit")
    assert debits == credits


def test_record_settlement_fee_split():
    init_db()
    pi_id = f"pi_test_{uuid.uuid4().hex[:8]}"
    record_settlement(pi_id, amount_cents=1000, fee_cents=29)

    entries = entries_for(pi_id)
    merchant_credit = next(e for e in entries if e.account == "merchant_payable")
    fee_credit = next(e for e in entries if e.account == "platform_fee_revenue")

    assert merchant_credit.amount_cents == 971
    assert fee_credit.amount_cents == 29
