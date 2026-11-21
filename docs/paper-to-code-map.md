# SHIFT: paper-to-code traceability map

This guide maps each part of the manuscript to the code that implements it, the experiment that produced its data, and the file that holds each reported number. Reviewers can use it to check the paper against the repository section by section.

All paths are relative to the repository root. Line numbers refer to the `dev` branch at the time of writing.

---

## 0. Setup and quick checks

```bash
python3 -m venv .venv
.venv/bin/pip install -e . pandas pyarrow scipy statsmodels unidiff pyyaml pytest swebench==4.0.4 defusedxml pyflakes
.venv/bin/python -m pytest -q          # expected: 137 passed
```

**Checks that need no Docker or GPU.** Every analysis script in sections 4–8 reads only committed files:
- the per-patch records in `results/raw/shift/main/records/`;
- the injection records in `results/raw/shift/injection/`;
- the processed tables in `results/processed/`.

Re-running a script overwrites its processed outputs, and `git diff` then shows any change.

**Checks that need Docker.** These are the SWE-bench `linux/arm64` images, rebuilt with `experiments/harness_local_mirror.py`:
- re-executing patches with `experiments/run_shift.py`;
- base runs of the contracts (`compile_contracts.py --execute`);
- the TRIM-style executions (`trim_baseline.py --execute`);
- the exhaustive-search follow-up runs.

**Checks that need GPUs.** These are the LLM judge runs, done through Ollama.

### What is and is not committed

| Data | Committed? | Location |
|---|---|---|
| Per-patch execution records (1,676 main, 500 injection) | yes | `results/raw/shift/main/records/`, `results/raw/shift/injection/records/` |
| Reference-patch validation and the excluded-architecture list | yes | `results/raw/gold_validation/` |
| Contract base executions (295) | yes | `results/raw/revision/contracts_base/` |
| TRIM-style new executions | yes | `results/raw/revision/trim/` |
| Exhaustive-audit follow-up executions (7 records) | yes | `results/raw/revision/exhaustive_followup/` |
| Additional (local) judge raw responses | yes | `results/raw/llm_local/full/` |
| **Main-panel judge raw responses (HPC)** | **no** (`hpc/fetched/` is in `.gitignore`) | only the parsed tables `results/processed/llm/full_*.csv` and `informed_*.csv` |
| SWE-bench dataset, agent submissions, repository clones, Docker images | no (external) | downloaded by `src/shift/data/` (see README) |

---

## 1. Approach (Section 3) → implementation

The evaluated pipeline is about 2,050 lines of Python (`wc -l src/shift/*.py src/shift/*/*.py`). The DSL frontend accounts for about 360 of them: `intent/dsl.py` (328) and `intent/benchmark.py` (32).

