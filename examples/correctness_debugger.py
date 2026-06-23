"""correctness_debugger.py -- the flagship: find the prompt rule breaking your output, fix it, see the lift.

The whole reframe in one offline, deterministic run (<1s, no API key): a structured-extraction task
with a CORRECTNESS oracle (right values vs ground truth, null-aware -- NOT mere JSON validity). A
well-meaning rule -- "always fill every field; never leave it blank" -- silently corrupts records by
hallucinating values for fields that should be empty. The JSON is valid; the values are WRONG, so a
validity checker never catches it. pieceofmind attributes correctness to each rule, finds the culprit,
cuts it, and VERIFIES the lift -- with the money.

(This is a deterministic stand-in so it runs offline; data/measurements/m21_correctness_debugger.py is
the same loop on a real model. Swap the `extract` stub for your LLM to run it on your own prompt.)

Run:  python examples/correctness_debugger.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pieceofmind import attribute_loo, render_loo  # noqa: E402

# Ground-truth extractions; some fields are legitimately MISSING (None).
TRUTHS = [
    {"name": "Jane Doe", "email": "jane@acme.io", "amount": "1200"},
    {"name": "Bob Smith", "email": "bob@globex.com", "amount": "450"},
    {"name": "Maria Lopez", "email": None, "amount": "89"},
    {"name": "Sam Kim", "email": "sam@nimbus.ai", "amount": None},
    {"name": "Lena Park", "email": "lena@orbit.dev", "amount": "5000"},
    {"name": "Tom Hardy", "email": None, "amount": None},
    {"name": "Nina Patel", "email": None, "amount": "320"},
    {"name": "Omar Said", "email": "omar@zen.io", "amount": "760"},
]
FIELDS = ("name", "email", "amount")

SECTIONS = ["schema", "fill_all", "be_polite", "explain"]


def extract(rules, truth):
    """Deterministic stand-in for an LLM following the active prompt rules."""
    if "schema" not in rules:                 # without the schema rule it doesn't emit the fields
        return {}
    out = dict(truth)
    if "fill_all" in rules:                    # the harmful rule: hallucinate a value for empty fields
        for k, v in list(out.items()):
            if v is None:
                out[k] = f"<guessed {k}>"
    return out                                  # be_polite / explain change nothing


def field_correctness(rules):
    ok = tot = 0
    for truth in TRUTHS:
        pred = extract(set(rules), truth)
        for f in FIELDS:
            ok += int(pred.get(f) == truth[f])   # None==None counts as correct (right to leave it blank)
            tot += 1
    return ok / tot


def record_correctness(rules):
    return sum(int(extract(set(rules), t) == t) for t in TRUTHS) / len(TRUTHS)


def main() -> int:
    full = record_correctness(SECTIONS)
    print(f"Your 4-rule extraction prompt: {full*100:.0f}% of records are fully correct.\n")

    # 1) FIND + WHY
    loo = attribute_loo(SECTIONS, field_correctness, k=1, ids=SECTIONS)
    print(render_loo(loo))

    # 2) SURGICAL FIX  3) VERIFIED LIFT
    harmful = [a.id for a in loo.per_input if a.attr < -0.02]
    kept = [r for r in SECTIONS if r not in harmful]
    fixed = record_correctness(kept)
    lift = fixed - full

    VOL, COST = 10_000, 0.50
    savings = lift * VOL * COST * 365

    print(f"\nFIX: cut {harmful} -> record-correctness {full*100:.0f}% -> {fixed*100:.0f}% (+{lift*100:.0f} pts).")
    print(f"WHY: 'always fill every field' makes the model HALLUCINATE values for fields that should be")
    print(f"     blank -- valid JSON, wrong data. A JSON-validity check never catches it; a correctness")
    print(f"     oracle does. pieceofmind found the one rule, you cut it, correctness is verified.")
    print(f"MONEY (illustrative: {VOL:,}/day x ${COST}/corrupted record): ~${savings:,.0f}/year recovered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
