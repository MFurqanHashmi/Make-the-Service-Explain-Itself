# Facilitator guide

The lab is designed to run from the participant guide without narration. One or two facilitators can support approximately twenty participants by pointing to recovery commands rather than debugging individual environments.

## Before participants arrive

1. Distribute the repository and pinned image bundle.
2. Ask participants to complete `./lab setup` or import the image archive before the session.
3. On the facilitator machine, run:

   ```bash
   ./lab validate-full
   ```

   This must pass, restore starter source, and stop the stack.
4. Run `./lab start && ./lab ready` on a projection/fallback machine.
5. Confirm every link from `./lab links` opens without login.
6. Confirm the working files match `checkpoints/0-starter` before distribution.

## Expected results

| Stage | Expected result |
| --- | --- |
| Initial state | HTTP 200 and normal runtime metrics; prose logs cannot reliably count, segment, and correlate the failures |
| Metrics | 100 completed requests, 25 business rejections, all in discounted CAD, zero non-200 responses |
| Traces | Fresh distributed traces with `payment.amount_validation` marked `ERROR` on rejected operations |
| Logs | Structured rejection events with expected 1000, received 1001, `HALF_EVEN` vs `HALF_UP`, and trace/span correlation |
| Diagnosis | Different rounding modes produced a one-cent mismatch for discounted CAD |

## Recovery commands

```bash
./lab recover metrics
./lab recover traces
./lab recover logs
```

Each command restores the cumulative known-good code, waits for hot reload, generates fresh incident traffic, and checks the real backend. It does not rebuild images or overwrite the participant worksheet.

If a participant is completely blocked, have them run the recovery command for the checkpoint they are on and continue from the observation questions.

## Common questions

### Why not use request ID as a metric attribute?

Metric labels create time series for each unique combination. A request ID is nearly unique per request, so it creates unbounded cardinality. Request-level identity belongs in traces or structured events, not metric labels.

### Why is the top-level request successful when a child span is an error?

Checkout deliberately returns HTTP 200 with a failed business outcome. Automatic HTTP instrumentation therefore sees a successful transport response. The custom validation span records the business operation that rejected the amount.

### Why is the event WARN rather than ERROR?

Payment fulfilled its responsibility by rejecting an invalid amount. The event is abnormal and operationally important, but Payment did not crash or fail to handle the request.

### Why are the amounts absent from the trace?

The trace is used to isolate where the rejection occurred. The event records the detailed decision context. This keeps the teaching distinction clear and avoids placing every diagnostic field on every signal.

## Timing

- Orientation and weak evidence: 6 minutes
- Metrics: 9 minutes
- Traces: 9 minutes
- Structured logs: 9 minutes
- Diagnosis and review gate: 12 minutes
- Protected buffer: 15 minutes

Do not add stretch content by default. Preserve the guided diagnosis by recovering participants to a completed checkpoint if needed.

## If the environment fails broadly

Use the facilitator machine to project the same prepared views and have participants complete the worksheet from the live evidence. This is a last resort; do not turn the session into Docker troubleshooting.

## End-of-session reset

```bash
./lab reset
```
