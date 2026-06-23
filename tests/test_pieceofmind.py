"""Tests for pieceofmind -- the attribution math (exact, deterministic) + the provenance adapter.

The value function is a pure callable here, so these are fast and offline. They pin: the Shapley
efficiency axiom, the redundant-pair credit split (the property leave-one-out lacks), and that the
generic kernel works with any value_fn.
"""

import itertools

from pieceofmind import (
    attribute_loo,
    attribute_shapley,
    build_synth_fn,
    provenance_value_fn,
    shapley_from_values,
)


def test_shapley_splits_redundant_pair_where_loo_zeros():
    n = 3
    def v(S):  # players 0,1 perfectly redundant (0.15 if either present); player 2 irrelevant
        return 0.15 if (0 in S or 1 in S) else 0.0
    values = {frozenset(c): v(set(c)) for r in range(n + 1) for c in itertools.combinations(range(n), r)}
    sh = shapley_from_values(values, n)
    assert abs(sh[0] - 0.075) < 1e-9
    assert abs(sh[1] - 0.075) < 1e-9
    assert abs(sh[2] - 0.0) < 1e-9
    assert abs(sum(sh) - 0.15) < 1e-9                 # efficiency axiom
    full = frozenset(range(n))
    assert abs(values[full] - values[full - {0}]) < 1e-9   # LOO gives the redundant player 0


# Deterministic stub value fn over 5 inputs: F1||F2 redundant (0.30 if either), F3 +0.05, rest inert.
_INPUTS = ["F1 a", "F2 b", "F3 c", "F4 d", "F5 e"]
def _stub(subset):
    has = lambda t: any(str(f).startswith(t + " ") for f in subset)
    return (0.30 if (has("F1") or has("F2")) else 0.0) + (0.05 if has("F3") else 0.0)


def test_loo_masks_redundancy():
    r = attribute_loo(_INPUTS, _stub, k=2, ids=["F1", "F2", "F3", "F4", "F5"])
    a = {x.id: x for x in r.per_input}
    assert abs(a["F1"].attr) < 1e-9 and not a["F1"].significant   # masked by F2
    assert abs(a["F2"].attr) < 1e-9 and not a["F2"].significant
    assert abs(a["F3"].attr - 0.05) < 1e-9 and a["F3"].significant


def test_shapley_reveals_redundancy_and_efficiency():
    r = attribute_shapley(_INPUTS, _stub, k=2, ids=["F1", "F2", "F3", "F4", "F5"])
    s = {p["id"]: p for p in r.per_input}
    assert abs(s["F1"]["shapley"] - 0.15) < 1e-9 and abs(s["F1"]["loo"]) < 1e-9   # Shapley reveals
    assert abs(s["F2"]["shapley"] - 0.15) < 1e-9
    assert abs(s["F3"]["shapley"] - 0.05) < 1e-9
    assert abs(s["F4"]["shapley"]) < 1e-9 and abs(s["F5"]["shapley"]) < 1e-9
    assert r.efficiency_ok()                              # sum(Shapley) == v(full) - v(empty)
    assert abs(r.efficiency_sum - 0.35) < 1e-9


def test_provenance_value_fn_with_mock_synth():
    # synth_fn keyed off findings: F1 present -> higher data_share (load-bearing data)
    def synth_fn(findings, situation, question):
        f1 = any(str(f).startswith("F1 ") for f in findings)
        ds = 0.6 if f1 else 0.45
        return {"recommendation": "x", "claims": [], "_provenance_summary": {"data_share": ds}}
    v = provenance_value_fn(synth_fn, "sit", "q?")
    assert v(_INPUTS) == 0.6
    assert v([f for f in _INPUTS if not f.startswith("F1 ")]) == 0.45


