# SHIFT v1 — Review, revision, and evidence report (2026-11-18)

Scope: `docs/JSS/v1/main.tex` and `references.bib`. The reviews are role-played by one AI assistant (Claude Code). They are **not independent peer review**.
Baseline for comparison: `main.tex` as received at the start of this session. A copy is kept outside the repository; `git diff` shows the changes.

---

## A. Artifacts produced

| Artifact | Path | Purpose |
|---|---|---|
| Revised manuscript | `docs/JSS/v1/main.tex`, `docs/JSS/v1/references.bib` | Two-file deliverable; builds with 0 errors and 0 undefined references; 26 pages |
| Exhaustive-search audit | `analysis/revision/exhaustive_audit.py` → `results/processed/revision/exhaustive_audit.{csv,json}` | Re-derives minimum-cardinality status from recorded outcomes; no new execution |
| Follow-up execution | `experiments/revision_exhaustive_followup.py` → `results/raw/revision/exhaustive_followup/*.json`, `results/raw/revision/exhaustive_followup.log` | 31 unobserved smaller closed configurations plus 7 witness re-checks |
| Revision statistics | `analysis/revision/revision_stats.py` → `results/processed/revision/revision_stats.json`, `rq2_agent_vs_reference_matched.csv`, `rq2_source_removable_by_system.csv`, `rq2_informed_matched.csv`, `rq4_cost_distribution.csv` | Matched agent–reference comparison, matched informed-judge comparison, McNemar test, cost distribution, count re-checks |
| Figures (pgfplots, inlined) | `analysis/revision/figures.py --inline` → `results/processed/revision/figures/*.tex` and the `%<<GEN:…>>` blocks in `main.tex` | Figs. 2–5 are generated from the processed tables |
| Code fix | `src/shift/counterfactual/triage.py` (`exhaustive_minimum`) | Enumerates closed configurations by their own size |
| Regression tests | `tests/test_edits_and_triage.py` (+41 tests; 121 total pass) | The regression case and 9 of 40 property cases fail on the old code |

Raw records in `results/raw/shift/main/records/` were not modified. The new evidence is written to separate directories.

Run order: `exhaustive_audit.py` → `revision_exhaustive_followup.py` (needs Docker images) → `revision_stats.py` → `figures.py --inline`.

---

## B. Independent reviewer reports (round 1, on the received manuscript)

Scores use a 1–5 scale (5 = meets the bar of TSE/TOSEM/EMSE).

### Reviewer A — Novelty and significance
**Strengths.** The paper reframes edit relevance as contract-relative evidence rather than location. It is unusually honest about overlap with TRIM. The contextual roles (N/J/C/U) separate a withdrawal outcome from witness membership, which is a real conceptual refinement over leave-one-out and plain ddmin.

**Weaknesses.**
1. Contribution 3 (the DSL) is a specification without an implementation or evaluation, yet it is listed as a contribution and has its own RQ (RQ5) with no results.
2. The positioning relies on prose only. No side-by-side comparison of problem, inputs, outputs, and guarantees is given.
3. The chess/Go analogy in the introduction is decorative and invites an "AlphaGo for patches" reading that the paper does not support.
4. The TRIM comparison does not use TRIM's own reported results, such as cost relative to DD or its claim that agent code is larger.

**Scores.** Novelty 3, Problem/motivation 3, Positioning 2, Significance 3. **Recommendation: major revision.**

### Reviewer B — Technical soundness and method
**Strengths.** The definitions are precise. The closure and withdrawal properties are proved. Proposition scope is stated carefully. Implementation boundaries (verdict conflation, direct-only add-back) are disclosed.

**Weaknesses.**
1. **(Critical)** RQ4 reports 4 records in which the "exhaustive minimum" exceeds a known passing witness, with cause "not established". This leaves the only external check of reduction quality unresolved.
2. **(Major)** RQ1 states "agent patches are generally concentrated". The protocol's own decision rule requires ≥31/46 systems; the maximum observed is 29/46. The claim contradicts the prespecified criterion.
3. **(Major)** The agent-vs-reference removability comparison relies on overlapping intervals of two separate estimates. There is no test of the difference, and agents resolve different instance subsets, so the comparison is confounded by instance composition.
4. The running-example listing misrepresents u3, which modifies an existing import, and omits the `elif` structure.
5. Algorithm 2 has no complexity statement, and the ddmin step does not explain why a post-pass is needed (closure breaks 1-minimality).