| Paper element | Code |
|---|---|
| Behavioral contract K = (T_g, T_p, η, ρ), Definition 1 | `Contract` in [src/shift/intent/dsl.py:74](../src/shift/intent/dsl.py#L74) |
| Oracle outcomes `invalid / unknown / goal-fail / pres-fail / valid`, Eq. (1) | `Verdict` and `InstanceOracle.verdict` in [src/shift/oracle/runner.py:39](../src/shift/oracle/runner.py#L39), [runner.py:162](../src/shift/oracle/runner.py#L162); the `unknown` outcome is recorded as `error` |
| **C1: \dsl{} grammar** (Listing 3) | tokenizer and `_Parser.document` in [dsl.py:135](../src/shift/intent/dsl.py#L135), [dsl.py:203](../src/shift/intent/dsl.py#L203) |
| C1 static rules (syntax, duplicate-block, unresolved-alias, goal-cardinality, empty-preservation, overlap, envelope-size, repeats) | `check_and_resolve` in [dsl.py:238](../src/shift/intent/dsl.py#L238); the rule ids are listed at [dsl.py:36](../src/shift/intent/dsl.py#L36) |
| C1 baseline validation | `validate_baseline` in [dsl.py:283](../src/shift/intent/dsl.py#L283) |
| C1 compilation and digest (Algorithm 1) | `compile_contract` and `Contract.digest` in [dsl.py:299](../src/shift/intent/dsl.py#L299), [dsl.py:85](../src/shift/intent/dsl.py#L85); `Catalog.digest` in [dsl.py:110](../src/shift/intent/dsl.py#L110) |
| Benchmark contract rendering (Listing 2 form) | `contract_text` and `catalog_for` in [src/shift/intent/benchmark.py](../src/shift/intent/benchmark.py); the running-example contract is in [results/processed/contracts/django__django-13297.intent](../results/processed/contracts/django__django-13297.intent) |
| **C2: edit units** (maximal runs within a hunk; one unit per created or deleted file) | `decompose` in [src/shift/patch/edits.py:102](../src/shift/patch/edits.py#L102) |
| C2 variant construction P ⊕ S (hunks located against the base) | `DecomposedPatch.apply` and `_locate_hunk` in [edits.py:72](../src/shift/patch/edits.py#L72), [edits.py:167](../src/shift/patch/edits.py#L167) |
| C2 requires relation R (imports and assignments matched per module; functions and classes across files) | `requires_relation` in [edits.py:248](../src/shift/patch/edits.py#L248), with `_defs`, `_uses` and `_defs_by_kind` at lines 207–246 |
| Closure cl_R, dep_R, withdraw_R (Eq. 2) | `closure` and `dependents` in [edits.py:282](../src/shift/patch/edits.py#L282), [edits.py:295](../src/shift/patch/edits.py#L295); `Session.close` and `dependents_of` in [src/shift/counterfactual/triage.py:39](../src/shift/counterfactual/triage.py#L39), [triage.py:71](../src/shift/counterfactual/triage.py#L71) |
| Parse precheck | `syntax_ok` in [edits.py:311](../src/shift/patch/edits.py#L311), applied in `Session.evaluate` at [triage.py:52](../src/shift/counterfactual/triage.py#L52) |
| Protected benchmark test files excluded from U | `InstanceOracle.protected_paths` in [runner.py:167](../src/shift/oracle/runner.py#L167); `overridden_units` in each record |
| **C3: Algorithm 2.** Preconditions, leave-one-out, closure-aware ddmin, final withdrawal pass | `triage` in [triage.py:177](../src/shift/counterfactual/triage.py#L177); `leave_one_out` (L85), `ddmin` (L95), `reduce_closed` (L127) |
| Operational roles N/J/C/U/X (Definition 2) | role assignment inside `triage` ([triage.py:177-212](../src/shift/counterfactual/triage.py#L177-L212)); the stored field is `labels` in each record |
| Outcome cache, scoped to one session | `Session` in [triage.py:27](../src/shift/counterfactual/triage.py#L27) |
| Exhaustive minimum over closed sets (RQ4 baseline, corrected) | `exhaustive_minimum` in [triage.py:148](../src/shift/counterfactual/triage.py#L148) |
| TRIM-style diff-only search (RQ4) | `trim_diff_only` in [triage.py:214](../src/shift/counterfactual/triage.py#L214) |
| **C4: envelope selection** (imports, filename, package and test-directory scores; top-k; min score 2) | `select_envelope` in [src/shift/envelope/select.py:32](../src/shift/envelope/select.py#L32) |
| C4 base-stable tests, reference filter, Reg(S) (Eq. 3), add-back (Algorithm 3) | `_envelope` and `_reference_runs` in [src/shift/pipeline.py:151](../src/shift/pipeline.py#L151), [pipeline.py:122](../src/shift/pipeline.py#L122); `_closure` (transitive add-back) at [pipeline.py:195](../src/shift/pipeline.py#L195) |
| Re-execution of recorded regressions in a fresh container | [experiments/confirm_regressions.py](../experiments/confirm_regressions.py) |
| End-to-end analysis of one patch, including ablations | `analyse_patch` and `_ablations` in [pipeline.py:22](../src/shift/pipeline.py#L22), [pipeline.py:88](../src/shift/pipeline.py#L88) |
| C5 review report and loop | **not implemented** (the paper marks it as proposed) |
| Propositions 1–2 (withdrawal minimality, omission witness) | property tests in [tests/test_edits_and_triage.py](../tests/test_edits_and_triage.py): `test_closed_one_minimality_property`, `test_reduce_closed_removes_unit_that_entered_only_via_closure`, `test_ddmin_is_one_minimal_and_matches_exhaustive_on_monotone_oracles` |

### Tests (137 collected)

- [tests/test_edits_and_triage.py](../tests/test_edits_and_triage.py) covers decomposition round-trip, every-subset-parses, the requires relation, roles (including the J case), closure, the precheck, ddmin 1-minimality, and the exhaustive minimum ordered by closed cardinality (the regression test for the RQ4 audit).
- [tests/test_intent.py](../tests/test_intent.py) covers the paper's example contract, render and parse round-trip, syntax-error positions, every static rule, all diagnostics reported together, baseline validation, benchmark-contract fidelity, transitive add-back closure, and the TRIM-style search.

### Implementation constants (Section 4.2)

| Constant | Value | Where |
|---|---|---|
| Container limits | 900 s timeout, 2 CPUs, 8 GB, `--network none` | [runner.py:63](../src/shift/oracle/runner.py#L63), [runner.py:93-94](../src/shift/oracle/runner.py#L93-L94) |
| Full-patch repeats | 2 | `triage(repeats_full=2)` |
| Envelope size k | 6 | `run_shift.py --k-env` (default 6) |
| Study configuration (panel, judge models, seeds) | frozen | [configs/study.yaml](../configs/study.yaml) |
| Protocol and amendments | — | [docs/protocol/evaluation-plan.md](protocol/evaluation-plan.md), [docs/protocol/project-state.md](protocol/project-state.md) |

---

## 2. Running example (Sections 2.6, 3.2–3.6; Table 2)

**Record:** [results/raw/shift/main/records/20260217_mini-v2.0.0_kimi-k2-5-high__django__django-13297.json](../results/raw/shift/main/records/20260217_mini-v2.0.0_kimi-k2-5-high__django__django-13297.json)

| Paper claim | Field in the record |
|---|---|
| Four units u1–u4 | `units` |
| R = {(u2,u1),(u4,u3)} | `requires` |
| Roles U,U,N,N | `labels` |
| Withdrawal outcomes (Table 2) | `loo` |
| Witness {u3,u4} | `minimal` |
| 8 oracle executions | `oracle_calls` and `runs` |
| No-closure ablation: {u4} fails the goal test and all 52 preservation tests | `ablations` |
| 75 envelope tests, no regression | `envelope` |

The contract is in [results/processed/contracts/django__django-13297.intent](../results/processed/contracts/django__django-13297.intent).

---

## 3. Executable contracts (Section 4.3)

**Script:** [experiments/compile_contracts.py](../experiments/compile_contracts.py). Run it without arguments for the static checks only, or with `--execute` to also run the base revision in Docker.

**Outputs:**
- [results/processed/revision/contracts.csv](../results/processed/revision/contracts.csv): one row per instance;
- [results/processed/revision/contracts_mutants.csv](../results/processed/revision/contracts_mutants.csv): seeded errors;
- `results/processed/contracts/*.intent`;
- `results/raw/revision/contracts_base/`.

| Number in the paper | How to check |
|---|---|
| 295 contracts; all match the triage's obligations | `contracts.csv`: `matches_oracle` is True in all 295 rows |
| Median 12 lines; mean 2.4 goal blocks (max 168); median 43 preservation tests | `lines.median()`, `n_goal.mean()`, `n_goal.max()`, `n_pres.median()` |
| 2,342 seeded errors, all rejected; 2,339 report the seeded rule | `contracts_mutants.csv`: row count, `rejected`, `expected_rule_reported` |
| 9 baseline mismatches (3.1%) | `contracts.csv`: `baseline != "ok"` (details in `baseline_detail`) |
| Median base time 1.4 s | `base_seconds.median()` |

---

## 4. RQ1: footprints (Section 4.4, Figure 1)

**Pipeline:**
1. [experiments/rq1_footprint.py](../experiments/rq1_footprint.py) computes the metrics with `edit_footprint` and `exploration_footprint` in [src/shift/footprint/metrics.py](../src/shift/footprint/metrics.py).
2. [analysis/rq1_stats.py](../analysis/rq1_stats.py) runs the statistics: Wilcoxon, Holm, rank-biserial, Spearman and GEE, using `analysis/stats.py`.

**Command:** `(cd analysis && ../.venv/bin/python rq1_stats.py)`

**Outputs:** [results/processed/rq1/](../results/processed/rq1/). The files are `rq1_summary.json`, `rq1_paired.csv`, `edit_footprint.csv`, `systems.csv`, `exploration.csv` and `rq1_exploration_summary.csv`.

| Number in the paper | Key in `rq1_summary.json` (unless noted) |
|---|---|
| 46 systems, 500 instances | `n_systems`, `n_instances` |
| 22,954 patches; 906 empty; 22,048 pairs | `edit_footprint.csv` / `rq1_paired.csv` row counts |
| Source files less 20 / more 6; blocks 29 / 1; churn 11 / 14; dispersion 22 / 0; auxiliary 0 / 32 | `<metric>.sig_less` / `.sig_greater` |
| Median r −0.31, −0.29, −0.45 | `<metric>.median_r` |
| H2 not supported, except auxiliary files (threshold 31/46) | `results/processed/revision/v2_checks.json` → `hypotheses.H2` |
| 0 of 14 mini-swe-agent 2.0 systems show the auxiliary effect | `v2_systems`, `v2_aux_sig_greater` |
| Spearman ρ = −0.83 and 0.94 | `spearman_resolve_vs_nonlocal_share_mean`, `spearman_resolve_vs_touches_gold_file` |
| GEE odds ratio 0.34 | `exp(gee.nonlocal_sh.coef)` = exp(−1.071) |
| Trajectory medians of 1–6 referenced files | `rq1_exploration_summary.csv` → `ref_median` |

---

## 5. RQ2: edit contribution (Section 4.5; Figure 2, Table 4)

**Pipeline:**
1. [analysis/shift_records.py](../analysis/shift_records.py) builds the unit and patch tables from the records.
2. [analysis/rq234.py](../analysis/rq234.py) computes the role shares, location proxies, judge metrics and bootstrap (`boot_metric`, L22).
3. [analysis/revision/revision_stats.py](../analysis/revision/revision_stats.py) adds the matched agent–reference comparison and the matched informed-judge comparison.
4. [analysis/revision/v2_checks.py](../analysis/revision/v2_checks.py) evaluates H3 and the structure of removable edits.

**Commands:**
```bash
.venv/bin/python analysis/rq234.py --llm-tag full
.venv/bin/python analysis/revision/revision_stats.py
.venv/bin/python analysis/revision/v2_checks.py
```

| Number in the paper | Source |
|---|---|
| 4,328 units; 20 X; 4,308 conclusive; 4 patches with X | `revision_stats.json` → `E_counts.units_total`, `units_X`, `X_patches` |
| Table 3 (panel and coverage) | `results/processed/rq234/units.csv` grouped by system; `patches.csv` |
| Agent N/J/C/U 62.0 / 0.3 / 1.9 / 35.9%; reference 64.1 / 0 / 2.0 / 33.9% | `rq234/summary.json` → `rq2.agent_share_*`, `rq2.gold_share_*` (each stored as estimate, lo, hi) |
| Source removable 1,093 / 3,206 (34.1%) vs 328 / 914 (35.9%) | `rq2.agent_source_unneeded_share`, `rq2.gold_source_unneeded_share`; `E_counts.agent_source_removable` |
| Pooled difference −1.8 [−8.6, 6.1]; matched −3.3 [−10.3, 5.4] | `revision_stats.json` → `A_agent_vs_reference.pooled_unmatched`, `.pooled_matched` |
| Per-system differences, Bonferroni intervals, Holm p (Figure 2) | `A_agent_vs_reference.per_system`; [rq2_agent_vs_reference_matched.csv](../results/processed/revision/rq2_agent_vs_reference_matched.csv) |
| Patches with ≥1 removable unit: 30.1% and 25.4% | `rq2.agent_patches_with_unneeded`, `rq2.gold_patches_with_unneeded` |
| 49 test and 139 auxiliary units, all removable | `rq2.agent_test_units`, `rq2.agent_aux_units` (each share = 1.0) |
| 797 removable units inside reference files; 60 retained units outside | `rq2.agent_source_unneeded_inside_gold_files`, `rq2.agent_source_needed_outside_gold_files` |
| Proxy rows of Table 4 | `rq2.proxies`; [rq2_proxies.csv](../results/processed/rq234/rq2_proxies.csv) |
| Judge rows of Table 4 (3-seed vote) | [results/processed/revision/local_judges.csv](../results/processed/revision/local_judges.csv), rows with `source=hpc, variant=vote` |
| Informed-judge ΔMCC | `revision_stats.json` → `B_informed_matched`; [rq2_informed_matched.csv](../results/processed/revision/rq2_informed_matched.csv) |
| H3 decision | `v2_checks.json` → `hypotheses.H3`, `H3_supported_all_location_proxies`, `H3_note` |
| Structure of removable units (15.8/4.5%, 28.8/18.8%, 69.4%, 31.0/40.1%, 53.2%; reference 14.0/8.0%, 8.5/32.3%, 23.8/24.7%) | `v2_checks.json` → `structure.*`; per-unit table [v2_unit_structure.csv](../results/processed/revision/v2_unit_structure.csv). The non-behavioral share is the sum of the comment/docstring, import and whitespace fractions. |

### LLM judges

**Prompts and parsing:** [src/shift/hypotheses/prompts.py](../src/shift/hypotheses/prompts.py). The inputs are `results/processed/llm_inputs/prompts.jsonl` and `prompts_informed.jsonl`.

**Main panel (HPC):**
- Run with [hpc/slurm/llm_judge.sbatch](../hpc/slurm/llm_judge.sbatch), [hpc/payload/llm_client.py](../hpc/payload/llm_client.py) and [hpc/scripts/fleet.py](../hpc/scripts/fleet.py).
- Parsed by `analysis/llm_judges.py --tag full` and `--tag informed`.
- Accounting (27 jobs, 11.6 GPU-hours) is in [results/processed/hpc_accounting.json](../results/processed/hpc_accounting.json).

**Additional judges (Devstral 24B, GPT-OSS 20B, Qwen3-Coder 30B; seed 11):**
1. Run with [experiments/run_local_judges.sh](../experiments/run_local_judges.sh).
2. Parse with `analysis/llm_judges.py --tag local --glob 'results/raw/llm_local/full/*.jsonl'`.
3. Score with [analysis/revision/local_judges.py](../analysis/revision/local_judges.py).

The rows to read in `local_judges.csv` are:
- `source=local`: the three additional judges;
- `source=hpc, variant=seed11`: Mistral Small's single-seed comparison point (F1 .50, MCC .46).

---

## 6. RQ3: preservation (Section 4.6, Figure 3)

**Injection jobs:**
- [experiments/build_injection_jobs.py](../experiments/build_injection_jobs.py) builds the jobs, using `make_injection` in [src/shift/envelope/inject.py:91](../src/shift/envelope/inject.py#L91).
- The job files are `results/processed/jobs/injection_*.jsonl`, and the SymPy sample is in `injection_sympy_sample.json`.
- The jobs run through `run_shift.py` into `results/raw/shift/injection/`.

**Analysis:** `rq3` in [analysis/rq234.py:147](../analysis/rq234.py#L147) and `part_c` in [revision_stats.py:155](../analysis/revision/revision_stats.py#L155).

| Number in the paper | Key |
|---|---|
| Envelope for 1,636 patches, empty for 38; median 104 tests | `rq234/summary.json` → `rq3.envelope_patches`, `envelope_empty`, `envelope_tests_median` |
| 19 of 1,346 agent patches (1.4%); 10 add-back; 9 persist in the witness | `rq3.agent_regression_n`, `rq3.agent_regression_rate`, `agent_harmful_unit_patches`, `agent_regression_tied_to_minimal`; `E_counts.agent_env_nonempty` |
| 2 reference-patch signals | `rq3.gold_regression_n` |
| 25 recorded regression records; direct and transitive add-back identical | `v2_checks.json` → `alignment.regression_records`, `alignment.addback_direct_vs_transitive_differences` |
| Official 78/249 (31.3%); with envelope 41.4%; gain 10.0; McNemar p < 1e-7 | `rq3.inj_semantic_*`; `revision_stats.json` → `C_injection.mcnemar_semantic` |
| Per-operator counts (Figure 3) | `C_injection.by_operator`; [rq3_injection_table.csv](../results/processed/rq234/rq3_injection_table.csv) |
| 0 of 249 neutral probes detected | `rq3.inj_neutral_*` |

---

## 7. RQ4: cost, interactions, reduction quality (Section 4.7; Figure 4, Table 5)

| Number in the paper | Source |
|---|---|
| Median 3 executions, p90 11; median 38.7 s; 79 precheck rejections | `rq234/summary.json` → `rq4.oracle_calls_median`, `oracle_calls_p90`, `wall_median_s`, `precheck_rejections_total` |
| Executions by unit bin, Spearman 0.97 (Figure 4) | `revision_stats.json` → `D_cost.bins`, `D_cost.spearman_units_calls`; [rq4_cost_distribution.csv](../results/processed/revision/rq4_cost_distribution.csv) |
| 877 one-unit and 376 two-unit patches | `E_counts.patches_1_unit`, `patches_2_units` |
| 82 C units in 43 patches; 9 J units in 7 patches | `E_counts.C_units`, `C_patches`, `J_units`, `J_patches` |
| Exhaustive audit: 1,603 records; 1,595 certified from recorded outcomes; 7 needing follow-up; 1 smaller valid set | [analysis/revision/exhaustive_audit.py](../analysis/revision/exhaustive_audit.py) → [exhaustive_audit.json](../results/processed/revision/exhaustive_audit.json) (`certified_min`, `not_certified_with_unobserved`, `smaller_valid_found`); per record in `exhaustive_audit.csv` |
| 31 follow-up configurations all fail; 7 witnesses pass again | [experiments/revision_exhaustive_followup.py](../experiments/revision_exhaustive_followup.py) → `results/raw/revision/exhaustive_followup/*.json` |
| Baseline defect: the original fails the regression case and 9 of 40 random cases | `test_exhaustive_minimum_orders_by_closed_cardinality` and `test_exhaustive_minimum_is_minimum_over_closed_sets_with_requires` in `tests/test_edits_and_triage.py` |
| 3,746 repeated configurations, 2 conflicting (django-16263 reference; sympy-13091 Kimi) | not produced by a committed script; reproduce with the snippet below |
| Table 5 rows: plain, precheck and closure ddmin | `v2_checks.json` → `ablation.all_*` (`runs_sum`, `invalid_sum`, `not_closed`, `same_as_shift`); per patch in [v2_ablation.csv](../results/processed/revision/v2_ablation.csv) |
| 363 patches with requires edges; LOO cost 3,246 | `ablation.n_with_requires`, `ablation.all_loo_runs_sum` |
| TRIM-style: 4,482 executions (823 for ≥17 units), 34 syntax-invalid, 32 not closed (3 undefined names), 752 same witness, 13 larger, 30 smaller | [experiments/trim_baseline.py](../experiments/trim_baseline.py) → [trim_baseline.csv](../results/processed/revision/trim_baseline.csv); see the snippet below |

### Reproduction snippets

```python
# Repeated-configuration agreement (RQ4 and threats): expected output "3746 2 [...]"
import json, glob, collections
rep, conf = 0, []
for f in glob.glob("results/raw/shift/main/records/*.json"):
    r = json.load(open(f)); obs = collections.defaultdict(list)
    for x in r.get("runs", []): obs[frozenset(x["cfg"])].append(x["outcome"])
    for v in (r.get("ablations") or {}).values():
        if isinstance(v, dict):
            for x in v.get("runs") or []:
                if isinstance(x, dict) and "cfg" in x: obs[frozenset(x["cfg"])].append(x["outcome"])
    for o in obs.values():
        if len(o) > 1:
            rep += 1
            if len(set(o)) > 1: conf.append(f.split("/")[-1])
print(rep, len(conf), conf)
```

```python
# Table 5, TRIM-style row: expected output 797 4482 823 34 32 3 752 13 30
import pandas as pd
t = pd.read_csv("results/processed/revision/trim_baseline.csv")
print(len(t), t.trim_runs.sum(), t[t.n_units >= 17].trim_runs.sum(), t.trim_invalid_runs.sum(),
      (~t.trim_closed).sum(), (t.trim_new_undefined_names.fillna(0) > 0).sum(), t.same_as_shift.sum(),
      (t.trim_size > t.shift_size).sum(), (t.trim_size < t.shift_size).sum())
```

---

## 8. Figures

[analysis/revision/figures.py](../analysis/revision/figures.py) generates the four pgfplots figures from the processed tables and writes them to [results/processed/revision/figures/](../results/processed/revision/figures/). The paper contains them verbatim between the `%<<GEN:...>>` and `%<<END:...>>` markers. To check a figure, regenerate it and compare it with the block in `main.tex`.

---

## 9. Known gaps and caveats for reviewers

- **Raw HPC judge responses are not in the repository.** Only the parsed per-unit predictions are committed (`results/processed/llm/full_*.csv`, `informed_*.csv`). Main-panel judge metrics can be recomputed from these files, but the responses cannot be re-parsed.
- **No committed script produces the repeated-configuration count** (3,746 / 2). The snippet in section 7 reproduces it from the records.
- **Hard-coded paths in the generators point at earlier manuscript versions.** `figures.py --inline` writes into `docs/JSS/v1/main.tex` and `analysis/make_tex.py` targets `docs/JSS/main.tex`. The v3 manuscript's numbers and figure blocks were transferred from the processed files listed above. The tables in sections 3–7 are the authoritative check.
- **`README.md` describes the v1 state** (121 tests, v1 manuscript path). The current test count is 137.
- **The manual coding sample** ([manual_coding_sample.csv](../results/processed/revision/manual_coding_sample.csv), 152 units, seed 2026) has been drawn but not yet coded. The paper reports no results from it.
- **C5 (review report and loop) and Studies A–C are not implemented.** The paper labels them as proposed or planned.
- **No immutable archival release** (DOI) has been made yet.
