---
name: se-journal-writing
description: Develop or substantially revise software engineering research manuscripts through evidence-based argument design, motivated formalization, reproducible evaluation, and repeated technical and editorial review. Use for research papers and study protocols, including journal submissions. Does not promise acceptance or invent missing experiments.
---

# Software engineering research writing and review

Develop a manuscript whose claims a skeptical software engineering researcher can trace to definitions, evidence, and appropriately scoped conclusions. Support the author's research direction while actively testing its assumptions. Treat venue prestige as a quality ambition, not a writing style or a guarantee of acceptance.

## Read selectively

- For a new study, weak motivation, or a major rewrite, read [argument and exposition](references/argument-and-exposition.md).
- For a technique, formal model, DSL, architecture diagram, or algorithms, also read [technical exposition](references/technical-exposition.md).
- For experiments, results, benchmarks, or missing implementation, read [evaluation and evidence](references/evaluation-and-evidence.md).
- Before delivering a substantial manuscript, perform the distinct passes in [review and revision](references/review-and-revision.md).
- When choosing journal exemplars or verifying literature, use [literature and journal exemplars](references/literature-and-exemplars.md).

Read the applicable resources before drafting their corresponding sections. Reuse inspected sources and existing project evidence instead of searching again without a reason.

## Establish the research state

Inspect the supplied manuscript, bibliography, repository instructions, implementation, study protocol, processed tables, and representative raw records. Preserve unrelated user edits. Record the requested output directory and file limits. Keep build products outside a directory that must contain only manuscript sources.

Determine whether this is a research proposal, protocol, implemented technique, completed empirical study, or a combination. A combined manuscript must mark which components are implemented, which results have actually been observed, and which experiments remain planned. A polished draft must not blur those categories.

Create a compact working ledger, in temporary files unless the author requests deliverable ledgers:

| Claim | Evidence or derivation | Scope | Status | Manuscript location |
|---|---|---|---|---|
| Main motivation | Primary study or observed case | Task, models, projects | Supported / hypothesis | Introduction |
| Technique property | Definitions and proof | Explicit assumptions | Established / conditional | Approach |
| Performance result | Raw records and analysis | Denominator, exclusions | Observed / unresolved | Evaluation |
| Intended extension | Design and evaluation plan | Unimplemented parts | Proposed | Approach and future study |

Use the ledger to constrain the abstract and contributions. When evidence contradicts a motivating hypothesis, narrow or replace the claim. Explain the scientifically useful question that remains.

## Develop the argument before polishing

Write a one-paragraph argument: a concrete stakeholder faces a consequential decision, existing methods leave a specific uncertainty, the proposed mechanism produces missing evidence, and a feasible evaluation can test whether that evidence helps. Name the nearest competing method and the residual distinction. If this cannot be stated precisely, improve the research argument before expanding the prose.

Review a small, relevant set of recent primary papers from the intended journal and neighboring venues. Read their actual introduction, technical sections, evaluation design, discussion, and limitations when accessible. Abstracts and search snippets cannot establish how full sections are written. Extract organizational decisions, never copy phrasing. Recheck recent nearest neighbors immediately before finalizing novelty claims.

Use a dependency order for drafting: evidence and research questions, definitions and example, approach, evaluation, related-work comparisons, introduction, abstract. This is a drafting aid, not a mandatory section order. Follow the author's requested presentation and venue requirements.

## Essential manuscript constraints

1. Motivate each definition with the decision it enables. Define symbols before using them. State the scope and assumptions of every guarantee.
2. Introduce a compact running example at the end of background when that structure is requested. Reuse the same identifiers, inputs, and outcomes in every approach component. Distinguish a simplified illustration from a measured repository case.
3. Start the approach with an overview when appropriate. Use an annotated diagram with component inputs, outputs, subcomponents, and feedback paths. Visually distinguish measured components from proposed extensions.
4. Explain each component through its purpose, input, operation, output, assumptions, and concrete example. Avoid repeatedly turning those words into mechanical paragraph headings.
5. Keep pseudocode readable. When the author requests 10--15 lines, enforce that range for numbered executable lines. Move long expressions to named, defined operations in nearby prose. Do not hide an entire method inside an undefined helper to satisfy the limit.
6. Map every research question to a construct, measurement, comparison, analysis, and answer criterion. Explain why the benchmark exercises that construct.
7. Describe high-level engineering details together in the implementation subsection. Keep file paths, job administration, and hardware inventories out of the conceptual approach unless they affect the method.
8. Separate test-relative sufficiency, patch correctness, maintainability, and human preference. Do not use a test-passing reduction as proof of any of the latter three.
9. Group related work by research problem or mechanism. End each group with a substantive comparison on shared assumptions, evidence, outputs, and limitations.
10. Use direct sentences and coherent paragraphs. Prefer a period to a semicolon when two assertions deserve separate explanation. Preserve necessary semicolons in code or notation. Do not replace them mechanically with awkward commas.

## Review, revise, validate

Perform separate argument, formal, empirical, literature, and reader reviews using the review resource. Apply the revisions, then repeat affected checks. Role-based self-review is not independent peer review. Do not claim independent review unless someone independently performed it. Delegate only if the user or applicable instructions authorize delegation.

Compile LaTeX with bibliography and cross-references in a temporary output directory. Inspect warnings and render representative pages containing the architecture figure, algorithms, tables, and long equations. A successful build does not prove readability. Check references, arithmetic, denominators, symbol consistency, and implementation status separately.

Finish with links to the requested artifacts, a short account of substantive changes and validation, and any concrete scientific limitations that remain. Never label an unfinished empirical study as submission-ready merely because the writing and typesetting are complete.
