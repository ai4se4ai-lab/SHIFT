"""Edit decomposition: unified diff -> atomic change blocks ("units").

A *unit* is a maximal run of consecutive added/removed lines inside a diff hunk
(context lines separate units). New and deleted files are single units.
Applying any subset of units to the base revision yields a concrete program
variant; this is what the counterfactual analysis enumerates.
"""
from __future__ import annotations

import ast
import builtins
import keyword
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable

from unidiff import PatchSet

TEST_PAT = re.compile(r"(^|/)(tests?|testing)(/|$)|(^|/)test_[^/]*\.py$|_tests?\.py$|(^|/)conftest\.py$")
PKG_ROOTS = {
    "django/django": "django/", "sympy/sympy": "sympy/", "sphinx-doc/sphinx": "sphinx/",
    "matplotlib/matplotlib": "lib/", "scikit-learn/scikit-learn": "sklearn/",
    "astropy/astropy": "astropy/", "pydata/xarray": "xarray/", "pytest-dev/pytest": "src/",
    "pylint-dev/pylint": "pylint/", "psf/requests": "requests/", "mwaskom/seaborn": "seaborn/",
    "pallets/flask": "src/flask/",
}


def file_kind(path: str, repo: str) -> str:
    """Classify a path as 'test', 'source' (inside the package) or 'aux'."""
    if "/" not in path:          # repository-root scripts (e.g. reproduce.py, test_fix.py)
        return "aux"
    if TEST_PAT.search(path):
        return "test"
    root = PKG_ROOTS.get(repo)
    if root and path.startswith(root):
        return "source"
    return "aux"


@dataclass(frozen=True)
class Unit:
    uid: str                 # stable id, e.g. "u03"
    path: str                # file path after the patch (old path for deletions)
    start: int               # 0-based index into the base file where removal/insertion begins
    removed: tuple[str, ...]
    added: tuple[str, ...]
    kind: str                # source | test | aux
    op: str = "modify"       # modify | add_file | delete_file

    @property
    def churn(self) -> int:
        return len(self.removed) + len(self.added)


@dataclass
class DecomposedPatch:
    units: list[Unit]
    base_files: dict[str, str | None]   # path -> base content (None if file is new)
    binary_or_skipped: list[str] = field(default_factory=list)

    @property
    def ids(self) -> list[str]:
        return [u.uid for u in self.units]

    def unit(self, uid: str) -> Unit:
        return next(u for u in self.units if u.uid == uid)

    def files(self) -> list[str]:
        return sorted({u.path for u in self.units})

    def apply(self, selected: Iterable[str]) -> dict[str, str | None]:
        """Return path -> new content (None = file absent) for every touched file."""
        sel = set(selected)
        out: dict[str, str | None] = {}
        for path in self.files():
            base = self.base_files.get(path)
            units = [u for u in self.units if u.path == path and u.uid in sel]
            if any(u.op == "delete_file" for u in units):
                out[path] = None
                continue
            if any(u.op == "add_file" for u in units):
                out[path] = "".join(units[0].added)
                continue
            if base is None:            # new file whose unit is not selected
                out[path] = None
                continue
            lines = base.splitlines(keepends=True)
            for u in sorted(units, key=lambda x: x.start, reverse=True):
                assert tuple(lines[u.start:u.start + len(u.removed)]) == u.removed, \
                    f"base mismatch applying {u.uid} to {path}"
                lines[u.start:u.start + len(u.removed)] = list(u.added)
            out[path] = "".join(lines)
        return out


def _line_text(line) -> str:
    v = line.value
    return v if v.endswith("\n") else v + "\n"