def test_known_limits_heterogeneity_and_cut_keep_ceiling():
    """The honest where-it-breaks demo: aggregate attribution nets a heterogeneous rule to ~0 (hiding
    that it is +1 on segment A and -1 on segment B), and cut/keep (50/50) cannot reach the reword
    optimum (100)."""
    import importlib.util
    from pathlib import Path
    from pieceofmind import attribute_loo

    ex = Path(__file__).resolve().parents[1] / "examples" / "known_limits.py"
    spec = importlib.util.spec_from_file_location("klim", ex)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    agg = {x.id: x.attr for x in attribute_loo(m.RULES, m.agg, k=1, ids=m.RULES).per_input}
    assert abs(agg["R"]) < 1e-9                                       # aggregate hides it (~0)
    a = {x.id: x.attr for x in attribute_loo(m.RULES, m.seg_only("A"), k=1, ids=m.RULES).per_input}
    b = {x.id: x.attr for x in attribute_loo(m.RULES, m.seg_only("B"), k=1, ids=m.RULES).per_input}
    assert abs(a["R"] - 1.0) < 1e-9 and abs(b["R"] - (-1.0)) < 1e-9    # per-segment reveals +1 / -1
    assert abs(m.agg(["R", "noise1", "noise2"]) - 0.5) < 1e-9          # keep -> 50
    assert abs(m.agg(["noise1", "noise2"]) - 0.5) < 1e-9               # cut  -> 50 (reword optimum = 100)


def test_correctness_debugger_finds_and_fixes_the_harmful_rule():
    """The flagship: the 'fill_all' rule corrupts records (hallucinates nulls); pieceofmind attributes
    it negative, and cutting it lifts record-correctness 50% -> 100%."""
    import importlib.util
    from pathlib import Path
    from pieceofmind import attribute_loo

    ex = Path(__file__).resolve().parents[1] / "examples" / "correctness_debugger.py"
    spec = importlib.util.spec_from_file_location("cdbg", ex)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    assert abs(m.record_correctness(m.SECTIONS) - 0.5) < 1e-9          # full prompt corrupts half
    loo = attribute_loo(m.SECTIONS, m.field_correctness, k=1, ids=m.SECTIONS)
    a = {x.id: x.attr for x in loo.per_input}
    assert a["fill_all"] < -0.05 and a["schema"] > 0.4                 # harmful vs load-bearing
    assert abs(a["be_polite"]) < 1e-9 and abs(a["explain"]) < 1e-9     # dead weight
    kept = [r for r in m.SECTIONS if a[r] >= -0.02]
    assert abs(m.record_correctness(kept) - 1.0) < 1e-9               # surgical fix -> 100%


def test_few_shot_example_flags_harmful_negative_and_splits_redundant():
    """The headline objective-metric example: a mislabelled few-shot gets a NEGATIVE Shapley value
    (meaningful here), redundant helpful examples split the credit, and the efficiency axiom holds."""
    import importlib.util
    from pathlib import Path

    ex = Path(__file__).resolve().parents[1] / "examples" / "few_shot_attribution.py"
    spec = importlib.util.spec_from_file_location("fsa", ex)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    from pieceofmind import attribute_shapley

    vfn = m.make_value_fn(m.TEST_SET, m.stub_predict)
    base = vfn([])
    r = attribute_shapley(m.FEWSHOTS, vfn, k=1, ids=m._IDS, empty_value=base)
    s = {p["id"]: p["shapley"] for p in r.per_input}
    assert s["E5"] < -0.05                          # mislabelled example is HARMFUL (negative)
    assert s["E1"] > 0.2 and s["E3"] > 0.2          # redundant helpful examples split the credit
    assert abs(s["E4"]) < 1e-9                       # off-topic example is inert
    assert r.efficiency_ok()                         # sum(Shapley) == v(full) - baseline


def test_marketing_example_reveals_redundancy_dead_and_harmful():
    """The non-technical demo: two channels reaching the same audience SPLIT the credit under Shapley
    (leave-one-out scores both $0 -- the costly trap), a dead channel is 0, a harmful one is negative."""
    import importlib.util
    from pathlib import Path

    ex = Path(__file__).resolve().parents[1] / "examples" / "marketing_attribution.py"
    spec = importlib.util.spec_from_file_location("mkt", ex)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    from pieceofmind import attribute_loo, attribute_shapley

    sh = attribute_shapley(m.CHANNELS, m.sales, k=1, ids=m._IDS, empty_value=m._BASELINE)
    s = {p["id"]: p["shapley"] for p in sh.per_input}
    assert abs(s["FB"] - 20.0) < 1e-9 and abs(s["INFL"] - 20.0) < 1e-9   # redundant pair splits the $40k
    assert abs(s["GOOG"] - 25.0) < 1e-9                                   # independent
    assert abs(s["BILL"]) < 1e-9                                         # dead money
    assert abs(s["POPUP"] - (-15.0)) < 1e-9                              # harmful (negative)
    assert sh.efficiency_ok()

    loo = attribute_loo(m.CHANNELS, m.sales, k=1, ids=m._IDS)
    a = {x.id: x.attr for x in loo.per_input}
    assert a["FB"] == 0.0 and a["INFL"] == 0.0   # the trap: LOO would tell you to cut both best channels


