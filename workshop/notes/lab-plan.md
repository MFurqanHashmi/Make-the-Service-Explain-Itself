# Guided Observability Lab Plan (Revised)

## Status

The lab format, learning model, and core technical direction are sound. This revision also closes the remaining design gaps that would otherwise threaten a self-guided delivery: deterministic incident data, explicit telemetry contracts, fresh-evidence verification, one-command recovery, containerized traffic generation, and provisioned trace-to-log correlation.

The plan is ready for a vertical-slice prototype. It is not ready for full implementation or delivery until that slice passes the validation gates at the end of this document.

## Lab objective

Participants instrument a small Python checkout system and then diagnose a deterministic incident using only the telemetry they added.

The lab applies the same four questions from the presentation:

* Detect: Is checkout behaving correctly?
* Scope: Which requests are affected, and how broadly?
* Isolate: Where did one operation spend its time, or fail?
* Explain: What application condition caused that operation to fail?

Note on Isolate: the presentation frames Isolate around where an operation spends its time. In this lab the same question isolates the cause of a failure. This small extension is intentional and should be stated once, so the framework reads consistently.

The success criterion is:

> I identified the issue from telemetry that already existed. I did not add more logs and redeploy after the investigation began.

## Delivery format: self-guided

This is a self-guided code-along. The participant guide and the supplied code drive the lab. A participant who can read the guide and copy code should complete the entire path without asking for help.

Facilitators are a light safety net, not the engine of the lab. Expect one or two facilitators for about twenty people. Their job is to watch for anyone stuck, point them to the self-service recovery step, and keep the room roughly together, not to narrate every checkpoint.

Progression is self-paced. There are clear checkpoints and stop markers so a participant always knows whether they are at a natural pause, but nobody waits on a facilitator to unlock the next step.

At each checkpoint, participants:

1. Read the operational question and why the current evidence is not enough.
2. Predict what evidence the next change should produce.
3. Open one specified Python file.
4. Find a clearly marked insertion point.
5. Paste the complete supplied code and save. The service hot-reloads; no rebuild.
6. Generate a small amount of real traffic with one command.
7. Open the supplied, pre-filtered Grafana view and see the evidence appear.
8. State what the evidence proves and what it does not prove.
9. Continue when ready, or run the self-service recovery step if the evidence did not appear.

Engagement comes from predicting, implementing, and then seeing the real evidence show up. It does not depend on a facilitator, on discovering the right file, on remembering an instrumentation API, on writing queries, or on exploring the platform unaided.

## Self-guided design principles

* The guide never says "instrument this function" without supplying the exact code.
* Every step names one repository-relative file path and one insertion marker.
* Seeing the evidence in the pre-filtered view is the confirmation that a step worked. The guide shows a screenshot of the expected view beside each step so participants can self-check.
* Every checkpoint has a one-command self-service recovery that jumps to a known-good state.
* Nothing in the main path requires a query language, a rebuild, or infrastructure configuration.
* A participant who falls behind can recover to the next checkpoint and rejoin without having missed a dependency.

## Locked implementation decisions

| Area | Decision |
| --- | --- |
| Language | Python 3.12 |
| Service framework | FastAPI with Uvicorn |
| Service communication | Real HTTP calls using `httpx` |
| Runtime | Local Docker Compose environment, one independent stack per participant |
| Code editing | Bind-mounted source with `uvicorn --reload`; edits apply on save, no rebuild |
| Traffic generation | Containerized Python runner invoked through `./lab traffic`; no host Python required |
| Observability standard | OpenTelemetry |
| Signal transport | Metrics, traces, and structured application logs exported through OTLP |
| Sampling and export | 100% trace sampling; metric export interval at most 5 seconds; short trace and log batching |
| Observability UI | Grafana with fixed, provisioned data-source and dashboard UIDs |
| Local telemetry stack | Pinned Grafana OpenTelemetry LGTM image |
| Participation | Complete individual path; pairing permitted as support only |
| Progression | Self-paced checkpoints with self-service recovery |
| Facilitation | One or two facilitators for about twenty people, safety net only |
| Incident | Same prepared deterministic incident for everyone |
| Failure surfacing | Checkout returns HTTP 200 with a failed business outcome |
| Main-path duration | 45 minutes |
| Protected buffer | 15 minutes within the 60-minute slot |
| Minimum hardware | 8 GB RAM, tested at 8 GB; images pre-pulled |

