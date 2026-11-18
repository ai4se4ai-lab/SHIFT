"""Hypothesis-to-edit mapping prompts (LLM judges, RQ2).

Each prompt shows the issue and the patch split into the same units SHIFT
analyses, and asks the model for repair hypotheses plus, per unit, the
hypothesis it serves, its role, and whether it is needed. The answer is a
*claim*; SHIFT's counterfactual evidence is what it is compared against.
"""
from __future__ import annotations

import hashlib
import json

from shift.patch.edits import DecomposedPatch

PROMPT_VERSION = "shift-judge-v1"
MAX_ISSUE = 6000
MAX_UNIT_LINES = 40

SYSTEM = ("You are an expert software engineer reviewing a patch that an automated coding agent "
          "produced to resolve a GitHub issue. You judge each edit of the patch on its own merits.")

INSTRUCTIONS = """Tasks:
1. Propose up to three hypotheses (H1, H2, H3) about the root cause that this patch addresses.
2. For EVERY edit listed above, report:
   - "hypothesis": the id of the hypothesis the edit implements, or null if none;
   - "role": one of "fix" (directly repairs the defect), "support" (needed by a fix edit, e.g. a helper or import),
     "test" (adds or changes tests), "debug_artifact" (reproduction or scratch code), "cleanup" (refactoring,
     formatting, comments), "unrelated" (not connected to the issue);
   - "needed": true if the issue would remain unresolved, or the fix would break, without this edit; otherwise false;
   - "confidence": a number between 0 and 1.
Answer with JSON only, following this schema:
{"hypotheses": [{"id": "H1", "text": "..."}], "edits": [{"uid": "u01", "hypothesis": "H1", "role": "fix", "needed": true, "confidence": 0.9}]}"""

SCHEMA = {
    "type": "object",
    "properties": {
        "hypotheses": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "text": {"type": "string"}}, "required": ["id", "text"]}},
        "edits": {"type": "array", "items": {"type": "object", "properties": {
            "uid": {"type": "string"}, "hypothesis": {"type": ["string", "null"]},
            "role": {"type": "string", "enum": ["fix", "support", "test", "debug_artifact", "cleanup", "unrelated"]},
            "needed": {"type": "boolean"}, "confidence": {"type": "number"}},
            "required": ["uid", "role", "needed", "confidence"]}},
    },
    "required": ["hypotheses", "edits"],
}


def render_unit(u, base_line_offset: int = 1) -> str:
    head = f"[{u.uid}] {u.path} ({'new file' if u.op == 'add_file' else 'deleted file' if u.op == 'delete_file' else f'line {u.start + base_line_offset}'})"
    body = [f"-{l.rstrip(chr(10))}" for l in u.removed[:MAX_UNIT_LINES]]
    body += [f"+{l.rstrip(chr(10))}" for l in u.added[:MAX_UNIT_LINES]]
    if len(u.removed) > MAX_UNIT_LINES or len(u.added) > MAX_UNIT_LINES:
        body.append(f"... ({len(u.removed)} removed / {len(u.added)} added lines in total)")
    return head + "\n```diff\n" + "\n".join(body) + "\n```"


MAX_TESTS = 4000


def build_prompt(issue: str, dp: DecomposedPatch, uids: list[str], tests: str | None = None) -> str:
    issue = issue if len(issue) <= MAX_ISSUE else issue[:MAX_ISSUE] + "\n[... truncated ...]"
    units = "\n\n".join(render_unit(dp.unit(u)) for u in uids)
    extra = ""
    if tests:
        t = tests if len(tests) <= MAX_TESTS else tests[:MAX_TESTS] + "\n[... truncated ...]"
        extra = ("The issue counts as resolved when the following tests pass. They are added or changed by this "
                 f"test patch:\n<tests>\n{t}\n</tests>\n\n")
    return (f"Issue:\n<issue>\n{issue}\n</issue>\n\n{extra}The patch consists of these edits:\n\n{units}"
            f"\n\n{INSTRUCTIONS}")


def prompt_record(instance_id: str, label: str, issue: str, dp: DecomposedPatch, uids: list[str],
                  tests: str | None = None) -> dict:
    user = build_prompt(issue, dp, uids, tests)
    return {"key": f"{label}__{instance_id}", "instance_id": instance_id, "label": label,
            "uids": uids, "system": SYSTEM, "user": user, "schema": SCHEMA,
            "prompt_version": PROMPT_VERSION,
            "sha256": hashlib.sha256((SYSTEM + user).encode()).hexdigest()}


def parse_answer(text: str, uids: list[str]) -> dict:
    """Parse a model answer; returns {'ok', 'edits': uid->dict, 'hypotheses', 'error'}."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("{"):]
    start, end = t.find("{"), t.rfind("}")
    try:
        obj = json.loads(t[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return {"ok": False, "edits": {}, "hypotheses": [], "error": "json"}
    edits = {}
    for e in obj.get("edits", []) if isinstance(obj, dict) else []:
        if isinstance(e, dict) and e.get("uid") in uids:
            edits[e["uid"]] = e
    missing = [u for u in uids if u not in edits]
    return {"ok": not missing, "edits": edits, "hypotheses": obj.get("hypotheses", []) if isinstance(obj, dict) else [],
            "error": f"missing {len(missing)}" if missing else None}
