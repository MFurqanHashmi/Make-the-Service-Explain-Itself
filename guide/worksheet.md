# Observability lab evidence worksheet

Complete this after all three instrumentation checkpoints. Do not change code during the
diagnosis.

> Keep the answer section at the bottom closed until every other line is filled in.

## Detect

- Incident time window:
- Business-failure percentage:
- HTTP response percentage:
- Host/runtime condition:
- Evidence statement:

## Scope

- Affected segment:
- Unaffected comparison groups:
- One claim the evidence does not support:
- Evidence statement:

## Isolate

- Fresh trace ID:
- Failing operation:
- Upstream operation that completed successfully:
- What the trace proves:
- What it does not explain:
- Evidence statement:

## Explain

- Stable event name:
- Expected minor units:
- Received minor units:
- Difference:
- Checkout rounding mode:
- Payment rounding mode:
- Evidence statement:

## Compare with where you started

- Minutes spent in section 1 without a reliable answer:
- Minutes spent on this worksheet:
- Which single signal moved you furthest, and why:

## Supported diagnosis

Write one paragraph using only claims supported by the evidence above.

## Pull-request review gate

- [ ] Detect: a signal shows whether checkout fulfils its responsibility.
- [ ] Scope: bounded dimensions show which requests are affected.
- [ ] Isolate: a distributed trace identifies the failing operation.
- [ ] Explain: a safe structured event records the application condition and correlates to the
      trace.

<details>
<summary>Check the expected diagnosis</summary>

Checkout returned HTTP 200 for every request while about a quarter of business outcomes failed.
The outcome metric scoped the failures to discounted CAD orders, with standard CAD and discounted
USD succeeding in the same window. A distributed trace showed Inventory completing successfully and
isolated the rejection to Payment amount validation. The correlated event recorded that Checkout
submitted 1001 minor units using `HALF_UP`, while Payment expected 1000 using `HALF_EVEN`. The
one-cent mismatch caused the validation rejection.

</details>