**Scores.** Rigor 3, Formal correctness 4, Evaluation design 3, Validity 3. **Recommendation: major revision.**

### Reviewer C — Evidence, reproducibility, presentation
**Strengths.** Denominators and exclusions are reported. Clustered bootstrap is used. Artifacts are traceable to processed tables.

**Weaknesses.**
1. **(Major)** The manuscript contains no data figures. All evidence is in tables or prose; distributions (per-system effects, cost growth) are invisible.
2. **(Major)** The informed-judge claim ("raises the best informed MCC to 0.45") compares a one-seed variant with a three-seed aggregate. On matched data, Mistral's MCC *decreases* (0.463 → 0.454).
3. The RQ1 sample (22,954 patches) silently drops 906 empty patches from the paired tests (22,048 pairs).
4. Flakiness is asserted as a threat but not quantified, although the records contain repeated configurations.
5. Access dates (2026-11-19) are later than the revision date. The data-availability text misses the existing git remote.

**Scores.** Statistics 3, Figures 1, Reproducibility 3, Presentation 3. **Recommendation: major revision.**

---

## C. Consolidated issue list and resolution record

| ID | Rev. | Sev. | Location | Issue | Change implemented | Evidence | Verification | Status |
|---|---|---|---|---|---|---|---|---|
| I1 | B | Critical | §4.6 RQ4 | 4 "exhaustive > witness" records unexplained | Diagnosed the bug: `exhaustive_minimum` enumerated generators by pre-closure size. Fixed the code and added tests. Re-derived the minimum from records; executed the 31 missing configurations plus 7 witness re-checks | `exhaustive_audit.json`; `exhaustive_followup/*.json`; pytest | All 4 records have requires edges and an observed-valid smaller witness. 1,602/1,603 witnesses have minimum cardinality; 1 genuine non-minimum (`sympy-19783`). Old code fails the regression case and 9 of 40 property cases | Resolved |
| I2 | B | Major | §4.3 RQ1, abstract, intro | Directional claim violates the ≥2/3 rule | Rewritten: no direction meets the rule; tendencies only; aux files meet it but are confounded by scaffold | `rq1_summary.json` (20/29/22 of 46) | Counts re-checked against `rq1_paired.csv` | Resolved |
| I3 | B | Major | §4.4 RQ2 | Agent–reference difference untested; instance confound | Pooled difference with joint instance bootstrap; per-system matched differences with Bonferroni intervals and Holm p-values; Fig. 3 | `revision_stats.json` A | −1.8 pp [−8.6, 6.1]; DeepSeek +11.6 (Holm p = .003) | Resolved (post-hoc, labelled) |
| I4 | C | Major | §4.4 RQ2 | Misleading informed-judge claim | Matched seed-11 comparison on units parsed in both variants, with bootstrap CI of ΔMCC | `rq2_informed_matched.csv` | Phi-4 +.07, Qwen +.15, Mistral −.01 (CI contains 0) | Resolved |
| I5 | C | Major | §4 | No data figures | Figs. 2–5 (RQ1 strip, RQ2 forest, RQ3 operator bars, RQ4 log box plot) generated by a script; Tables 5 and 6 replaced | `figures.py` | Rendered and inspected at 70 dpi; values match the CSVs | Resolved |
| I6 | A | Major | Intro, §4.1, §4.7 | Unevaluated DSL counted as a contribution and as RQ5 | Contributions reduced to three, with the DSL folded into C1 and marked proposed. RQ5 became "Planned evaluation" outside the RQ list | — | Text check: no remaining "RQ5" reference | Resolved |
| I7 | A | Major | §5 | No direct positioning | Table 6 compares families on question, inputs, outputs, and guarantee. TRIM's reported results are used in Discussion and Study B | Web check of arXiv:2607.18161 abstract | TRIM entries limited to what its abstract states | Resolved |
| I8 | C | Minor | §4.1 | 906 empty patches undisclosed | Stated (22,048 pairs) | `edit_footprint.csv` | 22,954 − 906 = 22,048 | Resolved |
| I9 | C | Major | §4.6, threats | Flakiness unquantified | 2 of 3,746 repeated configurations disagree; affected records named | Records' `runs` | Script count | Resolved |
| I10 | B | Minor | §2.6 Listing 1 | Listing not faithful to the patch | Diff-style listing matching the recorded patch | `shift_jobs.jsonl` | Manual comparison | Resolved |
| I11 | B | Minor | §3.4 | No complexity statement; reason for the post-pass unstated | Added both | — | Text check | Resolved |
| I12 | B | Minor | §3.3 | C2 example lacks evidence of why closure matters | Added the recorded no-closure ablation run `{u4}`: goal + 52 preservation failures; A7 history | Record `kimi…13297` | Record inspected | Resolved |
| I13 | A | Minor | Intro | Decorative chess/Go analogy | Removed; the references are no longer cited (bib entries kept, unused) | — | BibTeX: 37 entries used | Resolved |
| I14 | C | Minor | Header, bib | Future access dates; missing issue number | Header date corrected; Baltes et al. number = 2 added. The bib `note` access dates (2026-11-19) were **not** changed, because the underlying access was not re-performed for those URLs | Web check | — | Partially resolved — author to confirm access dates |
| I15 | C | Minor | Data availability | Remote not mentioned; revision scripts not listed | Remote URL and revision scripts listed; public availability explicitly unverified | `git remote -v` | — | Resolved |
| I16 | C | Minor | AI declaration | Did not cover this revision | Added a statement on Claude Code use | — | — | Resolved |
| I17 | A | Major | Overall | No implementation or evaluation of the DSL and review gate | Not addressable without new studies; Studies A–C specified | — | — | **Open (blocker for the DSL claims only)** |
| I18 | B | Major | RQ4 | No equal-budget comparison with TRIM | Not executable here (TRIM artifact, budgets); Study B specified | — | — | **Open** |
| I19 | C | Minor | Data availability | No archival DOI | Cannot be created by the assistant | — | — | **Open (author)** |
| I20 | B | Minor | RQ3 | Neutral zero-rate overstated | Added 95% upper bound 1.2% (rule of three) | — | Arithmetic | Resolved |

