"""SHIFT-Intent: textual behavioral contracts (parser, static checks, compilation).

Grammar (quoted tokens are terminals; see the paper, Listing "Core grammar")::

    Contract       ::= "intent" Id "{" Goal+ Preserve* Env Repeats Counterfactual Note? "}"
    Goal           ::= "goal" Id "{" "test" TestRef "}"
    Preserve       ::= "preserve" Id "{" "tests" TestSetRef "}"
    Env            ::= "envelope" "import_rts" "top" PositiveInt
    Repeats        ::= "evidence" "full_repeats" PositiveInt
    Counterfactual ::= "evidence" "counterfactual" "withdraw_and_reduce"
    Note           ::= "note" String

Identifiers start with a letter and contain letters, digits and underscores. A
TestRef/TestSetRef is a dot-separated identifier path resolved in a pinned
:class:`Catalog`. ``#`` starts a comment that runs to the end of the line.

Compilation = parse -> grammar/name checks -> alias resolution -> static rules
(goal alias resolves to exactly one test; T_g and T_p disjoint; envelope size > 0;
full_repeats >= 2) -> optional baseline validation against recorded or executed
base outcomes. Every failure is reported as a :class:`Diagnostic` with a rule id
and source position; nothing is silently repaired.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable

# --------------------------------------------------------------------------- data


@dataclass(frozen=True)
class Diagnostic:
    rule: str          # syntax | duplicate-block | unresolved-alias | goal-cardinality |
                       # empty-preservation | overlap | envelope-size | repeats | baseline
    message: str
    line: int = 0
    col: int = 0

    def __str__(self) -> str:
        pos = f"{self.line}:{self.col}: " if self.line else ""
        return f"{pos}[{self.rule}] {self.message}"


class ContractError(Exception):
    def __init__(self, diagnostics: list[Diagnostic]):
        self.diagnostics = diagnostics
        super().__init__("; ".join(map(str, diagnostics)))


@dataclass
class Block:
    kind: str          # goal | preserve
    name: str
    ref: str
    line: int
    col: int


@dataclass
class Document:
    name: str
    goals: list[Block]
    preserves: list[Block]
    envelope_k: int
    full_repeats: int
    counterfactual: str
    note: str | None = None


@dataclass(frozen=True)
class Contract:
    """K = (T_g, T_p, eta, rho) of Definition 1, plus provenance."""
    name: str
    goal_tests: tuple[str, ...]
    preservation_tests: tuple[str, ...]
    envelope: tuple[str, int]                  # (policy, k)
    full_repeats: int
    counterfactual: str
    note: str | None = None
    goal_blocks: tuple[tuple[str, str], ...] = field(default=())   # (block, test) for reports

    def digest(self, **context: str) -> str:
        """Identity of the obligations plus execution context (base, environment, catalog)."""
        body = {"name": self.name, "Tg": sorted(self.goal_tests), "Tp": sorted(self.preservation_tests),
                "eta": list(self.envelope), "rho": {"full_repeats": self.full_repeats,
                                                     "counterfactual": self.counterfactual},
                "context": dict(sorted(context.items()))}
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


class Catalog:
    """Pinned mapping from dotted aliases to test identifiers."""

    def __init__(self, single: dict[str, str] | None = None, sets: dict[str, Iterable[str]] | None = None,
                 version: str = ""):
        self.single = dict(single or {})
        self.sets = {k: tuple(v) for k, v in (sets or {}).items()}
        self.version = version

    def resolve(self, alias: str) -> tuple[str, ...] | None:
        if alias in self.single:
            return (self.single[alias],)
        if alias in self.sets:
            return self.sets[alias]
        return None

    def digest(self) -> str:
        return hashlib.sha256(json.dumps([self.version, sorted(self.single.items()),
                                          sorted((k, list(v)) for k, v in self.sets.items())]).encode()).hexdigest()


# ------------------------------------------------------------------------- lexing

_TOKEN = re.compile(r"""
    (?P<ws>[ \t\r]+) | (?P<nl>\n) | (?P<comment>\#[^\n]*)
  | (?P<string>"(?:[^"\\\n]|\\["\\])*")
  | (?P<ref>[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+)
  | (?P<id>[A-Za-z][A-Za-z0-9_]*)
  | (?P<int>[0-9]+)
  | (?P<punct>[{}])
""", re.VERBOSE)


@dataclass
class Tok:
    kind: str
    text: str
    line: int
    col: int


def tokenize(src: str) -> list[Tok]:
    toks, pos, line, lstart = [], 0, 1, 0
    while pos < len(src):
        m = _TOKEN.match(src, pos)
        if not m:
            raise ContractError([Diagnostic("syntax", f"unexpected character {src[pos]!r}", line, pos - lstart + 1)])
        kind = m.lastgroup
        if kind == "nl":
            line, lstart = line + 1, m.end()
        elif kind not in ("ws", "comment"):
            toks.append(Tok(kind, m.group(), line, pos - lstart + 1))
        pos = m.end()
    toks.append(Tok("eof", "", line, pos - lstart + 1))
    return toks


# ------------------------------------------------------------------------- parsing

class _Parser:
    def __init__(self, toks: list[Tok]):
        self.t, self.i = toks, 0

    @property
    def cur(self) -> Tok:
        return self.t[self.i]

    def fail(self, what: str):
        c = self.cur
        got = "end of input" if c.kind == "eof" else repr(c.text)
        raise ContractError([Diagnostic("syntax", f"expected {what}, found {got}", c.line, c.col)])

    def kw(self, word: str) -> Tok:
        if self.cur.kind == "id" and self.cur.text == word:
            self.i += 1
            return self.t[self.i - 1]
        self.fail(f"'{word}'")

    def kind(self, kind: str, what: str) -> Tok:
        if self.cur.kind == kind:
            self.i += 1
            return self.t[self.i - 1]
        self.fail(what)

    def punct(self, p: str):
        if self.cur.kind == "punct" and self.cur.text == p:
            self.i += 1
            return
        self.fail(f"'{p}'")

    def at(self, word: str) -> bool:
        return self.cur.kind == "id" and self.cur.text == word

    def positive(self) -> int:
        tok = self.kind("int", "a positive integer")
        return int(tok.text)

    def block(self, kind: str, inner: str) -> Block:
        head = self.kw(kind)
        name = self.kind("id", f"a {kind} block name").text
        self.punct("{")
        self.kw(inner)
        ref_tok = self.cur
        if ref_tok.kind not in ("ref", "id"):
            self.fail("a catalog reference")
        self.i += 1
        self.punct("}")
        return Block(kind, name, ref_tok.text, head.line, head.col)

    def document(self) -> Document:
        self.kw("intent")
        name = self.kind("id", "a contract name").text
        self.punct("{")
        goals = []
        while self.at("goal"):
            goals.append(self.block("goal", "test"))
        if not goals:
            self.fail("at least one 'goal' block")
        preserves = []
        while self.at("preserve"):
            preserves.append(self.block("preserve", "tests"))
        self.kw("envelope"), self.kw("import_rts"), self.kw("top")
        k = self.positive()
        self.kw("evidence"), self.kw("full_repeats")
        reps = self.positive()
        self.kw("evidence"), self.kw("counterfactual")
        cf = self.kw("withdraw_and_reduce").text
        note = None
        if self.at("note"):
            self.i += 1
            s = self.kind("string", "a quoted string").text
            note = re.sub(r'\\(["\\])', r"\1", s[1:-1])
        self.punct("}")
        if self.cur.kind != "eof":
            self.fail("end of input")
        return Document(name, goals, preserves, k, reps, cf, note)


def parse(src: str) -> Document:
    return _Parser(tokenize(src)).document()


# ---------------------------------------------------------------------- compilation

def check_and_resolve(doc: Document, catalog: Catalog) -> Contract:
    diags: list[Diagnostic] = []
    seen: dict[str, Block] = {}
    for b in doc.goals + doc.preserves:
        if b.name in seen:
            diags.append(Diagnostic("duplicate-block", f"block name '{b.name}' already used", b.line, b.col))
        seen.setdefault(b.name, b)
    goal_pairs, tg, tp = [], [], []
    for b in doc.goals:
        r = catalog.resolve(b.ref)
        if r is None:
            diags.append(Diagnostic("unresolved-alias", f"'{b.ref}' is not in the catalog", b.line, b.col))
        elif len(r) != 1:
            diags.append(Diagnostic("goal-cardinality", f"goal '{b.name}' resolves to {len(r)} tests, "
                                    "expected exactly one", b.line, b.col))
        else:
            goal_pairs.append((b.name, r[0]))
            tg.append(r[0])
    for b in doc.preserves:
        r = catalog.resolve(b.ref)
        if r is None:
            diags.append(Diagnostic("unresolved-alias", f"'{b.ref}' is not in the catalog", b.line, b.col))
        elif not r:
            diags.append(Diagnostic("empty-preservation", f"preserve '{b.name}' resolves to no tests", b.line, b.col))
        else:
            tp.extend(r)
    dup_goal = {t for t in tg if tg.count(t) > 1}
    for t in sorted(dup_goal):
        diags.append(Diagnostic("overlap", f"test '{t}' is named by more than one goal block"))
    for t in sorted(set(tg) & set(tp)):
        diags.append(Diagnostic("overlap", f"test '{t}' is both a goal and a preservation obligation"))
    if doc.envelope_k < 1:
        diags.append(Diagnostic("envelope-size", "envelope size must be positive"))
    if doc.full_repeats < 2:
        diags.append(Diagnostic("repeats", "full_repeats must be at least 2 for the stability check"))
    if diags:
        raise ContractError(diags)
    return Contract(doc.name, tuple(dict.fromkeys(tg)), tuple(dict.fromkeys(tp)),
                    ("import_rts", doc.envelope_k), doc.full_repeats, doc.counterfactual, doc.note,
                    tuple(goal_pairs))


BaseRunner = Callable[[Contract], dict[str, str]]   # test id -> PASSED/FAILED/...


def validate_baseline(contract: Contract, base_status: dict[str, str],
                      pass_states: Iterable[str] = ("PASSED", "XFAIL")) -> list[Diagnostic]:
    """Base revision must fail every goal test and pass every preservation test."""
    ok = set(pass_states)
    diags = []
    passing_goals = [t for t in contract.goal_tests if base_status.get(t) in ok]
    if passing_goals:
        diags.append(Diagnostic("baseline", f"{len(passing_goals)} goal test(s) already pass on the base, "
                                f"e.g. {passing_goals[0]}"))
    failing_pres = [t for t in contract.preservation_tests if base_status.get(t) not in ok]
    if failing_pres:
        diags.append(Diagnostic("baseline", f"{len(failing_pres)} preservation test(s) do not pass on the base, "
                                f"e.g. {failing_pres[0]}"))
    return diags


def compile_contract(src: str, catalog: Catalog, base: BaseRunner | dict[str, str] | None = None,
                     **context: str) -> tuple[Contract, str]:
    """Algorithm 1: parse, check, resolve, (optionally) validate the base; return (K, digest)."""
    contract = check_and_resolve(parse(src), catalog)
    if base is not None:
        status = base(contract) if callable(base) else base
        diags = validate_baseline(contract, status)
        if diags:
            raise ContractError(diags)
    return contract, contract.digest(catalog=catalog.digest(), **context)


# ------------------------------------------------------------------------ rendering

def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render(name: str, goals: list[tuple[str, str]], preserves: list[tuple[str, str]], envelope_k: int,
           full_repeats: int, note: str | None = None) -> str:
    """Pretty-print a contract document (inverse of :func:`parse`)."""
    out = [f"intent {name} {{"]
    out += [f"  goal {b} {{\n    test {r}\n  }}" for b, r in goals]
    out += [f"  preserve {b} {{\n    tests {r}\n  }}" for b, r in preserves]
    out += [f"  envelope import_rts top {envelope_k}", f"  evidence full_repeats {full_repeats}",
            "  evidence counterfactual withdraw_and_reduce"]
    if note is not None:
        out.append(f"  note {_q(note)}")
    out.append("}")
    return "\n".join(out) + "\n"
