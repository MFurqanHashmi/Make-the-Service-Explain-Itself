import logging
from fastapi import FastAPI
from pydantic import BaseModel
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from shared.telemetry import meter
from .validation import validate_amount

logger = logging.getLogger("payment.authorize")
app = FastAPI(title="Payment")
FastAPIInstrumentor.instrument_app(app)

class Authorization(BaseModel):
    currency: str
    discounted: bool
    unrounded_total: str
    received_minor_units: int

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/authorize")
def authorize(request: Authorization):
    # Neither prose log names the currency, the discount, or the decision.
    logger.info("Authorization requested")
    accepted = validate_amount(
        request.unrounded_total,
        request.received_minor_units,
        request.currency,
        request.discounted,
    )
    logger.info("Authorization decision returned")
    return {"accepted": accepted, "reason": None if accepted else "amount_validation_failed"}
