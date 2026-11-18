"""RQ2-RQ4 manuscript blocks (tables + macros) from results/processed/rq234/**."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from make_tex import LLM_NAMES, OPEN_W, PANEL_NAMES, ci, f, pct

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "results/processed"


def _n(x) -> str:
    return f"{int(x):,}".replace(",", "{,}")


def build(M) -> dict[str, str]:
    s = json.loads((P / "rq234/summary.json").read_text())
    units = pd.read_csv(P / "rq234/units.csv")
    patches = pd.read_csv(P / "rq234/patches.csv")
    el = pd.read_csv(P / "validated/jobs/eligibility.csv")
    ok = patches[patches.status == "ok"]
    blocks = {}

    # ---------------- panel table
    rows = []
    for key, name in PANEL_NAMES.items():
        e = el[el.label == key]
        cand = int((e.reason == "ok").sum())
        pk = patches[patches.label == key]
        valid = int((pk.status == "ok").sum())
        notvalid = int((pk.status == "not_valid").sum())
        other = int(len(pk) - valid - notvalid)
        nunits = int(units[units.label == key].shape[0])
        if key == "gold":
            rr = "--"
        else:
            rep = pd.read_csv(P / "rq1/rq1_paired.csv")
            rr = pct(rep.loc[rep.system == key, "resolve_rate"].iloc[0]) if (rep.system == key).any() else "--"
        rows.append(f"{name}{'$^\\dagger$' if name in OPEN_W else ''} & {rr} & {cand} & {valid} & {notvalid} & {other} & {_n(nunits)} \\\\")
    blocks["panel-table"] = rf"""\begin{{table}}[t]
\caption{{Execution panel. \emph{{Resolved (Verified)}}: official resolution rate on all 500 instances. \emph{{Candidates}}: officially resolved patches on the 295 validated Django and SymPy instances. \emph{{Valid}}: patches that also resolve in our environment and were triaged. \emph{{Not valid}}: patches that did not reproduce their resolution. \emph{{Other}}: flaky or erroneous runs. $^\dagger$Open weights.}}
\label{{tab:panel}}
\centering\footnotesize
\begin{{tabular}}{{lrrrrrr}}
\toprule
System & Resolved (Verified) & Candidates & Valid & Not valid & Other & Units \\
\midrule
{chr(10).join(rows)}
\bottomrule
\end{{tabular}}
\end{{table}}"""
    M["nValidPatches"] = _n(len(ok))
    M["nAgentValid"] = _n((ok.label != "gold").sum())
    M["nGoldValid"] = _n((ok.label == "gold").sum())
    M["nCandidates"] = _n((el.reason == "ok").sum())
    M["nNotValid"] = _n((patches.status == "not_valid").sum())
    M["nOtherStatus"] = _n((~patches.status.isin(["ok", "not_valid"])).sum())
    M["nUnits"] = _n(units.shape[0])

    # ---------------- RQ2 labels per system
    r2 = s["rq2"]
    u = units[units.shift_label != "X"].copy()
    lab_rows = []
    for key, name in PANEL_NAMES.items():
        g = u[u.label == key]
        if not len(g):
            continue
        src = g[g.kind == "source"]
        shares = {L: (g.shift_label == L).mean() for L in "NJCU"}
        pp = g.groupby("instance_id").apply(lambda x: (~x.needed).any(), include_groups=False)
        lab_rows.append(
            f"{name} & {g.instance_id.nunique()} & {_n(len(g))} & {pct(shares['N'])} & {pct(shares['J'])} & "
            f"{pct(shares['C'])} & {pct(shares['U'])} & {pct((~src.needed).mean()) if len(src) else '--'} & "
            f"{(g.kind != 'source').sum()} & {pct(pp.mean())} \\\\")
    blocks["rq2-label-table"] = rf"""\begin{{table}}[t]
