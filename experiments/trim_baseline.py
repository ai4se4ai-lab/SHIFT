"""v2 revision: equal-oracle comparison with a diff-only reimplementation of TRIM.

Replays ``trim_diff_only`` on every valid multi-unit patch against the recorded
outcomes of the main campaign (results/raw/shift/main/records, including ablation
and follow-up runs). Configurations never executed before are executed with the same
oracle and verdict rule as shift.pipeline (--execute) and stored in
results/raw/revision/trim/<record>.json; without --execute, the script only counts them.
Outputs: results/processed/revision/trim_baseline.csv
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "revision"))
from exhaustive_audit import _patch_text  # noqa: E402

from shift.counterfactual.triage import Session, trim_diff_only  # noqa: E402
from shift.data.repos import load_dataset, read_file  # noqa: E402
from shift.patch.edits import decompose, syntax_ok  # noqa: E402

REC = ROOT / "results/raw/shift/main/records"
FOLLOW = ROOT / "results/raw/revision/exhaustive_followup"
NEW = ROOT / "results/raw/revision/trim"
OUT = ROOT / "results/processed/revision/trim_baseline.csv"


class Missing(Exception):
    pass


def observed(name: str, r: dict) -> dict:
    obs = {frozenset(x["cfg"]): x["outcome"] for x in r["runs"]}
    for f in (FOLLOW / f"{name}.json", NEW / f"{name}.json"):
        if f.exists():
            for e in json.loads(f.read_text())["executed"]:
                obs.setdefault(frozenset(e["cfg"]), e["outcome"])
    return obs


def replay(name: str, execute: bool) -> dict:
    r = json.loads((REC / f"{name}.json").read_text())
    ids = [u["uid"] for u in r["units"]]
    files: dict[str, list[str]] = {}
    for u in r["units"]:
        files.setdefault(u["path"], []).append(u["uid"])
    groups = list(files.values())
    obs = observed(name, r)
    inst = load_dataset().loc[r["instance_id"]].to_dict()
    dp = decompose(_patch_text(r["instance_id"], r["patch_label"]), inst["repo"],
                   lambda p: read_file(inst["repo"], inst["base_commit"], p))
    pending: list[frozenset] = []
    stats = {"invalid_runs": 0}

    def oracle(cfg):
        if cfg in obs and obs[cfg] != "invalid":
            out = obs[cfg]
        elif not syntax_ok(dp.apply(cfg)):
            out = "invalid"                      # TRIM would execute it; the run fails
        elif execute:
            out = _execute(name, r, inst, dp, cfg)
            obs[cfg] = out
        else:
            pending.append(cfg)
            raise Missing
        if out == "invalid":
            stats["invalid_runs"] += 1
        return out

    sess = Session(ids, oracle, use_closure=False, precheck=None)
    try:
        w = trim_diff_only(sess, groups)
    except Missing:
        return {"record": name, "complete": False, "missing_first": sorted(pending[0])}
    req = {a: set(b) for a, b in (r.get("requires") or {}).items()}
    closed = all(req.get(u, set()) <= set(w) for u in w)
    return {"record": name, "complete": True, "n_units": len(ids), "n_files": len(groups),
            "has_requires": bool(req), "trim_size": len(w), "trim_runs": sess.oracle_calls,
            "trim_invalid_runs": stats["invalid_runs"], "trim_closed": closed,
            "trim_witness": " ".join(sorted(w)), "shift_witness": " ".join(sorted(r["minimal"])),
            "trim_new_undefined_names": None if closed else _new_undefined(dp, w, ids),
            "shift_size": len(r["minimal"]), "same_as_shift": sorted(w) == sorted(r["minimal"]),
            "shift_reduction_runs": r["ablations"]["closure_only"]["oracle_calls"] if r.get("ablations") else None,
            "shift_total_runs": r["oracle_calls"],
            "plain_ddmin_runs": r["ablations"]["plain_ddmin"]["oracle_calls"] if r.get("ablations") else None}


def _undefined(files: dict) -> set[tuple[str, str]]:
    from pyflakes.api import check
    from pyflakes.reporter import Reporter
    import io
    out = set()
    for path, src in files.items():
        if not path.endswith(".py") or src is None:
            continue
        buf = io.StringIO()
        check(src, path, Reporter(buf, io.StringIO()))
        for line in buf.getvalue().splitlines():
            if "undefined name" in line:
                out.add((path, line.split("undefined name", 1)[1].strip()))
    return out


def _new_undefined(dp, witness, ids) -> int:
    """Undefined names (pyflakes) in the witness variant that the full patch does not have:
    a passing configuration that leaves a use without its binding."""
    return len(_undefined(dp.apply(witness)) - _undefined(dp.apply(ids)))


def _execute(name, r, inst, dp, cfg) -> str:
    from shift.oracle.runner import InstanceOracle
    with InstanceOracle(inst, timeout=900) as orc:
        orc.write_config(dp.apply(cfg), orc.protected_paths())
        rr = orc.run_tests(None)
        v = orc.verdict(rr, inst["FAIL_TO_PASS"], inst["PASS_TO_PASS"])
    out = "valid" if v.valid else ("error" if rr.timed_out else ("goal_fail" if not v.goal_ok else "pres_fail"))
    NEW.mkdir(parents=True, exist_ok=True)
    f = NEW / f"{name}.json"
    d = json.loads(f.read_text()) if f.exists() else {"record": name, "executed": []}
    d["executed"].append({"cfg": sorted(cfg), "outcome": out, "sec": round(rr.seconds, 2)})
    f.write_text(json.dumps(d))
    print(name, sorted(cfg), out, flush=True)
    return out


def _job(args):
    name, execute = args
    return replay(name, execute)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    names = []
    for p in sorted(REC.glob("*.json")):
        r = json.loads(p.read_text())
        if r["status"] == "ok" and len(r["units"]) >= 2:
            names.append(p.stem)
    with cf.ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(_job, [(n, a.execute) for n in names]))
    R = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    R.to_csv(OUT, index=False)
    print(f"multi-unit records={len(R)} complete={int(R.complete.sum())} incomplete={int((~R.complete).sum())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
