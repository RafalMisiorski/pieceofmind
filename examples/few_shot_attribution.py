"""Which few-shot examples actually carry your LLM's accuracy?

The HEADLINE use case for pieceofmind -- and the one where the math shines, because the value
function is OBJECTIVE (accuracy on a labelled test set), not the model's self-report. That matters:

  * It generalizes. Accuracy is a hard metric, so the attribution measures a real property of the
    prompt, not an artifact of how the model describes itself.
  * NEGATIVE attribution is MEANINGFUL here. A mislabelled / misleading few-shot example genuinely
    LOWERS accuracy -- so a negative Shapley value is a real "this example is hurting you" signal,
    not noise.
  * Redundancy shows up cleanly. Two few-shots that teach the same thing each look unimportant under
    leave-one-out (the other covers); exact Shapley splits the credit fairly.

You attribute the test-set accuracy to each few-shot example. value_fn(subset_of_examples) = accuracy
when the model is prompted with ONLY those examples. Bring your own LLM via a predict_fn; this file
ships a DETERMINISTIC stub model so it runs OFFLINE in <1s with no API key.

Run:  python examples/few_shot_attribution.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# allow running from a source checkout without installing
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pieceofmind import attribute_loo, attribute_shapley, render_loo, render_shapley  # noqa: E402

# A tiny sentiment task. POS items carry the keyword "great", NEG items carry "broken".
TEST_SET = [
    ("great product", "+"), ("great team", "+"), ("great value", "+"), ("great support", "+"),
    ("broken app", "-"), ("broken promise", "-"), ("broken build", "-"), ("broken trust", "-"),
]

# Candidate few-shot examples (text, label). Some help, one is redundant, one is useless, one is
# MISLABELLED (it teaches the model the wrong thing about "great").
FEWSHOTS = [
    ("a great experience", "+"),     # E1: teaches great->+ (helps the POS items)
    ("a broken mess", "-"),          # E2: teaches broken->- (but the model already defaults to -)
    ("simply great", "+"),           # E3: teaches great->+ (REDUNDANT with E1)
    ("the weather is mild", "+"),    # E4: teaches mild->+ (no test item uses 'mild' -> useless)
    ("a great disappointment", "-"), # E5: teaches great->-  (MISLABELLED -> HARMFUL, flips POS)
]
_IDS = ["E1", "E2", "E3", "E4", "E5"]

_KEYWORDS = ("great", "broken", "mild")


def _keyword(text: str):
    for kw in _KEYWORDS:
        if kw in text:
            return kw
    return None


def stub_predict(fewshots, text: str) -> str:
    """Deterministic offline stand-in for an LLM few-shot classifier. It learns a keyword->label map
    from whatever few-shots are in context and votes; with no evidence it defaults to '-'. Swap this
    for a real LLM call (see the bottom of this file) to run it for real."""
    votes_by_kw: dict = {}
    for ftext, flabel in fewshots:
        kw = _keyword(ftext)
        if kw:
            votes_by_kw.setdefault(kw, []).append(flabel)
    kw = _keyword(text)
    votes = votes_by_kw.get(kw, []) if kw else []
    if not votes:
        return "-"
    pos, neg = votes.count("+"), votes.count("-")
    return "+" if pos > neg else "-"   # tie -> '-'


def make_value_fn(test_set, predict_fn):
    """value_fn(subset_of_fewshots) -> accuracy on the test set with those few-shots."""
    def v(subset):
        fs = list(subset)
        correct = sum(1 for text, label in test_set if predict_fn(fs, text) == label)
        return correct / len(test_set)
    return v


def main() -> int:
    value_fn = make_value_fn(TEST_SET, stub_predict)
    baseline = value_fn([])  # accuracy with NO few-shots (the empty coalition)
    print(f"Task: 8-item sentiment. Accuracy with no few-shots (baseline) = {baseline}\n")

    loo = attribute_loo(FEWSHOTS, value_fn, k=1, ids=_IDS)        # deterministic -> k=1 is exact here
    sh = attribute_shapley(FEWSHOTS, value_fn, k=1, ids=_IDS, empty_value=baseline)
    print(render_loo(loo))
    print()
    print(render_shapley(sh))
    print()
    print("READING (this is why the OBJECTIVE value function is the strong case):")
    print(" - E1 and E3 both teach 'great->+'. Leave-one-out under-counts each (the other covers);")
    print("   exact Shapley splits the accuracy credit between them.")
    print(" - E5 is MISLABELLED ('great->-'). Its Shapley value is NEGATIVE -- and that is CORRECT:")
    print("   a misleading few-shot genuinely lowers accuracy. (In the provenance use case a negative")
    print("   value was nonsense; here it is a real 'this example is hurting you' signal.)")
    print(" - E2 (redundant with the default) and E4 (off-topic) sit near zero.")
    print(" - sum(Shapley) = v(full) - baseline, by the efficiency axiom -- the receipt.")
    return 0


# --- For REAL use, replace stub_predict with your LLM (the only change) ---------------------------
# def llm_predict(fewshots, text):
#     shots = "\n".join(f"Text: {t}\nLabel: {lab}" for t, lab in fewshots)
#     prompt = f"{shots}\nText: {text}\nLabel:"               # classic few-shot prompt
#     return "+" if "+" in your_llm_call(prompt)[:3] else "-"
# value_fn = make_value_fn(TEST_SET, llm_predict)             # then attribute_shapley(FEWSHOTS, value_fn, k=8)
# NOTE: cost = 2^n * K * len(TEST_SET) LLM calls for exact Shapley -- keep n and the test set small,
# or use the cheaper attribute_loo. See BENCHMARK.md.

if __name__ == "__main__":
    raise SystemExit(main())
