"""Audit of the exhaustive-minimum ablation (revision v1; no new executions).

Diagnosis: ``exhaustive_minimum`` enumerates generator subsets by size *before*
closure, but evaluates their closure. A small generator whose closure is large can
therefore be returned as the "minimum" before smaller valid closed sets are reached.

This script re-derives, from the outcomes already recorded in each record's ``runs``
(and the main session's labels), the smallest *closed* configuration observed valid,
and checks whether every closed configuration of smaller cardinality has an observed
non-valid outcome. Under the deterministic-oracle assumption, a certified record proves
that the SHIFT witness has minimum cardinality among closed configurations.

Inputs : results/raw/shift/main/records/*.json   (read only)
Outputs: results/processed/revision/exhaustive_audit.csv, exhaustive_audit.json
"""
from __future__ import annotations

import itertools
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / "results/raw/shift/main/records"
OUT = ROOT / "results/processed/revision"


def closure(s, req):
    out, st = set(s), list(s)
    while st:
        for y in req.get(st.pop(), ()):
            if y not in out:
                out.add(y); st.append(y)
    return frozenset(out)


def closed_sets(ids, req):
    seen = set()
    for k in range(len(ids) + 1):
        for c in itertools.combinations(ids, k):
            cl = closure(c, req)
            if cl == frozenset(c) and cl not in seen:
                seen.add(cl); yield cl


_JOBS = None


def _patch_text(instance_id, label):
    global _JOBS
    if _JOBS is None:
        _JOBS = {}
        for line in (ROOT / "results/processed/jobs/shift_jobs.jsonl").open():
            j = json.loads(line)
            _JOBS[(j["instance_id"], j["label"])] = j["patch"]
    return _JOBS.get((instance_id, label))


def _precheck_fn(r):
    """Recompute the static syntax pre-check (no execution) for configurations of r."""
    from shift.data.repos import load_dataset, read_file
    from shift.patch.edits import decompose, syntax_ok
    patch = _patch_text(r["instance_id"], r["patch_label"])
    if patch is None:
        return None
    inst = load_dataset().loc[r["instance_id"]]
    dp = decompose(patch, inst.repo, lambda p: read_file(inst.repo, inst.base_commit, p))
    known = {u["uid"]: (u["path"], u["start"]) for u in r["units"]}
    if any(known.get(u.uid, (u.path, u.start)) != (u.path, u.start) for u in dp.units):
        return None                                   # decomposition drifted: do not use
    return lambda cfg: syntax_ok(dp.apply(cfg))


def audit(r):
    ids = [u["uid"] for u in r["units"]]
    req = {a: set(b) for a, b in (r.get("requires") or {}).items()}
    obs = defaultdict(set)
    for run in r.get("runs", []):
        obs[frozenset(run["cfg"])].add(run["outcome"])
    conflicts = sum(1 for v in obs.values() if len(v) > 1)
    valid = lambda s: obs.get(s) == {"valid"}           # noqa: E731
    nonvalid = lambda s: s in obs and "valid" not in obs[s] and "error" not in obs[s]  # noqa: E731
    cs = sorted(closed_sets(ids, req), key=len)
    obs_valid = [s for s in cs if valid(s)]
    d = frozenset(r["minimal"])
    m_obs = min((len(s) for s in obs_valid), default=None)
    smaller = [s for s in cs if len(s) < len(d)]
    unobserved = [s for s in smaller if not nonvalid(s) and not valid(s)]
    n_precheck_resolved = 0
    if unobserved and r.get("precheck_rejections", 0):
        pc = _precheck_fn(r)
        if pc is not None:
            still = [s for s in unobserved if pc(s)]
            n_precheck_resolved = len(unobserved) - len(still)
            unobserved = still
    smaller_valid = [s for s in smaller if valid(s)]
    ex = (r.get("ablations") or {}).get("exhaustive") or {}
    reported = min((len(m) for m in ex.get("minima", [])), default=None)
    rep_closed_sizes = sorted({len(closure(m, req)) for m in ex.get("minima", [])})
    return {
        "record": f'{r["patch_label"]}__{r["instance_id"]}', "instance_id": r["instance_id"],
        "patch_label": r["patch_label"], "n_units": len(ids), "n_closed_sets": len(cs),
        "has_requires": bool(req), "witness_size": len(d), "witness_observed_valid": valid(d),
        "reported_exhaustive_min": reported, "smallest_observed_valid_closed": m_obs,
        "n_smaller_closed": len(smaller), "n_smaller_unobserved": len(unobserved),
        "n_smaller_observed_valid": len(smaller_valid), "conflicting_cfgs": conflicts,
        "certified_min": len(smaller_valid) == 0 and len(unobserved) == 0 and valid(d),
        "precheck_rejections": r.get("precheck_rejections", 0),
        "n_smaller_resolved_by_static_precheck": n_precheck_resolved,
    }


def main():
    rows = []
    for f in sorted(REC.glob("*.json")):
        r = json.loads(f.read_text())
        if r.get("status") != "ok" or "exhaustive" not in (r.get("ablations") or {}):
            continue
        rows.append(audit(r))
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "exhaustive_audit.csv", index=False)
    disc = df[df.reported_exhaustive_min != df.witness_size]
    s = {
        "n_records": len(df),
        "reported_equal_witness": int((df.reported_exhaustive_min == df.witness_size).sum()),
        "reported_discrepant": disc[["record", "n_units", "has_requires", "witness_size",
                                     "reported_exhaustive_min", "smallest_observed_valid_closed",
                                     "n_smaller_unobserved", "certified_min"]].to_dict("records"),
        "certified_min": int(df.certified_min.sum()),
        "not_certified": int((~df.certified_min).sum()),
        "smaller_valid_found": int((df.n_smaller_observed_valid > 0).sum()),
        "not_certified_with_unobserved": int(((~df.certified_min) & (df.n_smaller_unobserved > 0)).sum()),
        "records_with_conflicting_outcomes": int((df.conflicting_cfgs > 0).sum()),
        "not_certified_precheck": int(((~df.certified_min) & (df.precheck_rejections > 0)).sum()),
        "witness_not_observed_valid": int((~df.witness_observed_valid).sum()),
    }
    (OUT / "exhaustive_audit.json").write_text(json.dumps(s, indent=1, default=str))
    print(json.dumps(s, indent=1, default=str))


if __name__ == "__main__":
    main()
