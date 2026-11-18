"""Flatten SHIFT raw records into analysis tables (patch-level and unit-level)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from shift.data.repos import load_dataset
from shift.graph.imports import distances_from, import_graph, module_name

ROOT = Path(__file__).resolve().parents[1]


def load_records(run: str) -> list[dict]:
    recs = []
    for f in sorted((ROOT / "results/raw/shift" / run / "records").glob("*.json")):
        recs.append(json.loads(f.read_text()))
    return recs


def _issue_mentions(text: str, path: str) -> bool:
    """Does the issue mention the file, its module path, or its basename stem (>= 5 chars)?"""
    stem = Path(path).stem
    mod = path[:-3].replace("/", ".") if path.endswith(".py") else path
    t = text or ""
    return (path in t) or (mod in t) or (len(stem) >= 5 and stem != "__init__" and re.search(rf"\b{re.escape(stem)}\b", t) is not None)


def unit_table(recs: list[dict]) -> pd.DataFrame:
    df = load_dataset()
    rows = []
    for r in sorted(recs, key=lambda x: x["instance_id"]):     # keeps the import-graph cache warm
        if r.get("status") != "ok":
            continue
        inst = df.loc[r["instance_id"]]
        gold_files = set(re.findall(r"diff --git a/(\S+)", inst.patch))
        g = import_graph(inst.repo, inst.base_commit)
        gmods = [m for p in gold_files if (m := module_name(p, inst.repo)) and m in g]
        env = r.get("envelope") or {}
        harmful = set(env.get("harmful_units_confirmed", env.get("harmful_units", {})) or {})
        for u in r["units"]:
            m = module_name(u["path"], inst.repo)
            dist = None
            if m in g and gmods:
                dm = distances_from(g, m, limit=6)
                ds = [dm[x] for x in gmods if x in dm]
                dist = min(ds) if ds else None
            lab = r["labels"][u["uid"]]
            rows.append({
                "instance_id": r["instance_id"], "repo": r["repo"], "label": r["patch_label"],
                "uid": u["uid"], "path": u["path"], "kind": u["kind"], "op": u["op"],
                "churn": u["n_added"] + u["n_removed"], "shift_label": lab,
                "needed": lab in ("N", "J"), "harmful": u["uid"] in harmful,
                "in_gold_file": u["path"] in gold_files,
                "issue_mentions_file": _issue_mentions(inst.problem_statement, u["path"]),
                "gold_dist": dist, "n_units_patch": len(r["units"]),
                "inj_target": r.get("inj_target"), "inj_op": r.get("inj_op"),
            })
    return pd.DataFrame(rows)


def patch_table(recs: list[dict]) -> pd.DataFrame:
    rows = []
    for r in recs:
        e = dict(r.get("envelope") or {})
        if "confirmation" in e:                        # regressions confirmed by re-execution
            c = e["confirmation"]
            e["status"] = e["status_confirmed"]
            e["regressions"] = c["confirmed"]
            e["regressions_in_minimal"] = c["in_minimal"]
            e["harmful_units"] = e["harmful_units_confirmed"]
        labs = list((r.get("labels") or {}).values())
        abl = r.get("ablations") or {}
        rows.append({
            "instance_id": r["instance_id"], "repo": r.get("repo"), "label": r["patch_label"],
            "status": r["status"], "n_units": len(r.get("units", [])), "n_N": labs.count("N"),
            "n_J": labs.count("J"), "n_U": labs.count("U"), "n_C": labs.count("C"), "n_X": labs.count("X"),
            "minimal_size": len(r.get("minimal", [])), "oracle_calls": r.get("oracle_calls"),
            "precheck_rejections": r.get("precheck_rejections"), "oracle_seconds": r.get("oracle_seconds"),
            "wall_seconds": r.get("wall_seconds"), "anomalies": len(r.get("anomalies", []) or []),
            "env_status": e.get("status"), "env_tests": e.get("n_tests"), "env_flaky": e.get("n_flaky"),
            "env_regressions": len(e.get("regressions", []) or []),
            "env_regressions_in_minimal": len(e.get("regressions_in_minimal", []) or []),
            "env_harmful_units": len(e.get("harmful_units", {}) or {}),
            "env_seconds": e.get("seconds"), "env_gold_changes": e.get("gold_changes"),
            "abl_plain_calls": (abl.get("plain_ddmin") or {}).get("oracle_calls"),
            "abl_plain_invalid_runs": (abl.get("plain_ddmin") or {}).get("invalid_oracle_runs"),
            "abl_closure_calls": (abl.get("closure_only") or {}).get("oracle_calls"),
            "abl_precheck_calls": (abl.get("precheck_only") or {}).get("oracle_calls"),
            "abl_loo_calls": (abl.get("loo_only") or {}).get("oracle_calls"),
            "abl_exh_calls": (abl.get("exhaustive") or {}).get("oracle_calls"),
            "abl_exh_minsize": min((len(m) for m in (abl.get("exhaustive") or {}).get("minima", [])), default=None),
            "abl_loo_necessary": len((abl.get("loo_only") or {}).get("necessary", [])),
            "inj_target": r.get("inj_target"), "inj_op": r.get("inj_op"),
            "error": r.get("error"), "anomaly_text": "; ".join(r.get("anomalies", []) or []),
        })
    return pd.DataFrame(rows)
