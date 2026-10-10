from common.luhn import TEST_CARD_NUMBERS, is_luhn_valid


def test_stripe_test_numbers_are_luhn_valid():
    for number in TEST_CARD_NUMBERS:
        assert is_luhn_valid(number), number


def test_tampered_digit_fails():
    tampered = "4242424242424241"
    assert not is_luhn_valid(tampered)


def test_non_digit_input_fails():
    assert not is_luhn_valid("4242-4242-4242-4242")