\caption{{Counterfactual labels of the units of valid patches. \emph{{Src U}}: share of source units that are removable (\lab{{U}} or \lab{{C}}). \emph{{Non-src}}: units in test or auxiliary files. \emph{{$\geq$1 removable}}: share of patches with at least one removable unit.}}
\label{{tab:labels}}
\centering\footnotesize
\begin{{tabular}}{{lrrrrrrrrr}}
\toprule
System & Patches & Units & \lab{{N}} & \lab{{J}} & \lab{{C}} & \lab{{U}} & Src U & Non-src & $\geq$1 removable \\
\midrule
{chr(10).join(lab_rows)}
\bottomrule
\end{{tabular}}
\end{{table}}"""
    for who in ("agent", "gold"):
        W = "Agent" if who == "agent" else "Gold"
        for L in "NJCU":
            v = r2.get(f"{who}_share_{L}")
            if v:
                M[f"rqtwo{W}Share{L}"] = pct(v[0])
                M[f"rqtwo{W}Share{L}CI"] = f"[{pct(v[1])}, {pct(v[2])}]"
        v = r2.get(f"{who}_patches_with_unneeded")
        M[f"rqtwo{W}PatchesUnneeded"] = pct(v[0])
        M[f"rqtwo{W}PatchesUnneededCI"] = f"[{pct(v[1])}, {pct(v[2])}]"
        M[f"rqtwo{W}SrcUnneeded"] = pct(r2.get(f"{who}_source_unneeded_share"))
        M[f"rqtwo{W}Units"] = _n(r2.get(f"{who}_units", 0))
        M[f"rqtwo{W}Patches"] = _n(r2.get(f"{who}_patches", 0))
        M[f"rqtwo{W}AuxUnits"] = _n(r2.get(f"{who}_aux_units", 0))
        M[f"rqtwo{W}TestUnits"] = _n(r2.get(f"{who}_test_units", 0))
        M[f"rqtwo{W}AuxUnneeded"] = pct(r2.get(f"{who}_aux_unneeded_share"))
        M[f"rqtwo{W}TestUnneeded"] = pct(r2.get(f"{who}_test_unneeded_share"))
    M["rqtwoSrcUnits"] = _n(r2["agent_source_units"])
    M["rqtwoNonlocalNeeded"] = _n(r2["agent_source_needed_outside_gold_files"])
    M["rqtwoUnneededInGold"] = _n(r2["agent_source_unneeded_inside_gold_files"])
    a = pd.read_csv(P / "rq234/rq2_agent_source_units.csv")
    M["rqtwoSrcUnneededN"] = _n((~a.needed).sum())
    M["rqtwoSrcNeededN"] = _n(a.needed.sum())
    M["rqtwoNonlocalUnits"] = _n((~a.in_gold_file).sum())
    M["rqtwoNonlocalNeededShare"] = pct(a[~a.in_gold_file].needed.mean())
    M["rqtwoLocalNeededShare"] = pct(a[a.in_gold_file].needed.mean())

    # ---------------- RQ2 proxies table
    pr = pd.DataFrame(r2["proxies"])
    names = {"p_gold_file": "Gold-file", "p_issue": "Issue-mention", "p_dep1": "Import-proximity",
             "p_all": "All-needed"}
    prow = []
    for _, x in pr.iterrows():
        nm = names.get(x.proxy) or LLM_NAMES.get(x.proxy.removeprefix("llm_"), x.proxy)
        fam = "LLM judge" if x.proxy.startswith("llm_") else "Location"
        f1ci = x.get("unneeded_f1_ci")
        mcci = x.get("mcc_ci")
        f1s = f(x.unneeded_f1) + (f" [{f(f1ci[0])}, {f(f1ci[1])}]" if isinstance(f1ci, list) else "")
        mcs = f(x.mcc) + (f" [{f(mcci[0])}, {f(mcci[1])}]" if isinstance(mcci, list) else "")
        prow.append((fam, f"{fam} & {nm} & {f(x.unneeded_precision)} & {f(x.unneeded_recall)} & {f1s} & {mcs} & "
                          f"{pct(x.nonlocal_needed_retention, 0)} \\\\"))
        key = x.proxy.replace("llm_", "L").replace("p_", "P").replace(":", "").replace(".", "").replace("-", "").replace("_", "")
        key = "".join(ch for ch in key if ch.isalpha())
        M[f"rqtwoFone{key}"] = f(x.unneeded_f1)
        M[f"rqtwoMcc{key}"] = f(x.mcc)
        M[f"rqtwoPrec{key}"] = f(x.unneeded_precision)
        M[f"rqtwoRec{key}"] = f(x.unneeded_recall)
        M[f"rqtwoRet{key}"] = pct(x.nonlocal_needed_retention, 0)
    loc = [r for fam, r in prow if fam == "Location"]
    llm = [r for fam, r in prow if fam != "Location"]
    blocks["rq2-proxy-table"] = rf"""\begin{{table*}}[t]
