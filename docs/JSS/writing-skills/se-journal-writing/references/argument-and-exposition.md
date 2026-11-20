# Argument and exposition

## Identify the decision the paper improves

A problem is more than an area with increasing interest. Identify who acts, what they must decide, what evidence they currently have, and what goes wrong when that evidence is insufficient. Explain the consequence through an observable failure or cost. Examples include reviewing unnecessary patch edits, missing regressions outside issue tests, accepting a configuration that violates a documented requirement, or choosing an expensive analysis with no additional fault detection.

Distinguish three levels of claims:

- A phenomenon: agents can retain exploratory edits in a final patch.
- A prevalence claim: this occurs in a stated fraction of a defined population.
- A causal explanation: a particular search process causes the retained edits.

Evidence for the first level does not establish the second or third. Comparisons of final patches alone cannot demonstrate how developers think. Agent tool logs measure recorded behavior, not internal cognition. A reference fix represents one human solution, not every reasonable human strategy.

When an author supplies an analogy, retain the useful design lesson and bound the analogy. Chess and Go illustrate that successful computational strategies need not reproduce a familiar human sequence. They do not demonstrate properties of software repair. Software also lacks the complete rules and outcome oracle available in a board game. Use the analogy briefly and immediately return to software-specific evidence.

## Build the introduction as a chain of necessary moves

The sequence below is a diagnostic tool. Adapt paragraph count and ordering to the actual paper.

1. **Consequential setting.** State the relevant task and why people rely on it. Introduce one concrete decision and its stakes. Avoid opening with an unbounded history of AI or assertions that a research area is popular.
2. **Failure scenario.** Show a small case in which normal evidence supports an inadequate decision. Explain what passes, what remains uncertain, and why a practitioner cannot simply inspect a location or a score.
3. **What current methods answer.** Present the strongest relevant method fairly. Distinguish its intended purpose from a misuse of its output. Static impact analysis is not invalidated because it was evaluated on human commits.
4. **Precise gap.** Name the missing relation, capability, or evidence. State the conditions under which it matters and the limits of available evidence.
5. **Insight.** Explain the conceptual move in plain language. A reader should understand why it might address the gap before encountering the acronym or formal notation.
6. **Technical obstacles and response.** Introduce the few obstacles that determine the method's structure. Connect each to a component rather than listing disconnected challenges.
7. **Contributions and evidence.** Enumerate deliverables, their scope, and the strongest observed results. State separately any proposed extension and any validation that remains outstanding.

Test the transitions by summarizing each paragraph in one sentence. The final idea of paragraph n should make the opening of paragraph n+1 natural. If paragraphs can be randomly reordered without affecting comprehension, the argument probably lacks progression.

## Write background to enable the method

Background should equip the reader to follow the approach, not become a second related-work survey. Include only concepts, notation, assumptions, and example behavior that the technique uses. An unfamiliar term needs a short explanation, even if a citation follows it.

Use this progression where appropriate:

- Task and observable inputs.
- Established mechanisms being reused.
- Behavioral specification or oracle.
- Change representation and permitted variants.
- Outcome and minimality concepts.
- Running example as the last background subsection.

Before a definition, explain the ambiguity it resolves. Afterward, interpret it and state what it does not imply when that boundary matters. For example, closure formalizes which edit combinations are admissible. It does not prove a dynamic program has no missing dependencies.

Avoid defining the full algorithm in background. Background introduces shared concepts. The approach explains the new choices that operate on those concepts.

## Maintain paragraph coherence

Give each paragraph a clear job. Start with its substantive claim, develop the evidence or mechanism, and end with the implication needed by the next paragraph. A paragraph should rarely mix a definition, an unrelated limitation, a hardware description, and a result.

Name concrete actors and artifacts. Prefer “The reviewer sees passing issue tests but no evidence for the added adapter branch” over “This presents a significant challenge in the evolving landscape.” Replace “this” and “it” with their referent when two interpretations are possible.

Short sentences are useful for the main point. Longer sentences can explain a dependency. Do not make every sentence the same length or split a connected explanation into telegraphic fragments. Avoid repeated “Why needed / Input / Output” mini-templates unless they materially improve a reference-style technical section.

Use stable terms. If “goal tests,” “preservation tests,” and “envelope tests” are distinct concepts, retain those names. Do not alternate among “intent,” “objective,” “requirement,” and “contract” as though they are identical. Define their relationships.

## Abstract and conclusion

Write the abstract last. Include the problem, precise gap, mechanism, evaluation population, key results, and the principal scope limit. Report exact denominators where needed to interpret a percentage. Do not introduce stronger novelty, implementation, or generalization claims than the body supports.

The conclusion should answer what the study established, for whom, and under which conditions. It may identify one or two consequential next experiments. Do not recite every section or imply that a proposed feature was evaluated because an underlying component was evaluated.
