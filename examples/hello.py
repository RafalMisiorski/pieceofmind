"""hello.py -- the 30-second "see it work" for a brand-new vibe coder. No LLM, no setup, <1s.

The whole idea of pieceofmind in 6 lines: you have a few INPUTS and a SCORE; it tells you which
inputs actually carry the score, which are dead weight, and which are HARMFUL. Here the inputs are
4 rules of a tiny prompt and the "score" is a toy stand-in for "did the AI do what I wanted".

Swap the toy `score` for YOUR thing -- your real prompt's pass-rate, your model's accuracy, your
sales -- and it works the same. (See prompt_section_attribution.py to run it on a real prompt.)
"""

from pieceofmind import attribute_shapley, render_shapley


def score(rules):
    # Toy "AI quality" for a 4-rule prompt: 'concise' and 'json' each help, 'polite' does nothing,
    # and 'emoji' is a cargo-culted rule that makes the output WORSE.
    s = 0.0
    if "concise" in rules:
        s += 0.4
    if "json" in rules:
        s += 0.4
    if "emoji" in rules:
        s -= 0.5
    return s


RULES = ["concise", "json", "polite", "emoji"]
print(render_shapley(attribute_shapley(RULES, score, k=1, ids=RULES)))
print("\nconcise + json carry the score (load-bearing, +0.4 each); 'polite' is dead weight (0, delete it);")
print("'emoji' is HARMFUL (-0.5, it makes things worse -- delete it first). Now swap `score` for YOUR")
print("prompt's pass-rate / your model's accuracy / your sales, and it works exactly the same.")
