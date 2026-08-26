import logging
from opentelemetry.trace import Status, StatusCode
from shared.domain import payment_expected_amount
from shared.telemetry import tracer

logger = logging.getLogger("payment.validation")

# The logging this service shipped with: prose only, no business fields, and
# three phrasings that drifted apart as the code was maintained. It is emitted
# at INFO, so rejections are indistinguishable from routine chatter.
# LAB 3 replaces the only call site; LAB 2 keeps it for one section, so the
# prose and its structured replacement can be compared side by side.
_WEAK_MESSAGES = (
    "amount check did not pass",
    "Declining authorization: totals differ",
    "validate_amount -> False",
)
_weak_message_index = 0


def _log_weak_rejection() -> None:
    global _weak_message_index
    logger.info(_WEAK_MESSAGES[_weak_message_index % len(_WEAK_MESSAGES)])
    _weak_message_index += 1


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
        _log_weak_rejection()
    return accepted
