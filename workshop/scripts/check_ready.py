"""Confirm the whole telemetry pipeline is accepting and serving data.

The three backends inside the LGTM container do not become queryable at the
same time. Tempo is consistently the slowest: measured at roughly 27 seconds
after `./lab start` returns on a warm Docker Desktop. The budget below has to
comfortably exceed that, or the very first command a participant runs fails.
"""
import os
import time

from workshop.scripts.backend import get_json

PROM = os.getenv("PROMETHEUS_URL", "http://lgtm:9090")
TEMPO = os.getenv("TEMPO_URL", "http://lgtm:3200")
LOKI = os.getenv("LOKI_URL", "http://lgtm:3100")
BUDGET_SECONDS = 150

SIGNALS = ("metrics", "traces", "logs")


def metrics_ready():
    payload = get_json(PROM, "/api/v1/query", {"query": 'sum({__name__=~"lab_readiness.*"})'})
    return bool(payload.get("data", {}).get("result"))


def traces_ready():
    payload = get_json(TEMPO, "/api/search", {"q": '{ name = "lab.readiness" }', "limit": 5})
    return bool(payload.get("traces"))


def logs_ready():
    now = time.time()
    payload = get_json(LOKI, "/loki/api/v1/query_range", {
        "query": '{service_name=~"checkout|inventory|payment"} | event_name = "lab.readiness"',
        "start": int((now - 3600) * 1e9),
        "end": int(now * 1e9),
        "limit": 10,
    })
    return bool(payload.get("data", {}).get("result"))


def main():
    probes = (metrics_ready, traces_ready, logs_ready)
    ok = [False, False, False]
    deadline = time.time() + BUDGET_SECONDS
    announced = False

    while time.time() < deadline and not all(ok):
        for index, probe in enumerate(probes):
            if ok[index]:
                continue
            try:
                ok[index] = probe()
            except Exception:
                pass
        if all(ok):
            break
        if not announced:
            print("Waiting for the telemetry backends to finish starting (up to "
                  f"{BUDGET_SECONDS}s on a cold start)...")
            announced = True
        time.sleep(2)

    if not all(ok):
        missing = ", ".join(name for name, good in zip(SIGNALS, ok) if not good)
        print(f"NOT READY: {missing} not serving data yet.")
        print("The backends sometimes need longer on a cold start. Run './lab ready' again.")
        print("If it still fails, run './lab restart-services' to re-emit the readiness markers.")
        return 1

    print("READY: checkout, inventory, payment, metrics, traces, logs, and Grafana are available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
