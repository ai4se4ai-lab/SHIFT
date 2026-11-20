"""SHIFT-Intent parser, static checks, compilation, and benchmark contracts."""
import pytest

from shift.intent.benchmark import contract_text
from shift.intent.dsl import (Catalog, ContractError, check_and_resolve, compile_contract, parse, render,
                              validate_baseline)
from shift.pipeline import _closure

PAPER_EXAMPLE = """intent django_13297 {
  goal url_parameter {
    test catalog.template_params_filtering
  }
  preserve existing_views {
    tests catalog.generic_view_preservation
  }
  envelope import_rts top 6
  evidence full_repeats 2
  evidence counterfactual withdraw_and_reduce
  note "Wrapped URL values remain usable in queries"
}
"""
GOAL = "test_template_params_filtering (generic_views.test_base.DeprecationTests)"
PRES = [f"t{i} (generic_views.test_base.X)" for i in range(52)]
CAT = Catalog({"catalog.template_params_filtering": GOAL}, {"catalog.generic_view_preservation": PRES})


def rules(src, cat=CAT):
    with pytest.raises(ContractError) as e:
        compile_contract(src, cat)
    return [d.rule for d in e.value.diagnostics]


def test_paper_example_compiles():
    k, digest = compile_contract(PAPER_EXAMPLE, CAT, base_commit="b", env="e")
    assert k.goal_tests == (GOAL,) and k.preservation_tests == tuple(PRES)
    assert k.envelope == ("import_rts", 6) and k.full_repeats == 2
    assert k.note == "Wrapped URL values remain usable in queries"
    assert len(digest) == 64 and digest != compile_contract(PAPER_EXAMPLE, CAT, base_commit="b2", env="e")[1]


def test_round_trip_render_parse():
    doc = parse(PAPER_EXAMPLE)
    txt = render(doc.name, [(b.name, b.ref) for b in doc.goals], [(b.name, b.ref) for b in doc.preserves],
                 doc.envelope_k, doc.full_repeats, doc.note)
    assert parse(txt) == doc


def test_comments_and_escapes():
    src = PAPER_EXAMPLE.replace('note "Wrapped URL values remain usable in queries"',
                                'note "say \\"hi\\" \\\\ ok"  # trailing comment')
    assert parse(src).note == 'say "hi" \\ ok'


@pytest.mark.parametrize("mutate,line", [
    (lambda s: s.replace("intent", "intnet", 1), 1),
    (lambda s: s.replace("  goal url_parameter {\n    test catalog.template_params_filtering\n  }\n", ""), 2),
    (lambda s: s.replace("top 6", "top six"), 8),
    (lambda s: s.replace("withdraw_and_reduce", "reduce"), 10),
    (lambda s: s.rstrip()[:-1], 12),
    (lambda s: s.replace("{", "(", 1), 1),
])
def test_syntax_errors_have_positions(mutate, line):
    with pytest.raises(ContractError) as e:
        parse(mutate(PAPER_EXAMPLE))
    d = e.value.diagnostics[0]
    assert d.rule == "syntax" and d.line == line and d.col >= 1


def test_preserve_block_optional_and_order_enforced():
    no_pres = PAPER_EXAMPLE.replace("  preserve existing_views {\n    tests catalog.generic_view_preservation\n  }\n", "")
    assert compile_contract(no_pres, CAT)[0].preservation_tests == ()
    swapped = PAPER_EXAMPLE.replace("evidence full_repeats 2\n  evidence counterfactual withdraw_and_reduce",
                                    "evidence counterfactual withdraw_and_reduce\n  evidence full_repeats 2")
    assert rules(swapped) == ["syntax"]


def test_static_rules():
    assert rules(PAPER_EXAMPLE.replace("existing_views", "url_parameter")) == ["duplicate-block"]
    assert rules(PAPER_EXAMPLE.replace("catalog.template_params_filtering", "catalog.nope")) == ["unresolved-alias"]
    assert rules(PAPER_EXAMPLE.replace("test catalog.template_params_filtering",
                                       "test catalog.generic_view_preservation")) == ["goal-cardinality"]
    assert rules(PAPER_EXAMPLE.replace("top 6", "top 0")) == ["envelope-size"]
    assert rules(PAPER_EXAMPLE.replace("full_repeats 2", "full_repeats 1")) == ["repeats"]
    overlap = Catalog({"catalog.template_params_filtering": GOAL},
                      {"catalog.generic_view_preservation": PRES + [GOAL]})
    assert rules(PAPER_EXAMPLE, overlap) == ["overlap"]
    empty = Catalog({"catalog.template_params_filtering": GOAL}, {"catalog.generic_view_preservation": []})
    assert rules(PAPER_EXAMPLE, empty) == ["empty-preservation"]


def test_all_diagnostics_reported_together():
    src = PAPER_EXAMPLE.replace("top 6", "top 0").replace("full_repeats 2", "full_repeats 1")
    assert sorted(rules(src)) == ["envelope-size", "repeats"]


def test_baseline_validation():
    k = check_and_resolve(parse(PAPER_EXAMPLE), CAT)
    ok = {GOAL: "FAILED", **{t: "PASSED" for t in PRES}}
    assert validate_baseline(k, ok) == []
    assert [d.rule for d in validate_baseline(k, {**ok, GOAL: "PASSED"})] == ["baseline"]
    assert [d.rule for d in validate_baseline(k, {**ok, PRES[3]: "ERROR"})] == ["baseline"]
    with pytest.raises(ContractError):
        compile_contract(PAPER_EXAMPLE, CAT, base={**ok, PRES[0]: "FAILED"})
    assert compile_contract(PAPER_EXAMPLE, CAT, base=lambda c: ok)[0].name == "django_13297"


def test_benchmark_contract_reproduces_obligations():
    inst = {"instance_id": "sympy__sympy-1", "FAIL_TO_PASS": ["test_a", "test_b"], "PASS_TO_PASS": ["test_c"]}
    txt, cat = contract_text(inst)
    k, _ = compile_contract(txt, cat)
    assert k.goal_tests == ("test_a", "test_b") and k.preservation_tests == ("test_c",)
    inst2 = dict(inst, PASS_TO_PASS=[])
    k2, _ = compile_contract(*contract_text(inst2))
    assert k2.preservation_tests == ()


def test_addback_closure_is_transitive():
    req = {"a": {"b"}, "b": {"c"}}
    assert _closure({"x", "a"}, req) == {"x", "a", "b", "c"}


def test_trim_diff_only_reverse_greedy():
    from shift.counterfactual.triage import Session, trim_diff_only
    need = {"b1"}                                   # only b1 is required
    sess = Session(["a1", "a2", "b1", "b2"], lambda c: "valid" if need <= c else "goal_fail", use_closure=False)
    assert trim_diff_only(sess, [["a1", "a2"], ["b1", "b2"]]) == ["b1"]
    # compensating pair: removing either alone fails, so a greedy one-at-a-time search keeps both
    ok = lambda c: "valid" if ({"x", "y"} <= c or not ({"x", "y"} & c)) and "z" in c else "goal_fail"  # noqa: E731
    sess = Session(["x", "y", "z"], ok, use_closure=False)
    assert trim_diff_only(sess, [["x", "y", "z"]]) == ["x", "y", "z"]
    assert trim_diff_only(Session(["x", "y", "z"], ok, use_closure=False), [["x", "y"], ["z"]]) == ["z"]
