"""Module-level import graph of a repository revision (package sources only)."""
from __future__ import annotations

import ast
import subprocess
from collections import deque
from functools import lru_cache

from shift.data.repos import list_files, repo_dir
from shift.patch.edits import PKG_ROOTS, TEST_PAT


def module_name(path: str, repo: str) -> str | None:
    root = PKG_ROOTS.get(repo, "")
    if not path.endswith(".py"):
        return None
    p = path[:-3]
    strip = {"pytest-dev/pytest": "src/", "pallets/flask": "src/", "matplotlib/matplotlib": "lib/"}.get(repo, "")
    if strip and p.startswith(strip):
        p = p[len(strip):]
    if p.endswith("/__init__"):
        p = p[: -len("/__init__")]
    return p.replace("/", ".") if path.startswith(root) or not root else None


def _batch_read(repo: str, commit: str, paths: list[str]) -> dict[str, str]:
    inp = "".join(f"{commit}:{p}\n" for p in paths).encode()
    r = subprocess.run(["git", "--git-dir", str(repo_dir(repo)), "cat-file", "--batch"],
                       input=inp, capture_output=True, check=True)
    out, data, i = {}, r.stdout, 0
    for p in paths:
        nl = data.index(b"\n", i)
        header = data[i:nl].split()
        i = nl + 1
        if len(header) < 3 or header[1] == b"missing":
            continue
        size = int(header[2])
        out[p] = data[i:i + size].decode("utf-8", errors="replace")
        i += size + 1
    return out


def _resolve(mod: str, is_pkg: bool, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    parts = mod.split(".")
    base = parts if is_pkg else parts[:-1]
    base = base[: len(base) - (node.level - 1)] if node.level > 1 else base
    return ".".join(base + ([node.module] if node.module else []))


@lru_cache(maxsize=8)
def import_graph(repo: str, commit: str) -> dict[str, set[str]]:
    """Undirected adjacency between package modules (tests excluded)."""
    files = [f for f in list_files(repo, commit)
             if f.endswith(".py") and not TEST_PAT.search(f) and module_name(f, repo)]
    src = _batch_read(repo, commit, files)
    mods = {module_name(f, repo): f for f in files}
    adj: dict[str, set[str]] = {m: set() for m in mods}

    def target(name: str) -> str | None:
        while name:
            if name in mods:
                return name
            name = name.rpartition(".")[0]
        return None

    for m, f in mods.items():
        try:
            tree = ast.parse(src.get(f, ""))
        except (SyntaxError, ValueError):
            continue
        is_pkg = f.endswith("__init__.py")
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                b = _resolve(m, is_pkg, node)
                names = [b] + [f"{b}.{a.name}" for a in node.names]
            for n in names:
                t = target(n)
                if t and t != m:
                    adj[m].add(t)
                    adj[t].add(m)
    return adj


def distances_from(adj: dict[str, set[str]], src: str, limit: int | None = None) -> dict[str, int]:
    dist = {src: 0}
    q = deque([src])
    while q:
        x = q.popleft()
        if limit is not None and dist[x] >= limit:
            continue
        for y in adj.get(x, ()):
            if y not in dist:
                dist[y] = dist[x] + 1
                q.append(y)
    return dist
