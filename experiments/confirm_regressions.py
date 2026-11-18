"""Confirm envelope regressions by independent re-execution (applied uniformly after the runs).

For every record with envelope status `regression`, re-run the full patch on the envelope
in a fresh container. A regression is confirmed only if the test fails again. Harmful-unit
attributions are re-checked: configuration D* ∪ cl({u}) is re-run and u stays harmful only if
it again fails a confirmed regression test that D* alone does not fail. The original fields are
kept; confirmed results are written to `envelope.confirmation` and the record status fields
`envelope.status_confirmed`, `envelope.harmful_units_confirmed`.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
from pathlib import Path

from shift.data.repos import load_dataset, read_file
from shift.oracle.runner import PASS_STATES, InstanceOracle
from shift.patch.edits import closure, decompose, requires_relation


def _passing(rr):
    return {t for t, s in rr.status.items() if s in PASS_STATES}


def confirm(path: str, jobs: dict) -> str:
    r = json.loads(Path(path).read_text())
    e = r.get("envelope") or {}
    if e.get("status") != "regression" or "confirmation" in e:
        return f"skip {Path(path).stem}"
    key = Path(path).stem
    job = jobs[key]
    inst = load_dataset().loc[r["instance_id"]].to_dict()
    dp = decompose(job["patch"], inst["repo"], lambda p: read_file(inst["repo"], inst["base_commit"], p))
    ids = [u["uid"] for u in r["units"]]
    req = requires_relation(dp)
    req = {a: {b for b in bs if b in ids} for a, bs in req.items() if a in ids}
    directives = e["directives"]
    with InstanceOracle(inst, timeout=900) as orc:
        prot = orc.protected_paths()

        def run(cfg):
            orc.write_config(dp.apply(cfg), prot)
            return orc.run_tests(directives)
        full = run(ids)
        confirmed = sorted(set(e["regressions"]) - _passing(full))
        harmful = {}
        if confirmed:
            dm = run(sorted(r["minimal"]))
            base_fail = set(confirmed) - _passing(dm)
            for u in e.get("harmful_units", {}):
                cfg = sorted(closure(set(r["minimal"]) | {u}, req))
                rr = run(cfg)
                hit = sorted((set(confirmed) - base_fail) - _passing(rr))
                if hit:
                    harmful[u] = hit
        else:
            base_fail = set()
    e["confirmation"] = {"confirmed": confirmed, "unconfirmed": sorted(set(e["regressions"]) - set(confirmed)),
                         "in_minimal": sorted(base_fail), "timed_out": full.timed_out}
    e["status_confirmed"] = "regression" if confirmed else "clean"
    e["harmful_units_confirmed"] = harmful
    r["envelope"] = e
    tmp = Path(path).with_suffix(".ctmp")
    tmp.write_text(json.dumps(r))
    os.replace(tmp, path)
    return f"{key}: {len(e['regressions'])} -> {len(confirmed)} confirmed, harmful {sorted(harmful)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    jobs = {}
    for l in open(a.jobs):
        j = json.loads(l)
        jobs[f"{j['label']}__{j['instance_id']}"] = j
    recs = sorted(str(p) for p in Path(a.run, "records").glob("*.json"))
    with cf.ProcessPoolExecutor(a.workers) as ex:
        for msg in ex.map(confirm, recs, [jobs] * len(recs)):
            if not msg.startswith("skip"):
                print(msg, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
