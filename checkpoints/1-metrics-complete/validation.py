import logging
from opentelemetry.trace import Status, StatusCode
from shared.domain import payment_expected_amount
from shared.telemetry import tracer

logger = logging.getLogger("payment.validation")

def validate_amount(
    unrounded_total: str,
    received_minor_units: int,
    currency: str,
    discounted: bool,
) -> bool:
    expected_minor_units = payment_expected_amount(unrounded_total)
    accepted = received_minor_units == expected_minor_units

    # LAB 2: replace validation evidence block
    if not accepted:
        logger.warning("Payment rejected because amount did not match expected value")
    return accepted
