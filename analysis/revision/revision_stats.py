"""Revision v1 statistics (no new executions; reads processed tables only).

A. Agent vs reference removability of conclusive source units:
   pooled difference and instance-matched per-system differences (joint instance-cluster
   bootstrap, 10,000 resamples, seed 2026), with Bonferroni-adjusted intervals across systems.
B. Informed vs uninformed LLM judges, matched on seed 11 and on units parsed in both
   variants; paired instance-cluster bootstrap of the MCC difference.
C. RQ3 paired detection: exact McNemar test (official vs official + envelope), per operator.
D. RQ4 per-patch cost distributions by unit-count bin (for the cost figure).
E. Recomputation of manuscript counts used as a consistency check.

Inputs : results/processed/rq234/{units,patches,rq3_injection}.csv,
         results/processed/llm/{full,informed}_edits.csv, results/processed/rq1/*.csv
Output : results/processed/revision/revision_stats.json and CSV tables
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
from stats import binary_metrics  # noqa: E402

P = ROOT / "results/processed"
OUT = P / "revision"
B, SEED = 10_000, 2026

SHORT = {
    "20250720_mini-v0.0.0-gpt-4o-2024-11-20": "GPT-4o",
    "20250803_mini-v1.0.0_qwen2-5-coder-32b-instruct": "Qwen2.5-Coder 32B",
    "20260217_mini-v2.0.0_claude-4-6-opus": "Claude 4.6 Opus",
    "20260217_mini-v2.0.0_deepseek-3-2-high": "DeepSeek V3.2 high",
    "20260217_mini-v2.0.0_gemini-3-pro-high": "Gemini 3 Pro high",
    "20260217_mini-v2.0.0_gpt-5-2-high": "GPT-5.2 high",
    "20260217_mini-v2.0.0_gpt-5-mini": "GPT-5 mini",
    "20260217_mini-v2.0.0_kimi-k2-5-high": "Kimi K2.5 high",
}


def _agg(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Per-instance numerator (removable) and denominator (conclusive) counts."""
    return df.groupby("instance_id").agg(**{f"{key}_n": ("removable", "sum"), f"{key}_d": ("removable", "size")})


def boot_ratio_diff(g: pd.DataFrame, a: str, b: str, alphas=(0.05,), rng=None):
    """sum(a_n)/sum(a_d) - sum(b_n)/sum(b_d), resampling instances (rows of g)."""
    rng = rng or np.random.default_rng(SEED)
    an, ad, bn, bd = (g[c].to_numpy(float) for c in (f"{a}_n", f"{a}_d", f"{b}_n", f"{b}_d"))
    idx = rng.integers(0, len(g), size=(B, len(g)))
    ra = an[idx].sum(1) / ad[idx].sum(1)
    rb = bn[idx].sum(1) / bd[idx].sum(1)
    d = ra - rb
    est = an.sum() / ad.sum() - bn.sum() / bd.sum()
    out = {"est": est, "ra": an.sum() / ad.sum(), "rb": bn.sum() / bd.sum(), "n_instances": len(g)}
    for al in alphas:
        lo, hi = np.nanpercentile(d, [100 * al / 2, 100 * (1 - al / 2)])
        out[f"ci_{al:g}"] = [float(lo), float(hi)]
    out["p_boot"] = float(min(1.0, 2 * min((d <= 0).mean(), (d >= 0).mean())))
    return out


