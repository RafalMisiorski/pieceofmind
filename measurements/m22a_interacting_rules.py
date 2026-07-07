"""M22a -- the cheapest test that can REFUTE us: pieceofmind (Shapley) vs naive 1-step LOO, on a task
with TWO REDUNDANTLY-HARMFUL rules.

M21 showed naive leave-one-out already finds a SINGLE harmful rule -> our Shapley/K-fold adds nothing
there. Our edge can ONLY appear when rules INTERACT. The canonical case: two rules that EACH
independently cause the harm. Then removing one alone does not fix it (the other still causes it), so
naive 1-step LOO scores BOTH ~0 (masked) and would tell you to cut NEITHER -> the harm persists.
Exact Shapley splits the blame and flags BOTH -> the correct fix is to cut both.

Two well-meaning "completeness" rules that each make the model hallucinate nullable fields:
  fill_all: "always provide a value for every field; never leave it blank/null"
  infer:    "if a value is not stated, infer the most likely value"
Empirical question on a REAL model (Gemini): is the harm actually REDUNDANT (removing one alone does
not recover), so Shapley beats naive LOO? If not -> honest: naive LOO suffices, our edge unproven.

PRE-REGISTERED win: the Shapley-guided fix recovers MORE record-correctness than the naive-LOO-guided
fix. Tie/loss -> we concede. ASCII-only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from pieceofmind import attribute_shapley, render_shapley  # noqa: E402
import pieceofmind.checkers as C  # noqa: E402
from llm_seam import make_llm  # noqa: E402

OUT = HERE / "M22a_result.local.md"

DOCS = [
    ("Invoice from Jane Doe (jane@acme.io) for $1,200.", {"name": "Jane Doe", "email": "jane@acme.io", "amount": "1200"}),
    ("Bill to Bob Smith, bob@globex.com. Total: $450.", {"name": "Bob Smith", "email": "bob@globex.com", "amount": "450"}),
    ("Lena Park requested $5,000, lena@orbit.dev.", {"name": "Lena Park", "email": "lena@orbit.dev", "amount": "5000"}),
    ("From Maria Lopez. Amount due: $89.", {"name": "Maria Lopez", "email": None, "amount": "89"}),       # no email
    ("Contact: Sam Kim (sam@nimbus.ai).", {"name": "Sam Kim", "email": "sam@nimbus.ai", "amount": None}),  # no amount
    ("Pay $320 to Nina Patel.", {"name": "Nina Patel", "email": None, "amount": "320"}),                  # no email
]
FIELDS = ("name", "email", "amount")

SECTIONS = {
    "schema":   "Return a JSON object with keys: name, email, amount.",
    "fill_all": "Always provide a value for every field; never leave a field blank or null.",   # harm A
    "infer":    "If a value is not stated in the text, infer the most likely value.",            # harm B (redundant)
    "amount_fmt": "Give amounts as plain numbers, no currency symbol and no thousands separators.",
}
IDS = list(SECTIONS)


def _norm(field, val):
    if val is None:
        return ""
    s = str(val).strip().lower()
    if field == "amount":
        s = re.sub(r"[^\d]", "", s)
    return s


def _field_correct(field, pred, truth):
    if truth is None:
        return pred in (None, "") or (isinstance(pred, str) and pred.strip().lower() in ("", "null", "none", "n/a", "unknown"))
    return _norm(field, pred) == _norm(field, truth)


def _parse(text):
    try:
        o = json.loads(C._extract_json(text))
        return o if isinstance(o, dict) else {}
    except Exception:
        return {}


_backend = None

def _llm(prompt, fn=None):
    global _backend
    if _backend is None:
        _backend = make_llm()
    r = {}
    for _ in range(3):                       # retry on empty/timeout -- channel noise corrupts coalitions
        r = _parse(_backend(prompt) or "")
        if r:
            return r
    return r


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="m22a")
    ap.add_argument("--model", default="via-PIECEOFMIND_LLM_CMD")
    args = ap.parse_args()
    caller = None  # the model comes from PIECEOFMIND_LLM_CMD (measurements/llm_seam.py)
    n_calls = [0]
    cache: dict = {}

    def out(subset, di):
        key = (frozenset(subset), di)
        if key not in cache:
            rules = "\n".join(SECTIONS[s] for s in subset)
            prompt = (rules + "\n\n" if rules else "") + f"Extract the fields.\n\nText: {DOCS[di][0]}"
            cache[key] = _llm(prompt, caller)
            n_calls[0] += 1
        return cache[key]

    def field_corr(subset):
        ok = tot = 0
        for di, (_, truth) in enumerate(DOCS):
            pred = out(subset, di)
            for f in FIELDS:
                ok += int(_field_correct(f, pred.get(f), truth[f]))
                tot += 1
        return ok / tot

    def record_corr(subset):
        ok = 0
        for di, (_, truth) in enumerate(DOCS):
            pred = out(subset, di)
            ok += int(all(_field_correct(f, pred.get(f), truth[f]) for f in FIELDS))
        return ok / len(DOCS)

    full_field = field_corr(IDS)
    full_record = record_corr(IDS)
    print(f"full prompt: field={full_field:.3f} record={full_record:.3f}")

    sh = attribute_shapley(IDS, field_corr, k=1, ids=IDS, empty_value=field_corr([]))
    print(render_shapley(sh))
    shap = {p["id"]: p["shapley"] for p in sh.per_input}
    loo = {p["id"]: p["loo"] for p in sh.per_input}

    TH = 0.03
    # naive 1-step LOO fix: cut rules whose single-drop (LOO) shows harm
    loo_cut = [r for r in IDS if loo[r] < -TH]
    loo_kept = [r for r in IDS if r not in loo_cut]
    loo_fix_record = record_corr(loo_kept)
    # pieceofmind Shapley fix: cut rules whose Shapley shows harm
    shap_cut = [r for r in IDS if shap[r] < -TH]
    shap_kept = [r for r in IDS if r not in shap_cut]
    shap_fix_record = record_corr(shap_kept)

    win = shap_fix_record > loo_fix_record + 1e-9
    verdict = (f"pieceofmind WINS the discriminator: Shapley-fix record-correctness {shap_fix_record:.3f} "
               f"> naive-LOO-fix {loo_fix_record:.3f}. naive LOO masked the redundant harmful pair "
               f"(cut {loo_cut}); Shapley caught it (cut {shap_cut})."
               if win else
               f"NO EDGE here: naive-LOO-fix {loo_fix_record:.3f} >= Shapley-fix {shap_fix_record:.3f}. "
               f"Honest concede -- on this real run the harm was not redundant enough for Shapley to "
               f"beat naive LOO (LOO cut {loo_cut}, Shapley cut {shap_cut}).")

    L = ["# M22a -- pieceofmind (Shapley) vs naive 1-step LOO on REDUNDANTLY-harmful rules", "",
         f"**{verdict}**", "",
         "The test that can refute us: two completeness rules (fill_all, infer) that each independently",
         "make the model hallucinate nullable fields. If the harm is redundant, naive 1-step LOO masks",
         "BOTH (each ~0) and fixes nothing; exact Shapley splits the blame and cuts both. Real model:",
         f"{args.model} (retry-on-empty). Oracle: exact value match vs ground truth, null-aware. "
         f"Total LLM calls = {n_calls[0]}.", "",
         f"Full prompt: field-correctness={full_field:.3f}, record-correctness={full_record:.3f}.", "",
         render_shapley(sh), "",
         "## The head-to-head fix",
         f"- naive 1-step LOO would cut {loo_cut} -> kept {loo_kept} -> record-correctness {loo_fix_record:.3f}",
         f"- pieceofmind Shapley cuts {shap_cut} -> kept {shap_kept} -> record-correctness {shap_fix_record:.3f}",
         f"- per-rule (Shapley | LOO): " + ", ".join(f"{r}={shap[r]}|{loo[r]}" for r in IDS), "",
         "Read: if fill_all and infer both show NEGATIVE Shapley but ~0 LOO, that is the masking naive",
         "LOO cannot see -- and cutting both (Shapley's call) recovers correctness that cutting per-LOO",
         "does not. If instead LOO already flags them, the harm was not redundant and we concede."]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print("\n" + verdict)
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
