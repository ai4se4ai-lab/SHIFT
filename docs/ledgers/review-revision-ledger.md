# Review–revision ledger (internal role-play reviews; not independent peer review)

## Round 1 (2026-11-17, draft with partial results)

| ID | Round | Sev. | Location | Issue | Change | Verification |
|---|---|---|---|---|---|---|
| R0-1 | R0 editor | MAJOR | Intro, Approach overview | Risk of being read as "ddmin applied to patches" | Contribution list names what is new (closure-aware reduction + proof, coupled label, per-module requires relation, envelope attribution, empirical findings); reuse stated explicitly in Overview | Text check |
| R1-1 | R1 method | BLOCKER | RQ2 design | Counterfactual labels used as reference could look circular | Added explicit statement: RQ2 measures how well cheaper proxies approximate the counterfactual measurement; it does not evaluate SHIFT's accuracy against itself; SHIFT's validity rests on Props 1–2 + RQ3 injection with known ground truth | Text check |
| R1-2 | R1 method | MAJOR | RQ2 | Necessity measured only on resolved patches | Stated in Setup/Threats (selection on success) | Text check |
| R1-3 | R1 method | MAJOR | RQ2 table | Gold-file proxy retention is 0 by construction; LLM retention high partly because recall is low | Added caveat sentences | Text check |
| R1-4 | R1 method | MINOR | RQ3 | Equivalent mutants inflate "undetected" | Stated as upper bound in RQ3 / Threats | Text check |
| R1-5 | R1 method | MAJOR | Evaluation plan | Informed-judge variant added post hoc | Labelled exploratory (A8) in protocol and paper | Protocol diff |
| R2-1 | R2 formal | BLOCKER | Prop. 2 (old) | 1-minimality false when units enter via closure | Added closure-aware reduction; new Prop. "closed 1-minimality" with proof; property test (40 cases) | pytest 80 passed |
| R2-2 | R2 formal | MAJOR | Def. labels | LOO-necessary units outside D* mislabelled N | New label C (coupled) | django__django-11333 record |
| R2-3 | R2 formal | MAJOR | Def. requires | Cross-file import matching spurious | Per-module scoping (A7) | django__django-13297 record |
| R2-4 | R2 formal | MINOR | Prop order, label precedence, line refs | Forward reference, overlapping X case | Reordered, X first, removed hard line numbers | LaTeX compile |
| R3-1 | R3 eng. | MAJOR | Decomposition | Hunks with offset line numbers mis-applied | Pre-image location like `git apply`; all 1,676 jobs + 306 gold apply | script check |
| R3-2 | R3 eng. | MAJOR | HPC | `sbatch --export` split SEEDS=11,22 | Separate seed-22 jobs; guard in fleet.py | jobs.jsonl note |
| R3-3 | R3 eng. | MINOR | Oracle | locale-gen re-run per test run | One-time setup per container (injection run onward); semantics unchanged | oracle smoke |
| R5-1 | R5 rev. A (novelty) | MAJOR | Related work | Missing comparison with patch/test-case minimisation literature beyond ddmin | Covered by delta debugging family; HDD cited | Text check |
| R5-2 | R5 rev. B (rigour) | MAJOR | RQ1 | Aux-file finding confounded by scaffold version | Reported by scaffold version; not attributed to models | rq1_summary.json |
| R5-3 | R5 rev. C (clarity) | MINOR | Intro | MCC phrase ambiguous ("at most") | Rewrite with both values | Text check |