\caption{{How well location proxies and LLM judges recover counterfactual necessity for the {_n(r2['agent_source_units'])} source units of valid agent patches. Precision, recall and F1 refer to flagging \emph{{removable}} units. MCC refers to the needed/removable decision. Brackets: 95\% instance-cluster bootstrap intervals. \emph{{Nonlocal retention}}: share of the {_n(r2['agent_source_needed_outside_gold_files'])} needed units outside reference-patch files that the proxy classifies as needed. LLM judges: majority vote over three seeds.}}
\label{{tab:proxies}}
\centering\footnotesize
\begin{{tabular}}{{llrrrrr}}
\toprule
Family & Proxy & Precision & Recall & F1 [95\% CI] & MCC [95\% CI] & Nonlocal retention \\
\midrule
{chr(10).join(loc)}
\midrule
{chr(10).join(llm)}
\bottomrule
\end{{tabular}}
\end{{table*}}"""
    agree = r2.get("llm_seed_agreement", {})
    if agree:
        M["rqtwoSeedAgreeMin"] = pct(min(agree.values()))
        M["rqtwoSeedAgreeMax"] = pct(max(agree.values()))
    pr_rate = r2.get("llm_parse_rate", {})
    if pr_rate:
        M["rqtwoParseMin"] = pct(min(pr_rate.values()))

    # ---------------- RQ2 informed judges (exploratory, A8)
    inf = P / "rq234/rq2_informed.csv"
    if inf.exists():
        d = pd.read_csv(inf)
        rows = []
        for m in LLM_NAMES:
            a_ = d[(d.model == m) & (d.variant == "full")]
            b_ = d[(d.model == m) & (d.variant == "informed")]
            if len(a_) and len(b_):
                a_, b_ = a_.iloc[0], b_.iloc[0]
                rows.append(f"{LLM_NAMES[m]} & {f(a_.precision)} & {f(a_.recall)} & {f(a_.mcc)} & "
                            f"{f(b_.precision)} & {f(b_.recall)} & {f(b_.mcc)} \\\\")
        blocks["rq2-informed-table"] = rf"""\begin{{table}}[pos=htbp]
