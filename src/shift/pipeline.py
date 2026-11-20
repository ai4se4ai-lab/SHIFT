"""End-to-end SHIFT analysis of one patch on one SWE-bench instance.

Stages: decompose -> intent obligations -> counterfactual triage -> envelope
check and attribution. Every oracle execution is logged to the result record.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
import traceback
from dataclasses import asdict

from shift.counterfactual.triage import Session, triage
from shift.data.repos import load_dataset, read_file
from shift.envelope.select import select_envelope
from shift.oracle.runner import PASS_STATES, InstanceOracle
from shift.patch.edits import decompose, requires_relation, syntax_ok


def analyse_patch(instance_id: str, patch: str, label: str, *, envelope: bool = True,
                  k_env: int = 6, ablations: bool = False, timeout: int = 900,
                  contract=None) -> dict:
    """``contract`` is an optional compiled SHIFT-Intent :class:`~shift.intent.dsl.Contract`.
    When given, it supplies T_g, T_p, the envelope size and the full-patch repeats;
    otherwise the benchmark's FAIL_TO_PASS / PASS_TO_PASS lists are used directly
    (the two are identical for contracts produced by shift.intent.benchmark)."""
    df = load_dataset()
    inst = df.loc[instance_id].to_dict()
    repo, commit = inst["repo"], inst["base_commit"]
    t0 = time.time()
    rec: dict = {"instance_id": instance_id, "patch_label": label, "repo": repo, "status": "started"}
    dp = decompose(patch, repo, lambda p: read_file(repo, commit, p))
    protected = set()
    try:
        with InstanceOracle(inst, timeout=timeout) as orc:
            protected = orc.protected_paths()
            units = [u for u in dp.units if u.path not in protected]
            rec["overridden_units"] = [u.uid for u in dp.units if u.path in protected]
            ids = [u.uid for u in units]
            req = requires_relation(dp)
            req = {a: {b for b in bs if b in ids} for a, bs in req.items() if a in ids}
            rec["units"] = [{"uid": u.uid, "path": u.path, "kind": u.kind, "op": u.op, "start": u.start,
                             "n_removed": len(u.removed), "n_added": len(u.added)} for u in units]
            rec["requires"] = {a: sorted(b) for a, b in req.items() if b}
            if contract is not None:
                f2p, p2p = list(contract.goal_tests), list(contract.preservation_tests)
                k_env, repeats = contract.envelope[1], contract.full_repeats
                rec["contract"] = {"name": contract.name, "digest": contract.digest()}
            else:
                f2p, p2p, repeats = inst["FAIL_TO_PASS"], inst["PASS_TO_PASS"], 2
            runs: list[dict] = []

            def run_cfg(cfg, directives=None):
                orc.write_config(dp.apply(cfg), protected)
                return orc.run_tests(directives)

            def oracle(cfg):
                rr = run_cfg(cfg)
                v = orc.verdict(rr, f2p, p2p)
                out = "valid" if v.valid else ("error" if rr.timed_out else
                                               ("goal_fail" if not v.goal_ok else "pres_fail"))
                runs.append({"cfg": sorted(cfg), "outcome": out, "sec": round(rr.seconds, 2),
                             "n_fail_goal": len(v.failing_goal), "n_fail_pres": len(v.failing_pres)})
                return out

            pre = lambda cfg: syntax_ok(dp.apply(cfg))  # noqa: E731
            sess = Session(ids, oracle, requires=req, precheck=pre)
            tr = triage(sess, repeats_full=repeats, full_oracle=oracle)
            rec.update({"status": tr.status, "labels": tr.labels, "loo": tr.loo, "minimal": tr.minimal,
                        "oracle_calls": tr.oracle_calls, "precheck_rejections": tr.precheck_rejections,
                        "anomalies": tr.anomalies, "runs": runs})

            if ablations and tr.status == "ok":
                rec["ablations"] = _ablations(ids, req, oracle, pre, sess.cache)

            if envelope and tr.status == "ok":
                rec["envelope"] = _envelope(orc, inst, dp, ids, tr, req, protected, run_cfg, k_env, f2p)
            rec["oracle_seconds"] = round(orc.oracle_seconds, 1)
    except Exception as e:  # recorded, never silently dropped
        rec.update({"status": "error", "error": f"{type(e).__name__}: {e}",
                    "traceback": traceback.format_exc()[-2000:]})
    rec["wall_seconds"] = round(time.time() - t0, 1)
    return rec


def _ablations(ids, req, oracle, pre, cache) -> dict:
    """Oracle cost of alternative minimisation strategies, reusing cached outcomes as ground truth.

    Each variant gets a fresh Session (fresh accounting) whose oracle first consults
    the main session's cache, so ablations only pay for genuinely new configurations.
    """
    from shift.counterfactual.triage import ddmin, exhaustive_minimum, leave_one_out, reduce_closed

    def cached_oracle(cfg):
        return cache[cfg] if cfg in cache else oracle(cfg)

    out = {}
    for name, kw in {"plain_ddmin": dict(use_closure=False, precheck=None),
                     "closure_only": dict(use_closure=True, precheck=None),
                     "precheck_only": dict(use_closure=False, precheck=pre)}.items():
        s = Session(ids, cached_oracle, requires=req, **kw)
        m = reduce_closed(s, ddmin(s, ids))
        out[name] = {"minimal": m, "configs": s.oracle_calls + s.precheck_rejections,
                     "oracle_calls": s.oracle_calls, "precheck": s.precheck_rejections,
                     "invalid_oracle_runs": sum(1 for c, o, k in s.trace if k == "oracle" and o == "invalid")}
    s = Session(ids, cached_oracle, requires=req, precheck=pre)
    loo = leave_one_out(s)
    out["loo_only"] = {"necessary": sorted(u for u, o in loo.items() if o != "valid"),
                       "oracle_calls": s.oracle_calls}
    if len(ids) <= 8:
        s = Session(ids, cached_oracle, requires=req, precheck=pre)
        ex = exhaustive_minimum(s, ids, max_units=8)
        out["exhaustive"] = {"minima": [sorted(x) for x in (ex or [])], "oracle_calls": s.oracle_calls}
    return out


_REF_CACHE = Path(__file__).resolve().parents[2] / "results/raw/shift/envelope_reference_cache"


def _reference_runs(orc, inst, dp, protected, run_cfg, directives):
    """Base (twice) and reference-patch runs of the envelope. They depend only on the
    instance and the selected test modules, so they are computed once and shared by all
    patches of the instance (file cache; identical measurement)."""
    import hashlib
    from types import SimpleNamespace
    key = hashlib.sha256(json.dumps([inst["instance_id"], directives]).encode()).hexdigest()[:20]
    f = _REF_CACHE / f"{inst['instance_id']}__{key}.json"
    if f.exists():
        d = json.loads(f.read_text())
        mk = lambda x: SimpleNamespace(status=x["status"], seconds=x["seconds"], timed_out=x["timed_out"])  # noqa: E731
        return mk(d["b1"]), mk(d["b2"]), mk(d["gold"]), True
    repo, commit = inst["repo"], inst["base_commit"]
    b1, b2 = run_cfg([], directives), run_cfg([], directives)
    gold = decompose(inst["patch"], repo, lambda p: read_file(repo, commit, p))
    orc.write_config(gold.apply(gold.ids), protected)
    g = orc.run_tests(directives)
    _REF_CACHE.mkdir(parents=True, exist_ok=True)
    dump = lambda r: {"status": r.status, "seconds": r.seconds, "timed_out": r.timed_out}  # noqa: E731
    tmp = f.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"directives": directives, "b1": dump(b1), "b2": dump(b2), "gold": dump(g)}))
    os.replace(tmp, f)
    return b1, b2, g, False


def _passing(rr) -> set[str]:
    return {t for t, s in rr.status.items() if s in PASS_STATES}


def _envelope(orc, inst, dp, ids, tr, req, protected, run_cfg, k_env, goal_tests=None) -> dict:
    """Preservation envelope: regressions invisible to the benchmark tests, with attribution."""
    repo, commit = inst["repo"], inst["base_commit"]
    edited_src = sorted({u.path for u in dp.units if u.kind == "source" and u.uid in ids})
    directives = select_envelope(repo, commit, edited_src, orc.protected_paths(), k=k_env)
    env: dict = {"directives": directives}
    if not directives:
        env["status"] = "empty"
        return env
    b1, b2, g, cached = _reference_runs(orc, inst, dp, protected, run_cfg, directives)
    env["reference_runs_cached"] = cached
    stable_pass = _passing(b1) & _passing(b2)
    flaky = {t for t in set(b1.status) | set(b2.status) if b1.status.get(t) != b2.status.get(t)}
    full = run_cfg(ids, directives)
    gold_fail = stable_pass - _passing(g)
    goal_tests = set(inst["FAIL_TO_PASS"] if goal_tests is None else goal_tests)
    regress = sorted(stable_pass - _passing(full) - gold_fail - goal_tests)
    env.update({"n_tests": len(stable_pass), "n_flaky": len(flaky), "gold_changes": len(gold_fail),
                "regressions": regress, "timed_out": any(r.timed_out for r in (b1, b2, g, full)),
                "seconds": round(full.seconds + (0 if cached else b1.seconds + b2.seconds + g.seconds), 1)})
    if not regress:
        env["status"] = "clean"
        return env
    minimal = set(tr.minimal)
    dm = run_cfg(sorted(minimal), directives)
    in_min = sorted(set(regress) - _passing(dm))
    env["regressions_in_minimal"] = in_min
    harmful = {}
    for u in ids:
        if u in minimal:
            continue
        # Add-back under the transitive requires closure (Algorithm 3). Before the v2
        # revision only direct requirements were added; for all 25 recorded regression
        # records the two coincide (analysis/revision/v2_checks.py).
        cfg = sorted(_closure(minimal | {u}, req))
        rr = run_cfg(cfg, directives)
        hit = sorted((set(regress) - set(in_min)) - _passing(rr))
        if hit:
            harmful[u] = hit
    env["harmful_units"] = harmful
    env["status"] = "regression"
    return env


def _closure(s, req) -> set[str]:
    s, todo = set(s), list(s)
    while todo:
        for b in req.get(todo.pop(), ()):
            if b not in s:
                s.add(b)
                todo.append(b)
    return s


def to_jsonl(rec: dict) -> str:
    return json.dumps(rec, default=lambda o: asdict(o) if hasattr(o, "__dataclass_fields__") else str(o))
