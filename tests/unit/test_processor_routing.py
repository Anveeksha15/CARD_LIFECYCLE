import pytest

from common.models import Network
from services.processor.routing import UnsupportedNetworkError, get_network


@pytest.mark.parametrize(
    "card_number, expected",
    [
        ("4242424242424242", Network.VISA),
        ("5555555555554444", Network.MASTERCARD),
        ("378282246310005", Network.AMEX),
        ("2223000048400011", Network.MASTERCARD),
    ],
)
def test_known_prefixes(card_number, expected):
    assert get_network(card_number) == expected


def test_unknown_prefix_raises():
    with pytest.raises(UnsupportedNetworkError):
        get_network("6011000000000004")  # Discover - not routed in this sim
