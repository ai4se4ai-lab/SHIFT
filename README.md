# SHIFT: Beyond Human-Centric Change Impact Analysis

SHIFT is an outcome-relative edit triage for agent-generated patches. For every edit of a
candidate patch it decides, by counterfactual execution against explicit goal and
preservation test obligations, whether the edit is **N**ecessary, **J**ointly needed,
**C**oupled, **U**nneeded, or **H**armful (via a dependency-selected preservation envelope).

The accompanying manuscript (JSS) is `docs/JSS/v1/main.tex` with `docs/JSS/v1/references.bib`; the v1 revision audit is in `docs/ledgers/v1-revision-report.md`.

## Repository layout

| Path | Content |
|---|---|
| `src/shift/patch/` | Unit decomposition of unified diffs, requires relation, syntax pre-check |
| `src/shift/counterfactual/` | Leave-one-out, dependency-aware ddmin, closure-aware reduction, labels |
| `src/shift/oracle/` | Execution oracle on official SWE-bench environments (Docker) |
| `src/shift/envelope/` | Import-based envelope test selection; controlled injections (RQ3) |
| `src/shift/graph/`, `src/shift/footprint/` | Module import graphs; edit and exploration footprints (RQ1) |
| `src/shift/hypotheses/` | LLM-judge prompts and answer parsing (RQ2) |
| `src/shift/data/` | SWE-bench Verified and public agent-submission loaders |
| `src/shift/pipeline.py` | End-to-end analysis of one patch |
| `experiments/` | Job builders and runners (`run_shift.py`, `rq1_footprint.py`, …) |
| `analysis/` | Statistics and LaTeX generation (`rq1_stats.py`, `rq234.py`, `make_tex.py`) |
| `hpc/` | Alliance (Rorqual/Narval) Slurm jobs, fleet controller, Ollama client |
| `configs/study.yaml` | Frozen study configuration (panel, models, seeds) |
| `docs/protocol/` | Research brief, locked evaluation protocol with amendments, project state |
| `tests/` | Unit and property-based tests (`pytest`) |
| `results/raw`, `results/processed` | Immutable per-patch records; derived tables |

## Reproduction

```bash
python3 -m venv .venv && .venv/bin/pip install -e . pandas pyarrow scipy statsmodels unidiff pyyaml pytest swebench==4.0.4 defusedxml
.venv/bin/python -m pytest -q                                   # 121 tests
# data
curl -L -o data/external/swebench_verified.parquet https://huggingface.co/api/datasets/princeton-nlp/SWE-bench_Verified/parquet/default/test/0.parquet
.venv/bin/python -m shift.data.submissions                       # patches + reports (bash-only track)
.venv/bin/python -m shift.data.submissions --trajs --systems <panel systems>
# environments (arm64 or x86_64), validated with the reference patches
.venv/bin/python experiments/harness_local_mirror.py --dataset_name princeton-nlp/SWE-bench_Verified \
    --predictions_path gold --instance_ids $(cat ids.txt) --namespace none --cache_level instance --run_id goldval
# RQ1
.venv/bin/python experiments/rq1_footprint.py && (cd analysis && ../.venv/bin/python rq1_stats.py)
# RQ2-RQ4
.venv/bin/python experiments/build_jobs.py --out results/processed/validated
.venv/bin/python experiments/run_shift.py --jobs results/processed/validated/jobs/shift_jobs.jsonl --out results/raw/shift/main --ablations
.venv/bin/python experiments/build_injection_jobs.py
.venv/bin/python experiments/run_shift.py --jobs results/processed/jobs/injection_jobs.jsonl --out results/raw/shift/injection
# LLM judges on Slurm (see hpc/), then
.venv/bin/python analysis/llm_judges.py --tag full && .venv/bin/python analysis/rq234.py
(cd analysis && ../.venv/bin/python make_tex.py)                 # regenerates every number in the paper
```

## HPC

`bash hpc/scripts/ssh-session.sh connect all` opens MFA-authenticated ControlMaster sessions.
`hpc/scripts/fleet.py probe|deploy|submit|status|fetch` drives node-local Ollama jobs
(`hpc/slurm/llm_judge.sbatch`) that verify full GPU residency before prompting. Seeds are passed
with `:` separators (`sbatch --export` splits on commas). Job submissions and decisions are logged
in `hpc/fetched/jobs.jsonl`.
