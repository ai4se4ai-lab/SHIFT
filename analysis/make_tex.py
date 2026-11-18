"""Generate manuscript tables, figures (pgfplots) and number macros from processed results,
and splice them into docs/JSS/main.tex between `% BEGIN:<name>` / `% END:<name>` markers.

Every number in the paper's evaluation is produced here from results/processed/**.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "docs/JSS/main.tex"
P = ROOT / "results/processed"

PANEL_NAMES = {
    "20260217_mini-v2.0.0_claude-4-6-opus": "Claude 4.6 Opus",
    "20260217_mini-v2.0.0_gpt-5-2-high": "GPT-5.2 (high)",
    "20260217_mini-v2.0.0_gemini-3-pro-high": "Gemini 3 Pro (high)",
    "20260217_mini-v2.0.0_kimi-k2-5-high": "Kimi K2.5 (high)",
    "20260217_mini-v2.0.0_deepseek-3-2-high": "DeepSeek V3.2 (high)",
    "20260217_mini-v2.0.0_gpt-5-mini": "GPT-5 mini",
    "20250803_mini-v1.0.0_qwen2-5-coder-32b-instruct": "Qwen2.5-Coder 32B",
    "20250720_mini-v0.0.0-gpt-4o-2024-11-20": "GPT-4o",
    "gold": "Reference (human)",
}
OPEN_W = {"Kimi K2.5 (high)", "DeepSeek V3.2 (high)", "Qwen2.5-Coder 32B"}
LLM_NAMES = {"qwen2.5-coder:7b": "Qwen2.5-Coder 7B", "llama3.1:8b": "Llama 3.1 8B", "gemma2:9b": "Gemma 2 9B",
             "phi4:14b": "Phi-4 14B", "mistral-small:24b": "Mistral Small 24B"}


def f(x, d=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "--"
    return f"{x:.{d}f}"


def pct(x, d=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "--"
    return f"{100 * x:.{d}f}\\%"


def ci(v, d=1):
    return f"{pct(v[0], d)} [{pct(v[1], d)}, {pct(v[2], d)}]"


def splice(text: str, name: str, body: str) -> str:
    pat = re.compile(rf"(% BEGIN:{re.escape(name)}\n).*?(% END:{re.escape(name)})", re.S)
    if not pat.search(text):
        raise KeyError(f"marker {name} not found")
    return pat.sub(lambda m: m.group(1) + body.rstrip("\n") + "\n" + m.group(2), text)


class Macros:
    def __init__(self):
        self.d: dict[str, str] = {}

    def __setitem__(self, k, v):
        assert re.fullmatch(r"[A-Za-z]+", k), k
        self.d[k] = str(v)

    def tex(self) -> str:
        return "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(self.d.items()))


# ------------------------------------------------------------------ RQ1
def rq1(M: Macros) -> dict[str, str]:
    s = json.loads((P / "rq1/rq1_summary.json").read_text())
    r = pd.read_csv(P / "rq1/rq1_paired.csv")
    M["rqoneSystems"] = s["n_systems"]
    M["rqoneInstances"] = s["n_instances"]
    for key, name in [("n_src_files", "Files"), ("src_blocks", "Blocks"), ("src_churn", "Churn"),
                      ("n_aux_files", "Aux"), ("dispersion", "Disp")]:
        M[f"rqone{name}Greater"] = s[key]["sig_greater"]
        M[f"rqone{name}Less"] = s[key]["sig_less"]
        M[f"rqone{name}MedR"] = f(s[key]["median_r"])
    g = s["gee"]
    M["rqoneGeeNonlocal"] = f(g["nonlocal_sh"]["coef"])
    M["rqoneGeeNonlocalOR"] = f(np.exp(g["nonlocal_sh"]["coef"]))
    M["rqoneGeeNonlocalLo"] = f(np.exp(g["nonlocal_sh"]["ci"][0]))
    M["rqoneGeeNonlocalHi"] = f(np.exp(g["nonlocal_sh"]["ci"][1]))
    M["rqoneGeeChurnP"] = f(g["log_churn"]["p"])
    M["rqoneGeeFilesP"] = f(g["n_src_files"]["p"])
    M["rqoneRhoNonlocal"] = f(s["spearman_resolve_vs_nonlocal_share_mean"][0])
    M["rqoneRhoTouches"] = f(s["spearman_resolve_vs_touches_gold_file"][0])
    M["rqoneRhoBlocks"] = f(s["spearman_resolve_vs_src_blocks_agent_mean"][0])
    M["rqoneVtwoSystems"] = s["v2_systems"]
    M["rqoneVtwoAuxGreater"] = s["v2_aux_sig_greater"]
    M["rqoneGoldBlocks"] = f(s["src_blocks"]["gold_mean"])
    M["rqoneGoldFiles"] = f(s["n_src_files"]["gold_mean"])
    ef = pd.read_csv(P / "rq1/edit_footprint.csv")
    M["rqonePatches"] = f"{int((ef.system != 'gold').sum()):,}".replace(",", "{,}")

    # Figure: per-system resolve rate vs nonlocal share and gold-file touch rate
    pts1 = " ".join(f"({x:.3f},{y:.3f})" for x, y in zip(r.resolve_rate, r.nonlocal_share_mean))
    pts2 = " ".join(f"({x:.3f},{y:.3f})" for x, y in zip(r.resolve_rate, r.touches_gold_file))
    fig = rf"""\begin{{figure}}[pos=htbp]
