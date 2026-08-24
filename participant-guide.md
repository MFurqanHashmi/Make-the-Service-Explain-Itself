# Guided observability lab

**Target time:** 45 minutes. The remaining 15 minutes in the session are buffer.

> **Read this file in a Markdown preview.** In VS Code press `Cmd+Shift+V`. This guide hides
> answers behind "Check your evidence" toggles, and in a plain text editor those answers are
> visible immediately, which removes most of the value of the exercise.

You will make three small, real instrumentation changes to the same checkout system. The guide
supplies every code block and every Grafana view. You do not need to configure the telemetry
stack or write a single query.

## Before you start

The stack must already be built. If you have not done it yet, run `./lab setup` once while
online (see [README.md](README.md)). It takes a few minutes and only has to happen once.

## What you are investigating

```text
Traffic generator
       |
       v
Checkout API ------> Inventory service
       |
       +-----------> Payment service
```

This is the same checkout world as the presentation, with a different incident. The services are
already running locally in Docker. **Every request returns HTTP 200, even when the checkout
business outcome is rejected.**

## How the lab is scored

You are answering four questions. Right now you can answer none of them. Each section unlocks
exactly one, and you will see this table again at every checkpoint.

| Question | Can you answer it? |
| --- | --- |
| **Detect** — is checkout behaving correctly? | ❌ not yet |
| **Scope** — which requests are affected? | ❌ not yet |
| **Isolate** — where did one operation fail? | ❌ not yet |
| **Explain** — what application condition caused it? | ❌ not yet |

---

## 0. Confirm the environment

```bash
./lab start
./lab ready
./lab links
```

`./lab start` can take two to three minutes the first time. Expected readiness message:

```text
READY: checkout, inventory, payment, metrics, traces, logs, and Grafana are available
PASS Grafana: dashboard, datasources, Explore access, and bidirectional correlation are provisioned
```

If `./lab ready` reports that a backend is not serving data yet, **run it again** — the telemetry
backends sometimes need a second attempt on a cold start. If it still fails, run
`./lab restart-services` and then `./lab ready`.

Keep the printed Grafana links available. All views use a relative 15-minute time range.

---

## 1. The weak starting state (3 minutes maximum)

### The situation

You are on call. A payments teammate says "a few customers are complaining that checkout does
nothing." You have what most services ship with: prose logs. Nothing else.

Generate the incident:

```bash
./lab traffic incident
```

That is 100 checkouts. Open **Noisy starting logs** from `./lab links`. You should be looking at
something like this:

![Explore showing 838 undifferentiated INFO log lines for 100 checkouts](docs/images/01-noisy-logs.png)

### Your task

Set a timer for three minutes. Using **only** those logs, write your answers here:

| # | Question | Your answer | Confidence |
| --- | --- | --- | --- |
| 1 | How many payment validations were rejected? | | |
| 2 | Which currency and discount segment was affected? | | |
| 3 | Which checkout request produced one specific rejection? | | |

**Stop at three minutes even if you are mid-scroll.** Do not skip this section. Feeling the
dead end is the point; the next three sections are only satisfying if you have earned them.

### Why this is worse than it looks

Count the log lines Grafana reports for those 100 checkouts. You will see roughly **840**, every
one of them at `INFO`, so even the level histogram tells you nothing.

- Nothing in any line names the outcome. Checkout logs `Finished checkout ord-4b2c1f8e0a` whether
  the checkout succeeded or was rejected.
- Nothing in any line names the currency or the discount. `Authorization requested` is all Payment
  says on the way in.
- The rejection itself is logged at `INFO`, in three different phrasings that drifted apart as the
  code was maintained: `amount check did not pass`, `Declining authorization: totals differ`, and
  `validate_amount -> False`. A text search for any one of them finds a third of the truth.
- Order IDs are opaque, so you cannot infer a segment from a name.

This is not a contrived handicap. It is what logging looks like when each line was written to help
one developer debug one function, and nobody ever asked whether the service could explain itself.

Now scale it. 840 lines per 100 checkouts is **8.4 lines per checkout**. A service doing 1,000
checkouts per minute emits **about 12 million lines a day**. The three minutes you just spent do
not get shorter; the haystack gets bigger.

**Prediction:** Host metrics look normal and every request is HTTP 200. Is checkout necessarily
healthy?

<details>
<summary>Check the idea</summary>

No. HTTP status shows that the API handled the request. It does not establish that the checkout
business process fulfilled its responsibility.

</details>

### Investigation state

| Question | Can you answer it? |
| --- | --- |
| **Detect** | ❌ Logs show activity, not correctness |
| **Scope** | ❌ No business fields to group by |
| **Isolate** | ❌ No link between a checkout and a payment decision |
| **Explain** | ❌ Prose records that something failed, not why |

---

## 2. Metrics: detect and scope the problem (about 9 minutes)

### The pain we are fixing

You could not say whether checkout is healthy, and you could not say who is affected. Counting by
hand does not scale past a few hundred lines.

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

