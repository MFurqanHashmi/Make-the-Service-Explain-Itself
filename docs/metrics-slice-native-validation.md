# Observability Lab — metrics slice validation report

**Prototype:** `observability-lab-metrics-prototype`

| Round | Date | Environment | Outcome |
|-------|------|-------------|---------|
| 1 | 2026-08-23 | Anthropic cloud sandbox, **native shim** (no container registry access) | Application logic PASS; 5 items unverifiable |
| 2 | 2026-08-23 | **Real Docker** — macOS 15.5 arm64, Docker Desktop 4.74.0 / Engine 29.4.3, Compose v5.1.4, 24 GB host | **All 5 residual items PASS — after fixing one lab-blocking bug found here** |

---

## Short version (updated after round 2)

`./lab validate-slice` now **passes end to end on real Docker in 36 seconds** against a
nine-minute budget, and all five items round 1 had to defer are confirmed.

Round 2 found **one lab-blocking bug that the native shim could not structurally detect**:
`scripts/check_metrics.py` undercounted business events, so `./lab check metrics` — the exact
command participants run to confirm they have found the incident — **failed with a confusing
`WAITING_FOR_TELEMETRY` even though the application was behaving perfectly**. `./lab recover
metrics` calls the same checker, so the self-service recovery path failed too. It is fixed and
verified below.

**Exactly one prototype file was changed during validation:** `scripts/check_metrics.py`
(full diff in *Changes made to the prototype* below). No service code, dashboard, compose file,
Dockerfile, checkpoint, or test was modified.

**Bottom line:** the slice is now genuinely validated on the real stack. Proceed to the
tracing/logging checkpoints.

---

## Round 2 — the bug the shim could not find

### Symptom
First real `./lab validate-slice` run failed at the recovery gate:

```
WAITING_FOR_TELEMETRY: fresh series incomplete:
  completed=64.0, failures=14.0, CAD_discount=14.0, HTTP=100.0
```

The application was correct — `.lab-state/last-traffic.json` recorded exactly
`100 requests, {"200": 100}, {"success": 75, "payment_rejected": 25}`. Only the *read-back*
was wrong. Re-running the check produced identical numbers, so this was **deterministic, not
a timing race**.

### Root cause
`deltas()` computed each series' delta as `last_sample - first_sample` *inside* the traffic
window. But **a Prometheus series does not exist until its label combination is first
exported.** A series born mid-window already carries accumulated counts in its very first
sample, and subtracting that sample throws them away.

Measured directly against live Prometheus:

| series (`outcome/currency/discounted`) | born at | first | last | counted | **lost** |
|---|---|---|---|---|---|
| `success/CAD/false`        | t=0.00s | 1  | 51 | 50 | 1 |
| `payment_rejected/CAD/true`| t=8.00s | 11 | 25 | 14 | **11** |
| `success/USD/true`         | t=8.00s | 25 | 25 | **0** | **25** |
| | | | **total** | **64** | **36** |

`sum(checkout_completed_total)` moved 1 → 101 correctly; the loss appeared only once the query
grouped by `(checkout_outcome, checkout_currency, checkout_discounted)`. The HTTP panel escaped
because it has a single label combination (`status="200"`) that existed from the first sample.

**Why round 1 missed it:** the native shim served metrics from an in-process store where every
label combination was present from t=0. Mid-window series birth is an emergent property of the
real OTLP exporter + Prometheus scrape pipeline, so no shim could have reproduced it.

### Fix applied — `scripts/check_metrics.py`
The baseline for a counter is the last sample **before** the window (0 if the series did not
exist yet), never its own first in-window sample:

- Added `LOOKBACK = 60` and widened `range_series` to query from `start - LOOKBACK`, so each
  series' pre-window value is visible.
- `deltas(series, start)` now splits samples at `start`, uses the pre-window sample as the
  baseline (0 when the series did not exist yet), and guards against counter resets
  (`if baseline > window[0]: baseline = 0.0`) so the uvicorn hot-reload restart inside
  `./lab recover metrics` — which zeroes the counters — is handled correctly.
- Both call sites updated to pass `start`.

Verified against the **same** traffic window that had failed (no new traffic — isolating the fix):

```
PASS: fresh backend evidence confirms hidden business failures
  completed=100, failures=25 (25.0%)
  discounted_CAD_failures=25
  HTTP_200=100, non_200=0
```

Exactly matching the traffic generator's ground truth. Confirmed again on fresh traffic and on
a clean `./lab reset` → `validate-slice` run that exercises the counter-reset path.

---

## Changes made to the prototype

**One file changed: `scripts/check_metrics.py`.** Nothing else in the repository was modified.
Verbatim diff:

