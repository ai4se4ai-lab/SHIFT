"""RQ2 (necessity + proxies + LLM judges), RQ3 (envelope, injection), RQ4 (cost).

Outputs to results/processed/rq234/: units.csv, patches.csv, rq2_*.csv, rq3_*.csv, rq4_*.csv, summary.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shift_records import load_records, patch_table, unit_table  # noqa: E402
from stats import binary_metrics, fast_cluster_bootstrap_ratio  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/processed/rq234"


def boot_metric(df: pd.DataFrame, truth: str, pred: str, metric: str, n: int = 2000, seed: int = 2026):
    """Instance-cluster bootstrap of a confusion-matrix metric (vectorised over resamples)."""
    t = df[truth].astype(bool).values
    p = df[pred].astype(bool).values
    g = pd.DataFrame({"c": df.instance_id.values, "tp": t & p, "fp": ~t & p, "fn": t & ~p, "tn": ~t & ~p}
                     ).groupby("c").sum()
    est = binary_metrics(t, p)[metric]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(g), size=(n, len(g)))
    tp, fp, fn, tn = (g[k].values[idx].sum(1).astype(float) for k in ("tp", "fp", "fn", "tn"))
    with np.errstate(invalid="ignore", divide="ignore"):
        prec, rec = tp / (tp + fp), tp / (tp + fn)
        vals = {"f1": 2 * prec * rec / (prec + rec), "precision": prec, "recall": rec,
                "mcc": (tp * tn - fp * fn) / np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))}[metric]
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return est, lo, hi


def rq2(units: pd.DataFrame, llm_tag: str | None) -> dict:
    u = units[units.shift_label != "X"].copy()
    u["agent"] = u.label != "gold"
    u["unneeded"] = ~u.needed
    s: dict = {}
    # label distribution
    for who, g in u.groupby("agent"):
        k = "agent" if who else "gold"
        s[f"{k}_units"] = len(g)
        s[f"{k}_patches"] = int(g.groupby(["label", "instance_id"]).ngroups)
        for lab in "NJUC":
            est, lo, hi = fast_cluster_bootstrap_ratio((g.shift_label == lab).astype(int), pd.Series(1, index=g.index),
                                                        g.instance_id)
            s[f"{k}_share_{lab}"] = [est, lo, hi]
        # patches with >= 1 unneeded unit
        pp = g.groupby(["label", "instance_id"]).unneeded.any().reset_index()
        est, lo, hi = fast_cluster_bootstrap_ratio(pp.unneeded.astype(int), pd.Series(1, index=pp.index), pp.instance_id)
        s[f"{k}_patches_with_unneeded"] = [est, lo, hi]
        for kind in ("source", "test", "aux"):
            gk = g[g.kind == kind]
            s[f"{k}_{kind}_units"] = len(gk)
            s[f"{k}_{kind}_unneeded_share"] = float(gk.unneeded.mean()) if len(gk) else None
    per_sys = u.groupby("label").agg(units=("uid", "size"), patches=("instance_id", "nunique"),
                                     N=("shift_label", lambda x: (x == "N").mean()),
                                     J=("shift_label", lambda x: (x == "J").mean()),
                                     U=("shift_label", lambda x: (x == "U").mean()),
                                     src_U=("unneeded", lambda x: float(x[u.loc[x.index, "kind"] == "source"].mean())
                                            if (u.loc[x.index, "kind"] == "source").any() else np.nan),
                                     nonlocal_needed=("needed", lambda x: int((x & ~u.loc[x.index, "in_gold_file"]
                                                                               & (u.loc[x.index, "kind"] == "source")).sum())),
                                     ).reset_index()
    per_sys.to_csv(OUT / "rq2_per_system.csv", index=False)

    # Proxies predicting NEEDED (agent source units only: proxies are about code locations)
    a = u[u.agent & (u.kind == "source")].copy()
    a["p_gold_file"] = a.in_gold_file
    a["p_issue"] = a.issue_mentions_file
    a["p_dep1"] = a.gold_dist.fillna(99) <= 1
    a["p_all"] = True
    proxies = ["p_gold_file", "p_issue", "p_dep1", "p_all"]
    if llm_tag:
        lf = ROOT / f"results/processed/llm/{llm_tag}_edits.csv"
        if lf.exists():
            le = pd.read_csv(lf)
            le = le[le.parsed]
            le["needed_f"] = le.needed.astype(float)
            vote = le.groupby(["model", "instance_id", "label", "uid"]).needed_f.mean().reset_index()
            for m, g in vote.groupby("model"):
                col = f"llm_{m}"
                g = g.assign(**{col: g.needed_f >= 0.5})[["instance_id", "label", "uid", col]]
                a = a.merge(g, on=["instance_id", "label", "uid"], how="left")
                proxies.append(col)
            # LLM self-consistency across seeds
            cons = le.groupby(["model", "instance_id", "label", "uid"]).needed.agg(lambda x: x.nunique() == 1)
            s["llm_seed_agreement"] = cons.groupby("model").mean().to_dict()
            s["llm_parse_rate"] = pd.read_csv(ROOT / f"results/processed/llm/{llm_tag}_gens.csv").groupby("model").ok.mean().to_dict()
    rows = []
    for p in proxies:
        d = a.dropna(subset=[p]).copy()
        d[p] = d[p].astype(bool)
        m_needed = binary_metrics(d.needed.values, d[p].values)
        m_unneeded = binary_metrics(~d.needed.values, ~d[p].values)
        nl = d[d.needed & ~d.in_gold_file]
        rows.append({"proxy": p, "n": len(d), "coverage": len(d) / len(a),
                     "unneeded_precision": m_unneeded["precision"], "unneeded_recall": m_unneeded["recall"],
                     "unneeded_f1": m_unneeded["f1"], "mcc": m_needed["mcc"],
                     "needed_recall": m_needed["recall"], "needed_precision": m_needed["precision"],
                     "nonlocal_needed_n": len(nl),
                     "nonlocal_needed_retention": float(nl[p].mean()) if len(nl) else np.nan})
        if p != "p_all":
            d["unneeded_true"], d["unneeded_pred"] = ~d.needed, ~d[p]
            est, lo, hi = boot_metric(d, "unneeded_true", "unneeded_pred", "f1")
            rows[-1]["unneeded_f1_ci"] = [lo, hi]
            est, lo, hi = boot_metric(d, "needed", p, "mcc")
            rows[-1]["mcc_ci"] = [lo, hi]
    pr = pd.DataFrame(rows)
    pr.to_csv(OUT / "rq2_proxies.csv", index=False)
    s["proxies"] = pr.to_dict("records")
    s["agent_source_units"] = len(a)
    s["agent_source_needed_outside_gold_files"] = int((a.needed & ~a.in_gold_file).sum())
    s["agent_source_unneeded_inside_gold_files"] = int((~a.needed & a.in_gold_file).sum())
    a.to_csv(OUT / "rq2_agent_source_units.csv", index=False)
    return s


def rq2_informed(units: pd.DataFrame) -> list[dict]:
    """Exploratory (A8): judges given goal tests + test patch vs. the same judges without, seed 11 only."""
    u = units[(units.shift_label != "X") & (units.label != "gold") & (units.kind == "source")].copy()
    out = []
    for tag, prompts in (("full", "prompts.jsonl"), ("informed", "prompts_informed.jsonl")):
        f = ROOT / f"results/processed/llm/{tag}_edits.csv"
        if not f.exists():
            continue
        le = pd.read_csv(f)
        le = le[(le.seed == 11) & le.parsed]
        for m, g in le.groupby("model"):
            d = u.merge(g[["instance_id", "label", "uid", "needed"]].rename(columns={"needed": "pred"}),
                        on=["instance_id", "label", "uid"], how="inner")
            d["pred"] = d.pred.astype(bool)
            mu = binary_metrics(~d.needed.values, ~d.pred.values)
            mc = binary_metrics(d.needed.values, d.pred.values)
            out.append({"variant": tag, "model": m, "n": len(d), "precision": mu["precision"], "recall": mu["recall"],
                        "f1": mu["f1"], "mcc": mc["mcc"]})
    pd.DataFrame(out).to_csv(OUT / "rq2_informed.csv", index=False)
    return out


def rq3(patches: pd.DataFrame, units: pd.DataFrame, inj: pd.DataFrame | None) -> dict:
    s: dict = {}
    p = patches[(patches.status == "ok") & ~patches.label.str.startswith("inj-")]
    e = p[p.env_status.isin(["clean", "regression"])]
    s["envelope_patches"] = len(e)
    s["envelope_empty"] = int((p.env_status == "empty").sum())
    s["envelope_tests_median"] = float(e.env_tests.median()) if len(e) else None
    for who, g in e.groupby(e.label == "gold"):
        k = "gold" if who else "agent"
        est, lo, hi = fast_cluster_bootstrap_ratio((g.env_status == "regression").astype(int), pd.Series(1, index=g.index), g.instance_id)
        s[f"{k}_regression_rate"] = [est, lo, hi]
        s[f"{k}_regression_n"] = int((g.env_status == "regression").sum())
        s[f"{k}_regression_tied_to_minimal"] = int((g.env_regressions_in_minimal > 0).sum())
        s[f"{k}_harmful_unit_patches"] = int((g.env_harmful_units > 0).sum())
    e.groupby("label").agg(n=("instance_id", "size"), regression=("env_status", lambda x: (x == "regression").mean()),
                           tests=("env_tests", "median")).to_csv(OUT / "rq3_per_system.csv")
    if inj is not None and len(inj):
        rows = []
        for _, r in inj.iterrows():
            kind = r.label.split("-", 1)[1]
            if r.status == "not_valid":
                outcome = "official_tests"          # caught by F2P/P2P: full patch no longer valid
            elif r.status != "ok":
                outcome = "error"
            else:
                iu = units[(units.label == r.label) & (units.instance_id == r.instance_id) & (units.path == r.inj_target)]
                lab = iu.shift_label.iloc[0] if len(iu) else "?"
                harm = bool(iu.harmful.iloc[0]) if len(iu) else False
                outcome = "envelope_H" if harm else ("unneeded_U" if lab == "U" else f"label_{lab}")
            rows.append({"instance_id": r.instance_id, "kind": kind, "op": r.inj_op, "outcome": outcome,
                         "env_status": r.env_status})
        d = pd.DataFrame(rows)
        d.to_csv(OUT / "rq3_injection.csv", index=False)
        tab = d.groupby(["kind", "outcome"]).size().unstack(fill_value=0)
        tab.to_csv(OUT / "rq3_injection_table.csv")
        s["injection_table"] = tab.to_dict()
        for kind, g in d[d.outcome != "error"].groupby("kind"):
            det_off = (g.outcome == "official_tests").astype(int)
            det_env = g.outcome.isin(["official_tests", "envelope_H"]).astype(int)
            s[f"inj_{kind}_n"] = len(g)
            s[f"inj_{kind}_official"] = list(fast_cluster_bootstrap_ratio(det_off, pd.Series(1, index=g.index), g.instance_id))
            s[f"inj_{kind}_with_envelope"] = list(fast_cluster_bootstrap_ratio(det_env, pd.Series(1, index=g.index), g.instance_id))
            gain = det_env - det_off
            s[f"inj_{kind}_gain"] = list(fast_cluster_bootstrap_ratio(gain, pd.Series(1, index=g.index), g.instance_id))
            s[f"inj_{kind}_labelled_U"] = float((g.outcome == "unneeded_U").mean())
        s["inj_semantic_by_op"] = d[d.kind == "semantic"].groupby("op").outcome.value_counts().unstack(fill_value=0).to_dict()
    return s


def rq4(patches: pd.DataFrame) -> dict:
    p = patches[(patches.status == "ok") & ~patches.label.str.startswith("inj-")].copy()
    s: dict = {"n": len(p)}
    s["oracle_calls_median"] = float(p.oracle_calls.median())
    s["oracle_calls_p90"] = float(p.oracle_calls.quantile(.9))
    s["wall_median_s"] = float(p.wall_seconds.median())
    s["oracle_seconds_median"] = float(p.oracle_seconds.median())
    s["precheck_rejections_total"] = int(p.precheck_rejections.sum())
    s["anomalies"] = int((p.anomalies > 0).sum())
    multi = p[p.n_units >= 3]
    s["multi_n"] = len(multi)
    for c in ("abl_plain_calls", "abl_closure_calls", "abl_precheck_calls", "abl_loo_calls", "abl_exh_calls"):
        s[c + "_sum_multi"] = float(multi[c].sum())
    s["abl_plain_invalid_runs_sum"] = float(p.abl_plain_invalid_runs.sum())
    ex = p.dropna(subset=["abl_exh_minsize"])
    s["exhaustive_n"] = len(ex)
    s["ddmin_matches_exhaustive_size"] = float((ex.minimal_size == ex.abl_exh_minsize).mean()) if len(ex) else None
    s["ddmin_larger_than_min"] = int((ex.minimal_size > ex.abl_exh_minsize).sum())
    s["loo_vs_shift_needed_gap"] = int(((p.n_N + p.n_J) - p.abl_loo_necessary).clip(lower=0).sum())
    s["patches_with_J"] = int((p.n_J > 0).sum())
    by_units = p.groupby(pd.cut(p.n_units, [0, 1, 2, 4, 8, 16, 1000])).agg(
        n=("oracle_calls", "size"), calls=("oracle_calls", "median"), wall=("wall_seconds", "median"))
    by_units.to_csv(OUT / "rq4_by_units.csv")
    s["by_units"] = {str(k): v for k, v in by_units.to_dict("index").items()}
    return s


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main")
    ap.add_argument("--inj-run", default="injection")
    ap.add_argument("--llm-tag", default="full")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    recs = load_records(a.run)
    units = unit_table(recs)
    patches = patch_table(recs)
    inj_recs = load_records(a.inj_run) if (ROOT / "results/raw/shift" / a.inj_run).exists() else []
    inj_units = unit_table(inj_recs) if inj_recs else pd.DataFrame()
    inj_p = patch_table(inj_recs) if inj_recs else None
    units.to_csv(OUT / "units.csv", index=False)
    patches.to_csv(OUT / "patches.csv", index=False)
    s = {"n_records": len(recs), "status": patches.status.value_counts().to_dict()}
    s["rq2"] = rq2(units, a.llm_tag)
    s["rq2"]["informed"] = rq2_informed(units)
    s["rq3"] = rq3(patches, inj_units, inj_p)
    s["rq4"] = rq4(patches)
    (OUT / "summary.json").write_text(json.dumps(s, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(json.dumps(s, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
