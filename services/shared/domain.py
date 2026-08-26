from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP

MINOR_UNIT = Decimal("0.01")


def to_minor_units(value: str, mode: str) -> int:
    rounding = {"HALF_UP": ROUND_HALF_UP, "HALF_EVEN": ROUND_HALF_EVEN}[mode]
    return int(Decimal(value).quantize(MINOR_UNIT, rounding=rounding) * 100)


def checkout_amount(value: str) -> int:
    return to_minor_units(value, "HALF_UP")


def payment_expected_amount(value: str) -> int:
    return to_minor_units(value, "HALF_EVEN")
