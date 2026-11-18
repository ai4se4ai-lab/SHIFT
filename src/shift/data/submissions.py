"""Fetch agent submissions (patches, reports, trajectories) from the public
SWE-bench submissions bucket (bash-only / mini-swe-agent track).

All systems in this track share one scaffold (mini-swe-agent), so differences
between systems are attributable mainly to the underlying LLM. Downloads are
idempotent: an existing non-empty file is never re-fetched.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from defusedxml import ElementTree as ET

BUCKET = "https://swe-bench-submissions.s3.amazonaws.com"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
LOG_FILES = ("patch.diff", "report.json")


def _get(url: str, retries: int = 4) -> bytes:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception:  # network hiccup; retry with backoff
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def list_prefix(prefix: str, delimiter: str | None = None) -> tuple[list[tuple[str, int]], list[str]]:
    """Return (keys with sizes, common prefixes) under prefix, following pagination."""
    keys, prefixes, token = [], [], None
    while True:
        q = f"list-type=2&max-keys=1000&prefix={urllib.parse.quote(prefix)}"
        if delimiter:
            q += f"&delimiter={urllib.parse.quote(delimiter)}"
        if token:
            q += f"&continuation-token={urllib.parse.quote(token)}"
        root = ET.fromstring(_get(f"{BUCKET}/?{q}"))
        for c in root.findall("s3:Contents", NS):
            keys.append((c.find("s3:Key", NS).text, int(c.find("s3:Size", NS).text)))
        for p in root.findall("s3:CommonPrefixes", NS):
            prefixes.append(p.find("s3:Prefix", NS).text)
        if root.find("s3:IsTruncated", NS).text != "true":
            return keys, prefixes
        token = root.find("s3:NextContinuationToken", NS).text


def list_systems(track: str = "bash-only") -> list[str]:
    _, prefixes = list_prefix(f"{track}/", "/")
    return [p.rstrip("/").split("/")[-1] for p in prefixes]


def fetch_system(track: str, system: str, out: Path, instance_ids: set[str],
                 with_trajs: bool, workers: int = 32) -> dict:
    """Download patch.diff/report.json (and optionally trajectories) of one system."""
    sysdir = out / system
    sysdir.mkdir(parents=True, exist_ok=True)
    keys, _ = list_prefix(f"{track}/{system}/")
    wanted = []
    for key, size in keys:
        m = re.match(rf"{re.escape(track)}/{re.escape(system)}/(logs|trajs)/([^/]+)/(.+)$", key)
        if not m:
            continue
        kind, iid, fname = m.groups()
        if iid not in instance_ids:
            continue
        if kind == "logs" and fname in LOG_FILES:
            wanted.append((key, sysdir / "logs" / iid / fname))
        elif kind == "trajs" and with_trajs and fname.endswith(".traj.json"):
            wanted.append((key, sysdir / "trajs" / f"{iid}.traj.json"))

    def job(item):
        key, dest = item
        if dest.exists() and dest.stat().st_size > 0:
            return 0
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = _get(f"{BUCKET}/{urllib.parse.quote(key)}")
        dest.write_bytes(data)
        return 1

    fetched = 0
    with cf.ThreadPoolExecutor(workers) as ex:
        for n in ex.map(job, wanted):
            fetched += n
    n_logs = len({p.parent.name for _, p in wanted if p.name == "patch.diff"})
    n_trajs = sum(1 for _, p in wanted if p.name.endswith(".traj.json"))
    manifest = {"system": system, "track": track, "instances_with_patch": n_logs,
                "trajectories": n_trajs, "files": len(wanted), "fetched_now": fetched,
                "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (sysdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main(argv=None) -> int:
    import pandas as pd

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="data/external/swebench_verified.parquet")
    ap.add_argument("--out", default="data/external/submissions")
    ap.add_argument("--track", default="bash-only")
    ap.add_argument("--systems", nargs="*", help="system ids; default = all in track")
    ap.add_argument("--trajs", action="store_true", help="also download trajectories")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    if a.list:
        print("\n".join(list_systems(a.track)))
        return 0
    ids = set(pd.read_parquet(a.dataset).instance_id)
    systems = a.systems or list_systems(a.track)
    for s in systems:
        m = fetch_system(a.track, s, Path(a.out), ids, a.trajs)
        print(json.dumps(m), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())


def read_resolved(report_path, instance_id: str) -> bool | None:
    """Resolution flag from a harness report.json (keyed by instance id or flat)."""
    try:
        r = json.loads(Path(report_path).read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(r, dict) and instance_id in r and isinstance(r[instance_id], dict):
        r = r[instance_id]
    v = r.get("resolved") if isinstance(r, dict) else None
    return bool(v) if v is not None else None