```diff
@@ line 5 @@
  STATE = Path("/workspace/.lab-state/last-traffic.json")
+ LOOKBACK = 60  # seconds of pre-window history used to establish counter baselines

@@ range_series @@
- return api("/api/v1/query_range", {"query": query, "start": start, "end": end, "step": 1})["result"]
+ return api("/api/v1/query_range", {"query": query, "start": start - LOOKBACK, "end": end, "step": 1})["result"]

@@ deltas @@
- def deltas(series):
+ def deltas(series, start):
+     # A label combination gets a Prometheus series only once its first datapoint is
+     # exported, so a series born mid-window already carries accumulated counts. Its
+     # baseline is the last sample *before* the window (0 if it did not exist yet) --
+     # not its own first in-window sample, which would discard those counts.
      out=[]
      for item in series:
-         vals=item.get("values", [])
-         if len(vals) < 2: continue
-         delta=max(0.0, float(vals[-1][1]) - float(vals[0][1]))
-         out.append((item["metric"], delta))
+         vals=[(float(t), float(v)) for t, v in item.get("values", [])]
+         window=[v for t, v in vals if t >= start]
+         if not window: continue
+         before=[v for t, v in vals if t < start]
+         baseline=before[-1] if before else 0.0
+         if baseline > window[0]: baseline=0.0  # counter reset (service restarted)
+         out.append((item["metric"], max(0.0, window[-1] - baseline)))
      return out

@@ main -- both call sites @@
- ... ({business})', start, end))
+ ... ({business})', start, end), start)
- ... ({http})', start, end))
+ ... ({http})', start, end), start)
```

**Not changed, but worth knowing:** the `deltas()` behaviour is only correct because
`traffic/generate.py` writes `started_at`/`ended_at` into `.lab-state/last-traffic.json`. Any
future `check_traces.py` / `check_logs.py` must keep that contract.

---

## Round 2 — the five residual items, all resolved

### 1. Peak memory vs the 8 GB minimum — **PASS**
Sampled every 3 s across a full run (35 samples), not just the end-of-run snapshot:

| container | peak |
|---|---|
| `observability-lab-lgtm` | 439.3 MiB |
| `observability-lab-checkout` | 84.3 MiB |
| `observability-lab-inventory` | 83.2 MiB |
| `observability-lab-payment` | 82.5 MiB |
| `tools` (ephemeral) | 21.7 MiB |
| **total peak** | **0.69 GiB** |

The whole stack peaks under **0.7 GiB**, roughly **9%** of the 7.75 GiB Docker VM. The 8 GB
laptop requirement has a very large margin — this was never close to the real constraint.

### 2. Grafana render, `schemaVersion: 41`, provisioning path — **PASS**
`otel-lgtm:0.29.0` bundles **Grafana 13.1.0**. `GET /api/dashboards/uid/checkout-overview`:

```
title      : Checkout observability: hidden failures
schemaVer  : 41          <- accepted natively, no migration
provisioned: True
folder     : Observability Lab
panels     : 7
```

The provisioning path `/otel-lgtm/grafana/conf/provisioning/dashboards/custom` is correct for
this image tag.

### 3. `service_name` resource-attribute promotion — **PASS** (round 1's biggest unknown)
The collector **does** promote resource attributes to Prometheus labels. Both host panels
return live data:

```
process_cpu_utilization_ratio{service_name="checkout", deployment_environment="lab", job="checkout"}  = 0.005
process_memory_usage_bytes{service_name="checkout", state="rss"}                                       = 69537792
```

### 4. Offline `--no-build --pull never` startup + real OTLP→Prometheus translation — **PASS**
`./lab start` brought the full stack up from local images with no registry contact, and
`./lab ready` confirmed the `lab_readiness` metric crossed the **real** collector into
Prometheus. Round 1's reproduction of the naming/label translation was accurate.

### 5. The timed nine-minute gate — **PASS**
Clean `./lab reset` → `validate-slice`:

```
Total validation elapsed: 36s      (budget 540s)
Recovery elapsed:         21s
PASS: Docker vertical slice completed within nine minutes
```

**36 s against a 540 s budget — 6.7% of the allowance**, after images are cached.

---

## Round 2 — all dashboard panels evaluated live

All 6 query-backed panels run against live Prometheus after incident traffic (the 7th panel,
"Question", is a static text panel):

| panel | result |
|---|---|
| HTTP 200 responses | **100** % |
| Business failure rate | **24.75** % |
| Checkout CPU | 0.5 % |
| Checkout memory | 80.4 MB |
| Business outcome over time | 2 series (success, payment_rejected) |
| Failures by segment | 1 series (discounted CAD) |

No panel is empty. The lab's central teaching contrast renders exactly as designed: **HTTP
says 100% healthy while the business metric says ~25% broken.**

---

## Round 1 — application-level findings (unchanged, all still PASS)

Confirmed again on real Docker in round 2.

- **Dependencies:** all 9 pinned packages in `docker/requirements.txt` install cleanly; the
  `python.Dockerfile` pip layer builds (image `observability-lab-python:0.1`, 301 MB).
