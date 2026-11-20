# Definitions, examples, diagrams, algorithms, and DSLs

## Choose a model that supports the claims

For every formal object, write down the operation or claim that needs it. Remove unused notation. Specify the universe, domains, codomains, boundary cases, and whether an operation is total or partial. Distinguish an executable implementation from an idealized mathematical object.

For change analysis, useful distinctions include:

- Applying a subset of edits can fail before the test oracle runs.
- Syntactic validity, successful loading, and behavioral validity are different properties.
- A conservative dependency relation may exclude feasible alternatives. A relation based only on names may also miss dynamic dependencies.
- Closing a candidate set can add edits back. A strict-decrease argument must account for this.
- Removing a provider requires removing its transitive dependents if closure is to be preserved.
- A timeout is missing evidence. Treating it as a behavioral failure can create unsupported necessity claims.

Do not call a name-matching relation a proven over-approximation of all semantic dependencies without a proof and a stated language fragment.

## State minimality precisely

Three common properties differ:

1. **Single-removal or neighborhood minimality:** no permitted elementary removal preserves the outcome.
2. **Inclusion minimality:** no proper subset preserves the outcome.
3. **Minimum cardinality:** no valid configuration has fewer units.

Without monotonicity assumptions, single-removal minimality does not imply inclusion minimality. Neither generally establishes global minimum cardinality. A patch can contain compensating edits such that deleting either one fails but deleting both succeeds.

Similarly, “removal from the full patch fails” does not imply “this edit appears in every successful subset.” Define labels by the observations that justify them. If historical labels such as necessary, jointly needed, or coupled are retained, explain their operational meaning and avoid stronger prose interpretations.

A useful label report records the chosen sufficient subset, the withdrawal configuration, its outcome, structural dependencies, and the contract version. A single categorical label often conceals the evidence a reviewer needs.

## Build one small example with enough structure

Prefer an example containing two plausible repair routes, one genuine obligation, a preserved behavior, and a dependency between an import or helper and a use. About 10--15 readable code lines can be sufficient. If using an actual case, verify the issue identifier, patch, test names, and recorded outcomes. Mark excerpts, omitted context, renamed variables, and synthetic variations.

Create a private walkthrough table before drafting:

| Component | Example input | Operation | Example output | Claim clarified |
|---|---|---|---|---|
| Contract | Goal and preservation requirement | Resolve test identifiers | Frozen obligations | Text is not executable evidence |
| Decomposition | Candidate diff | Split units, link binding dependencies | Four units and two requires edges | Dependencies are module scoped |
| Counterfactual search | Closed configurations | Withdraw, execute, reduce | Sufficient two-unit subset | Distance is not necessity |
| Preservation | Additional stable tests | Compare outcomes, add back groups | Regression witness or no observation | No failure does not prove harmlessness |
| Review | Units and witnesses | Apply explicit review policy | Recommendation with evidence | Reduction is not automatic deletion |

Use the actual paper's components rather than copying this table mechanically. Each approach subsection should advance the same example. An example does not need to exercise every theoretical corner case. Use a clearly marked synthetic extension to explain redundancy or compensation when the real case lacks it.

## Draw an architecture that explains causality

Put inputs and outputs on arrows. Use component names that exactly match subsection names. Show important subcomponents inside each box. A reader should see what travels from the contract to execution, from decomposition to counterfactual search, and from preservation checks to the final report.

Use a legend when line styles indicate status or evidence flow. If a parser, dashboard, or feedback controller is proposed while the core is implemented, distinguish them visually and state the boundary in the caption. A diagram should not silently convert a design into a completed system.

Check that every arrow is meaningful and every component is described. Avoid a central omnipotent box connected to unlabeled arrows. Render the figure at publication width and inspect its actual text size.

## Write executable-looking, readable pseudocode

Explain complex helpers before the algorithm and cite a reused standard algorithm. An operation such as `Withdraw(S,u)` can replace a long closure expression if its exact semantics are defined nearby. Avoid helpers such as `SolveEverything` that hide the contribution.

For 10--15-line algorithms, count numbered executable lines, not caption lines or Require/Ensure declarations. Keep each line to one conceptual step. State preconditions and output status. Show what happens on invalid inputs, unknown test outcomes, exhausted budgets, and unstable repeats when those cases affect the claim.

Check these invariants manually against the code:

- Every accepted reduction has an observed passing outcome.
- A reduction actually shrinks the stored configuration.
- Cached outcomes are keyed by the program, contract, environment, and configuration as necessary.
- Repeated executions intended to test stability bypass the cache.
- The returned report distinguishes evaluated failures from unknown outcomes.
- A stopping rule due to budget cannot masquerade as established minimality.

## Make a DSL a language rather than decorative configuration

Explain why existing test lists, YAML, contracts, or policy files are insufficient for the intended workflow. A DSL contribution needs more than a pleasant listing.

Provide:

- Intended users and the decision controlled by the language.
- A small grammar or exact schema, including cardinality and identifier resolution.
- A static semantics, including unresolved test identifiers, conflicting declarations, and invalid parameter values.
- An execution semantics mapping the document to obligations, selected tests, repeat rules, and a report.
- The authority boundary: who fixes the contract and whether an agent can change it.
- A version or digest that binds the specification and execution environment to the evidence.
- Error and budget semantics.
- An honest comparison with an equivalent general-purpose configuration.

If a DSL merely serializes inputs already consumed by an engine, call it a proposed frontend until its parser, diagnostics, and workflow value are implemented and evaluated. Evaluate authoring correctness and maintenance effort separately from analysis accuracy. High-level abstraction has to preserve meaningful distinctions, not hide unimplemented mechanisms.
