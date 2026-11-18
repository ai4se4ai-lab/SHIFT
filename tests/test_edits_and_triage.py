import itertools
import random

import pytest

from shift.counterfactual.triage import Session, ddmin, exhaustive_minimum, triage
from shift.patch.edits import closure, decompose, file_kind, requires_relation, syntax_ok

BASE_A = "import os\n\n\ndef f(x):\n    return x + 1\n\n\ndef g(y):\n    return y * 2\n\n\nVALUE = 3\n"
BASE_B = "from a import f\n\n\ndef h(z):\n    return f(z)\n"

DIFF = """diff --git a/pkg/a.py b/pkg/a.py
--- a/pkg/a.py
+++ b/pkg/a.py
@@ -1,12 +1,15 @@
 import os


 def f(x):
-    return x + 1
+    return x + 2


 def g(y):
     return y * 2

+def helper(q):
+    return q - 1
+

-VALUE = 3
+VALUE = 4
diff --git a/pkg/b.py b/pkg/b.py
--- a/pkg/b.py
+++ b/pkg/b.py
@@ -1,5 +1,5 @@
 from a import f


 def h(z):
-    return f(z)
+    return helper(f(z))
diff --git a/reproduce.py b/reproduce.py
new file mode 100644
--- /dev/null
+++ b/reproduce.py
@@ -0,0 +1,2 @@
+from pkg.b import h
+print(h(1))
"""


def reader(path):
    return {"pkg/a.py": BASE_A, "pkg/b.py": BASE_B}.get(path)


def test_decompose_units_and_apply_roundtrip():
    dp = decompose(DIFF, "x/x", reader)
    assert len(dp.units) == 5            # f-change, helper add, VALUE change, b change, new file
    full = dp.apply(dp.ids)
    assert "return x + 2" in full["pkg/a.py"] and "def helper" in full["pkg/a.py"]
    assert full["pkg/b.py"].endswith("return helper(f(z))\n")
    assert full["reproduce.py"].startswith("from pkg.b import h")
    none = dp.apply([])
    assert none["pkg/a.py"] == BASE_A and none["pkg/b.py"] == BASE_B and none["reproduce.py"] is None


def test_every_subset_applies_and_parses():
    dp = decompose(DIFF, "x/x", reader)
    for k in range(len(dp.units) + 1):
        for sub in itertools.combinations(dp.ids, k):
            assert syntax_ok(dp.apply(sub))


def test_requires_relation_links_use_to_new_definition():
    dp = decompose(DIFF, "x/x", reader)
    req = requires_relation(dp)
    helper = next(u.uid for u in dp.units if any("def helper" in l for l in u.added))
    user = next(u.uid for u in dp.units if any("helper(f(z))" in l for l in u.added))
    assert helper in req[user]
    assert helper in closure([user], req)


def test_file_kind():
    assert file_kind("django/db/models/query.py", "django/django") == "source"
    assert file_kind("tests/queries/tests.py", "django/django") == "test"
    assert file_kind("reproduce_bug.py", "django/django") == "aux"
    assert file_kind("sympy/core/tests/test_basic.py", "sympy/sympy") == "test"


# ---------------------------------------------------------------- triage with fake oracles
def make_oracle(needed_any_of: list[set[str]], harmful: set[str] = frozenset()):
    """valid iff config ⊇ one alternative in needed_any_of and contains no harmful unit."""
    def oracle(cfg):
        if cfg & harmful:
            return "pres_fail"
        return "valid" if any(alt <= cfg for alt in needed_any_of) else "goal_fail"
    return oracle


def test_triage_labels_simple():
    units = ["a", "b", "c", "d"]
    sess = Session(units, make_oracle([{"a", "c"}]))
    r = triage(sess)
    assert r.status == "ok"
    assert r.labels == {"a": "N", "b": "U", "c": "N", "d": "U"}
    assert r.minimal == ["a", "c"]


def test_triage_jointly_needed_alternatives():
    # either b or d suffices together with a: individually removable, jointly needed
    sess = Session(["a", "b", "d"], make_oracle([{"a", "b"}, {"a", "d"}]))
    r = triage(sess)
    assert r.labels["a"] == "N"
    assert {r.labels["b"], r.labels["d"]} == {"J", "U"}


def test_closure_respected_in_minimal_set():
    # x requires y (e.g. x calls a helper defined by y); only x matters for the goal
    sess = Session(["x", "y", "z"], make_oracle([{"x", "y"}]), requires={"x": {"y"}})
    r = triage(sess)
    assert set(r.minimal) == {"x", "y"}
    assert r.labels["z"] == "U"


def test_not_valid_and_base_valid():
    assert triage(Session(["a"], make_oracle([{"q"}]))).status == "not_valid"
    assert triage(Session(["a"], make_oracle([set()]))).status == "base_valid"


@pytest.mark.parametrize("seed", range(30))
def test_ddmin_is_one_minimal_and_matches_exhaustive_on_monotone_oracles(seed):
    rnd = random.Random(seed)
    units = [f"u{i}" for i in range(rnd.randint(2, 9))]
    needed = set(rnd.sample(units, rnd.randint(1, len(units))))
    sess = Session(units, make_oracle([needed]))
    m = ddmin(sess, units)
    assert sess.valid(m)
    for x in m:
        assert not sess.valid([y for y in m if y != x])
    assert set(m) == needed
    assert exhaustive_minimum(sess, units) == [frozenset(needed)]


def test_precheck_counts_and_avoids_oracle():
    calls = []

    def oracle(cfg):
        calls.append(cfg)
        return "valid" if "a" in cfg and "b" in cfg else "goal_fail"
    # configurations containing b but not c are "syntax errors"
    sess = Session(["a", "b", "c"], oracle, precheck=lambda cfg: not ("b" in cfg and "c" not in cfg))
    r = triage(sess)
    assert r.status == "ok"
    assert sess.precheck_rejections > 0
    assert all(not ("b" in c and "c" not in c) for c in calls)


def test_reduce_closed_removes_unit_that_entered_only_via_closure():
    # mirrors django__django-11333: u01 imports a helper defined by u04; {u04} alone is valid
    sess = Session(["u01", "u02", "u03", "u04"],
                   lambda c: "valid" if "u04" in c and (("u02" in c) == ("u03" in c)) else "goal_fail",
                   requires={"u01": {"u04"}})
    r = triage(sess)
    assert r.minimal == ["u04"]
    assert r.labels["u01"] == "U"
    assert r.labels["u04"] == "N"
    assert r.labels["u02"] == "C" and r.labels["u03"] == "C"   # coupled pair


@pytest.mark.parametrize("seed", range(40))
def test_closed_one_minimality_property(seed):
    rnd = random.Random(seed)
    units = [f"u{i}" for i in range(rnd.randint(2, 8))]
    req = {u: set(rnd.sample(units, rnd.randint(0, 1))) - {u} for u in units}
    needed = set(rnd.sample(units, rnd.randint(1, len(units))))
    sess = Session(units, make_oracle([needed]), requires=req)
    r = triage(sess)
    if r.status != "ok":
        return
    from shift.counterfactual.triage import dependents_of
    d = set(r.minimal)
    assert sess.valid(d)
    for u in d:
        rest = d - ({u} | (dependents_of(u, req) & d))
        assert not sess.valid(rest)
