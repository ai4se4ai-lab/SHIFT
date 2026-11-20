"""Revision v1: close the exhaustive-minimum audit for records it could not certify.

For each record listed in results/processed/revision/exhaustive_audit.csv with
unobserved smaller closed configurations, execute exactly those configurations (and
re-execute the witness once as a stability check) with the same oracle and verdict
rule as shift.pipeline. Original records are not modified.

Output: results/raw/revision/exhaustive_followup/<record>.json
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "revision"))
from exhaustive_audit import closure, _patch_text  # noqa: E402

from shift.data.repos import load_dataset, read_file  # noqa: E402
from shift.oracle.runner import InstanceOracle  # noqa: E402
from shift.patch.edits import decompose, syntax_ok  # noqa: E402

OUT = ROOT / "results/raw/revision/exhaustive_followup"


def run_record(rec_name: str) -> dict:
    r = json.loads((ROOT / "results/raw/shift/main/records" / f"{rec_name}.json").read_text())
    inst = load_dataset().loc[r["instance_id"]].to_dict()
    ids = [u["uid"] for u in r["units"]]
    req = {a: set(b) for a, b in (r.get("requires") or {}).items()}
    obs = {frozenset(x["cfg"]): x["outcome"] for x in r["runs"]}
    dp = decompose(_patch_text(r["instance_id"], r["patch_label"]), inst["repo"],
                   lambda p: read_file(inst["repo"], inst["base_commit"], p))
    d = frozenset(r["minimal"])
    todo = []
    for k in range(len(d)):
        for c in itertools.combinations(ids, k):
            s = frozenset(c)
            if closure(s, req) == s and s not in obs and syntax_ok(dp.apply(s)):
                todo.append(s)
    out = {"record": rec_name, "witness": sorted(d), "executed": [], "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    f2p, p2p = inst["FAIL_TO_PASS"], inst["PASS_TO_PASS"]
    with InstanceOracle(inst, timeout=900) as orc:
        protected = orc.protected_paths()
        for s in todo + [d]:
            orc.write_config(dp.apply(s), protected)
            rr = orc.run_tests(None)
            v = orc.verdict(rr, f2p, p2p)
            o = "valid" if v.valid else ("error" if rr.timed_out else ("goal_fail" if not v.goal_ok else "pres_fail"))
            out["executed"].append({"cfg": sorted(s), "is_witness_recheck": s == d, "outcome": o,
                                    "sec": round(rr.seconds, 2)})
            print(rec_name, sorted(s), o, flush=True)
    smaller = [e for e in out["executed"] if not e["is_witness_recheck"]]
    out["n_smaller_executed"] = len(smaller)
    out["smaller_valid"] = [e["cfg"] for e in smaller if e["outcome"] == "valid"]
    out["smaller_error"] = [e["cfg"] for e in smaller if e["outcome"] == "error"]
    out["witness_recheck"] = out["executed"][-1]["outcome"]
    out["certified_min_after_followup"] = (not out["smaller_valid"] and not out["smaller_error"]
                                           and out["witness_recheck"] == "valid")
    return out


def main():
    a = pd.read_csv(ROOT / "results/processed/revision/exhaustive_audit.csv")
    todo = a[(~a.certified_min) & (a.n_smaller_unobserved > 0)].record.tolist()
    OUT.mkdir(parents=True, exist_ok=True)
    for name in todo:
        f = OUT / f"{name}.json"
        if f.exists():
            continue
        f.write_text(json.dumps(run_record(name), indent=1))


if __name__ == "__main__":
    main()