def decompose(diff_text: str, repo: str, base_reader: Callable[[str], str | None]) -> DecomposedPatch:
    """Split a unified diff into units. ``base_reader(path)`` returns base content or None."""
    ps = PatchSet(diff_text)
    units: list[Unit] = []
    base_files: dict[str, str | None] = {}
    skipped: list[str] = []
    n = 0

    def nid() -> str:
        nonlocal n
        n += 1
        return f"u{n:02d}"

    for pf in ps:
        if pf.is_binary_file:
            skipped.append(pf.path)
            continue
        path = pf.target_file[2:] if pf.target_file.startswith("b/") else pf.path
        if pf.is_removed_file:
            path = pf.source_file[2:] if pf.source_file.startswith("a/") else pf.path
        kind = file_kind(path, repo)
        if pf.is_added_file:
            base_files[path] = None
            added = tuple(_line_text(l) for h in pf for l in h if l.is_added)
            units.append(Unit(nid(), path, 0, (), added, kind, "add_file"))
            continue
        base = base_reader(path)
        if base is None:
            raise FileNotFoundError(f"base revision of modified file not readable: {path}")
        base_files[path] = base
        if pf.is_removed_file:
            units.append(Unit(nid(), path, 0, tuple((base or "").splitlines(True)), (), kind, "delete_file"))
            continue
        if pf.source_file[2:] != path:      # renames are not decomposed further
            skipped.append(path)
            continue
        base_lines = [l.rstrip("\n") for l in base.splitlines()]
        for h in pf:
            cur_removed: list[str] = []
            cur_added: list[str] = []
            start = None
            pos = _locate_hunk(h, base_lines, path)   # 0-based; tolerant to offsets like `git apply`
            for line in h:
                if line.is_context:
                    if cur_removed or cur_added:
                        units.append(Unit(nid(), path, start, tuple(cur_removed), tuple(cur_added), kind))
                        cur_removed, cur_added, start = [], [], None
                    pos += 1
                elif line.is_removed:
                    if start is None:
                        start = pos
                    cur_removed.append(_line_text(line))
                    pos += 1
                elif line.is_added:
                    if start is None:
                        start = pos
                    cur_added.append(_line_text(line))
            if cur_removed or cur_added:
                units.append(Unit(nid(), path, start, tuple(cur_removed), tuple(cur_added), kind))
    # Repair "\ No newline at end of file": unidiff strips the marker; ensure base lines match.
    dp = DecomposedPatch(units, base_files, skipped)
    _fix_eof_newlines(dp)
    return dp


def _locate_hunk(h, base_lines: list[str], path: str) -> int:
    """Actual 0-based start of a hunk: nearest exact match of its pre-image to the declared line."""
    src = [l.value.rstrip("\n") for l in h if l.is_context or l.is_removed]
    declared = max(h.source_start - 1, 0)
    if not src:
        return declared
    n = len(src)
    best = None
    for i in range(0, len(base_lines) - n + 1):
        if base_lines[i] == src[0] and base_lines[i:i + n] == src:
            if best is None or abs(i - declared) < abs(best - declared):
                best = i
    if best is None:
        raise ValueError(f"hunk pre-image not found in base of {path} (declared line {h.source_start})")
    return best


def _fix_eof_newlines(dp: DecomposedPatch) -> None:
    fixed = []
    for u in dp.units:
        base = dp.base_files.get(u.path)
        if base is None or u.op != "modify":
            fixed.append(u)
            continue
        lines = base.splitlines(keepends=True)
        seg = tuple(lines[u.start:u.start + len(u.removed)])
        if seg != u.removed and tuple(s.rstrip("\n") for s in seg) == tuple(r.rstrip("\n") for r in u.removed):
            u = Unit(u.uid, u.path, u.start, seg, u.added, u.kind, u.op)
        fixed.append(u)
    dp.units = fixed


# ---------------------------------------------------------------- requires relation
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_DEF = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")
_ASSIGN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]*)?=(?!=)")
_IMPORT = re.compile(r"^\s*(?:from\s+\S+\s+)?import\s+(.+)$")
_STOP = set(keyword.kwlist) | set(dir(builtins)) | {"self", "cls"}


def _defs(lines: Iterable[str]) -> set[str]:
    names: set[str] = set()
    for ln in lines:
        if m := _DEF.match(ln):
            names.add(m.group(1))
        elif m := _IMPORT.match(ln):
            for part in m.group(1).strip("()\\\n ").split(","):
                part = part.strip().strip("()")
                if not part or part == "*":
                    continue
                alias = part.split(" as ")[-1].strip()
                names.add(alias.split(".")[0])
        elif m := _ASSIGN.match(ln):
            names.add(m.group(1))
    return {x for x in names if x not in _STOP}


