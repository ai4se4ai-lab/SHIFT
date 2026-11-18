#!/usr/bin/env bash
# Local background chain: SymPy gold validation after Django validation + SymPy mirror; then RQ1.
set -u
cd "$(dirname "$0")/.."
V=results/raw/gold_validation
until ! pgrep -f "harness_local_mirror.py.*ids_django" >/dev/null && ! pgrep -f "clone --bare -q https://github.com/sympy/sympy" >/dev/null; do sleep 30; done
echo "[$(date -u +%T)] starting sympy validation"
(cd $V && SHIFT_MIRRORED=django/django,sympy/sympy ../../../.venv/bin/python ../../../experiments/harness_local_mirror.py \
  --dataset_name princeton-nlp/SWE-bench_Verified --predictions_path gold --instance_ids $(cat ids_sympy.txt) \
  --namespace none --max_workers 16 --run_id goldval --cache_level instance --timeout 1800 > goldval_sympy.log 2>&1)
echo "[$(date -u +%T)] sympy validation done"
until ! pgrep -f "clone --bare" >/dev/null; do sleep 30; done
echo "[$(date -u +%T)] starting RQ1 footprint"
.venv/bin/python experiments/rq1_footprint.py --workers 8 > results/raw/rq1_footprint.log 2>&1
echo "[$(date -u +%T)] RQ1 done"
