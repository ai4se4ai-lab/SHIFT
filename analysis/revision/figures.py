"""Revision v1 figures as pgfplots code generated from processed data.

Each figure is written to results/processed/revision/figures/<name>.tex and, with
--inline, copied into docs/JSS/v1/main.tex between the markers
    %<<GEN:name>>  ...  %<<END:name>>
so that the manuscript directory remains a two-file deliverable (main.tex, references.bib).

Sources:
  fig_rq1_effects  : results/processed/rq1/rq1_paired.csv
  fig_rq2_matched  : results/processed/revision/rq2_agent_vs_reference_matched.csv,
                     results/processed/revision/revision_stats.json (pooled_matched)
  fig_rq3_ops      : results/processed/revision/revision_stats.json (C_injection)
  fig_rq4_cost     : results/processed/revision/rq4_cost_distribution.csv
Run analysis/revision/revision_stats.py first.
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "results/processed"
OUT = P / "revision/figures"
TEX = ROOT / "docs/JSS/v1/main.tex"

COLORS = (r"\definecolor{okblue}{HTML}{0072B2}\definecolor{okorange}{HTML}{E69F00}"
          r"\definecolor{okverm}{HTML}{D55E00}\definecolor{okgrey}{HTML}{999999}")


def fig_rq1() -> str:
    d = pd.read_csv(P / "rq1/rq1_paired.csv")
    metrics = [("n_src_files", "Source files"), ("src_blocks", "Source blocks"), ("src_churn", "Source churn"),
               ("dispersion", "Dispersion"), ("n_aux_files", "Auxiliary files")]
    rnd = random.Random(2026)
    sig, ns, notes = [], [], []
    for i, (m, _) in enumerate(metrics, start=1):
        for _, row in d.iterrows():
            r, p = row[f"{m}_r"], row[f"{m}_p_holm"]
            if pd.isna(r):
                continue
            pt = f"({r:.3f},{i + rnd.uniform(-0.28, 0.28):.3f})"
            (sig if p < 0.05 else ns).append(pt)
        less = int(((d[f"{m}_p_holm"] < 0.05) & (d[f"{m}_r"] < 0)).sum())
        more = int(((d[f"{m}_p_holm"] < 0.05) & (d[f"{m}_r"] > 0)).sum())
        notes.append(rf"\node[anchor=west,font=\scriptsize] at (axis cs:1.12,{i}) {{{less} / {more}}};")
    ticks = ",".join(str(i) for i in range(1, len(metrics) + 1))
    labels = ",".join(n for _, n in metrics)
    return rf"""\begin{{tikzpicture}}
\begin{{axis}}[width=0.74\linewidth,height=58mm,xmin=-1.05,xmax=1.05,ymin=0.5,ymax={len(metrics)}.5,
 y dir=reverse,ytick={{{ticks}}},yticklabels={{{labels}}},xlabel={{Matched-pairs rank-biserial $r$ (agent $-$ reference)}},
 xtick={{-1,-0.5,0,0.5,1}},tick label style={{font=\footnotesize}},label style={{font=\footnotesize}},
 clip=false,legend style={{font=\scriptsize,at={{(0.5,1.02)}},anchor=south,legend columns=2,draw=none}}]
