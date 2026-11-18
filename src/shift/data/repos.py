"""Read-only access to benchmark repositories at specific commits (bare git clones)."""
from __future__ import annotations

import functools
import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "cache" / "repos"
DATASET = ROOT / "data" / "external" / "swebench_verified.parquet"


def repo_dir(repo: str) -> Path:
    return CACHE / (repo.replace("/", "__") + ".git")


def ensure_clone(repo: str) -> Path:
    d = repo_dir(repo)
    if not d.exists():
        d.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--bare", "-q", f"https://github.com/{repo}.git", str(d)], check=True)
    return d


def git(repo: str, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "--git-dir", str(repo_dir(repo)), *args],
                       capture_output=True, text=True, errors="replace", check=False)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr[:300]}")
    return r.stdout


def read_file(repo: str, commit: str, path: str) -> str | None:
    r = subprocess.run(["git", "--git-dir", str(repo_dir(repo)), "show", f"{commit}:{path}"],
                       capture_output=True, check=False)
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", errors="surrogateescape")


def list_files(repo: str, commit: str) -> list[str]:
    return git(repo, "ls-tree", "-r", "--name-only", commit).splitlines()


@functools.lru_cache(maxsize=1)
def load_dataset() -> pd.DataFrame:
    df = pd.read_parquet(DATASET)
    for col in ("FAIL_TO_PASS", "PASS_TO_PASS"):
        df[col] = df[col].apply(lambda s: json.loads(s) if isinstance(s, str) else list(s))
    return df.set_index("instance_id", drop=False)