def _uses(lines: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for ln in lines:
        code = ln.split("#", 1)[0]
        out.update(t for t in _IDENT.findall(code) if t not in _STOP)
    return out


def _defs_by_kind(lines: Iterable[str]) -> dict[str, str]:
    """name -> 'def' (function/class) or 'local' (import alias / assignment target)."""
    out: dict[str, str] = {}
    for ln in lines:
        if m := _DEF.match(ln):
            out[m.group(1)] = "def"
        elif m := _IMPORT.match(ln):
            for part in m.group(1).strip("()\\\n ").split(","):
                part = part.strip().strip("()")
                if part and part != "*":
                    out.setdefault(part.split(" as ")[-1].strip().split(".")[0], "local")
        elif m := _ASSIGN.match(ln):
            out.setdefault(m.group(1), "local")
    return {k: v for k, v in out.items() if k not in _STOP}


def requires_relation(dp: DecomposedPatch) -> dict[str, set[str]]:
    """Over-approximate 'a requires b': applying a without b plausibly breaks name binding.

    (1) a uses a name that b newly binds (not bound in the base version of b's file).
        Import aliases and assignments bind per module, so they link units of the same
        file only; new functions/classes may be used from other files as well.
    (2) a removes the binding of a name whose remaining uses b removes (same scoping).
    Only Python units participate. The relation is used to keep counterfactual
    configurations well formed; it never decides a label on its own.
    """
    py = [u for u in dp.units if u.path.endswith(".py")]
    base_defs = {path: set(_defs(content.splitlines())) for path, content in dp.base_files.items()
                 if content and path.endswith(".py")}
    new_defs = {}
    rem_defs = {}
    for u in py:
        added, removed = _defs_by_kind(u.added), _defs_by_kind(u.removed)
        new_defs[u.uid] = {n: k for n, k in added.items() if n not in base_defs.get(u.path, set()) and n not in removed}
        rem_defs[u.uid] = {n: k for n, k in removed.items() if n not in added}
    uses_added = {u.uid: _uses(u.added) for u in py}
    uses_removed = {u.uid: _uses(u.removed) for u in py}
    req: dict[str, set[str]] = {u.uid: set() for u in dp.units}
    for a in py:
        for b in py:
            if a.uid == b.uid:
                continue
            same = a.path == b.path
            if any((same or k == "def") and n in uses_added[a.uid] for n, k in new_defs[b.uid].items()):
                req[a.uid].add(b.uid)
            if any((same or k == "def") and n in uses_removed[b.uid] for n, k in rem_defs[a.uid].items()):
                req[a.uid].add(b.uid)
    return req


def closure(selected: Iterable[str], req: dict[str, set[str]]) -> frozenset[str]:
    """Smallest superset of ``selected`` closed under the requires relation."""
    out = set(selected)
    stack = list(out)
    while stack:
        x = stack.pop()
        for y in req.get(x, ()):
            if y not in out:
                out.add(y)
                stack.append(y)
    return frozenset(out)


def dependents(uid: str, req: dict[str, set[str]]) -> set[str]:
    """All units that (transitively) require ``uid``."""
    rev: dict[str, set[str]] = {}
    for a, bs in req.items():
        for b in bs:
            rev.setdefault(b, set()).add(a)
    out, stack = set(), [uid]
    while stack:
        x = stack.pop()
        for y in rev.get(x, ()):
            if y not in out:
                out.add(y)
                stack.append(y)
    return out


def syntax_ok(files: dict[str, str | None]) -> bool:
    """Cheap pre-check: every resulting Python file must parse."""
    for path, content in files.items():
        if content is None or not path.endswith(".py"):
            continue
        try:
            ast.parse(content)
        except SyntaxError:
            return False
        except ValueError:      # null bytes etc.
            return False
    return True
