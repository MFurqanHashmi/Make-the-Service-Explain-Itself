# Validation status

## Metrics vertical slice

The initial metrics slice was validated on a real Docker Desktop environment:

- Grafana OpenTelemetry LGTM `0.29.0`
- 7.75 GiB Docker VM allocation
- Peak observed stack memory below 0.7 GiB
- Warm `validate-slice` execution: 36 seconds
- Dashboard provisioning and OTLP-to-Prometheus translation passed
- Deterministic result: 100 HTTP 200 responses, 75 business successes, and 25 discounted-CAD rejections

Native validation found and corrected grouped-counter undercounting for series first created during the traffic window. `workshop/scripts/check_metrics.py` therefore uses the last sample before the traffic boundary, or zero if the series did not yet exist, and handles counter resets after hot reload.

## Full lab

Run on the target participant platform:

```bash
./lab validate-full
```

The command validates:

- Starter restoration and offline startup from cached images
- Metrics, traces, and structured logs delivered through real OTLP pipelines
- Exact deterministic incident behavior
- Self-service recovery from broken Python at all three checkpoints
- In-container unit and structural tests
- The nine-minute automated validation budget
- Unconditional cleanup: starter source restored and Compose stopped

This sandbox does not provide a Docker daemon, so the traces, Loki structured metadata, Grafana correlation links, and full-container timing require the real-Docker validation above before delivery.

## Required manual rehearsal

After `./lab validate-full` passes, open every URL from `./lab links` and manually verify one Loki-to-Tempo link and one Tempo-to-Loki **Logs for this span** link. The automated gate confirms that the datasource correlation configuration is provisioned; it cannot prove the browser interaction itself. Capture actual Grafana screenshots for the participant guide during this rehearsal if visual references are required for the final session.
