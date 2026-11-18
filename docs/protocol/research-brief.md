# SHIFT — Research Brief (research contract, v1, 2026-11-17)

## Venue and study type
- Target: Journal of Systems and Software (JSS), Elsevier `cas-sc` class. Manuscript: `docs/JSS/main.tex` + `docs/JSS/references.bib` (single-file source, figures inline in TikZ/pgfplots).
- Study type: mixed — (i) large-scale empirical study over public artifacts, (ii) design-science technique (SHIFT) with formal properties, (iii) controlled experiments.

## One-sentence problem
Change-centric impact analysis and patch review judge a modification by *where* it lands relative to an expected fault location (patch size, locality, overlap with a reference fix), but agent-generated patches need an *outcome-relative* judgment of which individual edits are required for, neutral to, or harmful to the intended behavior.

## Concrete failure scenario (running example, to be instantiated on a real SWE-bench Verified Django issue)
An agent resolves an issue by editing the module named in the issue *and* a helper in a different module; it also leaves a reproduction script and touches an unrelated function. Location-based review either flags the necessary nonlocal helper edit as suspicious (false alarm) or accepts the whole patch because the official tests pass (missed unnecessary/harmful edit).

## Insight
Judge each edit counterfactually against explicit goal and preservation obligations, not against its syntactic distance from a presumed fault location. Exploration footprint, edit footprint, and behavioral relevance are separate quantities.

## Contributions (max three)
1. **Empirical (new):** footprint study of 13+ LLMs under one fixed scaffold (mini-swe-agent, bash-only track) vs human reference patches on all 500 SWE-bench Verified issues. Reused: public patches/trajectories/reports. Not claimed: statements about human *exploration* (no human trajectories exist).
2. **Technique (new):** SHIFT — intent specification compiled to goal/preservation obligations; edit decomposition with a def-use requires-relation; dependency-aware counterfactual minimization producing inclusion-1-minimal sufficient edit sets and edit labels {Necessary, Jointly-needed, Unneeded, Harmful, Unresolved}; dependency-selected preservation envelope with regression attribution; formal soundness of labels relative to a deterministic oracle and 1-minimality of the result. Reused: ddmin (Zeller & Hildebrandt 2002), SWE-bench execution environments and log parsers, regression-test-selection idea. Not claimed: verification of full program correctness; causal claims beyond the oracle.
3. **Evaluation (new):** edit-level necessity of resolved agent patches (Django + SymPy, 306 of 500 Verified issues), accuracy of change-centric proxies and five open-weight LLM judges against counterfactual evidence, a controlled injection study for preservation, and an oracle-cost study.

## Research questions
- **RQ1 Footprint.** How do agents' exploration and edit footprints differ from the human reference patches on the same issues, and how are footprint properties associated with resolution?
- **RQ2 Necessity.** What fraction of edits in resolved agent patches is counterfactually needed, and how well do location-, dependency- and LLM-judgment-based proxies recover edit necessity?
- **RQ3 Preservation.** Does a dependency-selected preservation envelope expose behavior changes that the benchmark regression tests (PASS_TO_PASS) miss, and does SHIFT attribute them to the responsible edits?
- **RQ4 Cost.** What does counterfactual triage cost, and how much do dependency-aware grouping and syntactic pre-checks reduce oracle executions relative to alternatives?

## Assumptions / scope
- Oracle-relative semantics: "needed" means needed for the specified obligations (F2P ∧ P2P [∧ envelope]) under the instance's execution environment. Tests are incomplete oracles; this is a stated construct limitation.
- In deployment the goal obligation comes from an issue-reproduction test; in our evaluation we use benchmark FAIL_TO_PASS tests as the intent oracle (post-hoc analysis setting, not agent-time).
- Execution environments: official SWE-bench 4.0.4 specs built natively for linux/arm64; instances whose gold patch does not validate are excluded and counted.

## Baselines / comparators
- RQ1: human reference (gold) patch for the same instance.
- RQ2 proxies: gold-file overlap; issue-mentioned location; import-graph proximity to gold files (k ≤ 1); "all edits needed" trivial baseline; LLM judges (5 open-weight models via Ollama, HPC GPUs).
- RQ3: official PASS_TO_PASS only vs SHIFT envelope.
- RQ4: leave-one-out only; plain ddmin without requires-closure or syntax pre-check; exhaustive subset search (small patches only).

## Resources
Local: NVIDIA GB10 (aarch64, 20 cores, 121 GB), Docker. HPC: Alliance Fir/Rorqual (H100), Narval (A100), account def-mbabaei_gpu / def-mbabaei_cpu, ~12 h authenticated session.

## Deliverables
Code (`src/shift`, `baselines`, `experiments`, `analysis`, `hpc`), tests, raw/processed results, protocol, ledgers, and `docs/JSS/main.tex` + `references.bib`.
