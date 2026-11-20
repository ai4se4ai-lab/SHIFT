# Literature verification and journal exemplars

## Search and verification

Search recent work in the target venue and neighboring software engineering journals. Prefer publisher full text, author manuscripts, official benchmark documentation, and primary repositories. Use an index to discover a paper, then verify the actual source. Read more than an abstract when analyzing exposition or a technical distinction.

Record each candidate's exact title, authors, venue, publication status, version, DOI or stable URL, and relevance. Record which sections were inspected and the organizational lesson. Check recent nearest neighbors again after drafting the approach.

Use a source-to-claim note that distinguishes a source's finding from your inference. Preserve conflicting findings rather than selecting only supporting papers. Avoid implying a systematic review unless a systematic protocol was actually followed.

Verify bibliography metadata separately from substantive claims. A DOI resolving correctly does not establish that a paper supports the adjacent sentence. A preprint must not become a journal article through an invented venue field. Online publication and issue assignment may have different years. Represent both accurately.

Do not copy prose, contribution lists, diagrams, or method structure merely because a paper appeared in a selective journal. Journal papers are exemplars to evaluate, not authority for every writing choice. Respect source quotation and summarization limits.

## Inspected examples for the SHIFT revision, 2026-11-19

These are a focused set of examples, not a systematic review or a journal ranking. Read their current primary versions when reusing them for a new study.

### TSE: repair fine-tuning study

Kai Huang, Jian Zhang, Xinlei Bao, Xu Wang, and Yang Liu. **Comprehensive Fine-Tuning Large Language Models of Code for Automated Program Repair.** IEEE Transactions on Software Engineering 51(4), 904--928, 2025. [Publisher DOI](https://doi.org/10.1109/TSE.2025.3532759). [Author manuscript](https://zhangj111.github.io/files/TSE25_LLM4APR.pdf).

Inspected the introduction, background, experimental setup, RQs, and result organization. The transferable lesson is to turn broad model capability into distinct design dimensions and measurable questions. Explain the experimental choices before presenting the results for each dimension. For a different study, choose dimensions from its own claims rather than inheriting this paper's model comparison matrix.

### TOSEM: hybrid repair technique

Fengjie Li, Jiajun Jiang, Jiajun Sun, and Hongyu Zhang. **Hybrid Automated Program Repair by Combining Large Language Models and Program Analysis.** ACM Transactions on Software Engineering and Methodology 34(7), Article 202, 2025. [Publisher DOI](https://doi.org/10.1145/3715004). [Author manuscript](https://xgdsmileboy.github.io/files/paper/tosem25-hybrid.pdf).

Inspected the introduction, motivating example, approach overview, experimental setup, RQ-based results, and component ablations. The transferable lesson is to explain why an LLM output is insufficient and then describe the program-analysis mechanism that changes it. Map ablations to named components. Check baseline information advantages explicitly instead of treating every reported number as directly comparable.

### EMSE: declarative specification repair

Mohannad Alhanahnah, Md Rashedul Hasan, Lisong Xu, and Hamid Bagheri. **An empirical evaluation of pre-trained large language models for repairing declarative formal specifications.** Empirical Software Engineering 30, Article 149, 2025. [Full text and publisher DOI](https://doi.org/10.1007/s10664-025-10687-1).

Inspected the introduction, Alloy background, repair settings, experiment design, results, and threats. The transferable lesson is to equip readers with domain semantics before comparing feedback strategies, and to distinguish repair effectiveness, failure characteristics, and cost. Language-level validity alone is insufficient for behavioral correctness.

### EMSE: LLM study reporting guidance

Sebastian Baltes and colleagues. **Guidelines for empirical studies in software engineering involving large language models.** [Full text and DOI](https://doi.org/10.1007/s10664-026-10922-3). Published online November 3, 2026, assigned to Empirical Software Engineering 32, Article 64, 2027.

Inspected scope, study types, reporting guidelines, applicability matrix, and reporting checklist. Use its reporting guidance to identify missing information about model inputs, versions, prompts, outputs, analysis, and artifacts. It is methodological guidance, not evidence that a particular repair method works.

## Closest-work update for the SHIFT study

**TRIM: Reducing AI-Generated CodeSlop via Agent Trajectory Minimization**, Mathai et al., [arXiv:2607.18161v1](https://arxiv.org/html/2607.18161v1). Read the trajectory reconstruction and hierarchical counterfactual search, not just the abstract. It directly overlaps with execution-based removal of residual agent edits. A new method cannot claim the general counterfactual minimization idea as unaddressed. Compare artifact requirements, search units, evidence outputs, preservation scope, and equal-budget behavior. Any performance advantage requires an actual comparison.

**SlopCodeBench**, Orlanski et al., [paper](https://arxiv.org/abs/2603.24755) and [primary repository](https://github.com/SprocketLab/slop-code-bench). Useful for planning iterative-development evaluation. Its distributions and releases evolve. Freeze the chosen version and do not combine the initial paper's task count with a later benchmark release.

These notes document source inspection and a research consequence. They are not evidence that SHIFT has implemented the DSL, completed the proposed comparisons, or established benefits for human reviewers.
