# Guided observability lab

**Target time:** 45 minutes. The remaining 15 minutes in the session are buffer.

You will make three small, real instrumentation changes to the same checkout system. The guide supplies every code block and Grafana view. You do not need to configure the telemetry stack or write queries.

## What you are investigating

```text
Traffic generator
       |
       v
Checkout API ------> Inventory service
       |
       +-----------> Payment service
```

This is the same checkout world as the presentation, with a different incident. The services are already running locally in Docker. Every request returns HTTP 200, even when the checkout business outcome is rejected.

## 0. Confirm the environment

Run:

```bash
./lab start
./lab ready
./lab links
```

Expected readiness message:

```text
READY: checkout, inventory, payment, metrics, traces, logs, and Grafana are available
```

Keep the printed Grafana links available. All views use a relative 15-minute time range.

---

## 1. Inspect the weak starting state (3 minutes maximum)

Generate the incident:

```bash
./lab traffic incident
```

Open **Noisy starting logs** from `./lab links`.

Try to answer all three questions using only those logs:

1. How many payment validations were rejected?
2. Which currency and discount segment was affected?
3. Which checkout request produced one selected rejection?

Stop after three minutes, even if you found individual lines.

You can search prose, but these messages have inconsistent wording and lack stable business fields. They do not reliably support counting, segmentation, or correlation. That limitation is noticeable with 100 requests; it is much worse with thousands of requests per minute.

**Prediction:** Host metrics look normal and every request is HTTP 200. Is checkout necessarily healthy?

<details>
<summary>Check the idea</summary>

No. HTTP status shows that the API handled the request. It does not establish that the checkout business process fulfilled its responsibility.

</details>

---

## 2. Metrics: detect and scope the problem (about 9 minutes)

### Operational question

How can we see whether checkout is succeeding, and which bounded segment is affected?

### Add the business-outcome metric

Open:

```text
checkout/app/checkout.py
```

Find:

```python
# LAB 1: record checkout result
```

Paste the following code immediately below the marker, the block begins with four spaces because it is inside `process_checkout`:

```python
    checkout_completed.add(
        1,
        {
            "checkout.outcome": outcome,
            "checkout.currency": request.currency,
            "checkout.discounted": request.discounted,
        },
    )
```

Save. Uvicorn reloads the service automatically; do not rebuild or restart it.

### Produce evidence

Run a healthy comparison, followed by the incident:

```bash
./lab traffic healthy
./lab traffic incident
```

Open **Runtime and checkout metrics** from `./lab links`, then refresh once. Within about 20 seconds you should see:

- HTTP 200 responses at 100%.
- Checkout runtime metrics remaining normal.
- Business failures around 25% during incident traffic.
- Failures concentrated in discounted CAD.

The dashboard is the primary verification. If it does not match, run:

```bash
./lab check metrics
```

If the check reports a code/service error or times out:

```bash
./lab recover metrics
```

Recovery restores the named cumulative checkpoint, waits for reload, generates fresh traffic, and verifies the evidence. Use the recovery command for your current stage; recovering to an earlier stage removes later instrumentation edits.

### Record what the metric proves

1. **Detect:** Checkout is unhealthy because ____________________________________.
2. **Scope:** The affected segment is __________________________________________.
3. The metric does not yet prove ______________________________________________.

<details>
<summary>Check your evidence</summary>

1. The checkout business-failure percentage rises to about 25%, even though every HTTP response is 200.
2. Rejections are concentrated in discounted CAD checkouts; standard CAD and discounted USD remain successful.
3. The metric does not show which operation rejected one request or why its amount was rejected.

`outcome`, `currency`, and `discounted` have small, bounded vocabularies. Request IDs, order IDs, customer IDs, trace IDs, product IDs, and raw URLs are deliberately excluded from metric attributes because they would create many unique time series.

</details>

**Checkpoint:** Do not continue until the dashboard or `./lab check metrics` confirms the new evidence.

---

## 3. Traces: isolate the failing operation (about 9 minutes)

### Operational question

Which operation rejected an affected checkout?

Automatic instrumentation already traces HTTP calls between Checkout, Inventory, and Payment. It does not yet record the payment-validation decision as a focused operation.

### Add the validation span

Open:

```text
payment/app/validation.py
```

Find this marker and the weak log/return block immediately below it:

```python
# LAB 2: replace validation evidence block
```

Replace the marker and everything from it through `return accepted` with the block below. Its first line begins with four spaces because it remains inside `validate_amount`:

```python
    # LAB 2: replace validation evidence block
    with tracer.start_as_current_span("payment.amount_validation") as span:
        span.set_attribute("payment.currency", currency)
        span.set_attribute("payment.discounted", discounted)
        span.set_attribute("validation.result", "accepted" if accepted else "rejected")
        if not accepted:
            span.set_status(Status(StatusCode.ERROR, "amount validation rejected"))

        # LAB 3: record amount validation rejection
        if not accepted:
            logger.warning("Payment rejected because amount did not match expected value")

        return accepted
```

Save the file.

