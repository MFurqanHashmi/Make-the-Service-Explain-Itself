#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
cleanup(){
  cp checkpoints/0-starter/checkout.py checkout/app/checkout.py
  cp checkpoints/0-starter/validation.py payment/app/validation.py
  docker compose down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
./lab reset >/dev/null 2>&1 || true
mkdir -p .lab-state
REPORT=.lab-state/full-validation-report.txt
: > "$REPORT"
log(){ echo "$*" | tee -a "$REPORT"; }
start=$(date +%s)
log "Full validation started: $(date -Iseconds)"
log "Docker: $(docker --version)"
log "Compose: $(docker compose version)"
./lab start | tee -a "$REPORT"
./lab ready | tee -a "$REPORT"
./lab test | tee -a "$REPORT"
for signal in metrics traces logs; do
  log "Validating recovery and $signal evidence..."
  case "$signal" in metrics) file=checkout/app/checkout.py;; *) file=payment/app/validation.py;; esac
  printf '
this is invalid python !!!
' >> "$file"
  sleep 2
  ./lab recover "$signal" | tee -a "$REPORT"
done
elapsed=$(( $(date +%s)-start ))
log "Total validation elapsed: ${elapsed}s"
(( elapsed <= 540 )) || { log "FAIL: exceeded nine-minute gate"; exit 1; }
log "PASS: complete lab validated; cleanup will restore starter state and stop Docker"
