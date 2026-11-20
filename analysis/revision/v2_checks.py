"""v2 revision analyses (no new execution; reads records and processed tables).

A. Prespecified decision rules (evaluation-plan.md): H2 (RQ1) and H3 (RQ2).
B. Reduction ablations recorded with every multi-unit patch (RQ4 of the brief):
   configurations queried, invalid program runs, witness agreement.
C. Code-alignment facts: base outcomes in the triage records; direct vs transitive
   add-back closure in all envelope-regression records.
D. Structural characterization of removable vs retained source units (deterministic
   rules on the unit's changed lines; reproducible, not a manual coding), plus a
   seeded stratified sample of removable units for independent manual coding.

Outputs (results/processed/revision/): v2_checks.json, v2_ablation.csv,
v2_unit_structure.csv, manual_coding_sample.csv
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis" / "revision"))
from exhaustive_audit import _patch_text  # noqa: E402

from shift.data.repos import load_dataset, read_file  # noqa: E402
from shift.patch.edits import decompose  # noqa: E402

OUT = ROOT / "results/processed/revision"
REC = ROOT / "results/raw/shift/main/records"
SEED = 2026


def records():
    for p in sorted(REC.glob("*.json")):
        r = json.loads(p.read_text())
        if r["status"] == "ok":
            yield p.stem, r


def closure(s, req):
    s, todo = set(s), list(s)
    while todo:
        for b in req.get(todo.pop(), ()):
            if b not in s:
                s.add(b)
                todo.append(b)
    return s


# ----------------------------------------------------------------------------- A
def hypotheses() -> dict:
    rq1 = json.loads((ROOT / "results/processed/rq1/rq1_summary.json").read_text())
    n, thr = rq1["n_systems"], int(np.ceil(2 * rq1["n_systems"] / 3))
    h2 = {}
    for m in ["n_src_files", "src_blocks", "src_churn", "dispersion", "n_aux_files", "n_test_files"]:
        g, l = rq1[m]["sig_greater"], rq1[m]["sig_less"]
        h2[m] = {"greater": g, "less": l, "threshold": thr, "supported": max(g, l) >= thr,
                 "direction": "agent>reference" if g >= thr else ("agent<reference" if l >= thr else None)}
    s = json.loads((ROOT / "results/processed/rq234/summary.json").read_text())
    px = {p["proxy"]: p for p in s["rq2"]["proxies"]}
    best_llm = max(p["unneeded_f1"] for k, p in px.items() if k.startswith("llm_"))
    h3 = {}
    for k in ["p_gold_file", "p_issue", "p_dep1"]:
        p = px[k]
        h3[k] = {"nonlocal_needed_retention": p["nonlocal_needed_retention"],
                 "retention_below_0.5": p["nonlocal_needed_retention"] < 0.5,
                 "unneeded_f1": p["unneeded_f1"], "best_llm_f1": best_llm,
                 "f1_below_best_llm": p["unneeded_f1"] < best_llm}
        h3[k]["both"] = h3[k]["retention_below_0.5"] and h3[k]["f1_below_best_llm"]
    return {"H2": h2, "H2_threshold": f"{thr}/{n}", "H3": h3,
            "H3_supported_all_location_proxies": all(v["both"] for v in h3.values()),
            "H3_note": "SHIFT's own F1 is 1 by construction (it defines the labels), so the "
                       "'or SHIFT's' clause is vacuous; the informative comparison is the best LLM judge."}


# ----------------------------------------------------------------------------- B
def ablations() -> tuple[pd.DataFrame, dict]:
    rows = []
    for name, r in records():
        ab = r.get("ablations")
        ids = [u["uid"] for u in r["units"]]
        if not ab or len(ids) < 2:
            continue
        req = {a: set(b) for a, b in (r.get("requires") or {}).items()}
        D = sorted(r["minimal"])
        row = {"record": name, "n_units": len(ids), "has_requires": bool(req),
               "shift_witness": len(D), "shift_calls": r["oracle_calls"],
               "shift_precheck": r["precheck_rejections"]}
        for k in ["plain_ddmin", "precheck_only", "closure_only"]:
            a = ab[k]
            row[f"{k}_configs"] = a["configs"]
            row[f"{k}_runs"] = a["oracle_calls"]
            row[f"{k}_invalid_runs"] = a["invalid_oracle_runs"]
            row[f"{k}_size"] = len(a["minimal"])
            row[f"{k}_same_as_shift"] = sorted(a["minimal"]) == D
            row[f"{k}_closed"] = closure(a["minimal"], req) == set(a["minimal"])
        row["loo_runs"] = ab["loo_only"]["oracle_calls"]
        row["loo_retained"] = len(ab["loo_only"]["necessary"])
        if "exhaustive" in ab:
            row["exhaustive_runs"] = ab["exhaustive"]["oracle_calls"]
        rows.append(row)
    A = pd.DataFrame(rows)
    dep = A[A.has_requires]
    summ = {"n_multi": len(A), "n_with_requires": len(dep)}
    for sub, D in [("all", A), ("with_requires", dep)]:
        for k in ["plain_ddmin", "precheck_only", "closure_only"]:
            summ[f"{sub}_{k}_runs_sum"] = int(D[f"{k}_runs"].sum())
            summ[f"{sub}_{k}_invalid_sum"] = int(D[f"{k}_invalid_runs"].sum())
            summ[f"{sub}_{k}_patches_with_invalid"] = int((D[f"{k}_invalid_runs"] > 0).sum())
            summ[f"{sub}_{k}_same_as_shift"] = int(D[f"{k}_same_as_shift"].sum())
            summ[f"{sub}_{k}_not_closed"] = int((~D[f"{k}_closed"]).sum())
            summ[f"{sub}_{k}_mean_size"] = float(D[f"{k}_size"].mean())
        summ[f"{sub}_loo_runs_sum"] = int(D.loo_runs.sum())
        summ[f"{sub}_shift_witness_mean"] = float(D.shift_witness.mean())
        summ[f"{sub}_loo_retained_mean"] = float(D.loo_retained.mean())
        summ[f"{sub}_loo_retained_gt_witness"] = int((D.loo_retained > D.shift_witness).sum())
    # paired relative saving of dependency-aware reduction against plain ddmin
    d = dep.plain_ddmin_runs - dep.closure_only_runs
    summ["with_requires_closure_saving_median"] = float(d.median())
    summ["with_requires_closure_fewer"] = int((d > 0).sum())
    summ["with_requires_closure_more"] = int((d < 0).sum())
    return A, summ


# ----------------------------------------------------------------------------- C
def alignment() -> dict:
    base, base_pres, regress, differ = Counter(), Counter(), 0, 0
    pres_inst = set()
    for _, r in records():
        b = next(x for x in r["runs"] if x["cfg"] == [])
        base[b["outcome"]] += 1
        if b["n_fail_pres"] > 0:
            base_pres["records"] += 1
            pres_inst.add(r["instance_id"])
        env = r.get("envelope") or {}
        if env.get("status") == "regression":
            regress += 1
            req = {a: set(v) for a, v in (r.get("requires") or {}).items()}
            m = set(r["minimal"])
            for u in (x["uid"] for x in r["units"]):
                if u not in m and m | {u} | req.get(u, set()) != closure(m | {u}, req):
                    differ += 1
    return {"base_outcomes": dict(base), "base_pres_fail_records": base_pres["records"],
            "base_pres_fail_instances": sorted(pres_inst), "regression_records": regress,
            "addback_direct_vs_transitive_differences": differ}


# ----------------------------------------------------------------------------- D
_CTRL = re.compile(r"^(if |elif |else\b|try\b|except\b|finally\b|raise\b|assert\b|return\b.*\bif\b)")


def _clean(lines):
    return [l.strip() for l in lines if l.strip()]


def classify(unit) -> str:
    ch = _clean(unit.removed) + _clean(unit.added)
    if not ch:
        return "whitespace"
    if all(l.startswith("#") or l[:3] in ('"""', "'''") or l.startswith(('"', "'")) for l in ch):
        return "comment_or_docstring"
    if all(l.startswith(("import ", "from ")) for l in ch):
        return "import"
    if any(_CTRL.match(l) for l in _clean(unit.added)):
        return "adds_branch_or_exception"
    return "other_code"