### Produce evidence

```bash
./lab traffic incident
./lab check traces
```

The check prints a fresh trace ID. Open **Failed payment-validation traces** from `./lab links`, choose a result from the latest traffic run, and inspect its waterfall.

Look for:

- One distributed trace containing Checkout, Inventory, and Payment work.
- A successful top-level HTTP request because Checkout returned 200.
- A `payment.amount_validation` child span marked `ERROR`.
- `payment.currency=CAD`, `payment.discounted=true`, and `validation.result=rejected`.

If the evidence does not appear:

```bash
./lab recover traces
```

### Record what the trace proves

1. Inventory ________________________________________________.
2. The request was rejected during ___________________________.
3. The trace still does not explain __________________________.

<details>
<summary>Check your evidence</summary>

1. Inventory completed successfully for the selected request.
2. The request was rejected during Payment amount validation.
3. The trace does not explain the expected value, received value, or why those values differed.

The span deliberately does not contain amounts or rounding modes. Those details belong in the event added next; otherwise the trace step would reveal the complete answer and the log would add no value.

</details>

**Checkpoint:** You should be able to name the failing operation without yet naming the cause.

---

## 4. Structured logs: explain the rejection (about 9 minutes)

### Operational question

What application condition caused Payment to reject the amount?

### Replace the weak prose event

In:

```text
payment/app/validation.py
```

Find:

```python
# LAB 3: record amount validation rejection
```

Replace the `if not accepted` log block immediately below that marker with the block below. Its first line begins with eight spaces because it remains inside the span:

```python
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
```

Save the file.

### Produce evidence

```bash
./lab traffic incident
./lab check logs
```

Open **Structured payment-validation events** from `./lab links`.

Filterable fields should include:

- `event_name=payment.amount_validation_rejected`
- `reason_code=minor_unit_mismatch`
- `expected_minor_units=1000`
- `received_minor_units=1001`
- `checkout_rounding_mode=HALF_UP`
- `payment_rounding_mode=HALF_EVEN`
- Trace and span context supplied by OpenTelemetry

Open one event’s trace link. In the trace, use **Logs for this span** to return to its correlated event. If either direction is unavailable, use the fresh trace ID printed by the checks and continue; report the correlation-link issue separately from the telemetry result.

If the event does not appear:

```bash
./lab recover logs
```

### Record what the event proves

1. Payment expected ______ minor units and received ______.
2. Checkout used __________________; Payment used __________________.
3. `WARN` is appropriate because ____________________________________________.

<details>
<summary>Check your evidence</summary>

1. Payment expected 1000 minor units and received 1001.
2. Checkout used `HALF_UP`; Payment used `HALF_EVEN`.
3. Payment handled the validation rejection correctly, but the event signals abnormal upstream behavior that matters operationally. It is not a Payment service crash.

Integer minor units avoid ambiguous formatted currency strings and preserve the exact one-cent difference. Card data, payment tokens, customer details, order IDs, and raw payloads are intentionally absent.

</details>

**Checkpoint:** You can now explain the mismatch using a structured event correlated to the failed span.

---

## 5. Guided diagnosis: no more code changes (about 8 minutes)

Instrumentation is complete. Freeze the code. Run one fresh incident:

```bash
./lab traffic incident
./lab check metrics
./lab check traces
./lab check logs
```

Complete [worksheet.md](worksheet.md) by opening the views in this order.

### Detect

Open the checkout dashboard. Record what changed, the business-failure percentage, and the time window.

### Scope

Use **Failures by segment**. Record the affected and unaffected groups, plus one claim the evidence would not support.

### Isolate

Open a fresh error trace. Record the failing operation, trace ID, what the trace establishes, and what it does not explain.

### Explain

Open the correlated structured event. Record expected and received minor units, the difference, and both rounding modes.

Only after completing the worksheet, open its answer section.

---

## 6. Apply the review gate (about 4 minutes)

Before approving a feature, ask whether its telemetry can answer:

- **Detect:** Is there a signal showing the feature is fulfilling its responsibility?
- **Scope:** Could we tell when behavior changed and how widely?
- **Isolate:** Can one operation be followed across its meaningful boundaries, including where it failed?
- **Explain:** Are key decisions recorded as structured, safe, correlated events?

For this checkout system, identify the evidence that now satisfies each question.

The key outcome is not that you used Grafana. It is that you diagnosed the incident without adding telemetry and redeploying after the investigation began.

### Connection to the presentation

The presentation described a reactive loop where teams add the evidence they wish they had during an incident. This lab ran the inverse: the evidence already existed when diagnosis started.

The Microsoft Teams study cited in the presentation found that many incidents were first detected by people rather than automated monitoring and that missing telemetry contributed to delayed root-cause identification in difficult cases. Here, the prepared evidence moved the investigation from hidden business failure to supported diagnosis in minutes.

## Finish or reset

To stop containers while preserving their current telemetry and completed code for later review:

```bash
./lab stop
```

To restore the starter state and delete local telemetry:

```bash
./lab reset
```