\addplot[only marks,mark=*,mark size=1.4pt,okblue,fill opacity=0.85] coordinates {{{" ".join(sig)}}};
\addlegendentry{{Holm-adjusted $p<0.05$}}
\addplot[only marks,mark=o,mark size=1.4pt,okgrey] coordinates {{{" ".join(ns)}}};
\addlegendentry{{not significant}}
\draw[densely dashed,black!60] (axis cs:0,0.5) -- (axis cs:0,{len(metrics)}.5);
\node[anchor=west,font=\scriptsize\itshape] at (axis cs:1.12,0.5) {{less / more}};
{chr(10).join(notes)}
\end{{axis}}
\end{{tikzpicture}}"""


def fig_rq2() -> str:
    t = pd.read_csv(P / "revision/rq2_agent_vs_reference_matched.csv")
    s = json.loads((P / "revision/revision_stats.json").read_text())["A_agent_vs_reference"]["pooled_matched"]
    t = t.sort_values("diff").reset_index(drop=True)
    rows = [(r.system, r.n_instances, 100 * r["diff"], 100 * r.ci_lo, 100 * r.ci_hi, 100 * r.ci_bonf_lo,
             100 * r.ci_bonf_hi) for _, r in t.iterrows()]
    n = len(rows)
    pool = ("All agents (pooled)", s["n_instances"], 100 * s["est"], 100 * s["ci_0.05"][0], 100 * s["ci_0.05"][1])
    thin, thick, pts = [], [], []
    for i, (_, _, e, lo, hi, blo, bhi) in enumerate(rows, start=1):
        thin.append(rf"\draw[okgrey,line width=0.5pt] (axis cs:{blo:.2f},{i}) -- (axis cs:{bhi:.2f},{i});")
        thick.append(rf"\draw[okblue,line width=1.6pt] (axis cs:{lo:.2f},{i}) -- (axis cs:{hi:.2f},{i});")
        pts.append(f"({e:.2f},{i})")
    yp = n + 1.4
    labels = ",".join(f"{{{name} ({k})}}" for name, k, *_ in rows) + f",{{{pool[0]} ({pool[1]})}}"
    ticks = ",".join(str(i) for i in range(1, n + 1)) + f",{yp}"
    return rf"""\begin{{tikzpicture}}
\begin{{axis}}[width=0.70\linewidth,height=62mm,xmin=-35,xmax=45,ymin=0.4,ymax={yp + 0.6},y dir=reverse,
 ytick={{{ticks}}},yticklabels={{{labels}}},xlabel={{Removable share, agent $-$ matched reference (percentage points)}},
 tick label style={{font=\footnotesize}},label style={{font=\footnotesize}},clip=false]
\draw[densely dashed,black!60] (axis cs:0,0.4) -- (axis cs:0,{yp + 0.6});
{chr(10).join(thin)}
{chr(10).join(thick)}
\addplot[only marks,mark=*,mark size=1.8pt,black] coordinates {{{" ".join(pts)}}};
\draw[okverm,line width=1.6pt] (axis cs:{pool[3]:.2f},{yp}) -- (axis cs:{pool[4]:.2f},{yp});
\addplot[only marks,mark=diamond*,mark size=2.6pt,okverm] coordinates {{({pool[2]:.2f},{yp})}};
\end{{axis}}
\end{{tikzpicture}}"""


def fig_rq3() -> str:
    c = json.loads((P / "revision/revision_stats.json").read_text())["C_injection"]
    names = {"relop_flip": "Relational flip", "bool_negate": "Condition negation",
             "return_none": "Return \\code{None}", "const_perturb": "Integer perturbation"}
    order = ["relop_flip", "bool_negate", "return_none", "const_perturb"]
    rows = [(names[o], c["by_operator"][o]) for o in order]
    neu = {r["kind"]: r for r in c["table"]}["neutral"]
    nn = neu["official_tests"] + neu["envelope_H"] + neu["unneeded_U"]
    rows.append(("Neutral (all)", {"n": nn, "official": neu["official_tests"], "envelope_extra": neu["envelope_H"],
                                   "undetected": neu["unneeded_U"]}))
    y = list(range(1, len(rows) + 1))
    co = lambda k: " ".join(f"({100 * r[k] / r['n']:.2f},{i})" for i, (_, r) in zip(y, rows))  # noqa: E731
    labels = ",".join(f"{{{name} ($n={r['n']}$)}}" for name, r in rows)
    ann = "\n".join(rf"\node[anchor=west,font=\scriptsize] at (axis cs:101,{i}) {{{r['official']}+{r['envelope_extra']}}};"
                    for i, (_, r) in zip(y, rows))
    return rf"""\begin{{tikzpicture}}
