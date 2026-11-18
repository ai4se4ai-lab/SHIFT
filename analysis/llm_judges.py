"""Parse LLM-judge responses into per-edit predictions (RQ2) and throughput stats (HPC planning).

Input: hpc/fetched/<site>/outputs/<tag>/*.jsonl ; prompts JSONL for uid lists.
Output: results/processed/llm/<tag>_edits.csv, <tag>_throughput.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from shift.hypotheses.prompts import parse_answer

ROOT = Path(__file__).resolve().parents[1]


def load(tag: str, prompts: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    P = {}
    for l in open(prompts):
        p = json.loads(l)
        P[p["key"]] = p
    rows, gens = [], []
    for f in sorted(ROOT.glob(f"hpc/fetched/*/outputs/{tag}/*.jsonl")):
        site = f.parts[-4]
        for l in open(f):
            try:
                r = json.loads(l)
            except json.JSONDecodeError:
                continue
            p = P.get(r["key"])
            if p is None:
                continue
            ans = parse_answer(r.get("content", ""), p["uids"]) if not r.get("error") else \
                {"ok": False, "edits": {}, "error": "transport"}
            gens.append({"site": site, "model": r["model"], "seed": r["seed"], "key": r["key"],
                         "ok": ans["ok"], "error": r.get("error") or ans.get("error"),
                         "wall_s": r.get("wall_s"), "eval_count": r.get("eval_count"),
                         "prompt_eval_count": r.get("prompt_eval_count"),
                         "eval_s": (r.get("eval_duration_ns") or 0) / 1e9, "host": r.get("host")})
            for uid in p["uids"]:
                e = ans["edits"].get(uid)
                rows.append({"site": site, "model": r["model"], "seed": r["seed"], "key": r["key"],
                             "instance_id": p["instance_id"], "label": p["label"], "uid": uid,
                             "parsed": e is not None,
                             "needed": None if e is None else bool(e.get("needed")),
                             "role": None if e is None else e.get("role"),
                             "hypothesis": None if e is None else e.get("hypothesis"),
                             "confidence": None if e is None else e.get("confidence")})
    return pd.DataFrame(rows), pd.DataFrame(gens)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--prompts", default=str(ROOT / "results/processed/llm_inputs/prompts.jsonl"))
    a = ap.parse_args(argv)
    edits, gens = load(a.tag, Path(a.prompts))
    out = ROOT / "results/processed/llm"
    out.mkdir(parents=True, exist_ok=True)
    edits.to_csv(out / f"{a.tag}_edits.csv", index=False)
    gens.to_csv(out / f"{a.tag}_gens.csv", index=False)
    if len(gens):
        t = gens.groupby(["site", "model"]).agg(n=("key", "size"), ok_rate=("ok", "mean"),
                                                 median_wall=("wall_s", "median"),
                                                 median_out_tok=("eval_count", "median"),
                                                 tok_per_s=("eval_count", "sum")).reset_index()
        es = gens.groupby(["site", "model"]).eval_s.sum().values
        t["tok_per_s"] = t["tok_per_s"] / es
        t.to_csv(out / f"{a.tag}_throughput.csv", index=False)
        print(t.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
