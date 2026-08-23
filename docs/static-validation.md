# Static validation report

The complete lab passed the available pre-Docker validation in the build sandbox.

## Passed

- All Python files compile.
- All Bash entry points pass `bash -n`.
- Compose, Grafana datasource provisioning, dashboard provisioning, and dashboard JSON parse successfully.
- 16 unit and contract tests pass.
- Deterministic traffic fixtures produce 100 requests with 25 discounted-CAD business rejections and 100 HTTP 200 responses.
- Prometheus grouped-counter checks cover pre-window baselines, series born inside the traffic window, and counter resets.
- Tempo response parsing verifies a distributed Checkout → Inventory → Payment trace and a failed validation span without explanation fields.
- Loki parsing verifies all required typed event fields and trace/span context.
- Cumulative recovery checkpoints compile and the distributed working tree contains starter code.
- `validate-full` has unconditional cleanup that restores starter files and stops/removes the validation stack.
- Participant copy/paste blocks include literal required indentation.

## Already validated on real Docker

The predecessor metrics slice was validated on Docker Desktop with Grafana OpenTelemetry LGTM `0.29.0`, including dashboard rendering, real OTLP-to-Prometheus translation, offline cached-image startup, hot reload, recovery, sub-0.7 GiB peak stack memory, and a 36-second warm validation.

## Required before delivery

This build sandbox has no Docker daemon. Run `./lab validate-full` on the target participant platform, then manually open all links from `./lab links` and verify one Loki-to-Tempo and one Tempo-to-Loki browser navigation. Capture final Grafana screenshots during that rehearsal if they will be included in participant materials.
