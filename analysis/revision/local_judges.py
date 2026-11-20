"""v2 revision (A16): score the larger, locally run LLM judges on RQ2 with the same metric code.

Inputs: results/processed/llm/local_edits.csv (analysis/llm_judges.py --tag local --glob ...),
        results/processed/llm/full_edits.csv (HPC judges), results/processed/rq234/rq2_agent_source_units.csv.
Rows are computed (a) as in Table tab:comparisons (seed vote >= 0.5; the local judges have one seed)
and (b) on seed 11 only for every judge, which is the like-for-like comparison.
Output: results/processed/revision/local_judges.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
from rq234 import boot_metric  # noqa: E402
from stats import binary_metrics  # noqa: E402

KEY = ["instance_id", "label", "uid"]


def score(a: pd.DataFrame, le: pd.DataFrame, source: str, variant: str) -> list[dict]:
    le = le[le.parsed].copy()
    le["needed_f"] = le.needed.astype(float)
    rows = []
    for m, g in le.groupby("model"):
        v = g.groupby(KEY).needed_f.mean().reset_index()
        d = a.merge(v, on=KEY, how="inner")
        d["pred"] = d.needed_f >= 0.5
        mu = binary_metrics(~d.needed.values, ~d.pred.values)
        mc = binary_metrics(d.needed.values, d.pred.values)
        d["ut"], d["up"] = ~d.needed, ~d.pred
        _, flo, fhi = boot_metric(d, "ut", "up", "f1")
        _, mlo, mhi = boot_metric(d, "needed", "pred", "mcc")
        nl = d[d.needed & ~d.in_gold_file]
        rows.append({"source": source, "variant": variant, "model": m, "seeds": int(g.seed.nunique()),
                     "n": len(d), "coverage": len(d) / len(a), "precision": mu["precision"],
                     "recall": mu["recall"], "f1": mu["f1"], "f1_lo": flo, "f1_hi": fhi,
                     "mcc": mc["mcc"], "mcc_lo": mlo, "mcc_hi": mhi,
                     "nonlocal_needed_retention": float(nl.pred.mean()) if len(nl) else np.nan})
    return rows


def main() -> int:
    a = pd.read_csv(ROOT / "results/processed/rq234/rq2_agent_source_units.csv")
    a["needed"] = a.needed.astype(bool)
    a["in_gold_file"] = a.in_gold_file.astype(bool)
    hpc = pd.read_csv(ROOT / "results/processed/llm/full_edits.csv")
    loc = pd.read_csv(ROOT / "results/processed/llm/local_edits.csv")
    rows = (score(a, hpc, "hpc", "vote") + score(a, hpc[hpc.seed == 11], "hpc", "seed11")
            + score(a, loc, "local", "vote"))
    out = pd.DataFrame(rows)
    (ROOT / "results/processed/revision").mkdir(parents=True, exist_ok=True)
    out.to_csv(ROOT / "results/processed/revision/local_judges.csv", index=False)
    print(out.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