- **Unit tests:** all **8** pass in-container (`test_domain`, `test_profiles`, `test_structure`).
- **Incident behaviour:** 100 requests → 100 × HTTP 200, 75 success / 25 `payment_rejected`,
  **all 25 failures in discounted-CAD**. The `Decimal` HALF_UP vs HALF_EVEN mismatch behaves
  exactly as designed.
- **OTLP→Prometheus naming:** `checkout.completed` → `checkout_completed_total`,
  `checkout.http.responses` → `checkout_http_responses_total`, bounded labels intact.
- **Hot reload / broken-paste gate / recovery:** appending invalid Python breaks `py_compile`
  and downs the worker; `./lab recover metrics` restores green in **21 s**.

---

## Issues found — status

| # | Issue | Severity | Status |
|---|---|---|---|
| 1 | `deltas()` undercounted grouped counters; `./lab check metrics` and `./lab recover metrics` both failed on correct behaviour | **Lab-blocking** | **FIXED & verified** |
| 2 | `validate-slice` leaves the working tree holding the **completed solution** | **Facilitator trap** | **OPEN** — see below |
| 3 | `pytest` not pinned; `tests/` has no `__init__.py`, so `unittest discover` fails | Minor | **OPEN** — workaround documented |
| 4 | `validate_slice.sh` never runs `./lab stop` | Cosmetic | **OPEN** |
| 5 | `validate_slice.sh` memory line is a single end-of-run snapshot | Cosmetic | **OPEN** — covered by sampling above |

### 2. `validate-slice` leaves the solution in the working tree — **read this before facilitating**
`scripts/validate_slice.sh` copies the **starter** checkpoint in, breaks it, then calls
`./lab recover metrics`, which copies in `checkpoints/1-metrics-complete/checkout.py`. It never
restores the starter afterwards. Confirmed after the passing run:

```
checkout/app/checkout.py  ->  MATCHES checkpoints/1-metrics-complete
                              (contains the `checkout_completed.add(...)` participants
                               are supposed to write themselves, at line 47)
```

**A facilitator who validates the lab and then hands out that working tree gives participants
the finished answer.** Always run `./lab reset` after `./lab validate-slice` and before a
session. Consider appending `./lab reset` to the end of `validate_slice.sh`, or having it print
a loud reminder.

### 3. Test invocation — not fixed, worked around
`pytest` is not in `docker/requirements.txt`, so `pytest tests` fails inside the lab image; the
tests are stdlib `unittest`. `tests/` also has no `__init__.py`, so
`python -m unittest discover -s tests -t .` fails with *"Start directory is not importable"*.
Round 1's report of "8 tests pass under pytest" reflects a native venv with pytest installed,
which the lab image does not have.

The invocation that works in-container, and which produced the 8/8 result above:

```bash
docker compose run --rm --no-deps -w /workspace tools \
  sh -c 'cd tests && python -m unittest test_domain test_profiles test_structure'
```

Consider adding `tests/__init__.py` or a `./lab test` subcommand so facilitators have one
documented command. **I did not change this** — it needs a decision about whether to pin pytest.

### 4 & 5. `validate_slice.sh` cosmetics — not fixed
The gate leaves the stack running (fine for a facilitator, worth a note in the guide), and its
peak-memory line is a single `docker stats --no-stream` snapshot that cannot observe a startup
spike. The 3-second sampling in residual item 1 covers the latter; the real peak is low either
way.

### Environment note
The Docker Desktop VM was allocated **7.75 GiB**, marginally under the lab's nominal 8 GB
minimum, on a 24 GB host. It made no difference — the stack peaks at 0.69 GiB — so the 8 GB
figure in the docs is very conservative and the lab would likely run on a 4 GB VM allocation.

---

## Recommendation

**Proceed with the tracing and logging checkpoints.** The metrics slice is now validated on the
real Docker stack, not a shim, and the one bug that would have derailed a live session is fixed.

Two things to carry into the next checkpoints, both consequences of the bug above:

- **Reuse the corrected `deltas()` baseline logic** in any `check_traces.py` / `check_logs.py`.
  The same mid-window series-birth trap applies to every grouped counter read-back.
- **Validate on real containers, not a native shim.** The application logic was fully correct
  in round 1; the defect lived entirely in the interaction with the real telemetry pipeline.
- **Decide on the four OPEN issues above**, especially #2 — `validate-slice` leaving the solved
  `checkout.py` in the working tree will burn a real session if a facilitator forgets `./lab reset`.

### Reproducing the gate

```bash
cd observability-lab-metrics-prototype
./lab setup            # pull otel-lgtm:0.29.0 + build the python image (needs registry access)
./lab validate-slice   # report written to .lab-state/validation-report.txt
./lab reset            # REQUIRED: restores the starter checkpoint (see OPEN issue 2)
```

Round 2 timings on the machine above: `./lab setup` ~2 min cold (3.1 GB otel-lgtm pull +
301 MB image build); `./lab validate-slice` 36 s thereafter.
