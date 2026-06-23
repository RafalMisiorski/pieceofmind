"""Which parts of your prompt actually matter? (the standard case -- run it on YOUR prompt)

Every vibecoder has a bloated system prompt / CLAUDE.md / Cursor-rules file with 10-20 instructions
and no idea which ones earn their tokens. `pieceofmind` answers it objectively: split your prompt into
sections, give a few test inputs and a pass/fail checker, and it tells you which sections are
LOAD-BEARING, which are REDUNDANT, which are DEAD WEIGHT (delete them -- shorter prompt, fewer
tokens), and which are HARMFUL (a rule that actively lowers your pass-rate -- a negative score).

value_fn(subset_of_sections) = pass-rate over your test inputs when the model is prompted with ONLY
those sections. Objective (a real checker, not the model's opinion -- the M16 lesson). Use
attribute_loo (cheap: (n+1)*K*|inputs| calls) for a quick read; attribute_shapley when sections are
redundant.

This file runs OFFLINE with a deterministic stub model (no API key, <1s) so you can see the shape
first; the BRING-YOUR-OWN-LLM block at the bottom is the 6-line change to run it on your real prompt.

Run:  python examples/prompt_section_attribution.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pieceofmind import attribute_loo, attribute_shapley, render_loo, render_shapley  # noqa: E402

# A bloated "extract the email, output ONLY the email" system prompt, split into named SECTIONS.
SECTIONS = {
    "R1_only_email":   "Output ONLY the email address. No other words.",
    "R2_no_prose":     "Do not add any explanation or surrounding prose.",   # redundant with R1
    "R3_be_concise":   "Be concise and professional.",                       # dead weight
    "R4_end_with_smiley": "Always end every reply with a friendly :) to seem warm.",  # HARMFUL
    "R5_contact_hint": "The wanted email is the one right after the word 'contact'.",  # helps hard cases
}
IDS = list(SECTIONS)

# Test inputs: (text, expected_email). Two EASY (one email), two HARD (a decoy email, real one after
# 'contact') -- the hard ones need the R5 hint to extract correctly.
TESTS = [
    ("Reach me at jane@acme.io anytime.", "jane@acme.io"),
    ("Ping bob@globex.com for access.", "bob@globex.com"),
    ("Old: noreply@spam.io. For support contact help@orbit.dev please.", "help@orbit.dev"),
    ("Sales: sales@decoy.co -- but contact founder@nimbus.ai directly.", "founder@nimbus.ai"),
]
_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def stub_predict(active_sections, text: str) -> str:
    """Deterministic offline stand-in for an LLM following the active prompt sections."""
    emails = _EMAIL.findall(text)
    hard = len(emails) > 1
    if hard:
        m = re.search(r"contact\s+([\w.+-]+@[\w.-]+\.\w+)", text)
        pick = m.group(1) if (m and "R5_contact_hint" in active_sections) else emails[0]  # decoy w/o R5
    else:
        pick = emails[0] if emails else ""
    only = "R1_only_email" in active_sections or "R2_no_prose" in active_sections
    out = pick if only else f"Sure! Contact them at {pick}, hope that helps."
    if "R4_end_with_smiley" in active_sections:           # cargo-cult rule -> breaks exact-match output
        out = out + " :)"
    return out


def make_value_fn(tests, predict_fn):
    def v(subset_sections):
        active = set(subset_sections)
        correct = sum(1 for text, expected in tests if predict_fn(active, text).strip() == expected)
        return correct / len(tests)
    return v


def main() -> int:
    value_fn = make_value_fn(TESTS, stub_predict)
    print(f"pass-rate with the FULL prompt (all 5 sections) = {value_fn(IDS):.2f}")
    print(f"pass-rate with just R1 = {value_fn(['R1_only_email']):.2f}, "
          f"with R1+R5 = {value_fn(['R1_only_email', 'R5_contact_hint']):.2f}\n")

    loo = attribute_loo(IDS, value_fn, k=1, ids=IDS)            # deterministic -> k=1 exact
    sh = attribute_shapley(IDS, value_fn, k=1, ids=IDS, empty_value=value_fn([]))
    print(render_loo(loo))
    print()
    print(render_shapley(sh))
    print()
    print("READING (what a vibecoder does with this):")
    print("  * R1 / R2 are a REDUNDANT load-bearing pair (both force 'email only'); keep one, cut one.")
    print("  * R5 (the 'contact' hint) is genuinely load-bearing on the hard inputs -- keep it.")
    print("  * R3 ('be concise') is DEAD WEIGHT -- delete it, shorter prompt, same result.")
    print("  * R4 ('end with a smiley') is HARMFUL (negative): the cargo-culted emoji breaks the")
    print("    exact-match output and drags the WHOLE prompt's pass-rate down. Delete it first.")
    return 0


# --- RUN IT ON YOUR PROMPT (no labels needed -- use a structural checker) ------------------------
# import pieceofmind.checkers as C
# CHECK = C.all_of(C.valid_json, C.has_keys("name", "email"))     # label-FREE: no ground truth needed
# MY_TESTS = ["first input", "second input", ...]                 # just inputs; the checker scores them
# def value_fn(active_sections):
#     system = "\n".join(SECTIONS[s] for s in active_sections)    # build prompt from the active sections
#     return sum(CHECK(your_llm_call(system, t)) for t in MY_TESTS) / len(MY_TESTS)
# print(render_loo(attribute_loo(list(SECTIONS), value_fn, k=2))) # LOO = the cheap default; cost =
#                                                                 # (n+1)*K*len(MY_TESTS) LLM calls.
# This is the friction-killer: point it at your existing CLAUDE.md / system prompt with NO labeled
# eval set -- the structural checker (valid JSON / required keys / under N words / no refusal) is the
# objective metric. See data/measurements/m19_prompt_live_gate.py for a live-model validation.

if __name__ == "__main__":
    raise SystemExit(main())
