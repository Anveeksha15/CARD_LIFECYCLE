from datetime import UTC, datetime

from sqlmodel import Field, Session, SQLModel, create_engine

_engine = create_engine("sqlite:///gateway.db", connect_args={"check_same_thread": False})


class Token(SQLModel, table=True):
    token: str = Field(primary_key=True)
    card_number: str


class PaymentIntent(SQLModel, table=True):
    id: str = Field(primary_key=True)
    amount_cents: int
    token: str
    status: str
    decline_reason: str | None = None
    request_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def init_db() -> None:
    SQLModel.metadata.create_all(_engine)


def get_session() -> Session:
    return Session(_engine)
