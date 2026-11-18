# SHIFT — Project State

## 2026-11-17 (session 1)
Done
- Research contract (`research-brief.md`) and locked evaluation protocol (`evaluation-plan.md`).
- Project structure: `src/shift/{data,patch,graph,footprint,envelope,oracle,counterfactual,hypotheses}`, `experiments/`, `analysis/`, `hpc/`, `tests/`, `configs/study.yaml`.
- Data: SWE-bench Verified parquet; 55 mini-swe-agent (bash-only) systems' patches + reports from the public `swe-bench-submissions` bucket; panel trajectories.
- Oracle: official SWE-bench 4.0.4 environments built natively on linux/arm64; repositories cloned from local bare mirrors via `git daemon` on the Docker bridge (`experiments/harness_local_mirror.py`).
- SHIFT pipeline verified end-to-end on django__django-11099 (gold and GPT-4o patches).
- 39 unit tests passing (decomposition, requires relation, triage, ddmin 1-minimality vs exhaustive).

Exclusions so far
- 10 Django/SymPy instances are pinned to x86_64 by the harness (`USE_X86`) and cannot be built on arm64.

Running (background)
- Django gold validation (221 instances) → then SymPy (74) → then RQ1 footprint extraction (`experiments/local_chain.sh`).

Next
- HPC: probe clusters, deploy prompts, smoke-test LLM judges on fir/rorqual/narval, choose full allocation from measured throughput.
- Local: SHIFT execution over gold + resolved panel patches; injection study; cost ablations.