\begin{{axis}}[xbar stacked,bar width=9pt,width=0.70\linewidth,height=52mm,xmin=0,xmax=100,
 ymin=0.4,ymax={len(rows)}.6,y dir=reverse,ytick={{{",".join(map(str, y))}}},yticklabels={{{labels}}},
 xlabel={{Share of evaluable probes (\%)}},tick label style={{font=\footnotesize}},label style={{font=\footnotesize}},
 legend style={{font=\scriptsize,at={{(0.5,1.03)}},anchor=south,legend columns=3,draw=none}},clip=false]
\addplot[fill=okblue,draw=none] coordinates {{{co("official")}}};
\addlegendentry{{Official tests}}
\addplot[fill=okorange,draw=none] coordinates {{{co("envelope_extra")}}};
\addlegendentry{{Envelope only}}
\addplot[fill=black!12,draw=none] coordinates {{{co("undetected")}}};
\addlegendentry{{Undetected}}
{ann}
\end{{axis}}
\end{{tikzpicture}}"""


def fig_rq4() -> str:
    t = pd.read_csv(P / "revision/rq4_cost_distribution.csv")
    boxes = []
    for i, r in enumerate(t.itertuples(), start=1):
        a, b = i - 0.25, i + 0.25
        boxes.append(rf"""\draw[okblue] (axis cs:{i},{r.calls_min:g}) -- (axis cs:{i},{r.calls_q1:g});
\draw[okblue] (axis cs:{i},{r.calls_q3:g}) -- (axis cs:{i},{r.calls_max:g});
\draw[okblue] (axis cs:{i - 0.12},{r.calls_min:g}) -- (axis cs:{i + 0.12},{r.calls_min:g});
\draw[okblue] (axis cs:{i - 0.12},{r.calls_max:g}) -- (axis cs:{i + 0.12},{r.calls_max:g});
\draw[okblue,fill=okblue!15] (axis cs:{a},{r.calls_q1:g}) rectangle (axis cs:{b},{r.calls_q3:g});
\draw[black,line width=1.2pt] (axis cs:{a},{r.calls_med:g}) -- (axis cs:{b},{r.calls_med:g});
\node[font=\scriptsize,anchor=south] at (axis cs:{i},{r.calls_max * 1.08:g}) {{{r.calls_med:g}}};""")
    labels = ",".join(f"{{{r.bin}\\\\($n={r.n}$)}}" for r in t.itertuples())
    return rf"""\begin{{tikzpicture}}
\begin{{semilogyaxis}}[width=0.72\linewidth,height=55mm,xmin=0.4,xmax={len(t)}.6,ymin=2,ymax=600,
 xtick={{{",".join(str(i) for i in range(1, len(t) + 1))}}},xticklabels={{{labels}}},
 xticklabel style={{align=center,font=\scriptsize}},yticklabel style={{font=\footnotesize}},
 xlabel={{Edit units per patch}},ylabel={{Core oracle executions}},label style={{font=\footnotesize}},
 log ticks with fixed point,clip=false]
\addplot[draw=none] coordinates {{(1,3)}};
{chr(10).join(boxes)}
\end{{semilogyaxis}}
\end{{tikzpicture}}"""


FIGS = {"fig_rq1_effects": fig_rq1, "fig_rq2_matched": fig_rq2, "fig_rq3_ops": fig_rq3, "fig_rq4_cost": fig_rq4}


def main(argv):
    OUT.mkdir(parents=True, exist_ok=True)
    body = TEX.read_text() if "--inline" in argv else None
    for name, fn in FIGS.items():
        code = fn()
        (OUT / f"{name}.tex").write_text(COLORS + "\n" + code + "\n")
        if body is not None:
            pat = re.compile(rf"(%<<GEN:{name}>>\n).*?(%<<END:{name}>>)", re.S)
            if not pat.search(body):
                print(f"marker for {name} not found; skipped")
                continue
            body = pat.sub(lambda m: m.group(1) + code + "\n" + m.group(2), body)
    if body is not None:
        TEX.write_text(body)
    print("wrote", ", ".join(FIGS))


if __name__ == "__main__":
    main(sys.argv[1:])
