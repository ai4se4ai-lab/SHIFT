"""Edit- and exploration-footprint measures (RQ1)."""
from __future__ import annotations

import itertools
import json
import re
import shlex
from pathlib import Path

from unidiff import PatchSet

from shift.graph.imports import distances_from, import_graph, module_name
from shift.patch.edits import file_kind

BASH_BLOCK = re.compile(r"```(?:bash|sh)?\s*\n(.*?)```", re.S)
WRITE_CMD = re.compile(r"(^|[;&|]\s*)(sed\s+-i|cat\s*>|tee\b|echo .*>|printf .*>|python[0-9.]*\s+-c\s+.*open\(.*['\"]w)")


def patch_files(diff: str, repo: str) -> list[dict]:
    """Per-file summary of a unified diff: path, kind, hunks, change blocks, churn, new/deleted."""
    out = []
    try:
        ps = PatchSet(diff)
    except Exception:
        return out
    for pf in ps:
        path = pf.path
        blocks = 0
        for h in pf:
            in_block = False
            for line in h:
                if line.is_context:
                    in_block = False
                elif not in_block:
                    blocks += 1
                    in_block = True
        out.append({"path": path, "kind": file_kind(path, repo), "hunks": len(pf),
                    "blocks": blocks, "added": pf.added, "removed": pf.removed,
                    "new": pf.is_added_file, "deleted": pf.is_removed_file})
    return out


def edit_footprint(diff: str, gold_diff: str, repo: str, commit: str, graph: dict | None = None) -> dict:
    files = patch_files(diff, repo)
    gold = {f["path"] for f in patch_files(gold_diff, repo) if f["kind"] == "source"}
    src = [f for f in files if f["kind"] == "source"]
    src_paths = {f["path"] for f in src}
    blocks_src = sum(f["blocks"] for f in src)
    nonlocal_blocks = sum(f["blocks"] for f in src if f["path"] not in gold)
    union = src_paths | gold
    jacc_div = 1 - (len(src_paths & gold) / len(union)) if union else 0.0
    res = {
        "n_files": len(files), "n_src_files": len(src),
        "n_test_files": sum(f["kind"] == "test" for f in files),
        "n_aux_files": sum(f["kind"] == "aux" for f in files),
        "n_new_aux_files": sum(f["kind"] == "aux" and f["new"] for f in files),
        "hunks": sum(f["hunks"] for f in files), "blocks": sum(f["blocks"] for f in files),
        "src_blocks": blocks_src,
        "churn": sum(f["added"] + f["removed"] for f in files),
        "src_churn": sum(f["added"] + f["removed"] for f in src),
        "divergence": jacc_div,
        "nonlocal_share": (nonlocal_blocks / blocks_src) if blocks_src else float("nan"),
        "touches_gold_file": bool(src_paths & gold),
        "dispersion": float("nan"), "disconnected_pairs": 0, "max_dist_to_gold": float("nan"),
    }
    if graph is None:
        graph = import_graph(repo, commit)
    mods = sorted({m for p in src_paths if (m := module_name(p, repo)) and m in graph})
    if len(mods) >= 2:
        ds, disc = [], 0
        for a, b in itertools.combinations(mods, 2):
            d = distances_from(graph, a).get(b)
            if d is None:
                disc += 1
            else:
                ds.append(d)
        res["dispersion"] = sum(ds) / len(ds) if ds else float("nan")
        res["disconnected_pairs"] = disc
    elif len(mods) == 1:
        res["dispersion"] = 0.0
    gmods = [m for p in gold if (m := module_name(p, repo)) and m in graph]
    if mods and gmods:
        best = []
        for m in mods:
            dm = distances_from(graph, m)
            cand = [dm[g] for g in gmods if g in dm]
            best.append(min(cand) if cand else None)
        known = [b for b in best if b is not None]
        res["max_dist_to_gold"] = max(known) if known else float("nan")
    return res


# ---------------------------------------------------------------- trajectories
def commands_from_traj(traj: dict) -> list[str]:
    cmds: list[str] = []
    for m in traj.get("messages", []):
        extra = m.get("extra") if isinstance(m.get("extra"), dict) else {}
        acts = extra.get("actions") if isinstance(extra.get("actions"), list) else None
        if acts:                                   # mini-swe-agent >= 1.1 records parsed actions
            cmds += [a["command"] for a in acts if isinstance(a, dict) and a.get("command")]
            continue
        if m.get("role") != "assistant":
            continue
        for tc in m.get("tool_calls") or []:
            try:
                args = json.loads(tc.get("function", {}).get("arguments", "{}"))
                if isinstance(args, dict) and args.get("command"):
                    cmds.append(args["command"])
            except (json.JSONDecodeError, TypeError):
                pass
        content = m.get("content")
        if isinstance(content, list):
            content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
        if isinstance(content, str):
            cmds += [b.strip() for b in BASH_BLOCK.findall(content)]
    return cmds


def _tokens(cmd: str) -> list[str]:
    try:
        return shlex.split(cmd, comments=False, posix=True)
    except ValueError:
        return cmd.split()


def exploration_footprint(traj: dict, repo_files: set[str], edited: set[str]) -> dict:
    """Files referenced by agent commands; reads vs writes separated heuristically."""
    cmds = commands_from_traj(traj)
    referenced: set[str] = set()
    written: set[str] = set()
    for c in cmds:
        toks = _tokens(c)
        hits = set()
        for t in toks:
            for cand in re.split(r"[\s:;|&<>()'\"]+", t):
                p = cand.strip().removeprefix("/testbed/").removeprefix("./").rstrip(",")
                if p in repo_files:
                    hits.add(p)
        referenced |= hits
        if WRITE_CMD.search(c):
            written |= hits
    n_src_read = sum(1 for p in referenced if p.endswith(".py"))
    return {"steps": len(cmds), "n_referenced": len(referenced), "n_referenced_py": n_src_read,
            "n_written_refs": len(written),
            "eer": len(referenced) / max(1, len(edited)),
            "edited_not_referenced": len(edited - referenced),
            "exit_status": (traj.get("info") or {}).get("exit_status"),
            "api_calls": ((traj.get("info") or {}).get("model_stats") or {}).get("api_calls"),
            "cost": ((traj.get("info") or {}).get("model_stats") or {}).get("instance_cost")}


def load_traj(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
