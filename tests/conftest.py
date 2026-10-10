import pytest

from services.gateway.db import init_db as init_gateway_db
from services.issuer.accounts import init_db as init_issuer_db


@pytest.fixture(scope="session", autouse=True)
def _init_dbs():
    init_gateway_db()
    init_issuer_db()
