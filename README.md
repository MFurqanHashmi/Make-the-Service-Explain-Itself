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
```

`./lab start` can take two to three minutes the first time. Then follow
[participant-guide.md](participant-guide.md) — read it in a Markdown preview, because it hides
answers behind toggles.

## Commands

Run `./lab` with no arguments for the full list. The ones you need during the lab:

```text
./lab start                    Start the stack
./lab ready                    Verify every backend is serving data
./lab links                    Print every prepared Grafana link
./lab traffic healthy          Generate a healthy baseline
./lab traffic incident         Generate the deterministic incident
./lab check metrics            Verify fresh metrics evidence
./lab check traces             Verify a fresh failed validation span
./lab check logs               Verify fresh structured rejection events
./lab stop                     Stop containers, keep telemetry and code
```

If something goes wrong:

```text
./lab ready                    Safe to re-run; backends can be slow on a cold start
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
| Grafana Explore redirects to a dashboard | The anonymous role lost Explore access. `compose.yaml` must set `GF_AUTH_ANONYMOUS_ORG_ROLE: Editor`; `./lab ready` checks this. |
| A `check` command times out | `./lab recover <signal>` for the stage you are on. |

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
distribution. Recorded validation runs and platform notes live in [docs/](docs/), and the
run-the-room instructions live in
[facilitator/facilitator-guide.md](facilitator/facilitator-guide.md).
