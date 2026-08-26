#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
cleanup(){
  cp workshop/checkpoints/0-starter/checkout.py services/checkout/app/checkout.py
  cp workshop/checkpoints/0-starter/validation.py services/payment/app/validation.py
  docker compose --progress quiet -f "$ROOT/workshop/compose.yaml" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
./lab reset >/dev/null 2>&1 || true
mkdir -p .lab-state
REPORT=.lab-state/full-validation-report.txt
: > "$REPORT"
log(){ echo "$*" | tee -a "$REPORT"; }

# The telemetry backends are not all queryable at the same moment after a cold
# start, and Tempo is consistently last. './lab ready' is designed to be re-run,
# so the gate retries rather than failing the whole validation on a cold race.
ready_with_retry(){
  local attempt
  for attempt in 1 2 3; do
    if ./lab ready 2>&1 | tee -a "$REPORT"; then return 0; fi
    log "readiness attempt ${attempt} did not pass; retrying"
    sleep 10
  done
  log "FAIL: telemetry pipeline never became ready"
  return 1
}

TIME_GATE_SECONDS=720
start=$(date +%s)
log "Full validation started: $(date -Iseconds)"
log "Docker: $(docker --version)"
log "Compose: $(docker compose version)"
./lab start | tee -a "$REPORT"
ready_with_retry
./lab test | tee -a "$REPORT"
for signal in metrics traces logs; do
  log "Validating recovery and $signal evidence..."
  case "$signal" in metrics) file=services/checkout/app/checkout.py;; *) file=services/payment/app/validation.py;; esac
  printf '
this is invalid python !!!
' >> "$file"
  sleep 2
  ./lab recover "$signal" | tee -a "$REPORT"
done
elapsed=$(( $(date +%s)-start ))
log "Total validation elapsed: ${elapsed}s"
(( elapsed <= TIME_GATE_SECONDS )) || { log "FAIL: exceeded ${TIME_GATE_SECONDS}s gate"; exit 1; }
log "PASS: complete lab validated; cleanup will restore starter state and stop Docker"