def _sim(a, b) -> float:
    a, b = "\n".join(_clean(a)), "\n".join(_clean(b))
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def unit_structure() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = load_dataset()
    U = pd.read_csv(ROOT / "results/processed/rq234/units.csv")
    U = U[(U.kind == "source") & U.shift_label.isin(list("NJCU"))]
    rows = []
    for (iid, label), g in U.groupby(["instance_id", "label"]):
        patch = _patch_text(iid, label)
        inst = df.loc[iid]
        dp = decompose(patch, inst["repo"], lambda p: read_file(inst["repo"], inst["base_commit"], p))
        by = {u.uid: u for u in dp.units}
        retained = [by[x] for x in g[g.shift_label.isin(["N", "J"])].uid if x in by]
        for _, r in g.iterrows():
            u = by.get(r.uid)
            if u is None:
                continue
            same_file = [v for v in retained if v.path == u.path and v.uid != u.uid]
            near = min((abs(v.start - u.start) for v in same_file), default=None)
            sim = max((_sim(u.added, v.added) for v in retained if v.uid != u.uid), default=0.0)
            rows.append({"instance_id": iid, "label": label, "agent": label != "gold", "uid": r.uid,
                         "path": u.path, "role": r.shift_label, "removable": r.shift_label in ("C", "U"),
                         "category": classify(u), "added": len(_clean(u.added)), "removed": len(_clean(u.removed)),
                         "in_reference_file": bool(r.in_gold_file),
                         "same_file_as_retained": bool(same_file),
                         "lines_to_retained": near, "max_similarity_to_retained": round(sim, 3),
                         "diff": "\n".join(["- " + l for l in u.removed] + ["+ " + l for l in u.added])[:4000]})
    S = pd.DataFrame(rows)
    # seeded stratified sample of removable units for manual coding: agent/reference x category
    rem = S[S.removable]
    rng = np.random.default_rng(SEED)
    parts = []
    for agent, n in [(True, 100), (False, 50)]:
        pool = rem[rem.agent == agent]
        w = pool.groupby("category").size()
        quota = (w / w.sum() * n).round().astype(int).clip(lower=min(3, n))
        for cat, q in quota.items():
            c = pool[pool.category == cat]
            parts.append(c.iloc[rng.permutation(len(c))[:q]])
    sample = pd.concat(parts).sample(frac=1, random_state=SEED).reset_index(drop=True)
    sample.insert(0, "item", range(1, len(sample) + 1))
    for col in ["code_mechanism", "code_value_beyond_tests", "coder", "notes"]:
        sample[col] = ""
    return S, sample


