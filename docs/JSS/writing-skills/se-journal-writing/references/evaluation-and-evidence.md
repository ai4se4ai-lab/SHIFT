# Evaluation, evidence, and reproducibility

## Start with a traceability matrix

For every RQ, specify the construct, observable measure, population, comparison, analysis, and decision criterion. Separate descriptive questions from effectiveness claims and from mechanism tests.

| RQ role | Appropriate evidence | Frequent mistake |
|---|---|---|
| Characterization | Paired tasks, descriptive distributions, scoped associations | Inferring human or model cognition from patch size |
| Analysis effectiveness | Independent witnesses, exhaustive checks under valid assumptions, adjudication | Scoring an analyzer against its own labels as correctness ground truth |
| Preservation | Separate held-out tests and validated fault probes | Claiming no regressions because selected tests passed |
| Efficiency | Equal task, evidence, budget, and output requirements | Comparing complete attribution with minimization alone |
| DSL or workflow value | Equivalent policies in a crossover or randomized study | Calling compact syntax an empirically validated abstraction benefit |
| Generalization | New projects, languages, scaffolds, or later task sequences | Reusing one benchmark and claiming industrial applicability |

For a proposal, specify the experiment in future tense and state exactly which outcomes would weaken the approach. Do not create empty “results” tables with guessed numbers.

## Choose benchmarks by capability

A suitable benchmark needs more than popularity. Check access to base revisions, reproducible environments, task specifications, candidate patches, validation tests, and an independent outcome oracle. If the approach uses trajectories, verify that comparable trajectories are available. Test whether the benchmark contains the interactions the method claims to handle.

For agentic patch analysis, SWE-bench Verified provides useful repository-level issue tasks and archived candidate patches. Its official tests are an executable measurement, not a complete specification. If the analyzer uses those tests for search, those tests are no longer held out for evaluating the analyzer's generalization.

Defects4J can support Java replication and controlled real-bug studies. Its curated reference patches do not themselves provide an agent behavior study. Generate or obtain agent patches and adapt the dependency model before making cross-language claims.

A benchmark with successive specification changes can evaluate cumulative maintainability and extension success. Freeze the exact version because released problem counts and task definitions can change. Do not mix counts from a preprint version and a live leaderboard.

Report inclusion and exclusion flow. State planned and achieved sample size separately. An architecture restriction, failed environment build, missing trajectory, nonreproducing patch, and timeout are different exclusions and may cause different selection biases.

## Separate search evidence from final evaluation

Define which information the generator, analyzer, and evaluator can see. Include the reference patch and hidden test files in that inventory.

- Generator-visible feedback supports agent iteration.
- Analyzer-visible tests support minimization and attribution.
- Evaluation-only tests measure preservation beyond the search oracle.
- A human reference patch can calibrate a retrospective benchmark experiment but is unavailable in normal deployment.

A reference-only baseline may be useful as a privileged diagnostic. Label it accordingly. Do not present it as deployable or allow the method under evaluation privileged information that its competitors lack without explaining the comparison.

For a stronger test suite, report the independent suite's provenance, creation date, and who saw it. Tests generated after reading the candidate patch can be biased. Mutation probes should not be treated as independent human requirements.

## Handle uncertainty explicitly

Count every candidate, valid patch, edit, unresolved edit, timeout, missing prediction, and failed repeat. Compute percentages on stated denominators. Report conditional accuracy and coverage together. Distinguish an “ok patch analysis” status from “every edit has a conclusive outcome.”

Repeated full-patch runs do not establish deterministic counterfactuals. A subset may exercise a different flaky path. Record each relevant repetition, cache policy, timeout, retry policy, and whether unknown results block a certification.

A semantic mutation may be equivalent or unreachable. An injected operator is not automatically a confirmed fault. Use feasible killing tests or manual witnesses before reporting false negatives for “real faults.” Conversely, a supposedly neutral rewrite may change source locations, tracing, logging, or evaluation order. State the observation model under which it is neutral.

A zero-event bootstrap can return [0,0] even when the population rate is uncertain. Do not interpret that interval as certainty. Use a suitable binomial or cluster-sensitive analysis and describe its independence assumptions.

## Audit before quoting aggregate results

Reconcile raw records, processed rows, summary JSON, and manuscript tables. At minimum check:

- Total edits equal conclusive labels plus unresolved labels.
- System subtotals equal aggregate totals.
- A percentage's numerator and denominator refer to the same eligible sample.
- Every claimed passing reduced patch has a recorded passing run.
- An “exhaustive minimum” cannot be larger than a known passing candidate in the same search universe.
- Metrics use the same positive class and do not silently omit unparsable predictions.
- Hardware and wall-time statistics identify what was timed.
- Patches revisited across models remain clustered by issue when estimating uncertainty.

If an invariant fails, investigate the implementation and provenance. For a writing-only task, do not quietly change experiment code or rerun expensive campaigns. Correct the manuscript claim and disclose the unresolved analysis. Never explain an inconsistency away with an unverified causal story.

## Select baselines and ablations fairly

Include the nearest current method, simple baselines, and the relevant classical alternative. Describe inputs, required artifacts, outputs, and budgets for each. Separate “agreement with our operational measurement” from “better correctness.”

For patch minimization, informative comparisons include unchanged patch, leave-one-out, dependency-free and dependency-aware delta debugging, structure-aware minimization, and a trajectory-aware method if logs exist. When outputs differ, compare common outputs first and measure the extra evidence separately.

An ablation should remove one mechanism while keeping the rest of the comparison meaningful. If it changes the set of admissible patches, report that change. Raw costs across different search spaces or output requirements do not isolate a speedup.

## Use statistics that fit the data

Identify nesting and pairing before choosing a test. Edits share a patch, and patches from different systems may share an issue. Report effect sizes and uncertainty, not only p-values. Correct a defined family of multiple tests. Distinguish advance hypotheses from post hoc patterns.

For a new experiment, predefine the primary outcome and choose a sample size using a meaningful effect and pilot variance or a precision target. Do not claim that an arbitrary sample is adequately powered. Include missing outcomes and failures in sensitivity analyses.

For a planned DSL study, a balanced crossover can compare natural language, an equivalent structured configuration, and the DSL. Use different tasks across conditions to limit learning effects. Measure policy mistakes, time, comprehension, and maintenance. Choose the primary endpoint and margin before looking at confirmatory outcomes.

## Discussion and threats

Discussion should integrate findings across RQs. Explain surprises and competing explanations. Give implications that follow from the evidence. A similar removable-edit rate for reference and agent patches limits any claim that the phenomenon is unique to agents. Fast analysis on tiny patches does not establish large-patch scalability. A modest mutation-detection gain can motivate stronger preservation checks without proving safety.

Write threats as threat, plausible direction of bias, mitigation, and remaining limit. Explain construct, internal, external, and conclusion validity in terms of this study, not generic textbook definitions.

## Reproducibility and artifact claims

Report model identifiers and dates, model digests where available, scaffold version, prompts, decoding settings, seeds, truncation, parsers, environment architecture, test commands, and timeout rules. Include protocol amendments and the rationale for exclusions.

Distinguish a local artifact, a public repository, and a deposited immutable archive. A repository URL in an old draft is not evidence that all artifacts are currently released. Do not invent an archival DOI, license, participant approval, completed manual validation, or author sign-off.
