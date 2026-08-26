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
    with tracer.start_as_current_span("payment.amount_validation") as span:
        span.set_attribute("payment.currency", currency)
        span.set_attribute("payment.discounted", discounted)
        span.set_attribute("validation.result", "accepted" if accepted else "rejected")
        if not accepted:
            span.set_status(Status(StatusCode.ERROR, "amount validation rejected"))

        # LAB 3: record amount validation rejection
        if not accepted:
            logger.warning(
                "Payment amount validation rejected",
                extra={
                    "event_name": "payment.amount_validation_rejected",
                    "reason_code": "minor_unit_mismatch",
                    "payment_currency": currency,
                    "payment_discounted": discounted,
                    "expected_minor_units": expected_minor_units,
                    "received_minor_units": received_minor_units,
                    "checkout_rounding_mode": "HALF_UP",
                    "payment_rounding_mode": "HALF_EVEN",
                },
            )

        return accepted
