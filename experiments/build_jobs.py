"""Build SHIFT execution jobs and LLM-judge prompts for the execution panel.

Inputs: validated instance set (gold validation reports), panel systems
(configs/study.yaml), their official per-instance reports. Outputs:
  results/processed/jobs/shift_jobs.jsonl          (gold + resolved panel patches)
  results/processed/llm_inputs/prompts.jsonl       (same patches, SHIFT units)
  results/processed/jobs/eligibility.csv           (every candidate with inclusion reason)
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd
import yaml

from shift.data.repos import load_dataset, read_file
from shift.data.submissions import read_resolved
from shift.hypotheses.prompts import prompt_record
from shift.patch.edits import decompose

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "data/external/submissions"
GOLDVAL = ROOT / "results/raw/gold_validation/logs/run_evaluation/goldval/gold"


def validated_instances(assume_valid: bool = False) -> dict[str, str]:
    """instance_id -> 'ok' | reason for exclusion."""
    df = load_dataset()
    cfg = yaml.safe_load(open(ROOT / "configs/study.yaml"))
    x86 = set((ROOT / "results/raw/gold_validation/excluded_x86.txt").read_text().split())
    out = {}
    for iid in df[df.repo.isin(cfg["execution"]["repos"])].instance_id:
        if iid in x86:
            out[iid] = "x86_only_environment"
            continue
        rep = GOLDVAL / iid / "report.json"
        if not rep.exists():
            out[iid] = "ok" if assume_valid else "gold_not_evaluated"
            continue
        r = json.loads(rep.read_text())[iid]
        out[iid] = "ok" if r.get("resolved") else "gold_not_resolved_on_arm64"
    return out


def official_resolved(system: str, iid: str) -> bool | None:
    return read_resolved(SUB / system / "logs" / iid / "report.json", iid)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results/processed"))
    ap.add_argument("--assume-valid", action="store_true", help="treat not-yet-validated instances as eligible")
    a = ap.parse_args(argv)
    df = load_dataset()
    cfg = yaml.safe_load(open(ROOT / "configs/study.yaml"))
    valid = validated_instances(a.assume_valid)
    rows, jobs, prompts = [], [], []
    for iid, why in sorted(valid.items()):
        inst = df.loc[iid]
        protected = set(re.findall(r"diff --git a/.* b/(.*)", inst.test_patch))
        cands = [("gold", None, inst.patch)]
        for s in cfg["panel"]:
            pf = SUB / s / "logs" / iid / "patch.diff"
            res = official_resolved(s, iid)
            cands.append((s, res, pf.read_text(errors="surrogateescape") if pf.exists() else None))
        for label, res, patch in cands:
            reason = why
            if reason == "ok" and patch is None:
                reason = "no_patch"
            elif reason == "ok" and label != "gold" and res is not True:
                reason = "not_resolved_officially"
            elif reason == "ok" and not patch.strip():
                reason = "empty_patch"
            rows.append({"instance_id": iid, "label": label, "reason": reason})
            if reason != "ok":
                continue
            try:
                dp = decompose(patch, inst.repo, lambda p: read_file(inst.repo, inst.base_commit, p))
            except Exception as e:
                rows[-1]["reason"] = f"decompose_error:{type(e).__name__}"
                continue
            uids = [u.uid for u in dp.units if u.path not in protected]
            if not uids:
                rows[-1]["reason"] = "only_test_patch_files"
                continue
            rows[-1]["n_units"] = len(uids)
            jobs.append({"instance_id": iid, "label": label, "patch": patch, "repo": inst.repo})
            prompts.append(prompt_record(iid, label, inst.problem_statement, dp, uids))
    out = Path(a.out)
    (out / "jobs").mkdir(parents=True, exist_ok=True)
    (out / "llm_inputs").mkdir(parents=True, exist_ok=True)
    with open(out / "jobs/shift_jobs.jsonl", "w") as fh:
        for j in jobs:
            fh.write(json.dumps(j) + "\n")
    with open(out / "llm_inputs/prompts.jsonl", "w") as fh:
        for p in prompts:
            fh.write(json.dumps(p) + "\n")
    el = pd.DataFrame(rows)
    el.to_csv(out / "jobs/eligibility.csv", index=False)
    print(el.groupby(["label", "reason"]).size().to_string())
    print(f"jobs={len(jobs)} prompts={len(prompts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
