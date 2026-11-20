"""v2 revision: run the implemented SHIFT-Intent frontend (Algorithm 1) on every
validated execution instance.

For each of the 295 instances:
  1. render the benchmark contract (shift.intent.benchmark) to
     results/processed/contracts/<instance>.intent;
  2. parse, check, and resolve it; verify that the compiled (T_g, T_p, eta, rho)
     equals the obligations the evaluated pipeline used (FAIL_TO_PASS, PASS_TO_PASS,
     envelope k = 6, two full-patch runs);
  3. statically seed one specification error of each class into the document and
     record whether compilation rejects it with the expected rule;
  4. execute the base revision (with the protected test patch) once in a fresh
     container and run the baseline validation (--execute).

Outputs: results/raw/revision/contracts_base/<instance>.json (base test statuses,
resumable), results/processed/revision/contracts.csv, contracts_mutants.csv.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
from shift.data.repos import load_dataset  # noqa: E402
from shift.intent.benchmark import contract_text  # noqa: E402
from shift.intent.dsl import ContractError, compile_contract, validate_baseline  # noqa: E402

CONTRACTS = ROOT / "results/processed/contracts"
BASE = ROOT / "results/raw/revision/contracts_base"
OUT = ROOT / "results/processed/revision"


def instances() -> list[str]:
    ids = []
    for p in sorted((ROOT / "results/raw/shift/main/records").glob("gold__*.json")):
        r = json.loads(p.read_text())
        if r["status"] == "ok":
            ids.append(r["instance_id"])
    return ids


# One seeded error per class. Each maps a valid document (and catalog) to an invalid one.
def _mutants(txt: str, cat):
    from shift.intent.dsl import Catalog
    first_goal = txt.split("test ", 1)[1].split("\n", 1)[0]
    pres = next(iter(cat.sets), None)
    out = {
        "syntax": (txt.replace("envelope import_rts", "envelope import-rts", 1), cat),
        "duplicate-block": (txt.replace("goal goal_1 {", "goal existing_behavior {", 1) if pres
                            else txt.replace("  envelope", "  goal goal_1 {\n    test " + first_goal + "\n  }\n  envelope", 1), cat),
        "unresolved-alias": (txt.replace(first_goal, first_goal + "_typo", 1), cat),
        "envelope-size": (txt.replace("top 6", "top 0"), cat),
        "repeats": (txt.replace("full_repeats 2", "full_repeats 1"), cat),
    }
    if pres:
        out["goal-cardinality"] = (txt.replace("test " + first_goal, "test " + pres, 1), cat)
        goal_test = cat.single[first_goal]
        out["overlap"] = (txt, Catalog(cat.single, {pres: list(cat.sets[pres]) + [goal_test]}, cat.version))
        out["empty-preservation"] = (txt, Catalog(cat.single, {pres: []}, cat.version))
    return out


def static_check(iid: str, inst: dict) -> tuple[dict, list[dict]]:
    txt, cat = contract_text(inst)
    CONTRACTS.mkdir(parents=True, exist_ok=True)
    (CONTRACTS / f"{iid}.intent").write_text(txt)
    k, digest = compile_contract(txt, cat, base_commit=inst["base_commit"], environment=f"sweb.eval.arm64.{iid}")
    row = {"instance_id": iid, "n_goal": len(k.goal_tests), "n_pres": len(k.preservation_tests),
           "lines": txt.count("\n"), "digest": digest,
           "matches_oracle": (list(k.goal_tests) == list(inst["FAIL_TO_PASS"])
                              and list(k.preservation_tests) == list(inst["PASS_TO_PASS"])
                              and k.envelope == ("import_rts", 6) and k.full_repeats == 2)}
    muts = []
    for rule, (mtxt, mcat) in _mutants(txt, cat).items():
        try:
            compile_contract(mtxt, mcat)
            got = []
        except ContractError as e:
            got = sorted({d.rule for d in e.diagnostics})
        muts.append({"instance_id": iid, "seeded": rule, "rejected": bool(got), "rules": "|".join(got),
                     "expected_rule_reported": rule in got})
    return row, muts


def run_base(iid: str) -> dict:
    f = BASE / f"{iid}.json"
    if f.exists():
        return json.loads(f.read_text())
    from shift.oracle.runner import InstanceOracle
    inst = load_dataset().loc[iid].to_dict()
    with InstanceOracle(inst, timeout=900) as orc:
        orc.write_config({}, orc.protected_paths())
        rr = orc.run_tests(None)
    d = {"instance_id": iid, "status": rr.status, "seconds": round(rr.seconds, 1), "timed_out": rr.timed_out,
         "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    BASE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d))
    print(iid, f"{rr.seconds:.0f}s", flush=True)
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="run the base revision in Docker")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(argv)
    df = load_dataset()
    ids = instances()
    rows, muts = [], []
    for iid in ids:
        r, m = static_check(iid, df.loc[iid].to_dict())
        rows.append(r)
        muts.extend(m)
    if a.execute:
        with cf.ProcessPoolExecutor(a.workers) as ex:
            list(ex.map(run_base, ids))
    for r in rows:
        f = BASE / f"{r['instance_id']}.json"
        if not f.exists():
            r["baseline"] = "not_executed"
            continue
        b = json.loads(f.read_text())
        inst = df.loc[r["instance_id"]].to_dict()
        txt, cat = contract_text(inst)
        try:
            compile_contract(txt, cat, base=b["status"])
            r["baseline"], r["baseline_detail"] = "ok", ""
        except ContractError as e:
            r["baseline"] = "mismatch"
            r["baseline_detail"] = "; ".join(d.message for d in e.diagnostics)
        r["base_seconds"] = b["seconds"]
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "contracts.csv", index=False)
    M = pd.DataFrame(muts)
    M.to_csv(OUT / "contracts_mutants.csv", index=False)
    R = pd.DataFrame(rows)
    print(f"instances={len(R)} matches_oracle={int(R.matches_oracle.sum())} "
          f"baseline={R.get('baseline', pd.Series(dtype=str)).value_counts().to_dict()}")
    print(M.groupby("seeded").agg(n=("rejected", "size"), rejected=("rejected", "sum"),
                                  expected=("expected_rule_reported", "sum")).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
