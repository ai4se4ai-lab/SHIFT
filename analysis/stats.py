"""Shared statistics: cluster bootstrap, paired Wilcoxon with rank-biserial effect, Holm."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def holm(pvals: list[float]) -> list[float]:
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    m = len(p)
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return adj.tolist()


def paired_wilcoxon(diff: np.ndarray) -> tuple[float, float]:
    """(p-value, matched-pairs rank-biserial r) for paired differences (zeros dropped, Pratt off)."""
    d = np.asarray(diff, float)
    d = d[~np.isnan(d)]
    nz = d[d != 0]
    if len(nz) < 5:
        return float("nan"), float("nan")
    p = stats.wilcoxon(nz).pvalue
    ranks = stats.rankdata(np.abs(nz))
    r = (ranks[nz > 0].sum() - ranks[nz < 0].sum()) / ranks.sum()
    return float(p), float(r)


def cluster_bootstrap(df: pd.DataFrame, cluster: str, stat, n: int = 10000, seed: int = 2026,
                      alpha: float = 0.05) -> tuple[float, float, float]:
    """Point estimate and percentile CI of stat(df) resampling clusters with replacement."""
    rng = np.random.default_rng(seed)
    groups = {k: g for k, g in df.groupby(cluster)}
    keys = np.array(list(groups))
    est = stat(df)
    vals = []
    for _ in range(n):
        pick = rng.choice(keys, size=len(keys), replace=True)
        vals.append(stat(pd.concat([groups[k] for k in pick], ignore_index=True)))
    lo, hi = np.nanpercentile(vals, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(est), float(lo), float(hi)


def fast_cluster_bootstrap_ratio(num: pd.Series, den: pd.Series, clusters: pd.Series, n: int = 10000,
                                 seed: int = 2026) -> tuple[float, float, float]:
    """Bootstrap CI for sum(num)/sum(den) with resampling of clusters (vectorised)."""
    g = pd.DataFrame({"n": num.values, "d": den.values, "c": clusters.values}).groupby("c").sum()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(g), size=(n, len(g)))
    nn, dd = g["n"].values[idx].sum(1), g["d"].values[idx].sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = nn / dd
    est = g["n"].sum() / g["d"].sum() if g["d"].sum() else float("nan")
    lo, hi = np.nanpercentile(r, [2.5, 97.5])
    return float(est), float(lo), float(hi)


def binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Precision/recall/F1 for the positive class, and MCC."""
    t, p = np.asarray(y_true, bool), np.asarray(y_pred, bool)
    tp, fp = int((t & p).sum()), int((~t & p).sum())
    fn, tn = int((t & ~p).sum()), int((~t & ~p).sum())
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if prec == prec and rec == rec and prec + rec else float("nan")
    den = np.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / den if den else float("nan")
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": prec, "recall": rec, "f1": f1, "mcc": mcc}