Note: the bib file still contains `campbell2002deepblue` and `silver2016alphago`. They are no longer cited, so BibTeX omits them from the reference list. Remove them if a clean bib is preferred.

---

## D. Statistical and visualization artifacts — provenance

| Manuscript item | Source data | Script | Method |
|---|---|---|---|
| Fig. 2 (RQ1) | `results/processed/rq1/rq1_paired.csv` | `figures.py` | Per-system matched-pairs rank-biserial *r*; Holm within metric (existing analysis) |
| Fig. 3, RQ2 difference text | `results/processed/rq234/units.csv` | `revision_stats.py` (A) | Ratio-of-sums difference; joint instance-cluster bootstrap, 10,000 resamples, seed 2026; Bonferroni (k = 8) intervals; Holm on bootstrap p |
| RQ2 informed comparison | `results/processed/llm/{full,informed}_edits.csv`, `units.csv` | `revision_stats.py` (B) | Seed 11, units parsed in both; paired instance bootstrap (2,000) of ΔMCC |
| Fig. 4, McNemar | `results/processed/rq234/summary.json` (rq3) | `revision_stats.py` (C) | Exact binomial McNemar on discordant pairs (25 vs 0) |
| Fig. 5 | `results/processed/rq234/patches.csv` | `revision_stats.py` (D) | Quantiles by unit bin; Spearman ρ |
| RQ4 minimality | `results/raw/shift/main/records/*.json`; follow-up JSON | `exhaustive_audit.py`, `revision_exhaustive_followup.py` | Enumeration of closed sets; observed or static-precheck outcomes; targeted execution |
| Count re-checks (E) | `patches.csv`, `units.csv` | `revision_stats.py` (E) | Direct counts |

