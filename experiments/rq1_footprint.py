"""RQ1: edit footprints of all bash-only systems and of the gold patches; exploration footprints
of the panel systems from their trajectories.

Outputs (results/processed/rq1/): edit_footprint.csv, exploration.csv, systems.csv
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import math
from pathlib import Path

import pandas as pd
import yaml

from shift.data.repos import list_files, load_dataset
from shift.data.submissions import read_resolved
from shift.footprint.metrics import edit_footprint, exploration_footprint, load_traj, patch_files
from shift.graph.imports import import_graph

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "data/external/submissions"


def systems(min_patches: int) -> pd.DataFrame:
    rows = []
    for d in sorted(SUB.iterdir()):
        n = len(list((d / "logs").glob("*/patch.diff"))) if (d / "logs").exists() else 0
        meta = ROOT / "data/external/swe-experiments/evaluation/verified" / d.name / "metadata.yaml"
        info = {}
        if meta.exists():
            try:
                info = (yaml.safe_load(meta.read_text()) or {}).get("info", {}) or {}
            except yaml.YAMLError:
                info = {}
        rows.append({"system": d.name, "n_patches": n, "included": n >= min_patches,
                     "name": info.get("name", d.name), "resolved_reported": info.get("resolved"),
                     "trajs": len(list((d / "trajs").glob("*.traj.json"))) if (d / "trajs").exists() else 0})
    return pd.DataFrame(rows)


def per_instance(iid: str, sys_list: list[str], panel: list[str]) -> tuple[list[dict], list[dict]]:
    df = load_dataset()
    inst = df.loc[iid]
    try:
        g = import_graph(inst.repo, inst.base_commit)
    except Exception:
        g = {}
    rows, xrows = [], []
    gold_fp = edit_footprint(inst.patch, inst.patch, inst.repo, inst.base_commit, g)
    rows.append({"instance_id": iid, "repo": inst.repo, "system": "gold", "resolved": True, **gold_fp})
    repo_files = None
    for s in sys_list:
        pf = SUB / s / "logs" / iid / "patch.diff"
        if not pf.exists():
            continue
        diff = pf.read_text(errors="surrogateescape")
        rep = SUB / s / "logs" / iid / "report.json"
        resolved = bool(read_resolved(rep, iid))
        fp = edit_footprint(diff, inst.patch, inst.repo, inst.base_commit, g) if diff.strip() else \
            {"n_files": 0, "empty": True}
        rows.append({"instance_id": iid, "repo": inst.repo, "system": s, "resolved": resolved,
                     "empty_patch": not diff.strip(), **fp})
        if s in panel:
            tp = SUB / s / "trajs" / f"{iid}.traj.json"
            traj = load_traj(tp) if tp.exists() else None
            if traj is not None:
                if repo_files is None:
                    repo_files = set(list_files(inst.repo, inst.base_commit))
                edited = {f["path"] for f in patch_files(diff, inst.repo)}
                xrows.append({"instance_id": iid, "repo": inst.repo, "system": s, "resolved": resolved,
                              "n_edited": len(edited), **exploration_footprint(traj, repo_files, edited)})
    return rows, xrows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    cfg = yaml.safe_load(open(ROOT / "configs/study.yaml"))
    out = ROOT / "results/processed/rq1"
    out.mkdir(parents=True, exist_ok=True)
    sy = systems(cfg["rq1"]["min_patches"])
    sy.to_csv(out / "systems.csv", index=False)
    sys_list = sy[sy.included].system.tolist()
    ids = load_dataset().instance_id.tolist()
    if a.limit:
        ids = ids[: a.limit]
    rows, xrows = [], []
    with cf.ProcessPoolExecutor(a.workers) as ex:
        for i, (r, x) in enumerate(ex.map(per_instance, ids, [sys_list] * len(ids), [cfg["panel"]] * len(ids)), 1):
            rows += r
            xrows += x
            if i % 50 == 0:
                print(f"{i}/{len(ids)}", flush=True)
    pd.DataFrame(rows).to_csv(out / "edit_footprint.csv", index=False)
    pd.DataFrame(xrows).to_csv(out / "exploration.csv", index=False)
    print(f"systems={len(sys_list)} rows={len(rows)} exploration_rows={len(xrows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
