"""RQ1 statistics: agent vs gold edit footprints (paired by instance), exploration footprints,
and association of footprint with resolution. Writes CSV + LaTeX-ready numbers."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from stats import holm, paired_wilcoxon

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "results/processed/rq1"
METRICS = ["n_src_files", "src_blocks", "src_churn", "n_aux_files", "n_test_files", "dispersion"]


def main() -> int:
    ef = pd.read_csv(IN / "edit_footprint.csv")
    ef = ef[~ef.get("empty_patch", False).fillna(False).astype(bool)]
    gold = ef[ef.system == "gold"].set_index("instance_id")
    agents = ef[ef.system != "gold"]
    rows = []
    for s, g in agents.groupby("system"):
        g = g.set_index("instance_id")
        common = g.index.intersection(gold.index)
        rec = {"system": s, "n": len(common), "resolve_rate": g.resolved.mean()}
        for m in METRICS:
            d = (g.loc[common, m] - gold.loc[common, m]).astype(float)
            p, r = paired_wilcoxon(d.values)
            rec.update({f"{m}_agent_mean": g.loc[common, m].mean(), f"{m}_gold_mean": gold.loc[common, m].mean(),
                        f"{m}_agent_median": g.loc[common, m].median(), f"{m}_p": p, f"{m}_r": r,
                        f"{m}_share_greater": float((d > 0).mean()), f"{m}_share_less": float((d < 0).mean())})
        rec["nonlocal_share_mean"] = g.loc[common, "nonlocal_share"].mean()
        rec["touches_gold_file"] = g.loc[common, "touches_gold_file"].mean()
        rec["divergence_mean"] = g.loc[common, "divergence"].mean()
        rec["aux_leftover_rate"] = (g.loc[common, "n_new_aux_files"] > 0).mean()
        rows.append(rec)
    res = pd.DataFrame(rows)
    res["scaffold"] = res.system.str.extract(r"_mini-v(\d+\.\d+)")[0].fillna("?")
    for m in METRICS:
        res[f"{m}_p_holm"] = holm(res[f"{m}_p"].fillna(1).tolist())
    res.to_csv(IN / "rq1_paired.csv", index=False)

    # Decision rule: H2 supported for a metric if >= 2/3 of systems show a Holm-significant
    # difference in the same direction.
    summary = {"n_systems": len(res), "n_instances": int(gold.shape[0])}
    for m in METRICS:
        sig = res[res[f"{m}_p_holm"] < 0.05]
        summary[m] = {"sig_greater": int((sig[f"{m}_r"] > 0).sum()), "sig_less": int((sig[f"{m}_r"] < 0).sum()),
                      "median_r": float(res[f"{m}_r"].median()),
                      "gold_mean": float(gold[m].mean()) if m in gold else None}

    from scipy.stats import spearmanr
    for col in ("nonlocal_share_mean", "touches_gold_file", "src_blocks_agent_mean", "aux_leftover_rate"):
        rho, p = spearmanr(res.resolve_rate, res[col])
        summary[f"spearman_resolve_vs_{col}"] = [float(rho), float(p)]
    summary["aux_by_scaffold"] = res.groupby("scaffold").agg(n=("system", "size"),
                                                           aux=("aux_leftover_rate", "mean")).reset_index().to_dict("records")
    # Decision-rule tally restricted to scaffold v2.x (aux-file handling differs across scaffold versions)
    v2 = res[res.scaffold.str.startswith("2.")]
    summary["v2_systems"] = len(v2)
    summary["v2_aux_sig_greater"] = int(((v2.n_aux_files_p_holm < 0.05) & (v2.n_aux_files_r > 0)).sum())

    # Association with resolution (exploratory): GEE logistic per pooled systems, clustered by instance.
    a = agents.dropna(subset=["src_churn", "n_src_files"]).copy()
    a["log_churn"] = np.log1p(a.src_churn)
    a["nonlocal_sh"] = a.nonlocal_share.fillna(0)
    a["resolved_i"] = a.resolved.astype(int)
    try:
        model = smf.gee("resolved_i ~ log_churn + nonlocal_sh + n_src_files + C(system)", "instance_id", a,
                        family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
        summary["gee"] = {k: {"coef": float(model.params[k]), "p": float(model.pvalues[k]),
                              "ci": [float(x) for x in model.conf_int().loc[k]]}
                          for k in ("log_churn", "nonlocal_sh", "n_src_files")}
    except Exception as e:  # reported, not hidden
        summary["gee_error"] = str(e)

    # Exploration footprint (panel with trajectories)
    xp = IN / "exploration.csv"
    if xp.exists():
        x = pd.read_csv(xp)
        summary["exploration"] = x.groupby("system").agg(
            n=("instance_id", "size"), steps_median=("steps", "median"), referenced_median=("n_referenced", "median"),
            eer_median=("eer", "median"), edited_median=("n_edited", "median"),
            resolved=("resolved", "mean")).reset_index().to_dict("records")
        x.groupby("system").agg(n=("instance_id", "size"), steps_median=("steps", "median"),
                                ref_median=("n_referenced", "median"), ref_q1=("n_referenced", lambda v: v.quantile(.25)),
                                ref_q3=("n_referenced", lambda v: v.quantile(.75)), eer_median=("eer", "median"),
                                edited_median=("n_edited", "median"), resolved=("resolved", "mean")
                                ).to_csv(IN / "rq1_exploration_summary.csv")
    (IN / "rq1_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=1, default=float)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
