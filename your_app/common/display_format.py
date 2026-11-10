"""Presentation-only rounding; raw prices and gem calculations remain in mesos."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def price_in_man(value):
    try:
        return int((Decimal(str(value)) / 10_000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return 0