---

## E. Scientific consistency audit (revised manuscript)

| Check | Result |
|---|---|
| Definitions ↔ algorithms | Def. 2 roles = `AssignOperationalRoles` = `triage.py` label rule (X first, then N/C/J/U). Eq. 2 = `dependents_of` + `leave_one_out`. ✔ |
| Algorithms ↔ implementation | Alg. 2 = `triage()` (ddmin over closure + `reduce_closed`). Alg. 3 vs `_envelope`: direct-only add-back disclosed. Alg. 1 not implemented, disclosed. ✔ |
| RQs ↔ experiments | RQ1–RQ4 each map to a figure or table and an answer paragraph. Planned studies are separated from RQs. ✔ |
| Reported values ↔ data | All numbers checked against `summary.json`, `rq1_summary.json`, and `revision_stats.json`. Two corrections made during the check: the patch-share definition ("unit of any kind") and the count of systems below the reference (four). ✔ |
| Figures ↔ values | Generated directly from the CSV/JSON tables; captions state denominators. ✔ |
| Running example ↔ record | Units, R, LOO outcomes, witness, 8 calls, 75 envelope tests, and 52 preservation tests match `…kimi-k2-5-high__django__django-13297.json`. Listing matches the patch. ✔ |
| Discussion ↔ evidence | Mechanism claims are labelled as explanations. The "797 of 1,093 removable source units inside reference files" figure is from data; "defensive/symmetric/duplicate" is an interpretation, not a coded measurement. ⚠ Could be strengthened by a manual coding sample |
| Abstract/conclusion ↔ results | Every number in the abstract appears in §4 with the same value. No claim of agent-specific excess or DSL benefit. ✔ |
| Citations ↔ statements | TRIM, SlopCodeBench, and Baltes et al. re-checked online (arXiv/Chalmers records). Classic references were not re-verified in this session (see `citation-verification.md`). ⚠ |

---

## F. Round-2 review and final readiness assessment

Round-2 reviews were carried out on the revised text by the same three roles. They re-check items I1–I20 above. Items are marked resolved only where a code, data, or text change was made **and** verified.

| Criterion | Before | After | Remaining risk |
|---|---|---|---|
| 1 Novelty and contribution | 3 | 3.5 | TRIM overlap remains; the distinct value (contract, roles, envelope) is unproven without Study B |
| 2 Problem and motivation | 3 | 4 | — |
| 3 Background and running example | 4 | 4.5 | — |
| 4 Technical rigor and approach | 4 | 4 | Requires relation is approximate; DSL unimplemented |
| 5 Evaluation design | 3 | 3.5 | Two projects, one scaffold family, resolved-only patches |
| 6 Statistical validity | 3 | 4 | Agent–reference comparison is post hoc |
| 7 Figures and tables | 1 | 4 | — |
| 8 Results interpretation and discussion | 3 | 4 | Mechanism explanation of removable edits is not coded |
| 9 Related work and positioning | 2 | 4 | — |
| 10 Reproducibility | 3 | 3.5 | No archival DOI; Docker images needed for re-execution |
| 11 Threats and honesty | 4 | 4.5 | — |
| 12 Presentation | 3 | 4 | 26 pages in the cas-sc single-column format |

**Overall (role-play): minor-to-major revision.** The empirical analysis part is close to submittable. The main acceptance risks are:
1. The DSL is presented as a design without implementation or user evidence (I17). Editors may ask for it to be removed or implemented.
2. There is no head-to-head comparison with TRIM (I18).
3. Generality is limited to two Python projects and one scaffold family.
4. The archival artifact is missing (I19).

**Distinguishing what was done:**
- *Verified corrections:* I1–I13, I15, I16, I20.
- *Unresolved, requiring new work:* I17, I18, I19, and the I14 access dates.
- *Proposed future improvements:* manual coding of a sample of removable edits (defensive, symmetric, duplicate, or other) to substantiate the discussion's mechanism claim; extending exhaustive certification beyond 8 units by sampling.
