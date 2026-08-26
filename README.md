# Build software that can explain itself: guided observability lab

This repository contains the complete hands-on lab that follows the presentation. Participants
instrument a Python checkout system with metrics, traces, and structured logs, then diagnose a
deterministic business failure hidden behind HTTP 200 responses.

The lab takes about 45 minutes inside a 60-minute session.

## Learning outcome

By the end, participants can use telemetry to answer four questions:

1. **Detect:** Is checkout behaving correctly?
2. **Scope:** Which requests are affected?
3. **Isolate:** Where did one operation fail?
4. **Explain:** What application condition caused it?

Success means diagnosing the incident from telemetry that existed before the investigation. No new
telemetry is added after the diagnosis begins.

## What is where

```text
lab              every command you run, start to finish (./lab with no arguments lists them)
guide/           what participants read via ./lab guide: guide.html and the worksheet,
                 plus the Markdown sources they are generated from
services/        the checkout system under test — checkout, inventory, payment, shared
workshop/        everything running the lab needs and nobody has to open:
                 checkpoints, telemetry config, traffic generator, tests, Docker, facilitator notes
```

Participants only ever touch two files, both under `services/`, and both named in the guide.

## Stack

- Python 3.12, FastAPI, Uvicorn, and `httpx`
- OpenTelemetry metrics, traces, and logs over OTLP/HTTP
- Grafana OpenTelemetry LGTM `0.29.0`
- Docker Compose, one independent stack per laptop

## Before the session

Requirements:

- Docker Desktop for Mac (Apple silicon or Intel) with Compose v2 or later
- At least 8 GB system RAM
- Ports `3000`, `4317`, `4318`, `8000`, and `9090` available
- Approximately 4 GB free disk space
- macOS with the built-in `bash`/`zsh` shell (the `./lab` script runs on both)

With internet access, prepare the images once:

```bash
./lab setup
```

For an offline session, a facilitator can distribute an image archive:

```bash
./lab export-images observability-lab-images.tar
./lab import-images observability-lab-images.tar
```

## Start the lab

```bash
./lab start
./lab ready
./lab guide
```

`./lab start` can take two to three minutes the first time. `./lab guide` then opens the lab page
in your browser — that is the lab. Work straight through it: every Grafana view is a button in the
page, every command has a copy button, and the answers stay hidden behind toggles until you open
them. `./lab guide worksheet` opens the evidence worksheet the same way, when section 5 asks for it.

Read the lab through `./lab guide`, not by opening the files under `guide/` directly.
`guide/participant-guide.md` and `guide/worksheet.md` are the Markdown sources the pages are
generated from, and any editor that shows them as plain text also shows every answer, screenshot
and reveal — which is most of the exercise.

## Commands

Run `./lab` with no arguments for the full list. The ones you need during the lab:

```text
./lab start                    Start the stack
./lab ready                    Verify every backend is serving data
./lab guide                    Open the lab guide in your browser (add 'worksheet' for the worksheet)
./lab traffic healthy          Generate a healthy baseline
./lab traffic incident         Generate the deterministic incident
./lab check metrics            Verify fresh metrics evidence
./lab check traces             Verify a fresh failed validation span
./lab check logs               Verify fresh structured rejection events
./lab stop                     Stop containers, keep telemetry and code
```

If something goes wrong:

```text
./lab logs checkout            Show a service's recent output (checkout|inventory|payment)
./lab ready                    Safe to re-run; backends can be slow on a cold start
./lab links                    Print the four Grafana URLs, if you would rather not use the buttons
./lab restart-services         Re-emit readiness markers, then run ./lab ready again
./lab recover metrics          Restore the completed metrics checkpoint
./lab recover traces           Restore metrics + traces
./lab recover logs             Restore all three checkpoints
./lab reset                    Restore starter code and remove telemetry data
```

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `cannot reach the Docker daemon` | Docker Desktop is not running or is still starting. |
| `missing Docker image(s)` | `./lab setup` has not run on this machine. |
| `NOT READY: traces not serving data yet` | The backends are slow on a cold start. Run `./lab ready` again; if it persists, `./lab restart-services`. |
| Port already allocated | Something else holds 3000, 4317, 4318, 8000, or 9090. Free it, then `./lab start`. |
| Grafana Explore redirects to a dashboard | The anonymous role lost Explore access. `workshop/compose.yaml` must set `GF_AUTH_ANONYMOUS_ORG_ROLE: Editor`; `./lab ready` checks this. |
| A `check` command times out | `./lab recover <signal>` for the stage you are on. |
| The guide's Grafana buttons open a connection error | The stack is not running. `./lab start`, then `./lab ready`. |
| The guide looks out of date after editing the Markdown | `./lab build-guide` regenerates `guide.html` and `worksheet.html`; `./lab test` fails if they are stale. |

## Deterministic incident

Every incident run sends 100 requests (plus one warm-up). Every request returns HTTP 200, while a
fixed subset receives a failed checkout business outcome. Segments are interleaved so that every
four consecutive requests contain exactly one from the failing segment, which keeps the dashboard's
rate window stable.

The affected segment and application condition are intentionally omitted here; participants
establish both from the telemetry they add. Order IDs are opaque, and no prose log names an
outcome, a currency, or a discount flag — the starting state is meant to be genuinely unhelpful.

The failure is produced by real application logic with Python `Decimal`. The telemetry reports that
behaviour; it does not fabricate diagnostic evidence.

## Validation

Facilitators should certify the package on the target participant platform before distribution:

```bash
./lab validate-full
```

The command always restores the starter files and stops the stack on success, failure, or
interruption. Rehearse on every supported operating system and CPU architecture before
distribution. Recorded validation runs and platform notes live in [workshop/notes/](workshop/notes/), and the
run-the-room instructions live in
[workshop/facilitator/facilitator-guide.md](workshop/facilitator/facilitator-guide.md).
