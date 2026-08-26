from fastapi import FastAPI, Response
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from shared.telemetry import meter
from .checkout import CheckoutRequest, process_checkout

app = FastAPI(title="Checkout")
FastAPIInstrumentor.instrument_app(app)
http_responses = meter.create_counter("checkout.http.responses", unit="{response}")

@app.middleware("http")
async def record_http_status(request, call_next):
    response: Response = await call_next(request)
    if request.url.path == "/checkout":
        http_responses.add(1, {"http.response.status_code": response.status_code})
    return response

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/checkout")
async def checkout(request: CheckoutRequest):
    # Deliberately returns HTTP 200 even when the business outcome is rejected.
    return await process_checkout(request)