\centering
\begin{{tikzpicture}}
\begin{{axis}}[width=0.52\linewidth, height=4.6cm, xlabel={{Resolution rate}}, ylabel={{Mean nonlocal share}},
  xmin=0, xmax=0.85, ymin=0, ymax=0.3, tick label style={{font=\scriptsize}}, label style={{font=\footnotesize}},
  title={{(a) Edits outside reference files}}, title style={{font=\footnotesize}}]
\addplot[only marks, mark=*, mark size=1.4pt, blue!60!black] coordinates {{{pts1}}};
\end{{axis}}
\end{{tikzpicture}}\hfill
\begin{{tikzpicture}}
\begin{{axis}}[width=0.52\linewidth, height=4.6cm, xlabel={{Resolution rate}}, ylabel={{Touches a reference file}},
  xmin=0, xmax=0.85, ymin=0.2, ymax=1, tick label style={{font=\scriptsize}}, label style={{font=\footnotesize}},
  title={{(b) Overlap with reference location}}, title style={{font=\footnotesize}}]
\addplot[only marks, mark=square*, mark size=1.3pt, orange!80!black] coordinates {{{pts2}}};
\end{{axis}}
\end{{tikzpicture}}
\caption{{Location of agent edits relative to the reference patch for the {s['n_systems']} mini-swe-agent systems (one point per system, SWE-bench Verified). (a) Mean share of source change blocks in files the reference patch does not edit. (b) Share of patches that edit at least one reference-patch file. Spearman $\rho$ with the resolution rate: {f(s['spearman_resolve_vs_nonlocal_share_mean'][0])} in (a) and {f(s['spearman_resolve_vs_touches_gold_file'][0])} in (b).}}
\label{{fig:rq1}}
\end{{figure}}"""

    # Table: exploration of the panel
    x = pd.read_csv(P / "rq1/rq1_exploration_summary.csv")
    x["name"] = x.system.map(PANEL_NAMES)
    x = x.dropna(subset=["name"]).sort_values("resolved", ascending=False)
    rows = "\n".join(
        f"{rw['name']} & {int(rw['n'])} & {pct(rw['resolved'])} & {rw['steps_median']:.0f} & {rw['ref_median']:.0f} "
        f"[{rw['ref_q1']:.0f}--{rw['ref_q3']:.0f}] & {rw['edited_median']:.0f} & {rw['eer_median']:.1f} \\\\"
        for _, rw in x.iterrows())
    tab = rf"""\begin{{table}}[t]
