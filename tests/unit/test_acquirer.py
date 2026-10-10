from services.acquirer.main import is_valid_merchant


def test_known_merchant_is_valid():
    assert is_valid_merchant("sk_test_demo_merchant")


def test_unknown_merchant_is_invalid():
    assert not is_valid_merchant("sk_test_nope")
