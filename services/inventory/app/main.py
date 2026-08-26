import logging
from fastapi import FastAPI
from pydantic import BaseModel
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from shared.telemetry import meter

logger = logging.getLogger("inventory.reserve")
app = FastAPI(title="Inventory")
FastAPIInstrumentor.instrument_app(app)

class Reservation(BaseModel):
    product_id: str
    quantity: int = 1

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/reserve")
def reserve(request: Reservation):
    logger.info("reserve called for product=%s quantity=%s", request.product_id, request.quantity)
    return {"reserved": True}