## Why Grafana OpenTelemetry LGTM

Use Grafana's OpenTelemetry LGTM Docker image as the local observability environment. It provides one development-oriented image containing:

* Grafana for the user interface
* Prometheus-compatible metrics storage
* Loki for logs
* Tempo for traces
* An OpenTelemetry Collector and OTLP endpoint

This is the best fit because:

* Grafana, Prometheus, Loki, Tempo, and OpenTelemetry are recognizable industry technologies.
* Participants use one interface for all three signals.
* The stack runs locally through Docker Compose with no hosted infrastructure.
* Dashboards, Explore views, data-source correlations, and links can be provisioned in advance.
* The participant experience starts from labelled links rather than query languages.
* The image is explicitly intended for development, demonstrations, and testing, which matches this lab.

The stack is supporting infrastructure, not curriculum. Participants will not configure Grafana, Prometheus, Loki, Tempo, or the Collector.

All application signals use the prepared OTLP pipeline. Python standard-library log records are bridged into OpenTelemetry and exported through OTLP with `service.name`, trace ID, and span ID. This is a locked decision because the lab requires structured fields in Loki and bidirectional trace-to-log navigation. The LGTM image does not collect application stdout automatically.

Grafana provisions both directions of correlation:

* Tempo to Loki: a selected span exposes a Logs for this span link, with service-name mapping and a small time-window shift.
* Loki to Tempo: the trace ID is stored as structured metadata and exposed through a derived field, not as a high-cardinality stream label.

References:

