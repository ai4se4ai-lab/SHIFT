"""Controlled edit injection for RQ3 (known ground truth by construction).

An injected unit is placed in a *nonlocal* module: one that the gold patch does
not edit but that is within import distance 1-2 of a gold-edited module.
Semantic operators change behaviour when the line executes; neutral operators
are semantics-preserving. The injected diff is appended to the gold patch.
"""
from __future__ import annotations

import ast
import difflib
import random

from shift.data.repos import read_file
from shift.graph.imports import distances_from, import_graph, module_name
from shift.patch.edits import PKG_ROOTS, TEST_PAT

SEMANTIC = ("relop_flip", "bool_negate", "const_perturb", "return_none")
NEUTRAL = ("comment_add", "redundant_parens", "dead_local")
_FLIP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE, ast.LtE: ast.Gt}


def _in_function(tree: ast.AST) -> dict[int, ast.AST]:
    """Map node id -> enclosing function for nodes inside function bodies."""
    owner = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for n in ast.walk(fn):
                owner.setdefault(id(n), fn)
    return owner


def _candidates(src: str, op: str) -> list[tuple[int, int, int, str]]:
    """(lineno, col, end_col, replacement) for single-line sites inside functions."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    owner = _in_function(tree)
    lines = src.splitlines()
    out = []
    for n in ast.walk(tree):
        if id(n) not in owner or not hasattr(n, "lineno"):
            continue
        single = getattr(n, "end_lineno", None) == n.lineno
        if not single and not isinstance(n, (ast.If, ast.While, ast.stmt)):
            continue
        if op == "relop_flip" and single and isinstance(n, ast.Compare) and len(n.ops) == 1 and type(n.ops[0]) in _FLIP:
            m = ast.Compare(left=n.left, ops=[_FLIP[type(n.ops[0])]()], comparators=n.comparators)
            out.append((n.lineno, n.col_offset, n.end_col_offset, ast.unparse(m)))
        elif op == "bool_negate" and isinstance(n, (ast.If, ast.While)) and n.test.lineno == n.test.end_lineno:
            t = ast.get_source_segment(src, n.test)
            if t:
                out.append((n.test.lineno, n.test.col_offset, n.test.end_col_offset, f"not ({t})"))
        elif op == "const_perturb" and single and isinstance(n, ast.Constant) and type(n.value) is int:
            out.append((n.lineno, n.col_offset, n.end_col_offset, str(n.value + 1)))
        elif op in ("return_none", "redundant_parens") and isinstance(n, ast.Return) and n.value is not None \
                and n.value.lineno == n.value.end_lineno:
            v = ast.get_source_segment(src, n.value)
            if v and v != "None":
                rep = "None" if op == "return_none" else f"({v})"
                out.append((n.value.lineno, n.value.col_offset, n.value.end_col_offset, rep))
        elif op in ("comment_add", "dead_local") and isinstance(n, ast.stmt) and not isinstance(
                n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and owner.get(id(n)) is not n:
            line = lines[n.lineno - 1]
            indent = line[: len(line) - len(line.lstrip())]
            if line.lstrip().startswith(("elif", "else", "except", "finally", "@")) or not indent:
                continue
            ins = "# SHIFT-injected: reviewed" if op == "comment_add" else "_shift_unused = 0"
            out.append((n.lineno, -1, -1, indent + ins))
    return out


def _apply(src: str, site: tuple[int, int, int, str]) -> str:
    lines = src.splitlines(keepends=True)
    ln, c0, c1, rep = site
    if c0 == -1:                                  # insertion before line ln
        lines.insert(ln - 1, rep + "\n")
    else:
        line = lines[ln - 1].encode()
        lines[ln - 1] = (line[:c0] + rep.encode() + line[c1:]).decode()
    return "".join(lines)


def _unified(path: str, before: str, after: str) -> str:
    d = difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                             f"a/{path}", f"b/{path}", n=3)
    return f"diff --git a/{path} b/{path}\n" + "".join(d)


def make_injection(inst: dict, op: str, seed: int, max_dist: int = 2) -> dict | None:
    """Return {'patch', 'target', 'op', 'site_line'} or None when no eligible site exists."""
    repo, commit = inst["repo"], inst["base_commit"]
    rnd = random.Random(f"{inst['instance_id']}:{op}:{seed}")
    g = import_graph(repo, commit)
    import re
    gold_files = re.findall(r"diff --git a/(\S+)", inst["patch"])
    gold_mods = {module_name(p, repo) for p in gold_files}
    near: dict[str, int] = {}
    for gm in gold_mods:
        if gm in g:
            for m, d in distances_from(g, gm, limit=max_dist).items():
                if 1 <= d <= max_dist and m not in gold_mods:
                    near[m] = min(d, near.get(m, 99))
    root = PKG_ROOTS[repo]
    mod2path = {}
    for m in near:
        base = m.replace(".", "/")
        for cand in (f"{base}.py", f"{base}/__init__.py"):
            if cand.startswith(root) and not TEST_PAT.search(cand):
                mod2path[m] = cand
    order = sorted(mod2path, key=lambda m: (near[m], m))
    rnd.shuffle(order)
    order.sort(key=lambda m: near[m])                # prefer distance 1, random within distance
    for m in order:
        path = mod2path[m]
        src = read_file(repo, commit, path)
        if not src:
            continue
        sites = _candidates(src, op)
        if not sites:
            continue
        site = rnd.choice(sites)
        after = _apply(src, site)
        try:
            ast.parse(after)
        except SyntaxError:
            continue
        inj = _unified(path, src, after)
        patch = inst["patch"].rstrip("\n") + "\n" + inj
        return {"patch": patch, "target": path, "op": op, "site_line": site[0], "distance": near[m],
                "kind": "semantic" if op in SEMANTIC else "neutral"}
    return None
