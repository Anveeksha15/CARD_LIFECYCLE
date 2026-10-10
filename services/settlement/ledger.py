from datetime import UTC, datetime

from sqlmodel import Field, Session, SQLModel, create_engine, select

_engine = create_engine("sqlite:///settlement.db", connect_args={"check_same_thread": False})


class LedgerEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    payment_intent_id: str
    account: str
    direction: str  # debit | credit
    amount_cents: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def init_db() -> None:
    SQLModel.metadata.create_all(_engine)


def record_settlement(payment_intent_id: str, amount_cents: int, fee_cents: int) -> None:
    """Move money issuer -> acquirer -> merchant (minus fee), as balanced debit/credit pairs."""
    merchant_amount_cents = amount_cents - fee_cents

    movements = [
        ("issuer_clearing", "debit", amount_cents),
        ("acquirer_clearing", "credit", amount_cents),
        ("acquirer_clearing", "debit", merchant_amount_cents),
        ("merchant_payable", "credit", merchant_amount_cents),
        ("acquirer_clearing", "debit", fee_cents),
        ("platform_fee_revenue", "credit", fee_cents),
    ]

    with Session(_engine) as session:
        for account, direction, amount in movements:
            session.add(
                LedgerEntry(
                    payment_intent_id=payment_intent_id,
                    account=account,
                    direction=direction,
                    amount_cents=amount,
                )
            )
        session.commit()


def entries_for(payment_intent_id: str) -> list[LedgerEntry]:
    with Session(_engine) as session:
        return list(
            session.exec(
                select(LedgerEntry).where(LedgerEntry.payment_intent_id == payment_intent_id)
            ).all()
        )