\caption{{Exploratory comparison (seed 11): LLM judges without and with the goal tests and the instance's test patch in the prompt. Precision and recall refer to flagging removable agent source units; MCC to the needed/removable decision.}}
\label{{tab:informed}}
\centering\footnotesize
\begin{{tabular}}{{lrrrrrr}}
\toprule
 & \multicolumn{{3}}{{c}}{{Issue and patch only}} & \multicolumn{{3}}{{c}}{{Plus goal tests}} \\
\cmidrule(lr){{2-4}}\cmidrule(lr){{5-7}}
Judge & Prec. & Rec. & MCC & Prec. & Rec. & MCC \\
\midrule
{chr(10).join(rows)}
\bottomrule
\end{{tabular}}
\end{{table}}"""
        M["rqtwoInfMaxRecall"] = f(d[d.variant == "informed"].recall.max())
        M["rqtwoInfMaxMcc"] = f(d[d.variant == "informed"].mcc.max())

    # ---------------- RQ3
    r3 = s["rq3"]
    M["rqthreeEnvPatches"] = _n(r3["envelope_patches"])
    M["rqthreeEnvEmpty"] = _n(r3["envelope_empty"])
    M["rqthreeEnvTestsMedian"] = f"{r3['envelope_tests_median']:.0f}" if r3.get("envelope_tests_median") else "--"
    for who in ("agent", "gold"):
        W = "Agent" if who == "agent" else "Gold"
        v = r3.get(f"{who}_regression_rate")
        if v:
            M[f"rqthree{W}RegRate"] = pct(v[0])
            M[f"rqthree{W}RegCI"] = f"[{pct(v[1])}, {pct(v[2])}]"
        M[f"rqthree{W}RegN"] = r3.get(f"{who}_regression_n", 0)
        M[f"rqthree{W}RegMinimal"] = r3.get(f"{who}_regression_tied_to_minimal", 0)
        M[f"rqthree{W}Harmful"] = r3.get(f"{who}_harmful_unit_patches", 0)
    if "injection_table" in r3:
        tab = pd.read_csv(P / "rq234/rq3_injection_table.csv", index_col=0)
        cols = [c for c in ["official_tests", "envelope_H", "unneeded_U", "label_N", "label_J", "label_C", "error"] if c in tab.columns]
        head = {"official_tests": "Official tests", "envelope_H": "Envelope (\\lab{H})", "unneeded_U": "Undetected (\\lab{U})",
                "label_N": "\\lab{N}", "label_J": "\\lab{J}", "label_C": "\\lab{C}", "error": "Error"}
        lines = [f"{k.capitalize()} & " + " & ".join(str(int(tab.loc[k, c])) for c in cols) + f" & {int(tab.loc[k, cols].sum())} \\\\"
                 for k in tab.index]
        blocks["rq3-injection-table"] = rf"""\begin{{table}}[t]
\caption{{Outcomes of the injection study: one injected unit per reference patch, in a module within two import hops of the edited modules. \emph{{Official tests}}: the patched program fails F2P or P2P. \emph{{Envelope}}: official tests pass, the envelope exposes a regression and attributes it to the injected unit. \emph{{Undetected}}: neither detects a change, and the unit is labelled unneeded.}}
\label{{tab:injection}}
\centering\footnotesize
\begin{{tabular}}{{l{'r' * (len(cols) + 1)}}}
\toprule
Injection & {' & '.join(head[c] for c in cols)} & Total \\
\midrule
{chr(10).join(lines)}
\bottomrule
\end{{tabular}}
\end{{table}}"""
        for kind in ("semantic", "neutral"):
            K = kind.capitalize()
            if f"inj_{kind}_n" in r3:
                M[f"rqthree{K}N"] = r3[f"inj_{kind}_n"]
                M[f"rqthree{K}Official"] = ci(r3[f"inj_{kind}_official"])
                M[f"rqthree{K}Envelope"] = ci(r3[f"inj_{kind}_with_envelope"])
                M[f"rqthree{K}Gain"] = ci(r3[f"inj_{kind}_gain"])
                M[f"rqthree{K}LabelledU"] = pct(r3[f"inj_{kind}_labelled_U"])

    # ---------------- RQ4
    r4 = s["rq4"]
    M["rqfourN"] = _n(r4["n"])
    M["rqfourCallsMedian"] = f"{r4['oracle_calls_median']:.0f}"
    M["rqfourCallsPninety"] = f"{r4['oracle_calls_p90']:.0f}"
    M["rqfourWallMedian"] = f"{r4['wall_median_s']:.0f}"
    M["rqfourOracleSecMedian"] = f"{r4['oracle_seconds_median']:.0f}"
    M["rqfourPrecheck"] = _n(r4["precheck_rejections_total"])
    M["rqfourCoupled"] = _n(r4["anomalies"])
    M["rqfourMultiN"] = _n(r4["multi_n"])
    M["rqfourPlainInvalid"] = _n(r4["abl_plain_invalid_runs_sum"])
    M["rqfourExhN"] = _n(r4["exhaustive_n"])
    M["rqfourExhMatch"] = pct(r4["ddmin_matches_exhaustive_size"])
    M["rqfourExhLarger"] = _n(r4["ddmin_larger_than_min"])
    M["rqfourLooGap"] = _n(r4["loo_vs_shift_needed_gap"])
    M["rqfourPatchesJ"] = _n(r4["patches_with_J"])
    bu = pd.read_csv(P / "rq234/rq4_by_units.csv")
    lines = [f"{row.iloc[0].replace('(', '').replace(']', '').replace(', ', '--')} & {int(row.n)} & {row.calls:.0f} & {row.wall:.0f} \\\\"
             for _, row in bu.iterrows() if row.n > 0]
    mult = ok[ok.n_units >= 3]
    strat = [("\\tool{} (memoised triage, this paper)", None),
             ("\\textsc{ddmin}, closure and pre-check", "abl_closure_calls"),
             ("\\textsc{ddmin} only (no closure, no pre-check)", "abl_plain_calls"),
             ("\\textsc{ddmin} with pre-check only", "abl_precheck_calls"),
             ("Leave-one-out only", "abl_loo_calls"),
             ("Exhaustive ($\\leq$8 units)", "abl_exh_calls")]
    srows = []
    for name, col in strat:
        if col is None:
            srows.append(f"{name} & {mult.oracle_calls.sum():.0f} & {mult.oracle_calls.median():.0f} \\\\")
        else:
            v = mult[col].dropna()
            srows.append(f"{name} & {v.sum():.0f} & {v.median():.0f} \\\\")
    blocks["rq4-table"] = rf"""\begin{{table}}[t]
\caption{{Cost of counterfactual triage. Left: median oracle executions and wall-clock seconds per patch by number of units (all {_n(r4['n'])} valid patches). Right: total and median oracle executions of alternative strategies on the {_n(r4['multi_n'])} patches with at least three units. Alternative strategies are replayed with \tool{{}}'s outcome cache as ground truth and counted as if run alone. \tool{{}}'s count includes leave-one-out, minimisation and the repeated full-patch run.}}
\label{{tab:cost}}
\centering\footnotesize
\begin{{tabular}}{{lrrr}}
\toprule
Units & Patches & Calls & Seconds \\
\midrule
{chr(10).join(lines)}
\bottomrule
\end{{tabular}}\hfill
\begin{{tabular}}{{lrr}}
\toprule
Strategy & Total & Median \\
\midrule
{chr(10).join(srows)}
\bottomrule
\end{{tabular}}
\end{{table}}"""
    return blocks
