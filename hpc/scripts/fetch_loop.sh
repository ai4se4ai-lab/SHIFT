#!/usr/bin/env bash
# Periodic fetch of SHIFT HPC outputs (every 10 min, at most 8 h). Uses existing SSH sessions only.
cd "$(dirname "$0")/../.."
for i in $(seq 1 48); do
  timeout 300 .venv/bin/python hpc/scripts/fleet.py fetch --sites rorqual,narval > /dev/null 2>&1
  timeout 120 .venv/bin/python hpc/scripts/fleet.py status --sites rorqual,narval 2>/dev/null | grep -E "^[0-9]+ shift" > hpc/fetched/queue_snapshot.txt
  echo "$(date +%T) active=$(grep -cE 'PENDING|RUNNING' hpc/fetched/queue_snapshot.txt) lines=$(cat hpc/fetched/*/outputs/full/*.jsonl 2>/dev/null | wc -l)"
  sleep 600
done