\caption{{Exploration footprint of the panel systems that publish trajectories (medians over SWE-bench Verified instances). \emph{{Referenced}}: distinct repository files named in the agent's shell commands (interquartile range in brackets). \emph{{EER}}: exploration-to-edit ratio, referenced files per edited file. GPT-4o's run has no published trajectories.}}
\label{{tab:explore}}
\centering\footnotesize
\begin{{tabular}}{{lrrrrrr}}
\toprule
System & $n$ & Resolved & Steps & Referenced & Edited & EER \\
\midrule
{rows}
\bottomrule
\end{{tabular}}
\end{{table}}"""
    M["rqoneExploreRefMin"] = f"{x.ref_median.min():.0f}"
    M["rqoneExploreRefMax"] = f"{x.ref_median.max():.0f}"
    return {"rq1-figure": fig, "rq1-explore-table": tab}


def example(M: Macros) -> None:
    """Running-example facts; asserts that the narrative in the paper matches the record."""
    rec = ROOT / "results/raw/shift/main/records/20260217_mini-v2.0.0_kimi-k2-5-high__django__django-13297.json"
    if not rec.exists():
        M["exOracleCalls"] = "\\pending{n}"
        return
    r = json.loads(rec.read_text())
    assert r["status"] == "ok", r["status"]
    assert r["labels"] == {"u01": "U", "u02": "U", "u03": "N", "u04": "N"}, r["labels"]
    assert r["minimal"] == ["u03", "u04"], r["minimal"]
    assert r["requires"] == {"u02": ["u01"], "u04": ["u03"]}, r["requires"]
    env = r["envelope"]
    assert env["status"] == "clean" and env["n_tests"] == 75 and len(env["directives"]) == 6, env
    M["exOracleCalls"] = r["oracle_calls"]
    edits = ROOT / "results/processed/llm/full_edits.csv"
    if edits.exists():
        e = pd.read_csv(edits)
        k = e[e.key == "20260217_mini-v2.0.0_kimi-k2-5-high__django__django-13297"]
        u2 = k[k.uid == "u02"]
        assert len(u2) and u2.needed.all() and (u2.role == "fix").all(), u2
        assert (k[k.uid == "u01"].role == "support").all()
        assert k.model.nunique() == 5


def main() -> int:
    M = Macros()
    blocks = {}
    example(M)
    acc = json.loads((P / "hpc_accounting.json").read_text())
    M["nGpuHours"] = f"{acc['gpu_hours_total']:.1f}"
    M["nGpuJobs"] = acc["jobs"]
    M["nGpuHoursRorqual"] = f"{acc['by_site']['rorqual']:.1f}"
    M["nGpuHoursNarval"] = f"{acc['by_site']['narval']:.1f}"
    g = pd.read_csv(P / "llm/full_gens.csv")
    M["nLlmGenerations"] = f"{len(g):,}".replace(",", "{,}")
    blocks.update(rq1(M))
    rq234_path = P / "rq234/summary.json"
    if rq234_path.exists() and (Path(__file__).parent / "make_tex_rq234.py").exists():
        import make_tex_rq234
        blocks.update(make_tex_rq234.build(M))
    text = TEX.read_text()
    used = set(re.findall(r"\\((?:rqone|rqtwo|rqthree|rqfour|ex|n)[A-Z][A-Za-z]*)", text))
    for name in sorted(used - set(M.d)):
        M[name] = f"\\pending{{{name}}}"          # visible marker, never a number
    blocks["results-macros"] = M.tex()
    for name, body in blocks.items():
        try:
            text = splice(text, name, body)
        except KeyError as e:
            print("skip", e)
    TEX.write_text(text)
    (P / "paper_macros.json").write_text(json.dumps(M.d, indent=1))
    print(f"{len(M.d)} macros, blocks: {sorted(blocks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
