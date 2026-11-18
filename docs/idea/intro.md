# **Beyond Human-Centric Change Impact Analysis: A New Software Engineering Paradigm for AI-Generated Code**

I think this direction has the potential to be **more original and scientifically important than the initial RAVEN proposal**. Instead of developing another risk-adaptive testing technique, we can challenge a fundamental assumption in software engineering:

> The way a software change is analyzed, constrained, and validated should not necessarily be the same when the developer is an autonomous AI agent rather than a human programmer.

However, I would refine your hypothesis. The key difference may not be that AI edits more files. It may be that **AI agents explore, reason about, and realize software changes through different sequences of actions and alternative implementations**, whereas many existing development tools expose only the final syntactic modification.

This distinction creates an opportunity for a new modeling language, change-analysis technique, and validation methodology.

## **1. The deeper research problem**

Traditional change-impact analysis often starts with an observable software modification and asks:

*What other program elements or behaviors may be affected by this change?*

But for autonomous AI development, a potentially more fundamental question is:

*Which software transformations legitimately achieve a desired behavioral outcome, including transformations outside the initially suspected fault location, and how can we distinguish useful exploration from unnecessary modification?*

These are different research questions.

Conventional change-centric analysis

Modified code

Known starting point

Dependency traversal

Potentially affected code

Regression tests

Proposed outcome-centric analysis

Behavioral objective

Known starting point

Explore repair hypotheses

Explain intended effects of edits

Validate outcome and preserved behavior

Conceptual comparison. Conventional impact analysis is not inherently limited to human development, and the proposed distinction must be demonstrated empirically.

### **Three hypotheses worth investigating**

**H1 — Different exploration patterns.** AI coding agents may explore more alternative fault locations, code paths, and repair strategies than human developers working on comparable tasks.

**H2 — Different modification patterns.** AI-generated patches may differ from human patches in the number, distribution, and semantic relevance of their edits, even when both solve the same issue.

**H3 — Mismatch between exploration and existing validation.** Tools that reason primarily from changed lines and dependency proximity may not adequately distinguish legitimate nonlocal repairs from unjustified edits.

These hypotheses are testable. We should not present them as established facts.

For example, an AI agent may examine 40 files but modify only two. Another agent may modify 12 files, all legitimately required. A human may perform a broad refactoring during a bug fix. Treating all three situations as equivalent would produce misleading conclusions.

I recommend studying **exploration footprint, edit footprint, and behavioral relevance separately**.

## **2. What does existing research actually support?**

The research landscape provides evidence that AI-assisted software repair requires new analysis methods, but it does **not yet justify the universal claim that AI agents make broader or less relevant edits than humans**.

The strongest literature foundation comes from five research areas.

### **A. Autonomous AI software repair**

