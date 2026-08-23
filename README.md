# Build software that can explain itself: guided observability lab

This repository contains the complete 45-minute hands-on lab that follows the presentation. Participants instrument a Python checkout system with metrics, traces, and structured logs, then diagnose a deterministic business failure hidden behind HTTP 200 responses.

## Learning outcome

By the end, participants can use telemetry to answer four questions:

1. **Detect:** Is checkout behaving correctly?
2. **Scope:** Which requests are affected?
3. **Isolate:** Where did one operation fail?
4. **Explain:** What application condition caused it?

Success means diagnosing the incident from telemetry that existed before the investigation. No new telemetry is added after the diagnosis begins.

## Stack

- Python 3.12, FastAPI, Uvicorn, and `httpx`
- OpenTelemetry metrics, traces, and logs over OTLP/HTTP
- Grafana OpenTelemetry LGTM `0.29.0`
- Docker Compose, one independent stack per laptop

## Before the session

Requirements:

- Docker Desktop for Mac (Apple silicon or Intel) with Compose v2
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

Then follow [participant-guide.md](participant-guide.md).

## Useful commands

```text
./lab links                    Print every prepared Grafana link
./lab traffic healthy          Generate a healthy baseline
./lab traffic incident         Generate the deterministic incident
./lab check metrics            Verify fresh metrics evidence
./lab check traces             Verify a fresh failed validation span
./lab check logs               Verify fresh structured rejection events
./lab recover metrics          Restore the completed metrics checkpoint
./lab recover traces           Restore metrics + traces
./lab recover logs             Restore all three checkpoints
./lab reset                    Restore starter code and remove telemetry data
./lab test                     Run in-container unit and contract tests
./lab validate-full            Validate the complete path; restores starter and stops afterward
```

## Deterministic incident

Every incident run sends exactly 100 requests. Every request returns HTTP 200, while a fixed subset receives a failed checkout business outcome. The affected segment and application condition are intentionally omitted here; participants establish both from the telemetry they add.

The failure is produced by real application logic with Python `Decimal`. The telemetry reports that behavior; it does not fabricate diagnostic evidence.

## Validation

The original metrics vertical slice was validated on Docker Desktop with a 7.75 GiB Docker VM, peaking below 0.7 GiB and completing the warm validation in 36 seconds. The full traces-and-logs extension must be validated on the target participant platform with:

```bash
./lab validate-full
```

The command always restores the starter files and stops the stack on success, failure, or interruption. Rehearse on every supported operating system and CPU architecture before distribution; this package has not been certified for an unspecified platform matrix.
