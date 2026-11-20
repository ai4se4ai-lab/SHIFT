#!/usr/bin/env bash
# Repeat the TRIM-style replay until no record needs a new configuration (each pass
# executes the next missing configuration of every incomplete record).
set -euo pipefail
cd "$(dirname "$0")/.."
for i in $(seq 1 60); do
  out=$(PYTHONPATH=src .venv/bin/python experiments/trim_baseline.py --execute --workers "${1:-3}")
  echo "$out" | tail -1
  echo "$out" | grep -q "incomplete=0" && break
done