def part_a(units: pd.DataFrame) -> dict:
    u = units[(units.shift_label != "X") & (units.kind == "source")].copy()
    u["removable"] = u.shift_label.isin(["U", "C"])
    ref = _agg(u[u.label == "gold"], "ref")
    res: dict = {}
    ag = _agg(u[u.label != "gold"], "ag")
    g = ref.join(ag, how="left").fillna(0.0)
    g = g[(g.ref_d > 0)]
    # pooled: all agent units vs all reference units, resampling instances jointly
    # pooled: all agent units vs all reference units (unmatched; instances resampled jointly)
    res["pooled_unmatched"] = boot_ratio_diff(g, "ag", "ref")
    # pooled, matched: reference units restricted to instances with at least one agent unit
    res["pooled_matched"] = boot_ratio_diff(g[g.ag_d > 0], "ag", "ref")
    # per system, matched to the instances that system resolved (instance difficulty controlled)
    rows = []
    k = len(SHORT)
    for lab, name in SHORT.items():
        a = _agg(u[u.label == lab], "ag")
        m = ref.join(a, how="inner")
        m = m[(m.ag_d > 0) & (m.ref_d > 0)]
        r = boot_ratio_diff(m, "ag", "ref", alphas=(0.05, 0.05 / k))
        rows.append({"system": name, "label": lab, "n_instances": r["n_instances"],
                     "agent_units": int(m.ag_d.sum()), "ref_units": int(m.ref_d.sum()),
                     "agent_share": r["ra"], "ref_share_matched": r["rb"], "diff": r["est"],
                     "ci_lo": r["ci_0.05"][0], "ci_hi": r["ci_0.05"][1],
                     "ci_bonf_lo": r[f"ci_{0.05 / k:g}"][0], "ci_bonf_hi": r[f"ci_{0.05 / k:g}"][1],
                     "p_boot": r["p_boot"]})
    t = pd.DataFrame(rows)
    t["p_holm"] = _holm(t.p_boot.tolist())
    t.to_csv(OUT / "rq2_agent_vs_reference_matched.csv", index=False)
    res["per_system"] = t.to_dict("records")
    # agent-only per-system shares with cluster CIs (for the figure)
    rows = []
    for lab, name in list(SHORT.items()) + [("gold", "Reference")]:
        a = _agg(u[u.label == lab], "x")
        rng = np.random.default_rng(SEED)
        idx = rng.integers(0, len(a), size=(B, len(a)))
        n, d = a.x_n.to_numpy(float), a.x_d.to_numpy(float)
        r = n[idx].sum(1) / d[idx].sum(1)
        rows.append({"system": name, "units": int(d.sum()), "instances": len(a), "share": n.sum() / d.sum(),
                     "lo": float(np.percentile(r, 2.5)), "hi": float(np.percentile(r, 97.5))})
    pd.DataFrame(rows).to_csv(OUT / "rq2_source_removable_by_system.csv", index=False)
    res["by_system_shares"] = rows
    return res


def _holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj, run = np.empty_like(p), 0.0
    for r, i in enumerate(o):
        run = max(run, min(1.0, (len(p) - r) * p[i]))
        adj[i] = run
    return adj.tolist()


def part_b(units: pd.DataFrame) -> list[dict]:
    u = units[(units.shift_label != "X") & (units.label != "gold") & (units.kind == "source")]
    preds = {}
    for tag in ("full", "informed"):
        le = pd.read_csv(P / f"llm/{tag}_edits.csv")
        le = le[(le.seed == 11) & le.parsed]
        preds[tag] = le[["model", "instance_id", "label", "uid", "needed"]].rename(columns={"needed": tag})
    m = preds["full"].merge(preds["informed"], on=["model", "instance_id", "label", "uid"])
    m = m.merge(u[["instance_id", "label", "uid", "needed"]], on=["instance_id", "label", "uid"])
    out = []
    for model, g in m.groupby("model"):
        y = g.needed.to_numpy(bool)
        fa, inf = g["full"].astype(bool).to_numpy(), g["informed"].astype(bool).to_numpy()
        mf = binary_metrics(~y, ~fa)["mcc"]
        mi = binary_metrics(~y, ~inf)["mcc"]
        inst = g.instance_id.to_numpy()
        keys, inv = np.unique(inst, return_inverse=True)
        members = [np.flatnonzero(inv == i) for i in range(len(keys))]
        rng = np.random.default_rng(SEED)
        diffs = []
        for _ in range(2000):
            pick = rng.integers(0, len(keys), len(keys))
            ix = np.concatenate([members[i] for i in pick])
            diffs.append(binary_metrics(~y[ix], ~inf[ix])["mcc"] - binary_metrics(~y[ix], ~fa[ix])["mcc"])
        lo, hi = np.nanpercentile(diffs, [2.5, 97.5])
        out.append({"model": model, "n_matched": len(g), "mcc_uninformed": mf, "mcc_informed": mi,
                    "diff": mi - mf, "ci": [float(lo), float(hi)]})
    pd.DataFrame(out).to_csv(OUT / "rq2_informed_matched.csv", index=False)
    return out


def part_c() -> dict:
    inj = pd.read_csv(P / "rq234/rq3_injection_table.csv")
    s = json.loads((P / "rq234/summary.json").read_text())["rq3"]
    by = s["inj_semantic_by_op"]
    ops = sorted(by["official_tests"])
    res = {"table": inj.to_dict("records"), "by_operator": {}}
    b = s["injection_table"]["envelope_H"]["semantic"]       # detected only with envelope
    c = 0                                                     # official-only detections: envelope adds tests
    res["mcnemar_semantic"] = {"b_envelope_only": b, "c_official_only": c,
                               "p_exact": float(stats.binomtest(b, b + c, 0.5).pvalue)}
    for op in ops:
        o, e, un = by["official_tests"][op], by["envelope_H"][op], by["unneeded_U"][op]
        n = o + e + un
        res["by_operator"][op] = {"n": n, "official": o, "envelope_extra": e, "undetected": un,
                                  "official_rate": o / n, "combined_rate": (o + e) / n}
    return res