def test_prompt_section_example_finds_harmful_rule_and_redundant_pair():
    """The standard vibecoder case: a cargo-culted rule (R4) is HARMFUL (negative Shapley) and drags
    the full prompt to 0; two rules forcing the same thing (R1/R2) are a redundant load-bearing pair
    that leave-one-out masks; a filler rule (R3) is dead weight."""
    import importlib.util
    from pathlib import Path

    ex = Path(__file__).resolve().parents[1] / "examples" / "prompt_section_attribution.py"
    spec = importlib.util.spec_from_file_location("psa", ex)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    from pieceofmind import attribute_shapley

    vfn = m.make_value_fn(m.TESTS, m.stub_predict)
    assert vfn(m.IDS) == 0.0                              # full prompt sabotaged by R4
    r = attribute_shapley(m.IDS, vfn, k=1, ids=m.IDS, empty_value=vfn([]))
    s = {p["id"]: p["shapley"] for p in r.per_input}
    assert s["R4_end_with_smiley"] < -0.3                 # HARMFUL (negative)
    assert s["R1_only_email"] > 0.1 and abs(s["R1_only_email"] - s["R2_no_prose"]) < 1e-6  # redundant pair
    assert s["R5_contact_hint"] > 0.05                    # load-bearing on hard cases
    assert abs(s["R3_be_concise"]) < 1e-9                 # dead weight


def test_hello_example_is_clean_and_correct():
    import importlib.util
    from pathlib import Path
    from pieceofmind import attribute_shapley

    ex = Path(__file__).resolve().parents[1] / "examples" / "hello.py"
    spec = importlib.util.spec_from_file_location("hello", ex)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)                            # also exercises the print at import
    r = attribute_shapley(m.RULES, m.score, k=1, ids=m.RULES)
    s = {p["id"]: p["shapley"] for p in r.per_input}
    assert abs(s["concise"] - 0.4) < 1e-9 and abs(s["json"] - 0.4) < 1e-9   # load-bearing
    assert abs(s["polite"]) < 1e-9                                          # dead weight
    assert abs(s["emoji"] - (-0.5)) < 1e-9                                  # harmful
    assert r.efficiency_ok()


def test_label_free_checkers():
    import pieceofmind.checkers as C
    assert C.valid_json('{"a": 1}') and not C.valid_json("sorry, no json here")
    assert C.valid_json('```json\n{"a":1}\n```')                      # tolerates fences
    assert C.has_keys("name", "email")('{"name":"x","email":"y","phone":null}')
    assert not C.has_keys("name", "email")('{"name":"x"}')
    assert C.under_words(3)("a b c") and not C.under_words(3)("a b c d")
    assert C.no_refusal("here it is") and not C.no_refusal("I'm sorry, I can't do that")
    assert C.no_preamble('{"a":1}') and not C.no_preamble("Sure! Here you go: ...")
    combined = C.all_of(C.valid_json, C.has_keys("name"))
    assert combined('{"name":"x"}') and not combined("nope")


def test_build_synth_fn_parses_and_computes_data_share():
    canned = '{"recommendation":"z","claims":[{"claim":"a","provenance":"data","source":"F1"},' \
             '{"claim":"b","provenance":"model","source":"reasoning"}]}'
    synth_fn = build_synth_fn(lambda system, user: "prose " + canned + " trailing")
    rec = synth_fn(["F1 x"], "sit", "q?")
    assert rec["_provenance_summary"]["data_share"] == 0.5
