"""SHIFT-Intent contracts for SWE-bench instances.

Builds a pinned catalog from an instance's FAIL_TO_PASS / PASS_TO_PASS lists and
renders the corresponding contract document. Compiling that document must give
back exactly the obligations the oracle evaluates (checked in
experiments/compile_contracts.py).
"""
from __future__ import annotations

import re

from shift.intent.dsl import Catalog, render


def _ident(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", s).strip("_")
    return s if s[:1].isalpha() else f"i_{s}"


def catalog_for(inst: dict, version: str = "swebench-verified@4.0.4") -> tuple[Catalog, list[tuple[str, str]], list[tuple[str, str]]]:
    iid = _ident(inst["instance_id"])
    single = {f"catalog.{iid}.goal_{k + 1}": t for k, t in enumerate(inst["FAIL_TO_PASS"])}
    sets = {f"catalog.{iid}.pass_to_pass": list(inst["PASS_TO_PASS"])} if len(inst["PASS_TO_PASS"]) else {}
    goals = [(f"goal_{k + 1}", a) for k, a in enumerate(single)]
    preserves = [("existing_behavior", a) for a in sets]
    return Catalog(single, sets, version=f"{version}/{inst['instance_id']}"), goals, preserves


def contract_text(inst: dict, envelope_k: int = 6, full_repeats: int = 2) -> tuple[str, Catalog]:
    cat, goals, preserves = catalog_for(inst)
    note = f"Benchmark obligations for {inst['instance_id']}"
    return render(_ident(inst["instance_id"]), goals, preserves, envelope_k, full_repeats, note), cat