def part_d(patches: pd.DataFrame) -> dict:
    p = patches[(patches.status == "ok") & ~patches.label.str.startswith("inj-")].copy()
    bins = [(1, 1, "1"), (2, 2, "2"), (3, 4, "3--4"), (5, 8, "5--8"), (9, 16, "9--16"), (17, 10**6, "$\\geq$17")]
    rows = []
    for lo, hi, name in bins:
        g = p[(p.n_units >= lo) & (p.n_units <= hi)]
        q = g.oracle_calls.quantile([0, .25, .5, .75, .9, 1]).tolist()
        w = g.wall_seconds.quantile([.25, .5, .75]).tolist()
        rows.append({"bin": name, "n": len(g), "calls_min": q[0], "calls_q1": q[1], "calls_med": q[2],
                     "calls_q3": q[3], "calls_p90": q[4], "calls_max": q[5],
                     "wall_q1": w[0], "wall_med": w[1], "wall_q3": w[2],
                     "units_median": float(g.n_units.median())})
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "rq4_cost_distribution.csv", index=False)
    # relation between calls and unit count (Spearman) and calls relative to n+3 (LOO + full x2 + base)
    rho = stats.spearmanr(p.n_units, p.oracle_calls)
    ratio = (p.oracle_calls / (p.n_units + 3))
    return {"bins": rows, "spearman_units_calls": [float(rho.statistic), float(rho.pvalue)],
            "calls_over_loo_floor_median": float(ratio.median()),
            "calls_over_loo_floor_p90": float(ratio.quantile(.9))}


def part_e(units: pd.DataFrame, patches: pd.DataFrame) -> dict:
    p = patches[~patches.label.str.startswith("inj-")]
    ok = p[p.status == "ok"]
    u = units
    ag = u[u.label != "gold"]
    agp = ok[ok.label != "gold"]
    src = ag[(ag.kind == "source") & (ag.shift_label != "X")]
    e = ok[ok.env_status.isin(["clean", "regression"])]
    return {
        "records": len(p), "ok": len(ok), "not_valid": int((p.status == "not_valid").sum()),
        "agent_valid_patches": len(agp), "ref_valid_patches": int((ok.label == "gold").sum()),
        "units_total": len(u), "units_X": int((u.shift_label == "X").sum()),
        "X_patches": int(ok[ok.n_X > 0].shape[0]), "X_source_units": int(((u.shift_label == "X") & (u.kind == "source")).sum()),
        "agent_source_conclusive": len(src), "agent_source_removable": int(src.shift_label.isin(["U", "C"]).sum()),
        "agent_test_units": int(((ag.kind == "test") & (ag.shift_label != "X")).sum()),
        "agent_aux_units": int(((ag.kind == "aux") & (ag.shift_label != "X")).sum()),
        "C_units": int((u.shift_label == "C").sum()), "C_patches": int((ok.n_C > 0).sum()),
        "J_units": int((u.shift_label == "J").sum()), "J_patches": int((ok.n_J > 0).sum()),
        "patches_1_unit": int((ok.n_units == 1).sum()), "patches_2_units": int((ok.n_units == 2).sum()),
        "agent_env_nonempty": int((e.label != "gold").sum()),
        "agent_env_regression": int(((e.label != "gold") & (e.env_regressions > 0)).sum()),
        "precheck_rejections": int(ok.precheck_rejections.sum()),
        "multi_unit_patches": int((ok.n_units > 1).sum()),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    units = pd.read_csv(P / "rq234/units.csv")
    patches = pd.read_csv(P / "rq234/patches.csv")
    units = units[~units.label.str.startswith("inj-")]
    s = {"A_agent_vs_reference": part_a(units), "B_informed_matched": part_b(units),
         "C_injection": part_c(), "D_cost": part_d(patches), "E_counts": part_e(units, patches)}
    (OUT / "revision_stats.json").write_text(json.dumps(s, indent=1, default=float))
    print(json.dumps(s, indent=1, default=float)[:7000])


if __name__ == "__main__":
    main()
