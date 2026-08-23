# Observability lab evidence worksheet

Complete this after all three instrumentation checkpoints. Do not change code during the diagnosis.

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

## Supported diagnosis

Write one paragraph using only claims supported by the evidence above.

## Pull-request review gate

- [ ] Detect: a signal shows whether checkout fulfills its responsibility.
- [ ] Scope: bounded dimensions show which requests are affected.
- [ ] Isolate: a distributed trace identifies the failing operation.
- [ ] Explain: a safe structured event records the application condition and correlates to the trace.

<details>
<summary>Check the expected diagnosis</summary>

Checkout returned HTTP 200 for every request while 25% of business outcomes failed. The outcome metric scoped the failures to discounted CAD orders. A distributed trace showed Inventory completing successfully and isolated the rejection to Payment amount validation. The correlated event recorded that Checkout submitted 1001 minor units using `HALF_UP`, while Payment expected 1000 using `HALF_EVEN`. The one-cent mismatch caused the validation rejection.

</details>