Paste the following code immediately below the marker. The block begins with four spaces because
it sits inside `process_checkout`:

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

Save. Uvicorn reloads the service in about a second; do not rebuild or restart it.

### Produce evidence

Open **Runtime and checkout metrics** from `./lab links` and leave it on screen. It auto-refreshes
every five seconds, so you can watch both runs land. Each command takes about 45 seconds.

```bash
./lab traffic healthy
./lab traffic incident
```

Watch **Business outcome over time**: the healthy run draws one green line, and the incident run
draws a second red one underneath it. When both have finished you should see:

- **HTTP 200 responses: 100%.** Transport never noticed.
- **Checkout CPU and memory:** normal.
- **Peak business failures: 24–27%.** This panel reports the worst 15-second window, so it lands
  near but not exactly on the true rate depending on where the window falls.
- **Checkout outcomes by segment:** exact whole checkouts. `CAD discounted=true → payment_rejected`
  is the only failing row.

![Dashboard showing 100% HTTP 200 beside a 24% business failure rate, and 25 rejected discounted CAD checkouts](docs/images/02-checkout-dashboard.png)

The dashboard is the primary verification. For the exact numbers, run:

```bash
./lab check metrics
```

If the check reports a code/service error or times out:

```bash
./lab recover metrics
```

Recovery restores the named cumulative checkpoint, waits for reload, generates fresh traffic, and
verifies the evidence. Use the recovery command for your current stage; recovering to an earlier
stage removes later instrumentation edits.

### Score section 1

Go back to your table in section 1. The true answers are **25 rejections**, all in **discounted
CAD**. How close were you, and how long did it take compared with the ten seconds it took to read
the segment panel?

### Record what the metric proves

1. **Detect:** Checkout is unhealthy because ____________________________________.
2. **Scope:** The affected segment is __________________________________________.
3. The metric does not yet prove ______________________________________________.

<details>
<summary>Check your evidence</summary>

1. About a quarter of checkouts return a failed business outcome, even though every HTTP response
   is 200.
2. Rejections are concentrated in discounted CAD checkouts. Standard CAD and discounted USD ran in
   the same window and every one of them succeeded.
3. The metric does not show which operation rejected one request or why its amount was rejected.

`outcome`, `currency`, and `discounted` have small, bounded vocabularies. Request IDs, order IDs,
customer IDs, trace IDs, product IDs, and raw URLs are deliberately excluded from metric attributes
because they would create many unique time series.

</details>

### Investigation state

| Question | Can you answer it? |
| --- | --- |
| **Detect** | ✅ ~25% of checkouts fail their business outcome |
| **Scope** | ✅ Discounted CAD only; other segments are clean |
| **Isolate** | ❌ The metric counts outcomes, it does not follow a request |
| **Explain** | ❌ No amounts, no reason |

**Checkpoint:** Do not continue until the dashboard or `./lab check metrics` confirms the new
evidence.

---

## 3. Traces: isolate the failing operation (about 9 minutes)

### The pain we are fixing

You know a quarter of discounted CAD checkouts fail. You still cannot point at the operation that
rejected one. Checkout calls Inventory and Payment; either could be at fault, and the metric
cannot tell you which.

### Operational question

Which operation rejected an affected checkout?

Automatic instrumentation already traces HTTP calls between Checkout, Inventory, and Payment. It
does not yet record the payment-validation decision as a focused operation.

### Add the validation span

Open:

```text
payment/app/validation.py
```

Find this marker and the weak log/return block immediately below it:

```python
# LAB 2: replace validation evidence block
```

Replace the marker and everything from it through `return accepted` with the block below. Its
first line begins with four spaces because it remains inside `validate_amount`:

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
            _log_weak_rejection()

        return accepted