[SWE-bench: Can Language Models Resolve Real-World GitHub Issues? | Princeton Language and Intelligence](https://images.openai.com/static-rsc-4/fo4ANjGw85680TvU9MX1sdRnyp83fWT-97ySvWURKHxyrhdByfeJYs8PpHNteK7JiBSujSlNMasuFSGG24kK04pyUsnRLpCNGMPUbDyuC1iJ_oDuVgoc4gtBtcRG4WLzKx2ckmwTgucxm7KYo5iwnqGn9XQflz9VJltvelMrxzE?purpose=inline)

**SWE-bench: Can Language Models Resolve Real-World GitHub Issues?** — Jimenez et al., ICLR 2024.

Introduced a benchmark based on real GitHub issues and corresponding repository changes. It established an important evaluation setting for comparing software repair systems on realistic repository-level tasks.

[Read paper](https://arxiv.org/abs/2310.06770?utm_source=chatgpt.com)

[SWE-Agent Technical Report   Cool to finally read the technical report for SWE-agent.   SWE-agent is an open-source LLM-based autonomous agentic system that can interact with a computer to solve… | Elvis S.](https://images.openai.com/static-rsc-4/QRaxl1Qu_4n7gKaHitXCmL9VOAtygoUS3YhAZqpjvgHGSJmLGpLCT4otv1Q691xE-kyMIeQ8YWe8Jg7D5qP5fXemg5GEFSxIwNv0M7yhWMEkooSNv3BX54KCtQ_-B9hL_mW7nH5zRALDi9aqFhDAyXcxcBT8YqgBEYDbjqv7Nak?purpose=inline)

**SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering** — Yang et al., 2024.

Demonstrates an agentic development process involving repository inspection, command execution, modification, and feedback. The sequence of interactions is relevant to studying AI exploration behavior.

[Read paper](https://arxiv.org/abs/2405.15793?utm_source=chatgpt.com)

[Paper page - Agentless: Demystifying LLM-based Software Engineering Agents](https://images.openai.com/static-rsc-4/A0vdMrLTbipDhixI4WWQ7-ylGmlFk0LwR1cpNBPM7U19Ieyw0g1M1rrJ7Ytsv6Yk4qLIi4xNnMOeHpvqkb2xyJ5ymhbxeYJ_p2ynOcypEFY9C8vdKkFMqv78HeZa-1Ft5KfBCbGaTSiydDKB4joR5rhiKEGCcnr9WxIop61Syfc?purpose=inline)

**Agentless: Demystifying LLM-based Software Engineering Agents** — Xia et al., 2024.

Its localization–repair–validation design provides an important counterpoint to unrestricted agentic exploration. It helps test whether elaborate exploration is actually beneficial.

[Read paper](https://arxiv.org/abs/2407.01489?utm_source=chatgpt.com)

**What these studies support:** Automated software repair can be organized through different exploration, localization, and repair strategies.

**What they do not establish:** That AI-generated edits are generally more scattered, less focused, or more dangerous than human-written edits.

That missing evidence could become the first contribution of our paper.

### **B. Fault localization and program repair**

Important foundations include:

| Research                                                                                                    | Relevance to our hypothesis                                                                                            |
| ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Jones & Harrold, *Empirical Evaluation of the Tarantula Automatic Fault-Localization Technique* (2005)      | Execution spectra can rank suspicious code without modeling a developer's reasoning                                    |
| Le Goues et al., *GenProg: A Generic Method for Automatic Software Repair* (2012)                           | Automated repair already explored edits beyond manually authored patches                                               |
| Long & Rinard, *Automatic Patch Generation by Learning Correct Code* (2016), Prophet                        | Shows that candidate patches can be generated and ranked with learned signals                                          |
| Long & Rinard, *An Analysis of the Search Spaces for Generate and Validate Patch Generation Systems* (2016) | Demonstrates the importance of repair search spaces and the difficulty of separating correct fixes from plausible ones |

These works are important because they prevent us from incorrectly claiming that non-human repair search is entirely new.

The real research gap is **how to describe and validate goal-directed transformations when an AI agent can dynamically inspect, reason about, and modify a repository without a predetermined repair location**.

### **C. Change-impact analysis and regression testing**

Traditional foundations include:

- Bohner and Arnold, *Software Change Impact Analysis* (1996).
- Rothermel and Harrold, *A Safe, Efficient Regression Test Selection Technique* (1997).
- Orso, Apiwattanapong, and Harrold, *Leveraging Field Data for Impact Analysis and Regression Testing* (2003).

A critical correction to the original hypothesis is necessary here.

These techniques are not inherently based on human cognitive behavior. Many provide rigorous dependency-based, dynamic, or semantic analysis that is agnostic to whether a human or AI created the patch.

Therefore, our paper should **not** argue that traditional change-impact analysis is unsound because it was designed for humans.

Instead, we should argue that its usual starting point—the actual modification—is insufficient for a distinct task: *controlling which transformations an autonomous developer should be allowed to explore and accept before the final patch is known.*

That distinction is defensible and potentially publishable.

### **D. Intent, program synthesis, and semantic repair**

Several established ideas are especially relevant:

- **Design by Contract:** Expressing expected preconditions, postconditions, and invariants.
- **Program synthesis:** Searching for implementations that satisfy behavioral specifications.
- **Semantics-based repair:** Generating corrections from logical constraints and test evidence.
- **Program equivalence and relational verification:** Comparing the behavior of two implementations.
- **Counterexample-guided synthesis:** Refining candidate programs based on counterexamples.

Our DSL must go beyond merely restating preconditions and postconditions.

Its added value should be an explicit model linking:

\\[ \text{Repair Intent} \rightarrow \text{Hypothesis} \rightarrow \text{Transformation} \rightarrow \text{Behavioral Evidence}. \\]

This is the key relationship I would investigate.

### **E. AlphaGo and the analogy with human cognition**

Your chess and Go analogy is useful, but we should employ it carefully.

[Breve historia visual de la inteligencia artificial](https://images.openai.com/static-rsc-4/J_v1dEdElQUeHhohBZTSclLShUtsq3-Sr999Xy9qm5MbpomhMgJ5VpTbCk9aVLkOY3QEWv1aybQdT4r7xxMAh9NvFjFmqa9bCE1VFVemW50_oTRAxnCgFyjSWhbitG4SIOScUoSFYXpqGBtqsKbxC3g6RvVDb_JpOVkdPCQ5iGw?purpose=inline)

AlphaGo

Silver et al., *Mastering the Game of Go with Deep Neural Networks and Tree Search*, Nature 2016.

[Move 37: When the Machine Taught Us to See Differently | Abraham's Covenant](https://images.openai.com/static-rsc-4/z2PMr-9X2GIeWLXERyXq1XG1uzEGLKMHBjCfwdY6tHNhZ18NoEPM0tXVFHxqzHEwd4W2mb6X6nd6MX7SXJT0mUBhgzSl4bn7dZZALvhzgUDEOpHdUgRTJrByOyToURAHBepTDE7r2-lxu8qYiu2UjB453thr1Nt2yhfAO5klPfo?purpose=inline)

AlphaZero

Silver et al., *A General Reinforcement Learning Algorithm that Masters Chess, Shogi, and Go through Self-Play*, Science 2018.

These systems demonstrate that machine search and learned strategies can produce decisions that differ from established human strategies.

However, the analogy has limits: Go has a formally defined objective and game rules. Real-world software maintenance involves incomplete requirements, environmental dependencies, and multiple competing quality objectives.

The useful lesson is not that AI makes unconventional moves. It is that **the objective of a system should be specified independently of the particular sequence of actions used to achieve it**.

That principle could motivate the new DSL.

### **Literature conclusion**

Based on established research available to me, the strongest opportunity is at the intersection of autonomous program repair, semantic specifications, program synthesis, and change-impact analysis.

I cannot verify publications from late 2024 through November 2026 because live web search is disabled. Consequently, this is a preliminary related-work analysis, not a verified claim that no recent system already implements the proposed concepts. Before submission, closely check recent ICSE, FSE, ASE, ISSTA, TSE, EMSE, and JSS papers, particularly research on agent trajectories, edit locality, patch overfitting, intent-aware repair, and agent action constraints.

## **3. Proposed research: ORBIT**

## **ORBIT: Outcome-Driven Behavioral Intent Modeling for Autonomous Software Development**

I suggest naming the approach **ORBIT**, emphasizing that software modifications should be evaluated relative to behavioral objectives rather than only their syntactic distance from an initial fault location.

The central principle is:

> An AI-generated software change should be judged by whether its transformations are necessary, justified, and behaviorally consistent with the intended outcome—not merely by the number or proximity of modified lines.

This principle also avoids the opposite extreme: allowing an agent to change any part of the repository as long as the existing tests pass.

### **3.1 Four core innovations**

| Component                          | Scientific purpose                                                                            | Why it matters                                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| **Intent abstraction**             | Represent repair objectives independently of files and implementation strategies              | Allows alternative, nonlocal repairs                             |
| **Hypothesis-to-edit mapping**     | Link each proposed change to a falsifiable explanation of how it contributes to the objective | Makes otherwise unexplained edits analyzable                     |
| **Semantic change envelope**       | Compute the set of effects permitted by the objective and its preservation requirements       | Constrains harmful changes without arbitrary file limits         |
| **Counterfactual edit validation** | Determine whether individual changes or groups of changes are actually needed                 | Identifies potentially unnecessary edits and hidden dependencies |

The combination is more interesting than simply creating a DSL that specifies which files can be modified.

## **4. Component 1: A higher-level DSL for software-development intent**

I recommend an **intent-centered DSL** that describes the repair goal, preservation requirements, permissible behavior changes, and evidence expected from candidate transformations.

Call it **ORBIT-DSL**.

Consider an issue in which a financial reporting system incorrectly excludes refunds.

A location-based policy might tell the agent to modify `ledger.py` and avoid changing other files.

But perhaps the underlying problem involves both refund normalization and report aggregation. A legitimate repair might require changing the data-normalization layer, which is outside the initially suspected location.

An ORBIT specification could instead describe:

```

repair RefundAccounting {

  scope {
    entrypoint: Ledger.generate_report;
    environment: production;
  }

  objective CorrectNetBalance {
    for_all transaction_sets T:
      report(T).net == sum(T.amount);
  }

  preserve {
    transaction_identity;
    currency_precision;
    external_api_schema;
    authorization_behavior;
  }

  allow_change {
    behavior: refund_normalization;
    behavior: transaction_aggregation;
  }

  require_evidence {
    failing_case_before;
    passing_case_after;
    preservation_checks;
    explanation_for_each_change;
  }

  require_justification {
    for_each_changed_component;
    counterfactual_when_feasible;
  }
}

```

This is a proposed language design, not an existing executable implementation. A real compiler would need a precise grammar, typed references, and an operational interpretation of each clause.

The formal core should be small and machine-checkable. Natural-language descriptions can help an agent propose goals or explanations, but cannot be treated as proofs.

### **Why this is different from existing contract languages**

Traditional contracts specify when a function may execute and what it must guarantee.

ORBIT additionally relates the original software, the candidate software, and the modification process.

For example:

- The `objective` specifies the intended new behavior.
- The `preserve` clauses specify behavior that must remain unchanged or satisfy existing guarantees.
- The `allow_change` clauses identify justified behavioral categories, not necessarily source-code locations.
- The `require_justification` clauses demand evidence connecting edits to the objective.

It is important that `allow_change` not simply become a hardcoded list of permitted files. That would reproduce location-centric constraints at a different syntax level.

## **5. Component 2: From fault localization to repair hypotheses**

This is where I see the greatest potential for innovation.

Conventional fault localization estimates which program elements are likely responsible for a failure.

ORBIT would introduce a second representation: a **repair hypothesis**.

A repair hypothesis is a proposed causal explanation connecting an observed failure to a behavioral transformation.

For example:

Example: Incorrect refund reporting

OBSERVED FAILURE

The final report overstates revenue because refunds are not subtracted.

Hypothesis H1

The aggregation function ignores negative values.

Candidate: change aggregation logic

Hypothesis H2

The normalization layer incorrectly changes refund signs.

Candidate: change normalization logic

**Candidate transformations + discriminating tests**

Determine which hypothesis is supported by actual executions

The AI agent is permitted to investigate either hypothesis. The method does not presume that the initially suspected line must be the true repair location.

But every accepted transformation must be linked to at least one hypothesis and evaluated against the specified behavioral outcome.

### **Formal representation**

Let:

- \\(P\\): original program.
- \\(g\\): behavioral goal.
- \\(H=\\{h_1,\ldots,h_n\\}\\): candidate repair hypotheses.
- \\(\Delta=\\{\delta_1,\ldots,\delta_m\\}\\): candidate edit operations.

Define a relation:

\\[ J\subseteq H\times\Delta \\]

where:

\\[ (h,\delta)\in J \\]

means the agent claims that edit \\(\delta\\) implements or helps test hypothesis \\(h\\).

This relation initially records an explanation, not verified causality.

To validate it, ORBIT should establish additional evidence:

\\[ \operatorname{Support}(h,\delta,E) \\]

where \\(E\\) contains executable counterexamples, dependency evidence, or controlled intervention results.

A crucial distinction is that **LLM-generated explanations alone must not count as evidence of causal relevance**.

### **Proposed innovation: Hypothesis coverage**

Rather than measuring only how much of the code was modified or executed, measure how effectively the agent's actions investigate plausible repair hypotheses.

For example:

\\[ \operatorname{HypCoverage} = \frac{ |\\{h\in H:\operatorname{Tested}(h)\\}| }{ |H| }. \\]

This requires careful interpretation: an agent-generated hypothesis set is not necessarily exhaustive, and generating hundreds of trivial hypotheses could distort the metric.

I would therefore treat hypothesis coverage as a diagnostic metric, not a primary correctness metric.

A more defensible measure is whether the agent uses **discriminating experiments** that can eliminate competing explanations.

That is an important distinction between broad exploration and productive exploration.

## **6. Component 3: Semantic Change Envelope**

This would be the central formal contribution.

Instead of restricting modifications to a particular function or module, define the permissible behavioral difference between the original and modified software.

Let:

\\[ P'=\operatorname{Apply}(P,\Delta). \\]

Let \\(\mathcal O(P,x)\\) represent the relevant observable behavior of program \\(P\\) on input \\(x\\), including outputs and specified external effects.

Partition the modeled input/environment space into:

- \\(X\_{\mathrm{repair}}\\): inputs or situations where behavior is required to change or satisfy new goals.
- \\(X\_{\mathrm{preserve}}\\): inputs or situations where specified observations must be preserved.
- \\(X\_{\mathrm{unknown}}\\): remaining cases without sufficient requirements.

For repair inputs:

\\[ \forall x\in X\_{\mathrm{repair}}: \Phi\_{\mathrm{goal}}(P',x). \\]

For preservation inputs:

\\[ \forall x\in X\_{\mathrm{preserve}}: \pi\_{\mathrm{pres}}(\mathcal O(P',x)) = \pi\_{\mathrm{pres}}(\mathcal O(P,x)), \\]

where \\(\pi\_{\mathrm{pres}}\\) selects the observations required to remain unchanged.

This avoids requiring full behavioral equivalence where a legitimate repair should change the program.

It also avoids requiring the change to be close to the original fault location.

Illustrative semantic envelope

Conceptual illustration: repair objectives and preservation requirements may overlap and must both hold. The regions represent behavioral constraints, not sets of source files.

### **The key innovation**

A change to a distant file should be acceptable if the resulting program satisfies the goal and preservation obligations.

A change to the originally suspected function should be rejected if it violates those obligations.

Thus, **semantic relevance takes precedence over syntactic locality**.

However, passing these obligations alone does not establish that every changed line was necessary. That requires the next component.

## **7. Component 4: Counterfactual Edit Validation**

Suppose an AI agent modifies five functions to fix one bug.

The tests pass, but three functions appear unrelated to the issue.

How can we determine whether these modifications were necessary?

ORBIT could use counterfactual validation.

Let:

\\[ \Delta=\\{\delta_1,\ldots,\delta_m\\}. \\]

For a candidate edit \\(\delta_i\\), construct:

\\[ P\_{-\delta_i} = \operatorname{Apply}(P,\Delta\setminus\\{\delta_i\\}). \\]

If \\(P\_{-\delta_i}\\) still satisfies all the specified repair and preservation obligations, then the removed edit may be unnecessary relative to those obligations.

If removing it reintroduces the defect, the edit has evidence of necessity in the current patch context.

But two limitations matter.

First, edits can depend on each other: removing one edit may make the program uncompilable. Second, individually unnecessary edits may be jointly necessary in alternative combinations.

Therefore, a stronger method analyzes **minimal sufficient edit sets** rather than only one-edit-at-a-time deletion.

Define:

\\[ \operatorname{Valid}(D) \equiv \operatorname{Apply}(P,D) \models \Phi, \\]

where \\(\Phi\\) includes repair and preservation obligations.

A subset \\(D\subseteq\Delta\\) is inclusion-minimal if:

\\[ \operatorname{Valid}(D) \land \forall D'\subsetneq D: \neg\operatorname{Valid}(D'). \\]

This definition is relative to the formalized requirements and supported execution model. It does not mean the patch is globally optimal or minimal by number of lines.

Because searching all subsets is exponential, ORBIT could use dependency-aware delta debugging, hierarchical grouping, and test-guided search.

**This could be a major practical innovation:** rather than penalizing an AI agent for producing a large patch, identify whether its additional modifications contribute to satisfying the required behavior.

That is much more meaningful than measuring patch size alone.

# **8. Research questions and hypotheses**

I recommend structuring the study around four research questions.

| RQ                                  | Research question                                                                                                                      | Central hypothesis                                                                                                           |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **RQ1 — Behavioral differences**    | How do autonomous AI agents differ from human developers in exploring and modifying software during bug repair?                        | AI trajectories and patches exhibit measurable differences in locality, dispersion, and repair strategy                      |
| **RQ2 — Analysis effectiveness**    | Does outcome-centric analysis better distinguish justified nonlocal edits from unrelated modifications than change-centric techniques? | Semantic objectives and preservation constraints reduce misleading impact classifications                                    |
| **RQ3 — Repair effectiveness**      | Does ORBIT improve the correctness and maintainability of AI-generated repairs?                                                        | Intent-guided exploration and counterfactual edit validation reduce harmful edits without suppressing valid nonlocal repairs |
| **RQ4 — Formal assurance and cost** | What correctness guarantees and computational costs arise from the proposed abstractions and analysis algorithms?                      | ORBIT can provide scoped semantic guarantees with acceptable overhead on selected repository tasks                           |

I would treat RQ1 as an independent empirical investigation. If the data contradict the hypothesis, that finding should change the paper's motivation.

For example, AI-generated patches may be *smaller* than human patches, while AI exploration trajectories are considerably broader. That would still be a valuable result and might strengthen the argument for modeling intent and search behavior separately.

## **9. The most suitable benchmark**

[Understanding LLM Code Benchmarks: From HumanEval to SWE-bench](https://images.openai.com/static-rsc-4/ZtdvjTB1cgB4yBxFc8XYpZFUkZXBddKAE5wcGaSAjnFw400Cqy-_gn2Pyeow-Isg051kVboSVN2lj9mahbFTU_EDXKOMIMYidvzn-LH6eCY4lqGuEcwSisPqGEfgsICD-lUs4hQbeh5k-ChjUbhiX4hKz2DxkR1GHx14PmWcTKo?purpose=inline)

## **SWE-bench Verified**

Best primary benchmark

500 human-validated real-world GitHub issue instances, with repository context and reference fixes.

[Official GitHub repository](https://github.com/SWE-bench/SWE-bench?utm_source=chatgpt.com)

**Why it is particularly suitable**

It offers a natural comparison between the human-authored reference patch and AI-generated patches for the same underlying issue. It also supports execution-based evaluation of whether candidate repairs resolve the issue.

The availability of reference patches is especially valuable, but there is a methodological problem we must handle carefully.

A human reference patch is not necessarily the unique correct repair or the smallest acceptable repair. It may include housekeeping changes, and the benchmark tests do not establish complete correctness.

Consequently, using the reference patch as the sole definition of relevant code would bias the study toward human solutions—the very assumption we intend to question.

### **Recommended benchmark combination**

| Dataset                | Approximate scope                  | Main use                                                                                                                     |
| ---------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **SWE-bench Verified** | 500 validated issue instances      | Primary human-versus-AI comparison and end-to-end repair evaluation                                                          |
| **SWE-bench Lite**     | 300 instances                      | Smaller-scale prototyping and reproducibility checks; overlaps with SWE-bench, so do not treat as an independent replication |
| **BugsInPy**           | Approximately 500 real Python bugs | Controlled fault localization, program behavior, and regression analysis                                                     |
| **Defects4J**          | Hundreds of real Java defects      | Cross-language replication of the analysis, if implementation time permits                                                   |

For the December deadline, I would focus on SWE-bench Verified, with BugsInPy as an optional secondary validation set.

The most important practical requirement is access to actual **AI execution trajectories**, not merely final patches.

SWE-bench provides issues and evaluation infrastructure; complete model trajectories depend on the agent system and run artifacts. Where public trajectories are unavailable or incomplete, we would have to generate them ourselves.

### **A matched evaluation protocol**

For each selected issue:

1. Recover the original failing repository revision, issue description, and human reference patch.
2. Run or obtain trajectories from two AI repair configurations, ideally one localization-oriented and one exploratory.
3. Record every file inspected, command executed, hypothesis proposed, test run, and file modified.
4. Independently evaluate the final patches using the benchmark test suite and additional regression checks.
5. Label the behavioral relevance of changed components without relying exclusively on human-patch overlap.
6. Compare conventional change analysis with the proposed ORBIT method on the same issues and candidate patches.

This allows us to study both the development process and the resulting artifact.

## **10. An empirical study of human versus AI repair behavior**

Before implementing the entire framework, I would first investigate whether the central hypothesis is supported.

### **Study A: Difference in repair footprints**

For each issue, construct three footprints:

\\[ F\_{\mathrm{inspect}}: \text{files inspected} \\]

\\[ F\_{\mathrm{edit}}: \text{files modified} \\]

\\[ F\_{\mathrm{semantic}}: \text{behaviors potentially changed}. \\]

Then define metrics.

**Edit dispersion**

Measure how far modified components are distributed through the repository dependency graph.

\\[ \operatorname{Dispersion}(\Delta) = \frac{1}{|M|(|M|-1)} \sum\_{\substack{u,v\in M\\\u\neq v}} d_G(u,v), \\]

where \\(M\\) is the set of modified components and \\(d_G\\) is a defined graph distance. For disconnected components, report them separately or use a documented finite penalty rather than silently inventing a distance.

**Reference-patch divergence**

\\[ \operatorname{Divergence} = 1- \frac{ |M\_{\mathrm{AI}}\cap M\_{\mathrm{human}}| }{ |M\_{\mathrm{AI}}\cup M\_{\mathrm{human}}| }. \\]

This is a descriptive measure of difference from the reference patch, not a direct measure of defectiveness.

**Unjustified edit rate**

\\[ \operatorname{UER} = \frac{ \text{edits independently judged unjustified} }{ \text{all assessed edits} }. \\]

This requires a careful annotation protocol with multiple assessors, adjudication, and agreement statistics.

**Exploration-to-edit ratio**

\\[ \operatorname{EER} = \frac{ |\text{distinct inspected components}| }{ \max(1,|\text{modified components}|) }. \\]

This captures differences in exploratory behavior that patch-level analysis would miss.

### **Important design limitation**

SWE-bench reference patches give us human *final modifications*, not necessarily human exploration trajectories.

Therefore, we can make a matched comparison of human and AI **patch characteristics**, but cannot reliably compare their full cognitive or exploration processes without additional human development logs, IDE telemetry, or observational studies.

I would report this limitation explicitly rather than interpreting patch differences as direct evidence about how humans reason.

### **Study B: Are nonlocal AI edits harmful or useful?**

For every AI edit outside the reference patch's changed components, classify it as:

- Necessary for the evaluated repair.
- Valid alternative implementation.
- Unnecessary but behavior-preserving.
- Harmful or regression-inducing.
- Unresolved due to insufficient evidence.

This is more informative than the simple binary classification of “inside versus outside the human patch.”

A subset of the patches should undergo counterfactual deletion experiments to test whether ostensibly unrelated edits are necessary.

The expected result is not predetermined: nonlocal edits may be beneficial, harmful, or neutral.

That observation would directly determine how ORBIT should handle them.

# **11. Evaluating the proposed ORBIT approach**

The primary experimental comparison should isolate the benefits of intent modeling and counterfactual validation.

### **Baselines**

| Configuration | Method                                                                        |
| ------------- | ----------------------------------------------------------------------------- |
| B0            | Unmodified AI repair agent                                                    |
| B1            | AI agent with syntactic change-impact feedback                                |
| B2            | AI agent with dependency-graph change-impact feedback                         |
| B3            | AI agent with goal/postcondition checks only                                  |
| B4            | AI agent with goal and preservation constraints                               |
| **ORBIT**     | Goal + preservation + hypothesis-to-edit evidence + counterfactual validation |

Use the same underlying model, repair budget, prompts where applicable, and tool access wherever possible.

The comparison must distinguish improvements caused by ORBIT from improvements caused simply by additional inference or testing resources.

### **Evaluation measures**

Primary outcomes

Repair effectiveness

## **Resolved %**

Fraction of issues whose candidate patches pass the official evaluation

Regression avoidance

## **Defect rate**

Independent regression failures and introduced behavioral violations

Edit justification

## **Precision / recall**

Accuracy of classifications against adjudicated edit-level labels

Efficiency

## **Cost / fix**

Wall-clock time, executed tests, tokens, and cost per successful repair

I would also measure nonlocal-edit retention: how often the method correctly retains a valid nonlocal change instead of removing it merely because it is outside the expected repair region.

That is particularly important for proving the practical value of your hypothesis.

### **Ablation study**

Remove one ORBIT mechanism at a time:

| Ablation                           | Scientific question                                             |
| ---------------------------------- | --------------------------------------------------------------- |
| Without intent DSL                 | Do explicit behavioral objectives improve decision quality?     |
| Without preservation constraints   | Do goals alone encourage regressions?                           |
| Without hypothesis-to-edit mapping | Does causal explanation improve edit assessment?                |
| Without counterfactual validation  | Can semantic checking alone identify unnecessary modifications? |
| Without nonlocal exploration       | Are broader repair strategies actually beneficial?              |

For the final comparison, use issue-level paired measurements with multiple independent agent runs where resources allow. Report confidence intervals, effect sizes, and paired statistical analyses. Repeated seeds on one issue should not be counted as independent issues.

# **12. Formal soundness and completeness**

The proposed DSL provides a useful opportunity for formal methods, but its strongest guarantees should concern **behavioral preservation and validity of accepted transformations**, not whether an AI agent's explanation accurately represents its internal reasoning.

I suggest three formal contributions.

### **Theorem 1 — Soundness of semantic impact overapproximation**

Let \\(A^\\#(\Delta)\\) be the abstract set of behaviors potentially affected by a candidate transformation.

Under a sound abstraction of the supported program semantics:

\\[ \operatorname{Affected}(P,P') \subseteq \gamma(A^\\#(\Delta)). \\]

The proof can use relational abstract interpretation and simulation between the concrete and abstract transition systems.

The critical benefit is that the analysis does not assume the fault and repair must lie near one another in the dependency graph.

### **Theorem 2 — Soundness of accepted transformations**

Let \\(\Phi\_{\mathrm{goal}}\\) and \\(\Phi\_{\mathrm{pres}}\\) be the objectives and preservation requirements compiled from ORBIT-DSL.

If ORBIT returns `Verified` only after soundly discharging all their proof obligations, then:

\\[ \operatorname{Verified}(P,P') \Rightarrow P'\models\Phi\_{\mathrm{goal}} \land (P,P')\models\Phi\_{\mathrm{pres}}. \\]

This theorem depends on complete specification coverage of the behaviors being claimed, sound verification procedures, and a faithful source-language model.

It does not imply that the entire program is bug-free.

### **Theorem 3 — Bounded completeness of transformation validation**

For a finite, faithfully modeled program-state space, assume exhaustive exploration of all required verification obligations.

Then:

\\[ \exists \tau: \tau\models\neg\Phi \Rightarrow \operatorname{ORBIT} \text{ discovers a counterexample}. \\]

This establishes bounded completeness for the specified property, subject to sufficient resources and a complete bounded exploration procedure.

The counterfactual edit-reduction component can also have a useful theorem: exhaustive subset search returns an inclusion-minimal satisfying edit set whenever one exists, under a deterministic and complete validity oracle.

A heuristic delta-debugging implementation would need a weaker guarantee.

## **13. How model checking should be used**

I would combine three complementary methods.

| Method                                            | Responsibility                                                                                 |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **SMT solving and relational symbolic execution** | Verify repair objectives and preservation constraints for supported program fragments          |
| **Abstract interpretation / CEGAR**               | Conservatively identify semantic effects and refine uncertain behavioral regions               |
| **TLA+ / TLC**                                    | Verify the ORBIT protocol that handles hypotheses, edits, evidence, validation, and acceptance |

The TLA+ protocol should enforce important invariants:

\\[ \Box(\mathsf{Accepted}\Rightarrow \mathsf{GoalVerified}\land\mathsf{PreservationVerified}) \\]

\\[ \Box(\mathsf{Accepted}\Rightarrow \mathsf{NoUnresolvedMandatoryObligations}) \\]

\\[ \Box(\mathsf{EvidenceDischarged} \Rightarrow\mathsf{EvidenceValid}) \\]

and, under bounded execution and fairness assumptions:

\\[ \Diamond(\mathsf{Accepted}\lor \mathsf{Rejected}\lor\mathsf{Inconclusive}). \\]

These formulas describe desired properties, not already-proven results.

I would model-check faulty variants that permit unsupported edit explanations, allow preservation requirements to be bypassed, discard counterexamples, or accept when mandatory evidence is missing.

This also provides a clear differentiation from your IEEE TSE manuscript. That paper governs authorization, versions, provenance, withdrawal, and rollback of self-evolving artifacts. ORBIT would formalize **the behavioral meaning and justification of software modifications**. Its evaluation should involve patch validity and edit relevance rather than reusing the TSE governance experiments.

## **15. My preferred scientific positioning**

Of the ideas discussed so far, I see three possible papers:

| Paper                                      | Main scientific contribution                                                          | Risk                                                               |
| ------------------------------------------ | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Human versus AI Software Repair            | Empirical characterization of repair strategies and edit behavior                     | May be descriptive without a sufficiently strong new method        |
| ORBIT-DSL                                  | Formal language for behavioral intent and permissible transformations                 | May appear incremental relative to contracts and program synthesis |
| **ORBIT: Outcome-Centric Change Analysis** | New semantic analysis that explains and validates nonlocal AI-generated modifications | Requires formalization and convincing comparative evidence         |

The third is my preferred direction.

The novelty should not be framed as “we introduce a DSL to govern AI code changes.” That sounds close to existing governance and contract systems, including your TSE work.

Instead, I would formulate the paper's main claim as:

> **Existing change-impact techniques characterize the consequences of observed modifications, whereas autonomous software development also requires reasoning about the behavioral legitimacy of candidate transformations before their final locations are known. ORBIT introduces an outcome-centric abstraction that connects repair intent, alternative transformation hypotheses, and behavioral preservation obligations, allowing nonlocal but justified edits while identifying unnecessary or harmful changes.**

This is a stronger and more specific research proposition.

For a concrete next step, I recommend preparing a **research design document centered on the ORBIT semantic model**, including one realistic SWE-bench issue, two competing repairs at different locations, the corresponding DSL specification, a formal judgment of both patches, and the exact experimental comparison with conventional change-impact analysis. That single worked example will reveal whether ORBIT truly offers a new capability—or merely renames existing program-repair techniques.