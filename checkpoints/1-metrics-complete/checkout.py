import logging
import os
import httpx
from pydantic import BaseModel
from shared.domain import checkout_amount
from shared.telemetry import meter

logger = logging.getLogger("checkout.workflow")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://inventory:8001")
PAYMENT_URL = os.getenv("PAYMENT_URL", "http://payment:8002")

checkout_completed = meter.create_counter(
    "checkout.completed", unit="{checkout}",
    description="Completed checkout attempts by business outcome",
)

class CheckoutRequest(BaseModel):
    order_id: str
    product_id: str = "weekly-report"
    currency: str
    discounted: bool
    unrounded_total: str

async def process_checkout(request: CheckoutRequest) -> dict:
    logger.info("Starting checkout for %s", request.order_id)
    async with httpx.AsyncClient(timeout=5.0) as client:
        inventory = await client.post(
            f"{INVENTORY_URL}/reserve",
            json={"product_id": request.product_id, "quantity": 1},
        )
        inventory.raise_for_status()
        if not inventory.json()["reserved"]:
            outcome = "inventory_rejected"
        else:
            received_minor_units = checkout_amount(request.unrounded_total)
            payment = await client.post(
                f"{PAYMENT_URL}/authorize",
                json={
                    "currency": request.currency,
                    "discounted": request.discounted,
                    "unrounded_total": request.unrounded_total,
                    "received_minor_units": received_minor_units,
                },
            )
            payment.raise_for_status()
            outcome = "success" if payment.json()["accepted"] else "payment_rejected"
    logger.info("Finished checkout %s with %s", request.order_id, outcome)

    # LAB 1: record checkout result
    checkout_completed.add(
        1,
        {
            "checkout.outcome": outcome,
            "checkout.currency": request.currency,
            "checkout.discounted": request.discounted,
        },
    )

    return {"order_id": request.order_id, "outcome": outcome}