```

Save the file. `_log_weak_rejection` is the old prose helper; it stays for one more section so you
can compare it directly with what replaces it.

### Produce evidence

```bash
./lab traffic incident
./lab check traces
```

The check prints a fresh trace ID. Open **Failed payment-validation traces** from `./lab links`,
**click any Trace ID** from the latest run, and read the waterfall.

Look for:

- One distributed trace containing Checkout, Inventory, and Payment work.
- A successful top-level HTTP request, because Checkout returned 200.
- A `payment.amount_validation` child span marked with a red `ERROR` icon.
- **Click that span** to expand it, then read its attributes: `payment.currency=CAD`,
  `payment.discounted=true`, and `validation.result=rejected`.

![Trace waterfall with checkout, inventory and payment, and a red payment.amount_validation span](docs/images/03-failed-trace.png)

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

1. Inventory completed successfully for the selected request, in well under a millisecond.
2. The request was rejected during Payment amount validation.
3. The trace does not explain the expected value, received value, or why those values differed.

The span deliberately does not contain amounts or rounding modes. Those details belong in the event
added next; otherwise the trace step would reveal the complete answer and the log would add no
value. `./lab check traces` actively fails if amounts leak into the span.

</details>

### Investigation state

| Question | Can you answer it? |
| --- | --- |
| **Detect** | ✅ ~25% of checkouts fail their business outcome |
| **Scope** | ✅ Discounted CAD only |
| **Isolate** | ✅ Payment amount validation, with Inventory ruled out |
| **Explain** | ❌ You can name the operation, not the condition |

**Checkpoint:** You should be able to name the failing operation without yet naming the cause.

---

## 4. Structured logs: explain the rejection (about 9 minutes)

### The pain we are fixing

You know where it broke. If you page the Payments team now, the entire content of your message is
"amount validation rejects discounted CAD." They will ask what the amounts were, and the only
answer available is `validate_amount -> False`.

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

Replace the `if not accepted` block immediately below that marker with the block below. Its first
line begins with eight spaces because it remains inside the span:

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

Open **Structured payment-validation events** from `./lab links`. **Expand one log row** to see the
attached fields — OpenTelemetry sends them as Loki structured metadata, so they are attributes on
the row rather than text in the message.

Fields should include:

- `event_name=payment.amount_validation_rejected`
- `reason_code=minor_unit_mismatch`
- `expected_minor_units=1000`
- `received_minor_units=1001`
- `checkout_rounding_mode=HALF_UP`
- `payment_rounding_mode=HALF_EVEN`
- Trace and span context supplied by OpenTelemetry

![Explore showing WARN events with every business field listed in the Fields sidebar at 100%](docs/images/04-structured-events.png)

Compare that with what the same rejection looked like ten minutes ago: `validate_amount -> False`.
Every field in that sidebar is now something you can filter and group by.

Open one event's **Open trace** link. In the trace, use **Logs for this span** to come back to the
correlated event. If either direction is unavailable, use the fresh trace ID printed by the checks
and continue; report the correlation-link issue separately from the telemetry result.

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
3. Payment handled the validation rejection correctly, but the event signals abnormal upstream
   behaviour that matters operationally. It is not a Payment service crash. Note that the old prose
   line was `INFO`, which is why it never stood out from routine chatter.

Integer minor units avoid ambiguous formatted currency strings and preserve the exact one-cent
difference. Card data, payment tokens, customer details, order IDs, and raw payloads are
intentionally absent.

</details>

### Investigation state

| Question | Can you answer it? |
| --- | --- |
| **Detect** | ✅ ~25% of checkouts fail their business outcome |
| **Scope** | ✅ Discounted CAD only |
| **Isolate** | ✅ Payment amount validation |
| **Explain** | ✅ HALF_UP vs HALF_EVEN, 1001 against an expected 1000 |

**Checkpoint:** You can now explain the mismatch using a structured event correlated to the failed
span.

---

## 5. Guided diagnosis: no more code changes (about 8 minutes)

Instrumentation is complete. Freeze the code. Run one fresh incident:

```bash
./lab traffic incident
./lab check metrics
./lab check traces
./lab check logs
```

Complete [worksheet.md](worksheet.md) by opening the views in this order. Open it in a Markdown
preview too — its answer section is behind a toggle.

### Detect

Open the checkout dashboard. Record what changed, the business-failure percentage, and the time
window.

### Scope

Use **Checkout outcomes by segment**. Record the affected and unaffected groups, plus one claim the
evidence would not support.

### Isolate

Open a fresh error trace. Record the failing operation, trace ID, what the trace establishes, and
what it does not explain.

### Explain

Open the correlated structured event. Record expected and received minor units, the difference, and
both rounding modes.

Only after completing the worksheet, open its answer section.

### The whole point

Three minutes in section 1 produced no reliable answer. The same incident, with the same 100
requests, now takes under a minute to diagnose end to end — and the last code change happened
*before* the investigation started.

---

## 6. Apply the review gate (about 4 minutes)

Before approving a feature, ask whether its telemetry can answer:

- **Detect:** Is there a signal showing the feature is fulfilling its responsibility?
- **Scope:** Could we tell when behaviour changed and how widely?
- **Isolate:** Can one operation be followed across its meaningful boundaries, including where it
  failed?
- **Explain:** Are key decisions recorded as structured, safe, correlated events?

For this checkout system, identify the evidence that now satisfies each question.

The key outcome is not that you used Grafana. It is that you diagnosed the incident without adding
telemetry and redeploying after the investigation began.

### Connection to the presentation

The presentation described a reactive loop where teams add the evidence they wish they had during
an incident. Section 1 was that loop's starting position. Sections 2 to 4 were the work that team
would have done *after* the pager went off, under time pressure, with a deploy for each attempt.
Section 5 was what it costs when the evidence is already there.

The Microsoft Teams study cited in the presentation found that many incidents were first detected
by people rather than automated monitoring, and that missing telemetry contributed to delayed
root-cause identification in difficult cases.

## Finish or reset

To stop containers while preserving their current telemetry and completed code for later review:

```bash
./lab stop
```

To restore the starter state and delete local telemetry:

```bash
./lab reset
```
