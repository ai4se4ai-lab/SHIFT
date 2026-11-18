#!/usr/bin/env bash
# Post-processing after all runs: confirm regressions, parse LLM outputs, compute all RQ
# statistics, and regenerate every table/figure/number in the manuscript.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY experiments/confirm_regressions.py --run results/raw/shift/main --jobs results/processed/validated/jobs/shift_jobs.jsonl --workers 8
$PY experiments/confirm_regressions.py --run results/raw/shift/injection --jobs results/processed/jobs/injection_jobs.jsonl --workers 8
$PY analysis/llm_judges.py --tag full
$PY analysis/llm_judges.py --tag informed --prompts results/processed/llm_inputs/prompts_informed.jsonl
(cd analysis && ../$PY rq1_stats.py > /dev/null)
$PY analysis/rq234.py --run main --inj-run injection --llm-tag full > /dev/null
(cd analysis && ../$PY make_tex.py)
(cd docs/JSS && latexmk -pdf -interaction=nonstopmode main.tex > /dev/null 2>&1 || true; grep -c '^!' main.log || true)
