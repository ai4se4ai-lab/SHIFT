# Multiple review and revision passes

Use distinct passes because fluent prose can conceal a weak argument, and correct mathematics can conceal an unhelpful research question. Keep a temporary issue ledger with severity, location, evidence, required revision, and resolution. Resolve substantive findings before cosmetic ones. Reopen affected checks after each change.

## Pass 1: Contribution and argument

Read the title, abstract, introduction, contribution list, and conclusion together.

- State the main claim in one sentence. Is the problem consequential and the contribution concrete?
- Does the introduction show an actual failure of available evidence rather than asserting that all prior work is obsolete?
- Is the strongest nearest method acknowledged? Does the remaining distinction matter?
- Are an analogy, anecdote, prevalence claim, and causal claim kept separate?
- Does a negative result refine the premise rather than disappear from the story?
- Do claimed contributions match completed artifacts and observed evidence?

**Revision gate:** no unsupported universal statement or missing nearest neighbor in the central argument. If the novelty claim changes, rewrite the abstract, contributions, and conclusion together.

## Pass 2: Formal and algorithmic adversary

Read only the definitions, equations, algorithms, proofs, and running example. Try tiny counterexamples.

- Could two individually removable edits both be required as alternatives?
- Could two individually indispensable edits be removed together?
- Could closure re-add a removed edit, defeat strict decrease, or include units outside the current configuration?
- Could an invalid subset or timeout be mislabeled as a semantic failure?
- Does a guarantee rely on monotonicity or determinism that has not been stated?
- Is “minimum,” “inclusion-minimal,” or “1-minimal” used correctly?
- Do add-back experiments implicate an edit alone or an edit plus its required support?
- Do algorithm preconditions, return statuses, and the prose agree?
- Are all helpers and symbols defined, and are code listings short enough to read?

**Revision gate:** proofs establish exactly the stated property, and no label claims more than its witness establishes. Use operational names where stronger semantic names would mislead.

## Pass 3: Empirical and statistical auditor

Independently recompute the key counts from existing records when practical. Audit denominators and provenance before trusting summary tables.

- Can every central number be traced to a record and calculation?
- Are unresolved outcomes, missing predictions, exclusions, and protocol amendments visible?
- Is the unit of analysis consistent with clustering and pairing?
- Is any oracle used both to search and to assert independent correctness?
- Are code, data, model names, hardware details, and timing scopes consistent?
- Does every RQ have a matching design, result, answer, and limitation?
- Do the comparisons isolate the claimed mechanism?
- Do repeated runs or exhaustive results violate a known invariant?

**Revision gate:** inconsistent measurements do not support a performance or correctness claim. If experiments cannot be repaired within the task, disclose the limitation and narrow the claim. Do not convert a planned study into observed results to complete a section.

## Pass 4: Literature and novelty

Search for recent work on the same mechanism, including preprints. Verify venue and publication status from primary sources.

- Does each citation support the adjacent claim?
- Are related-work groups compared with the proposed method on concrete shared axes?
- Is a deployable method distinguished from a privileged diagnostic baseline?
- Are claims such as “first” or “none” defensible against the closest work?
- Are recent findings that contradict the author's premise reported fairly?
- Are title, authors, year, venue, DOI, and version correct?

**Revision gate:** no invented reference, no misleading publication status, and no omission that changes the apparent novelty. Record a bounded literature-search date when useful.

## Pass 5: Reader and structure

Read section transitions and the first and last sentences of each paragraph. Then read the paper normally, without consulting the implementation.

- Does the reader understand the problem before the notation?
- Does every definition have a reason to exist?
- Is the running example introduced at the requested location and reused in every component?
- Does the architecture diagram match the prose and algorithm names?
- Are implementation details collected in the appropriate subsection?
- Are results distinguishable from interpretation and future work?
- Are vague pronouns, repeated claims, semicolon chains, and overloaded paragraphs removed?

**Revision gate:** a reader can reconstruct the method and evaluation without guessing terminology or backtracking repeatedly.

## Pass 6: Artifact and rendered manuscript

Build the final sources in a temporary directory. Check bibliography and references after the final pass, not only before revisions.

- Resolve missing citations, duplicate labels, and undefined references.
- Inspect overfull boxes and float placement.
- Render and inspect the overview, algorithm, example, widest table, and equation-heavy pages.
- Check that code and diagram text remain readable at intended page width.
- Check that the output directory satisfies the author's exact file constraints.
- Confirm that reported changes do not include unrelated user files.

**Revision gate:** the sources build and the critical pages are readable. Record scientific issues separately from typesetting issues.

## Second cycle and stopping

After these passes, reread the abstract and introduction against the final evidence. Repeat any pass affected by substantive revisions. At least one complete second cycle is appropriate for a major rewrite. Do not claim that a fixed number of self-reviews guarantees journal quality.

Stop when the requested artifacts are complete, substantive claims are supported or explicitly scoped, and remaining research gaps are accurately disclosed. If implementation or new experiments are outside the task, the manuscript can be a complete revision while the research still needs further validation.

Do not call these passes external, blind, independent, or peer review unless that description is factually true. A self-review can be rigorous without pretending to be a journal decision.
