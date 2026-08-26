# Facilitator guide

The lab is designed to run from the participant guide without narration. One or two facilitators
can support approximately twenty participants by pointing to recovery commands rather than
debugging individual environments.

## Where things live

```text
lab                      every command; ./lab with no arguments lists them
guide/                   what participants read (guide.html + its Markdown source)
services/                the checkout system — the only place participants edit
workshop/checkpoints/    known-good code for each stage, used by recover/checkpoint
workshop/telemetry/      Grafana dashboards, datasources, provisioning
workshop/traffic/        the deterministic traffic generator
workshop/scripts/        readiness and evidence checks, link builder, guide build
workshop/tests/          contract tests; ./lab test runs them in-container
workshop/notes/          validation records and the original lab plan
```

## Before participants arrive

1. Distribute the repository and pinned image bundle.
2. Ask participants to complete `./lab setup` or import the image archive before the session.
3. Tell them to run `./lab guide`, which opens `guide/guide.html` — the lab page, with the Grafana
   views built in as buttons. `./lab guide worksheet` opens the worksheet the same way. The guide
   does not offer a Markdown reading path, and neither should you: `guide/participant-guide.md` and
   `guide/worksheet.md` are the sources those pages are generated from, and an editor showing them
   as plain text reveals every answer toggle, which removes most of the exercise.
4. On the facilitator machine, run:

   ```bash
   ./lab validate-full
   ```

   This must pass, restore starter source, and stop the stack.
5. Run `./lab start && ./lab ready` on a projection/fallback machine.
6. Confirm every link from `./lab links` opens without login, including the three that open
   Grafana Explore. The four buttons in the guide page carry the same URLs — open one from
   `./lab guide` to check the page reaches the running stack.
7. Confirm the working files match `workshop/checkpoints/0-starter` before distribution.

## Expected results

| Stage | Expected result |
| --- | --- |
| Initial state | HTTP 200 and normal runtime metrics; ~840 prose log lines per 100 checkouts, all at INFO, that name no outcome, currency, or discount |
| Metrics | 100 completed requests, 25 business rejections, all in discounted CAD, zero non-200 responses |
| Traces | Fresh distributed traces with `payment.amount_validation` marked `ERROR` on rejected operations |
| Logs | Structured rejection events with expected 1000, received 1001, `HALF_EVEN` vs `HALF_UP`, and trace/span correlation |
| Diagnosis | Different rounding modes produced a one-cent mismatch for discounted CAD |

## Running section 1 well

Section 1 is the section most likely to be rushed, and it carries the emotional weight of the whole
lab. Hold the room to the full three minutes. The starting state is deliberately hostile:

- Order IDs are opaque, so no segment can be inferred from a name.
- No prose log names an outcome, a currency, or a discount flag.
- The rejection is logged at `INFO`, in three different phrasings, so a text search for any one of
  them finds roughly a third of the rejections.

Participants who "solve" it in section 1 have usually guessed. Ask them for their confidence, then
have them check it against the exact numbers in section 2.

## Recovery commands

```bash
./lab recover metrics
./lab recover traces
./lab recover logs
```

Each command restores the cumulative known-good code, waits for hot reload, generates fresh
incident traffic, and checks the real backend. It does not rebuild images or overwrite the
participant worksheet.

If a participant is completely blocked, have them run the recovery command for the checkpoint they
are on and continue from the observation questions.

## Common questions

### Why does `./lab ready` sometimes fail the first time?

The three backends inside the LGTM container do not become queryable together, and Tempo is the
slowest. `./lab ready` waits up to 150 seconds and is safe to re-run. `./lab restart-services`
re-emits the readiness markers if a backend came up after the applications did.

### Why not use request ID as a metric attribute?

Metric labels create time series for each unique combination. A request ID is nearly unique per
request, so it creates unbounded cardinality. Request-level identity belongs in traces or
structured events, not metric labels.

### Why is the top-level request successful when a child span is an error?

Checkout deliberately returns HTTP 200 with a failed business outcome. Automatic HTTP
instrumentation therefore sees a successful transport response. The custom validation span records
the business operation that rejected the amount.

### Why is the event WARN rather than ERROR?

Payment fulfilled its responsibility by rejecting an invalid amount. The event is abnormal and
operationally important, but Payment did not crash or fail to handle the request. The pre-lab line
was `INFO`, which is exactly why nobody noticed it.

### Why are the amounts absent from the trace?

The trace is used to isolate where the rejection occurred. The event records the detailed decision
context. This keeps the teaching distinction clear and avoids placing every diagnostic field on
every signal. `./lab check traces` fails deliberately if amounts leak into the span.

### Why does "Peak business failures" read 24–27% instead of exactly 25%?

It reports the highest failure rate in any 15-second window, and the window at the edge of the
traffic burst is skewed. The exact whole-checkout counts are in **Checkout outcomes by segment**
and in `./lab check metrics`. This is worth calling out: it is a real property of rate panels.

### Why is `_log_weak_rejection` still in the file after LAB 2?

Deliberately. It lets participants compare the old prose line with the structured event they write
in section 4. Real codebases keep retired logging helpers around too.

## Timing

- Orientation and weak evidence: 6 minutes
- Metrics: 9 minutes
- Traces: 9 minutes
- Structured logs: 9 minutes
- Diagnosis and review gate: 12 minutes
- Protected buffer: 15 minutes

Traffic runs take about 45 seconds each; section 2 runs two of them. Do not add stretch content by
default. Preserve the guided diagnosis by recovering participants to a completed checkpoint if
needed.

## If the environment fails broadly

Use the facilitator machine to project the same prepared views and have participants complete the
worksheet from the live evidence. This is a last resort; do not turn the session into Docker
troubleshooting.

## End-of-session reset

```bash
./lab reset
```
