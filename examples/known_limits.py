"""known_limits.py -- where pieceofmind structurally breaks (honest, deterministic, offline).

Two limits, shown on one clean construction so you can see exactly when NOT to trust an aggregate run.
A rule `R` that is LOAD-BEARING for one input segment (A) and HARMFUL for another (B), in equal
measure. (Real example: "interpret ambiguous dates as US MM/DD" -- right for US inputs, wrong for EU.)

LIMIT 1 -- aggregate attribution HIDES heterogeneity. The help on A and the harm on B cancel, so the
aggregate score moves ~0 and pieceofmind calls R "dead weight". Cutting it (because "dead") then
silently destroys segment A. The honest mitigation: attribute PER SEGMENT, not just in aggregate.

LIMIT 2 -- cut/keep cannot REWORD. The optimum is "apply R only to segment A", which reaches 100%.
pieceofmind can only keep R (A right, B wrong = 50%) or cut R (A wrong, B right = 50%). The +50 the
reword reaches is structurally unreachable by cut/keep -- an optimizer that rewrites can beat us here.

These are facts about the METHOD's expressiveness, not about any model. pieceofmind still DIAGNOSES
(per-segment it points straight at R); it just cannot, by itself, reach the rewrite-only optimum.

Run:  python examples/known_limits.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pieceofmind import attribute_loo, render_loo  # noqa: E402

# 4 segment-A docs + 4 segment-B docs. R helps A (A correct only WITH R), hurts B (B correct only
# WITHOUT R). noise1/noise2 do nothing.
SEGMENTS = ["A", "A", "A", "A", "B", "B", "B", "B"]
RULES = ["R", "noise1", "noise2"]


def correctness(rules, segments):
    ok = 0
    for seg in segments:
        ok += int(("R" in rules) if seg == "A" else ("R" not in rules))
    return ok / len(segments)


def agg(rules):
    return correctness(rules, SEGMENTS)


def seg_only(letter):
    docs = [s for s in SEGMENTS if s == letter]
    return lambda rules: correctness(rules, docs)


def main() -> int:
    print("A rule R that helps segment A and hurts segment B equally.\n")

    print("=== LIMIT 1: aggregate attribution HIDES heterogeneity ===")
    print(render_loo(attribute_loo(RULES, agg, k=1, ids=RULES)))
    print("\n-> aggregate says R is ~0 ('dead weight'). But per segment:")
    a = {x.id: x.attr for x in attribute_loo(RULES, seg_only("A"), k=1, ids=RULES).per_input}
    b = {x.id: x.attr for x in attribute_loo(RULES, seg_only("B"), k=1, ids=RULES).per_input}
    print(f"   segment A: R = {a['R']:+.2f} (LOAD-BEARING)   segment B: R = {b['R']:+.2f} (HARMFUL)")
    print("   Cutting R because the aggregate called it 'dead' would silently destroy segment A.")
    print("   Honest mitigation: run attribution per segment, not just in aggregate.\n")

    print("=== LIMIT 2: cut/keep cannot REWORD ===")
    keep = agg(["R", "noise1", "noise2"])
    cut = agg(["noise1", "noise2"])
    reword = 1.0   # "apply R only to segment A" -> A right AND B right
    print(f"   keep R:  {keep*100:.0f}%   cut R: {cut*100:.0f}%   <- pieceofmind's only two options")
    print(f"   reword R (apply only to A): {reword*100:.0f}%  <- the optimum, unreachable by cut/keep")
    print(f"   gap an optimizer that REWRITES can take that we cannot: +{(reword-max(keep,cut))*100:.0f} pts.\n")

    print("BOTTOM LINE: pieceofmind is an aggregate cut/keep diagnostic. When a rule's effect is")
    print("heterogeneous across input segments, (1) read it per-segment, and (2) the fix may be a")
    print("REWORD you or an optimizer must do -- pieceofmind points at the rule, it does not rewrite it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
