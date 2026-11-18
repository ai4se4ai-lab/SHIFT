"""Run SHIFT over a job list in parallel (resumable; one JSON record per job).

Job file: JSONL with {"instance_id", "label", "patch_path" | "patch"}.
Usage: python experiments/run_shift.py --jobs J.jsonl --out results/raw/shift/RUN --workers 14
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import time
from pathlib import Path

from shift.pipeline import analyse_patch, to_jsonl


def _key(job: dict) -> str:
    return f"{job['label']}__{job['instance_id']}"


def _run(job: dict, out: str, envelope: bool, ablations: bool, k_env: int, timeout: int) -> str:
    patch = job.get("patch") or Path(job["patch_path"]).read_text(errors="surrogateescape")
    rec = analyse_patch(job["instance_id"], patch, job["label"], envelope=envelope,
                        k_env=k_env, ablations=ablations, timeout=timeout)
    rec.update({k: v for k, v in job.items() if k not in ("patch",)})
    rec["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    dest = Path(out) / "records" / f"{_key(job)}.json"
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(to_jsonl(rec))
    os.replace(tmp, dest)
    return f"{_key(job)} {rec['status']} calls={rec.get('oracle_calls')} {rec.get('wall_seconds')}s"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--no-envelope", action="store_true")
    ap.add_argument("--ablations", action="store_true")
    ap.add_argument("--k-env", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    (Path(a.out) / "records").mkdir(parents=True, exist_ok=True)
    jobs = [json.loads(l) for l in open(a.jobs) if l.strip()]
    done = {p.stem for p in (Path(a.out) / "records").glob("*.json")}
    todo = [j for j in jobs if _key(j) not in done]
    if a.limit:
        todo = todo[: a.limit]
    print(f"{len(jobs)} jobs, {len(done)} done, {len(todo)} to run", flush=True)
    with cf.ProcessPoolExecutor(a.workers) as ex:
        futs = {ex.submit(_run, j, a.out, not a.no_envelope, a.ablations, a.k_env, a.timeout): j for j in todo}
        for i, f in enumerate(cf.as_completed(futs), 1):
            try:
                print(f"[{i}/{len(todo)}] {f.result()}", flush=True)
            except Exception as e:  # infrastructure failure: logged, job left for resume
                print(f"[{i}/{len(todo)}] FAILED {_key(futs[f])}: {e}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