* [Grafana OpenTelemetry LGTM documentation](https://grafana.com/docs/opentelemetry/docker-lgtm/)
* [Grafana Explore documentation](https://grafana.com/docs/grafana/latest/explore/)
* [OpenTelemetry Python documentation](https://opentelemetry.io/docs/languages/python/)
* [OpenTelemetry Python logs auto-instrumentation](https://opentelemetry.io/docs/languages/python/automatic/logs-example/)
* [Grafana trace-to-logs configuration](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/configure-trace-to-logs/)

## Independent per-participant environment

Every participant runs the entire stack on their own laptop: the three services, the traffic generator, and one Grafana OpenTelemetry LGTM container.

Consequences that shape the rest of the design:

* All Grafana links use the same default `localhost:3000` base URL because each person has their own Grafana. `./lab ready` checks that the required ports are available before startup, and `./lab links` is the single source of generated URLs so a tested port override can be supported if necessary.
* Telemetry is naturally isolated per laptop. There is no cross-participant contamination and no need to filter by a per-person identifier for correctness.
* There is no shared, facilitator-selected trace. Any "open a failed trace" step uses the participant's local saved Explore query, filtered to the Payment validation error span. Because Tempo search does not guarantee newest-first results, the guide identifies a result created after the latest traffic run and provides a known-fresh trace ID through `./lab check traces` if needed.
* Because everyone runs LGTM plus three services plus traffic, memory matters. Require 8 GB RAM, and test on an 8 GB machine rather than a high-spec one. Pre-pull or distribute all images so no image is fetched from the public internet during the session.

## Hot-reload editing

Services run from a bind-mounted source directory with `uvicorn --reload`. When a participant pastes code and saves, the service reloads in place within a second or two. There is no `docker compose build` and no container restart on the main path.

Use polling-based file watching in the lab containers so hot reload behaves consistently across Docker Desktop, WSL2, macOS, and Linux. After every save, the helper first checks Python compilation, service health, and successful reload before it asks the participant to generate traffic.

This is the single most important timing decision. It removes the rebuild-and-restart cycle from all three instrumentation checkpoints and keeps each edit-to-evidence loop short.

Neither the main path nor recovery rebuilds images. Dependency versions and images are fixed before the session.

## Verification is seeing the evidence

Verification is not a hidden pass or fail. The participant instruments the code, runs a little traffic, opens the pre-filtered view, and sees the new evidence appear. That is the confirmation, and it is also the teaching moment: they watch the signal they just added become visible.

To make this reliable without a facilitator:

* Each checkpoint page shows a screenshot of the expected view so participants can compare at a glance.
* A short built-in wait covers ingestion delay. The guide tells participants the evidence should appear within roughly fifteen to twenty seconds of running traffic, and to refresh once.
* A self-service helper, `./lab check <signal>`, polls the real backend with the same filters used by Grafana and a bounded timeout of about twenty seconds. Each `./lab traffic` command records a freshness boundary before it sends requests. A check passes only when matching telemetry newer than that boundary contains the expected metric attributes, span fields, or log fields. It cannot pass on stale evidence from an earlier checkpoint.
* The helper validates local prerequisites first: the insertion marker appears exactly once, Python compiles, the service reloaded, and all health checks pass. It then distinguishes `WAITING_FOR_TELEMETRY` from `CODE_OR_SERVICE_ERROR` and prints the appropriate self-service recovery command.

## Proposed system

Use a small checkout environment related to the presentation without repeating its retry incident:

```text
Traffic generator
       |
       v
Checkout API ---> Inventory service
       |
       v
Payment service
```

This is the same checkout world as the talk, viewed through a different slice. Say that once in the intro so the change from the talk's Checkout to Payments to Fraud path does not cause a double-take.

### Checkout API

Responsibilities:

* Receive checkout requests.
* Request inventory reservation.
* Calculate the payable amount.
* Request payment authorization.
* Return a checkout result. A rejected payment returns HTTP 200 with a failed business outcome, not a 5xx. This is deliberate and is the core of the hidden-failure lesson.

### Inventory service

Responsibilities:

* Reserve a requested product.
* Return a deterministic success response.

This service exists to make the trace distributed and realistic. It should not contain a second fault path.

### Payment service

Responsibilities:

* Recalculate or validate the expected amount.
* Reject a payment when the submitted total does not match its expected total.

### Traffic generator

Use a prepared Python runner packaged as a Compose service, not a host-side dependency and not an extreme load tool. Participants invoke it only through commands such as `./lab traffic healthy`, `./lab traffic incident`, and `./lab traffic checkpoint`. Each command uses a fixed seed, request count, mix, and duration, then prints the expected range of outcomes. The lab needs enough repeated requests to make rates visible; it does not simulate production-scale load.

## Deterministic incident

### Currency-rounding mismatch, surfaced behind an HTTP 200

Discounted CAD orders fail payment validation because Checkout and Payment apply different rounding rules. The totals differ by one minor unit. Checkout returns HTTP 200 with a failed business outcome, so the request looks successful at the HTTP and infrastructure level.

The incident arithmetic is fixed and uses Python `Decimal`; binary floating-point behavior is never involved:

* Checkout rounds the final payable amount with `ROUND_HALF_UP`.
* Payment independently validates it with `ROUND_HALF_EVEN`.
* The discounted CAD fixture produces an unrounded total of `10.005`: Checkout submits `1001` minor units while Payment expects `1000`.
* The discounted USD fixture produces `10.015`: both modes produce `1002` minor units.
* Non-discounted CAD totals are already exact to two decimal places.

The incident profile sends exactly 100 requests with a fixed seed:

* 50 non-discounted CAD orders that succeed.
* 25 discounted USD orders that succeed.
* 25 discounted CAD orders that fail.

The expected business-failure percentage is therefore 25%, within a small documented tolerance only if requests are retried by the runner. The healthy profile sends a separate fixed mix in which every request succeeds. Unit tests assert all expected minor-unit values and prove that only discounted CAD fails by exactly one cent.

This creates a real failure through application logic. The telemetry reports the behavior; it does not fabricate the answer.

The hidden-failure property is a design requirement, not an accident. Host metrics stay healthy and every request is HTTP 200, so nothing at the infrastructure or status-code level reveals the problem. Only the business outcome attribute added in Checkpoint 1 exposes it. This is the lab's version of the talk's point that a customer can get an HTTP 200 while the service is not doing its job.

Expected evidence chain:

| Question | Evidence |
| --- | --- |
| Detect | Checkout business-failure percentage rises above the healthy baseline, even though HTTP status and host metrics look fine. |
| Scope | Failures are concentrated in discounted CAD requests. |
| Isolate | Failed traces identify payment amount validation as the failing operation. |
| Explain | A correlated structured event shows the expected and received minor-unit values and the mismatched rounding modes. |

Expected final diagnosis:

> Checkout was returning HTTP 200 while a segment of orders failed. The outcome metric showed failures rising for discounted CAD orders. A failed trace isolated the problem to payment amount validation. The correlated event showed that Checkout and Payment used different rounding rules, producing a one-cent mismatch.

## What is prebuilt

Participants arrive with the repository and container images already prepared. They do not spend lab time installing dependencies or configuring infrastructure.

Prebuild:

* All three FastAPI services and their Dockerfiles.
* Docker Compose configuration with bind-mounted source and `uvicorn --reload`.
* Grafana OpenTelemetry LGTM service.
* OpenTelemetry providers, exporters, resource attributes, and HTTP context propagation.
* Automatic FastAPI, Uvicorn, and `httpx` instrumentation.
* Provisioned Grafana data sources and dashboards with pinned UIDs, anonymous local access, and no onboarding prompts.
* Mandatory bidirectional trace-to-logs correlation with fixed `service.name`, `trace_id`, and `span_id` mappings and tested time-window padding.
* Deterministic healthy, checkpoint, and incident traffic profiles with documented request counts and expected outcomes.
* Visible insertion markers in the starter code.
* Exact copyable code blocks for every participant edit.
* One recovery branch or tag per checkpoint.
* The `./lab check` telemetry-poll backstop.
* Reset and readiness scripts.
* A prepared evidence worksheet.
* A fallback evidence capture generated by the real services.

Participants start the complete environment with one command:

```bash
docker compose up -d
```

The repository also provides a readiness check:

```bash
./lab ready
```

Expected result:

```text
READY: checkout, inventory, payment, telemetry, and Grafana are available
```

Environment setup is pre-work, not lab content. Before the session, attendees receive the repository and pinned image bundle and run one setup command. At the session, the 45-minute clock begins only after `./lab ready` succeeds. The readiness check validates ports, service health, Grafana access, and end-to-end delivery of one synthetic metric, span, and structured event through the same pipelines used by the lab.

## Repository shape

Use a single repository with predictable paths:

```text
observability-lab/
├── README.md
├── lab                       # the only command participants run
├── guide/
│   ├── guide.html            # generated; ./lab guide opens it
│   ├── worksheet.html
│   ├── participant-guide.md  # source of truth for both pages
│   ├── worksheet.md
│   └── images/
├── services/                 # the system under test
│   ├── shared/               # telemetry.py, domain.py
│   ├── checkout/app/{main,checkout}.py
│   ├── inventory/app/main.py
│   └── payment/app/{main,validation}.py
└── workshop/                 # machinery; participants never open it
    ├── compose.yaml
    ├── checkpoints/{0-starter,1-metrics,2-traces,3-logs}
    ├── docker/
    ├── telemetry/{grafana,otel}
    ├── traffic/generate.py
    ├── scripts/              # check_*.py, links.py, build_guide.py, guide_template/
    ├── tests/
    ├── facilitator/
    └── notes/
```

The root `./lab` command is the only executable at the top level, which is why the helper package is named `workshop/` rather than `lab/`: a file and a directory cannot share one path. The participant guide must always identify one repository-relative path and one insertion marker per edit.

## Starting state

The initial system is weak but believable:

* Prepared process/runtime CPU and memory metrics are available and look healthy. They are emitted through the same OpenTelemetry pipeline, avoiding an additional infrastructure exporter solely for the lab.
* Every request is HTTP 200, including the failing ones.
* Automatic HTTP traces show service hops but not the important business decision.
* Application logs are unstructured, repetitive, and incomplete.
* There is no checkout outcome metric segmented by bounded business context.
* The incident can be reproduced, but the available evidence cannot answer the four questions.

Do not make the starting state completely blind. That feels artificial. It should contain the kind of telemetry a team inherits: technically active, operationally incomplete. The poor logs come from real application activity, not from fake loops that only print noise.

### The weak starting state has a hard visual target

The opening exploration must not become an open-ended hunt or make a claim that prose logs are literally unsearchable. The guide gives one concrete task with a three-minute limit: use the available logs to identify every payment-validation rejection, determine which segment is affected, and tie one rejection to its checkout request.

Participants may find individual lines through text search, but they cannot reliably count, segment, or correlate the complete set because the messages have inconsistent prose and no stable event or business fields. The guide then states the scale point: if that is unreliable in a tiny lab, it is far worse in a real service handling thousands of requests a minute. A visible stop marker ends the search and moves them on without facilitator intervention.

## Participant code changes

Participants complete all three instrumentation changes.

### Checkpoint 1: Metrics for detection and scope

Target file:

```text
checkout/app/checkout.py
```

Insertion marker:

```python
# LAB 1: record checkout result
```

The supplied snippet records one metric contract:

* Counter name: `checkout.completed`.
* Unit: `{checkout}`.
* Outcome attribute: `success`, `payment_rejected`, or `inventory_rejected`.
* Currency attribute: `CAD` or `USD`.
* Discount attribute: Boolean.

The business-failure percentage is defined as the rate of completed checkouts whose outcome is not `success`, divided by the rate of all completed checkouts. The by-segment view groups only by currency and discount. The attribute vocabularies are bounded and documented.

A duration histogram is not part of the required edit because latency does not help diagnose this incident. The guide notes that good telemetry is selected for the question being answered; the lab does not add an unused signal merely to exercise another API.

Prefer separating the lab run by environment or time window rather than by a metric label. Do not put a run identifier on a metric as a high-cardinality label.

Explicitly exclude customer ID, order ID, request ID, trace ID, product ID, and raw URL from metric attributes.

Confirmation: run the fixed healthy profile followed by the incident profile, open the checkout overview and by-segment view, and see the business-failure percentage move from 0% to 25%, concentrated in discounted CAD. Checkpoint confirmation is a brief visual check; participants reserve the full interpretation for the guided diagnosis.

Prediction question before the edit:

* Host metrics are green and every request is HTTP 200. Is checkout healthy?

Questions after:

* Which view tells us a problem exists, given that HTTP status looked fine?
* Which view limits the affected segment?
* Why would a request identifier be unsuitable as a metric attribute?

### Checkpoint 2: Trace detail for isolation

Target file:

```text
payment/app/validation.py
```

Insertion marker:

```python
# LAB 2: annotate amount validation span
```

Automatic instrumentation already provides the distributed HTTP trace. The supplied snippet adds application-specific evidence to a focused validation span:

* Operation name.
* Currency.
* Discount presence.
* Validation result.
* Error status when validation rejects the amount.

The span deliberately stops short of the expected and received amounts and the rounding modes. Those values belong only to the Checkpoint 3 event. This is a build requirement: if the span already carries the amounts, the log step has nothing left to reveal and the distinction between where and why collapses.

Do not place full customer or payment information on the span.

Confirmation: run fresh checkpoint traffic, open the saved trace search filtered by `service.name=payment`, the validation span name, and span status `ERROR`, then select a result created after the checkpoint traffic began. The top-level HTTP span remains successful because the response is HTTP 200; the custom validation child span carries the error status. `./lab check traces` verifies that at least one matching fresh span exists and prints its trace ID as a deterministic fallback.

Questions:

* What did automatic instrumentation already show?
* What decision was invisible before this annotation?
* What can the trace establish, and what still needs event-level context?

### Checkpoint 3: Structured event for explanation

Target file:

```text
payment/app/validation.py
```

Insertion marker:

```python
# LAB 3: record amount validation rejection
```

Participants replace one weak prose log with a supplied structured event emitted through the preconfigured Python logging-to-OTLP bridge. The event contains:

* Stable event name: `payment.amount_validation_rejected`.
* Reason code.
* Currency.
* Discount presence.
* Expected amount in minor units.
* Received amount in minor units.
* Checkout rounding mode.
* Payment rounding mode.
* Trace and span identifiers through configured correlation.

Do not include card data, payment tokens, customer details, or raw request payloads.

Confirmation: run fresh checkpoint traffic, open the payment-validation events view filtered to the stable event name, and use the provisioned trace link on that event. Then open the same fresh trace and use Logs for this span to navigate back to the event. Both directions are required and use trace IDs as structured metadata rather than Loki stream labels.

Questions:

* Which fields make the event filterable and groupable?
* Why use integer minor units rather than formatted currency strings?
* What does the event explain that the trace did not?
* Why is `WARN` appropriate for a validation rejection that the Payment service handled correctly but that signals abnormal upstream behavior?

## Pre-filtered participant links

Every checkpoint provides a named link. Participants do not construct PromQL, LogQL, or TraceQL on the main path. Because each participant runs their own stack, every link is an identical `localhost:3000` URL.

All overview links use a relative range, `now-15m` to `now`, so a link never goes stale when traffic stops. Dashboard calculations use short rate windows that make the healthy-to-incident transition visible despite repeated checkpoint traffic. `./lab links` generates every URL from pinned dashboard and data-source UIDs; participants never copy encoded Explore state manually.

Recommended links:

1. Runtime health
   * Prepared CPU and memory indicators for the three Python service processes.
   * Purpose: show why healthy runtime behavior and HTTP 200 responses cannot establish healthy checkout behavior.

2. Checkout overview
   * Completed-checkout rate and business-failure percentage, including the healthy-to-incident transition.
   * Purpose: Detect.

3. Checkout outcomes by segment
   * Currency and discount dimensions already selected.
   * Purpose: Scope.

4. Payment-validation error traces
   * A saved Explore query filters on the Payment service, the custom validation span name, and child-span error status. Participants sort or identify a result created after their latest traffic run. Tempo search does not guarantee that the first result is the newest, so the guide never claims it does. `./lab check traces` prints a known-fresh trace ID if selection is ambiguous.
   * Purpose: Isolate.

5. Payment validation events
   * Stable event name and relative window selected.
   * Purpose: Explain.

6. Correlated event from trace
   * Direct navigation from a trace to its logs, demonstrating cross-signal correlation.
   * Purpose: show the link between where and why.

The participant guide shows links as large, human-readable buttons or headings, each followed by one sentence stating the question it helps answer, and a screenshot of the expected result.

## 45-minute self-guided path

Times are a pacing guide for a self-paced room, not facilitator gates.

| Time | Phase | Participant action |
| --- | --- | --- |
| 0–3 min | Orientation | Open the guide, Grafana, and worksheet; confirm the already-started environment is ready |
| 3–6 min | Weak starting state | Run incident traffic; attempt the bounded log task; read the scale point and stop |
| 6–15 min | Metrics | Predict, paste, save, run the fixed healthy and incident profiles, briefly confirm the outcome metric and segment view |
| 15–24 min | Traces | Paste the span annotation, run fresh traffic, briefly confirm the validation error span |
| 24–33 min | Structured logs | Paste the structured event, run fresh traffic, briefly confirm the event and bidirectional correlation |
| 33–41 min | Guided diagnosis | Freeze the code; follow Detect, Scope, Isolate, Explain and record one evidence statement at each step |
| 41–45 min | Debrief | Complete the review gate, state the supported diagnosis, and close the loop back to the talk |

## Fifteen-minute buffer policy

The remaining 15 minutes in the slot are deliberately unallocated.

Use the buffer for:

* Docker startup or machine-specific issues.
* Telemetry ingestion delay.
* Self-service recovery to a checkpoint branch.
* Useful discussion when a concept prompts it.
* A short break between the presentation and the lab.
* Final questions.

Do not add stretch content to consume the buffer by default. Reliably finishing the complete path matters more than filling every minute. If the path runs long, preserve the guided diagnosis and recover participants to completed branches rather than cutting the diagnosis or debrief.

## Guided diagnosis

Participants run the incident traffic profile themselves and open one view at a time, recording an evidence statement before moving on. This is the formal investigation boundary: instrumentation is complete, code is frozen, and nobody adds telemetry during diagnosis. The guide reveals the views in order so the reasoning is structured without needing a facilitator.

### Detect

Open the checkout overview.

Record:

* What changed.
* Failure percentage.
* Time window.

Required evidence statement:

> Checkout business failures increased during the incident window, even though every request returned HTTP 200 and host metrics stayed healthy.

### Scope

Open checkout outcomes by segment.

Record:

* Affected segment.
* Unaffected comparison groups.
* One claim that would be too broad.

Required evidence statement:

> Failures are concentrated in discounted CAD orders; the evidence does not support saying that all checkout traffic is failing.

### Isolate

Open a failed checkout trace.

Record:

* Failing operation.
* Trace ID.
* What the trace proves.
* What it does not explain.

Required evidence statement:

> The failed request reached Inventory successfully and was rejected during Payment amount validation. The trace does not yet explain why the values differed.

### Explain

Open the correlated structured event.

Record:

* Expected amount.
* Received amount.
* Difference in minor units.
* Rounding modes.

Required evidence statement:

> Checkout and Payment used different rounding rules for discounted CAD totals, producing a one-cent mismatch and a validation rejection.

### Debrief: close the loop back to the talk

End by connecting the experience back to two points from the presentation:

* The reactive loop. Nobody added instrumentation during the diagnosis. The evidence existed before the investigation started, which is the opposite of the reactive cycle the talk opened with.
* The Microsoft Teams study on Slide 3. In that study 45 percent of incidents were first found by people rather than monitoring, and missing telemetry was tied to delayed root-cause identification in a meaningful share of complex incidents. In the lab, because the evidence was in place first, the same class of problem was found and explained in minutes without a redeploy.

## Participant guide design

Each checkpoint page contains:

1. The operational question.
2. A short explanation of why the current evidence is insufficient.
3. Exact file path.
4. Function name and insertion marker.
5. Two to four surrounding code lines for orientation.
6. Complete copyable code.
7. The traffic command.
8. The pre-filtered Grafana link and a screenshot of the expected view.
9. One prediction question.
10. One evidence statement to complete before seeing the answer.
11. A collapsed Check your answer section containing the expected evidence statement and a short explanation. Screenshots and headings must not reveal the affected segment or root cause before this point.
12. A visible stop marker.
13. The self-service recovery command.

The guide never asks participants to instrument something without supplying the implementation, and it never depends on a facilitator to unlock a step. Each code block is complete in context, includes required imports or uses predeclared handles, is safe to paste once, and is guarded against duplicate metric registration.

## Facilitator guide design

Because the lab is self-guided, the facilitator guide is short. It contains:

* A one-paragraph description of how the lab runs itself and what the facilitator is watching for.
* The self-service recovery commands, so a facilitator can point rather than solve.
* Expected participant answers for each question.
* Common misconceptions and a two-sentence answer for the cardinality question so it does not become a lecture.
* Ingestion-delay expectations.
* A tested fallback evidence capture from the same real application behavior, projected if a participant's environment fails entirely.

## Recovery strategy: self-service

Provide one completed branch or tag per checkpoint, but hide Git mechanics behind an idempotent recovery command:

```text
checkpoint/0-starter
checkpoint/1-metrics-complete
checkpoint/2-traces-complete
checkpoint/3-logs-complete
```

Recovery is a step in the guide, not an escalation to a facilitator. Direct `git switch` is never shown because it can fail when participants have uncommitted pasted edits. If evidence does not appear and the check times out, the guide gives one command:

```bash
./lab recover metrics
```

The recovery helper safely replaces only the lab-editable files with the cumulative known-good checkpoint, removes duplicate snippets, waits for hot reload, checks service health, establishes a fresh evidence boundary, generates checkpoint traffic, and verifies the expected signal. It preserves participant worksheets and does not rebuild images. The command is tested from dirty files, syntax errors, duplicate pastes, stopped services, and partial checkpoints.

## Individual and paired participation

The lab is designed so one person completes every step independently. If participants pair up, both answer every question and both follow the complete diagnosis. Pairing is a support mechanism, not a way to split the curriculum.

## Scope boundaries

Participants will not:

* Install Python dependencies during the lab.
* Build the services from scratch.
* Configure OpenTelemetry providers or exporters.
* Configure Grafana data sources.
* Build dashboards.
* Write query languages from memory.
* Implement context propagation.
* Rebuild containers on the main path.
* Debug Docker networking as a learning activity.
* Generate extreme traffic volume.
* Search freely for a different incident.
* Fix the rounding defect before completing the diagnosis.

## Reliability requirements

Before delivery:

* Pin every Docker image and Python dependency version.
* Pre-pull or distribute all images so nothing is fetched from the public internet during the session.
* Require 8 GB RAM and test on an 8 GB machine, not a high-spec one.
* Test on Windows with Docker Desktop and WSL2 if that is a supported participant environment.
* Document minimum Docker memory and disk requirements.
* Confirm `docker compose up -d` works offline with no build or pull.
* Pin and test Docker/Compose versions, CPU architecture, Docker memory allocation, disk availability, line endings, file sharing, and required ports for every supported participant platform.
* Confirm hot-reload applies a pasted edit within a couple of seconds with no rebuild; enable polling-based reload where file events are unreliable.
* Confirm all dashboards and localhost links open the expected filtered view after a clean reset.
* Confirm every overview link uses a relative range and every provisioned UID survives a clean restart.
* Configure metric export at no more than five seconds, use 100% trace sampling, shorten log/trace batching, and confirm all three signals appear within the stated twenty-second bound.
* Confirm `./lab check` rejects stale telemetry and uses the same backend filters as the visible Grafana view.
* Provide a reset command that restores code, traffic state, and dashboards to a known state.
* Keep a facilitator machine with the complete environment projected as a last resort.
* Keep screenshots or exported evidence as the final fallback.

## Definition of done

The lab is ready only when:

* A clean 8 GB machine can start the full environment with one command, offline.
* The readiness check reports every dependency clearly and proves end-to-end delivery of a synthetic metric, span, and structured event under a dedicated `lab-readiness` service name that is excluded from participant views.
* A beginner can follow every code edit and every diagnosis step from the guide alone, without a facilitator.
* A pasted edit becomes visible evidence in the pre-filtered view within about twenty seconds, with no rebuild.
* The incident stays hidden behind HTTP 200 and healthy host metrics until the outcome metric reveals it.
* The deterministic traffic profiles produce the exact documented request counts, a 25% incident business-failure percentage, a one-cent mismatch only for discounted CAD, and unaffected comparison groups every run.
* Every supplied localhost link opens the expected filtered view over a relative window in a clean browser with no login, onboarding prompt, or manual data-source selection.
* The Checkpoint 2 span does not carry the amounts, so Checkpoint 3 is genuinely necessary.
* The final diagnosis is supported by evidence from all three signals.
* No participant needs to learn Grafana query syntax.
* Self-service recovery succeeds from dirty files, syntax errors, duplicate snippets, stopped services, and partial checkpoints without facilitator intervention.
* The starter logs and Checkpoint 2 span cannot reveal the rounding mismatch before the structured event is added.
* A spoiler review confirms participant headings, screenshots, links, filenames, and prompts do not disclose the diagnosis before learners record their evidence.
* At least two Python beginners complete the path unaided within 45 minutes on the minimum supported machine; the target rehearsal time is 40 minutes or less to preserve delivery margin.

## Remaining planning questions

These can be decided during prototyping without changing the lab model:

1. Exact FastAPI route and data model names.
2. Exact FastAPI function, model, and internal variable names around the locked telemetry contracts.
3. Whether images are pre-pulled through a setup session or distributed as an archive.
4. Final wording of the screenshots and expected-output captures in the guide.
5. The supported operating-system and CPU-architecture matrix after the vertical-slice tests.

## Recommended next step before implementation

Prototype one vertical slice only:

```text
starter repository
→ docker compose startup
→ supplied checkout metric edit (hot-reloaded)
→ run traffic
→ pre-filtered Grafana metric view showing failures behind HTTP 200
→ ./lab check metrics backstop
```

Test that slice unaided with at least two Python beginners and one experienced developer on the minimum supported machine. The slice must prove offline startup, end-to-end readiness, hot reload, fresh-evidence checking, the pre-filtered view, and recovery from a broken paste. Do not build tracing, logging, or the rest of the participant guide until this path is reliable and comfortably fits within nine minutes.

## Final review verdict

This design satisfies the intended requirements:

* Educational: every edit is tied to one operational question, and the final diagnosis requires complementary evidence from metrics, traces, and structured logs.
* Engaging: participants predict, make a real code change, see real telemetry, and defend an evidence statement rather than watching a demo or following an open-ended hunt.
* Self-guided: exact code, stable links, screenshots, checks, answer reveals, and one-command recovery remove the need for continuous facilitation.
* Aligned to the presentation: the lab applies Detect, Scope, Isolate, and Explain; reinforces hidden business failures behind HTTP 200; and ends by applying the observable-enough review gate.

The remaining risk is execution reliability, not learning design. The vertical-slice gate is therefore mandatory: if the metric checkpoint cannot run unaided, offline, and recoverably within nine minutes on an 8 GB machine, simplify the environment or workflow before implementing the other signals.
