#!/usr/bin/env bash
# Start the full injection run once no other SHIFT run is active (resume skips finished records).
cd "$(dirname "$0")/.."
sleep 60
while ps -eo cmd | grep -q "[r]un_shift.py --jobs"; do sleep 30; done
exec .venv/bin/python experiments/run_shift.py --jobs results/processed/jobs/injection_jobs.jsonl \
  --out results/raw/shift/injection --workers 15 > results/raw/shift_injection.log 2>&1
