"""Counterfactual edit triage (SHIFT core).

Given a patch decomposed into units U and an oracle that judges a configuration
S ⊆ U against goal and preservation obligations, compute:

* leave-one-out necessity of every unit (removing the unit and its dependents),
* an inclusion 1-minimal sufficient set D* via dependency-aware ddmin,
* edit labels: N (necessary: in D* and indispensable alone), J (jointly needed: in D*
  but individually removable), U (unneeded), C (coupled: indispensable alone but
  removable together with other units outside D*), X (unresolved).

The oracle is abstract (``Evaluate``) so the algorithm is testable without
Docker; ``Session`` adds caching, closure under the requires relation, a
syntax pre-check, and accounting of oracle executions.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Callable, Iterable, Literal

Outcome = Literal["valid", "goal_fail", "pres_fail", "invalid", "error"]
Evaluate = Callable[[frozenset[str]], Outcome]


@dataclass
class Session:
    """Memoising wrapper around an oracle with closure and pre-checks."""
    units: list[str]
    oracle: Evaluate                              # runs tests; expensive
    requires: dict[str, set[str]] = field(default_factory=dict)
    precheck: Callable[[frozenset[str]], bool] | None = None   # cheap static validity
    use_closure: bool = True
    cache: dict[frozenset[str], Outcome] = field(default_factory=dict)
    oracle_calls: int = 0
    precheck_rejections: int = 0
    trace: list[tuple[tuple[str, ...], Outcome, str]] = field(default_factory=list)

    def close(self, s: Iterable[str]) -> frozenset[str]:
        s = frozenset(s)
        if not self.use_closure:
            return s
        out, stack = set(s), list(s)
        while stack:
            x = stack.pop()
            for y in self.requires.get(x, ()):
                if y not in out:
                    out.add(y)
                    stack.append(y)
        return frozenset(out)

    def evaluate(self, s: Iterable[str]) -> Outcome:
        cfg = self.close(s)
        if cfg in self.cache:
            return self.cache[cfg]
        if self.precheck is not None and not self.precheck(cfg):
            self.precheck_rejections += 1
            out: Outcome = "invalid"
            self.trace.append((tuple(sorted(cfg)), out, "precheck"))
        else:
            self.oracle_calls += 1
            out = self.oracle(cfg)
            self.trace.append((tuple(sorted(cfg)), out, "oracle"))
        self.cache[cfg] = out
        return out

    def valid(self, s: Iterable[str]) -> bool:
        return self.evaluate(s) == "valid"


def dependents_of(uid: str, requires: dict[str, set[str]]) -> set[str]:
    rev: dict[str, set[str]] = {}
    for a, bs in requires.items():
        for b in bs:
            rev.setdefault(b, set()).add(a)
    out, stack = set(), [uid]
    while stack:
        for y in rev.get(stack.pop(), ()):
            if y not in out:
                out.add(y)
                stack.append(y)
    return out


def leave_one_out(sess: Session) -> dict[str, Outcome]:
    """Outcome of the full patch minus each unit (and the units requiring it)."""
    full = set(sess.units)
    res = {}
    for u in sess.units:
        drop = {u} | (dependents_of(u, sess.requires) if sess.use_closure else set())
        res[u] = sess.evaluate(full - drop)
    return res


def ddmin(sess: Session, units: list[str]) -> list[str]:
    """Zeller–Hildebrandt ddmin, minimising a *valid* configuration.

    Returns a list C ⊆ units with valid(close(C)) such that removing any single
    element of C yields a non-valid configuration (1-minimality), assuming the
    oracle is deterministic. Requires valid(units).
    """
    c = list(units)
    n = 2
    while len(c) >= 2:
        chunk = max(1, len(c) // n)
        subsets = [c[i:i + chunk] for i in range(0, len(c), chunk)]
        reduced = False
        for sub in subsets:                       # try a subset alone
            if sess.valid(sub):
                c, n, reduced = sub, 2, True
                break
        if not reduced:
            for sub in subsets:                   # try a complement
                comp = [x for x in c if x not in sub]
                if comp and sess.valid(comp):
                    c, n, reduced = comp, max(n - 1, 2), True
                    break
        if not reduced:
            if n >= len(c):
                break
            n = min(len(c), 2 * n)
    if len(c) == 1 and sess.valid([]):
        c = []
    return c


def reduce_closed(sess: Session, d: Iterable[str]) -> list[str]:
    """Closure-aware 1-minimality pass applied to the ddmin result.

    Repeatedly tries to drop one unit together with the units of D that require it;
    keeps the drop if the closed remainder is still valid. On termination, for every
    u in D, cl(D minus ({u} plus its dependents in D)) is not valid (deterministic oracle).
    """
    d = set(sess.close(d))
    changed = True
    while changed:
        changed = False
        for u in sorted(d):
            drop = {u} | (dependents_of(u, sess.requires) & d if sess.use_closure else set())
            rest = d - drop
            if sess.valid(rest):
                d = set(sess.close(rest))
                changed = True
                break
    return sorted(d)


def exhaustive_minimum(sess: Session, units: list[str], max_units: int = 10) -> list[frozenset[str]] | None:
    """All cardinality-minimum valid closed subsets (only for small patches)."""
    if len(units) > max_units:
        return None
    for k in range(0, len(units) + 1):
        found = [sess.close(c) for c in itertools.combinations(units, k) if sess.valid(c)]
        if found:
            return sorted(set(found), key=lambda s: sorted(s))
    return []


@dataclass
class TriageResult:
    status: str                          # ok | not_valid | base_valid | flaky | error
    labels: dict[str, str]               # uid -> N/J/U/C/X
    loo: dict[str, Outcome]
    minimal: list[str]
    oracle_calls: int
    precheck_rejections: int
    anomalies: list[str]


def triage(sess: Session, repeats_full: int = 2, full_oracle: Evaluate | None = None) -> TriageResult:
    """Label every unit. ``full_oracle`` (uncached) is used to re-check the full patch for flakiness."""
    units = list(sess.units)
    anomalies: list[str] = []
    full = sess.evaluate(units)
    if full != "valid":
        return TriageResult("not_valid", {u: "X" for u in units}, {}, [], sess.oracle_calls,
                            sess.precheck_rejections, [f"full={full}"])
    if full_oracle is not None:
        for _ in range(repeats_full - 1):
            sess.oracle_calls += 1
            again = full_oracle(sess.close(units))
            if again != "valid":
                return TriageResult("flaky", {u: "X" for u in units}, {}, [], sess.oracle_calls,
                                    sess.precheck_rejections, [f"full repeat={again}"])
    if sess.valid([]):
        return TriageResult("base_valid", {u: "X" for u in units}, {}, [], sess.oracle_calls,
                            sess.precheck_rejections, ["empty configuration already valid"])
    loo = leave_one_out(sess)
    minimal = reduce_closed(sess, ddmin(sess, units))
    labels = {}
    for u in units:
        o = loo[u]
        if o == "error":
            labels[u] = "X"
        elif o != "valid" and u in minimal:
            labels[u] = "N"
        elif o != "valid":
            labels[u] = "C"          # coupled: indispensable alone, removable together with others
            anomalies.append(f"{u}: LOO-necessary but outside D* (coupled edits)")
        elif u in minimal:
            labels[u] = "J"
        else:
            labels[u] = "U"
    return TriageResult("ok", labels, loo, minimal, sess.oracle_calls, sess.precheck_rejections, anomalies)