def structure_summary(S: pd.DataFrame) -> dict:
    out = {}
    for who, D in [("agent", S[S.agent]), ("reference", S[~S.agent])]:
        for rm, E in [("removable", D[D.removable]), ("retained", D[~D.removable])]:
            k = f"{who}_{rm}"
            out[k + "_n"] = len(E)
            for c, v in E.category.value_counts(normalize=True).items():
                out[f"{k}_{c}"] = round(float(v), 4)
            out[k + "_same_file_as_retained"] = round(float(E.same_file_as_retained.mean()), 4)
            out[k + "_within_20_lines_of_retained"] = round(float((E.lines_to_retained <= 20).mean()), 4)
            out[k + "_similar_to_retained_0.6"] = round(float((E.max_similarity_to_retained >= 0.6).mean()), 4)
            out[k + "_median_changed_lines"] = float((E.added + E.removed).median())
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"hypotheses": hypotheses()}
    A, res["ablation"] = ablations()
    A.to_csv(OUT / "v2_ablation.csv", index=False)
    res["alignment"] = alignment()
    S, sample = unit_structure()
    S.drop(columns=["diff"]).to_csv(OUT / "v2_unit_structure.csv", index=False)
    sample.to_csv(OUT / "manual_coding_sample.csv", index=False)
    res["structure"] = structure_summary(S)
    res["manual_sample"] = {"n": len(sample), "agent": int(sample.agent.sum()), "seed": SEED}
    (OUT / "v2_checks.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
