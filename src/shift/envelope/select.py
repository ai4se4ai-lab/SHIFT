"""Dependency-selected preservation envelope (regression test selection).

Selects test modules beyond the benchmark's own test files that exercise the
modules a patch edits: a test file scores 3 for importing an edited module
directly, 1 for importing its parent package (depth >= 3), and 3 for a
file-name match (``test_<module>.py``). The top-k files form the envelope.
This is a static, approximate RTS; its recall is a measured quantity (RQ3).
"""
from __future__ import annotations

import re

from shift.data.repos import list_files
from shift.graph.imports import _batch_read, module_name
from shift.oracle.runner import django_label
from shift.patch.edits import TEST_PAT


_GENERIC = {"contrib", "utils", "core", "tests", "test", "base", "__init__", "functions", "elementary",
            "db", "models", "backends", "fields", "sql", "options", "views", "forms"}


def _test_files(repo: str, commit: str) -> list[str]:
    files = list_files(repo, commit)
    if repo == "django/django":
        return [f for f in files if f.startswith("tests/") and f.endswith(".py")
                and "/" in f[len("tests/"):] and f.rsplit("/", 1)[-1].startswith("test")]
    return [f for f in files if TEST_PAT.search(f) and f.endswith(".py")
            and f.rsplit("/", 1)[-1].startswith("test_")]


def select_envelope(repo: str, commit: str, edited_src: list[str], exclude: list[str],
                    k: int = 6) -> list[str]:
    """Return test directives (repo-specific form) for the envelope."""
    mods = [m for p in edited_src if (m := module_name(p, repo))]
    if not mods:
        return []
    tests = [t for t in _test_files(repo, commit) if t not in set(exclude)]
    bench_dirs = {e.rsplit("/", 1)[0] for e in exclude if "/" in e}
    contents = _batch_read(repo, commit, tests)
    scored = []
    for t, src in contents.items():
        s = 0
        imports = "\n".join(re.findall(r"^[ \t]*(?:from[ \t]+\S+[ \t]+import[^\n]+|import[ \t][^\n]+)", src, re.M))
        for m in mods:
            leaf = m.rsplit(".", 1)[-1]
            parent = m.rsplit(".", 1)[0]
            if re.search(rf"(?<![\w.]){re.escape(m)}(?![\w])", imports):
                s += 3
            elif parent.count(".") >= 2 and re.search(rf"from {re.escape(parent)} import [^\n]*\b{re.escape(leaf)}\b", src):
                s += 3
            elif parent.count(".") >= 2 and re.search(rf"(?<![\w.]){re.escape(parent)}(?![\w])", imports):
                s += 1
            if t.rsplit("/", 1)[-1] in (f"test_{leaf}.py", f"tests_{leaf}.py"):
                s += 3
            # app/package affinity: tests/auth_tests/... for django.contrib.auth.*,
            # sympy/core/tests/... for sympy.core.*
            comps = [c for c in m.split(".")[1:] if c not in _GENERIC]
            test_dirs = t.split("/")[:-1]
            if any(c and any(c in d for d in test_dirs) for c in comps):
                s += 2
        if t.rsplit("/", 1)[0] in bench_dirs:
            s += 2
        if s >= 2:
            scored.append((-s, t))
    chosen = [t for _, t in sorted(scored)[:k]]
    if repo == "django/django":
        return [django_label(t) for t in chosen]
    return chosen
