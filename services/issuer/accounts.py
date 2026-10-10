from sqlmodel import Field, Session, SQLModel, create_engine

_engine = create_engine("sqlite:///issuer.db", connect_args={"check_same_thread": False})


class Account(SQLModel, table=True):
    card_number: str = Field(primary_key=True)
    status: str = "active"  # active | blocked
    balance_cents: int = 0


def init_db() -> None:
    SQLModel.metadata.create_all(_engine)


def get_account(card_number: str) -> Account | None:
    with Session(_engine) as session:
        return session.get(Account, card_number)


def upsert_account(card_number: str, status: str, balance_cents: int) -> None:
    with Session(_engine) as session:
        account = session.get(Account, card_number)
        if account is None:
            account = Account(card_number=card_number, status=status, balance_cents=balance_cents)
        else:
            account.status = status
            account.balance_cents = balance_cents
        session.add(account)
        session.commit()
