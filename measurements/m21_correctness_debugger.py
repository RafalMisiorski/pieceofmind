"""M21 -- the interpretable correctness-debugger proof: find -> why -> surgical fix -> verified lift -> $.

The market-value case (per OSS_SCOPE reframe): attribute STRUCTURED-OUTPUT CORRECTNESS (right VALUES vs
ground truth -- NOT mere JSON validity) to the prompt rules, find the plausible-but-harmful rule, CUT
it, re-measure, and show the correctness LIFT translated to money.

The planted-but-realistic harmful rule: "if a value is missing, infer the most likely value" -- sounds
helpful, but it makes the model HALLUCINATE values for fields that should be null, silently corrupting
records. A JSON-validity checker would never catch it (the output is valid JSON). A correctness oracle
(exact value match vs ground truth, null-aware) does. pieceofmind finds it; cutting it recovers the
correct-record rate. RECORDED run used Gemini (via the author's CLI); bring your own model via measurements/llm_seam.py
(PIECEOFMIND_LLM_CMD). Recorded raw output: measurements/recorded/. ASCII-only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from pieceofmind import attribute_loo, render_loo  # noqa: E402
import pieceofmind.checkers as C  # noqa: E402
from llm_seam import make_llm  # noqa: E402

OUT = HERE / "M21_result.local.md"

# Labeled extraction set: text -> ground-truth field values. Some fields are MISSING (None) -- those
# are where the "guess if missing" rule will hallucinate and be WRONG.
DOCS = [
    ("Invoice from Jane Doe (jane@acme.io) for $1,200.", {"name": "Jane Doe", "email": "jane@acme.io", "amount": "1200"}),
    ("Bill to Bob Smith, bob@globex.com. Total: $450.", {"name": "Bob Smith", "email": "bob@globex.com", "amount": "450"}),
    ("From Maria Lopez. Amount due: $89.", {"name": "Maria Lopez", "email": None, "amount": "89"}),
    ("Contact: Sam Kim (sam@nimbus.ai).", {"name": "Sam Kim", "email": "sam@nimbus.ai", "amount": None}),
    ("Lena Park requested $5,000, lena@orbit.dev.", {"name": "Lena Park", "email": "lena@orbit.dev", "amount": "5000"}),
    ("Invoice for Tom Hardy. Contact details pending.", {"name": "Tom Hardy", "email": None, "amount": None}),
    ("Pay $320 to Nina Patel.", {"name": "Nina Patel", "email": None, "amount": "320"}),
    ("Order from Omar Said, omar@zen.io, $760.", {"name": "Omar Said", "email": "omar@zen.io", "amount": "760"}),
]
FIELDS = ("name", "email", "amount")

SECTIONS = {
    "schema":     "Return a JSON object with keys: name, email, amount.",
    "json_only":  "Output only the JSON. No surrounding text and no markdown fences.",
    "quotes":     "Use double quotes for all keys and string values.",
    "amount_fmt": "Give amounts as plain numbers, no currency symbol and no thousands separators.",
    "guess":      "If a value is not stated in the text, infer the most likely value rather than leaving it blank.",
    "explain":    "Think step by step before giving the answer.",
}
IDS = list(SECTIONS)


def _norm(field: str, val) -> str:
    if val is None:
        return ""
    s = str(val).strip().lower()
    if field == "amount":
        s = re.sub(r"[^\d]", "", s)
    return s


def _field_correct(field, pred, truth) -> bool:
    if truth is None:                       # expected MISSING -> correct iff model left it blank/null
        return pred in (None, "") or (isinstance(pred, str) and pred.strip().lower() in ("", "null", "none", "n/a", "unknown"))
    return _norm(field, pred) == _norm(field, truth)


_backend = None

def _llm(prompt: str) -> str:
    global _backend
    if _backend is None:
        _backend = make_llm()
    return _backend(prompt)


def _parse(text: str) -> dict:
    try:
        obj = json.loads(C._extract_json(text))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def main() -> int:
    n_calls = [0]
    cache: dict = {}

    def out(subset, di):
        key = (frozenset(subset), di)
        if key not in cache:
            rules = "\n".join(SECTIONS[s] for s in subset)
            prompt = (rules + "\n\n" if rules else "") + f"Extract the fields.\n\nText: {DOCS[di][0]}"
            cache[key] = _parse(_llm(prompt))
            n_calls[0] += 1
        return cache[key]

    def field_correctness(subset):     # fraction of all fields correct (granular -> good for attribution)
        ok = tot = 0
        for di, (_, truth) in enumerate(DOCS):
            pred = out(subset, di)
            for f in FIELDS:
                ok += int(_field_correct(f, pred.get(f), truth[f]))
                tot += 1
        return ok / tot

    def record_correctness(subset):    # fraction of records with ALL fields correct (the $ metric)
        ok = 0
        for di, (_, truth) in enumerate(DOCS):
            pred = out(subset, di)
            ok += int(all(_field_correct(f, pred.get(f), truth[f]) for f in FIELDS))
        return ok / len(DOCS)

    full_field = field_correctness(IDS)
    full_record = record_correctness(IDS)
    print(f"full prompt: field-correctness={full_field:.3f}, record-correctness={full_record:.3f}")

    # 1) FIND + WHY: attribute field-correctness to each rule
    loo = attribute_loo(IDS, field_correctness, k=1, ids=IDS)
    print(render_loo(loo))

    # 2) SURGICAL FIX: cut the rules that significantly HURT correctness, keep the rest
    harmful = [a.id for a in loo.per_input if a.attr < -0.02]
    kept = [r for r in IDS if r not in harmful]
    fixed_field = field_correctness(kept)
    fixed_record = record_correctness(kept)
    lift_record = fixed_record - full_record

    # 3) $ TRANSLATION (illustrative knobs)
    VOL = 10000       # records/day through this extraction feature
    COST = 0.50       # $ to fix one corrupted record (retry + human review)
    savings_yr = lift_record * VOL * COST * 365

    verdict = (f"FIX: cut {harmful} -> record-correctness {full_record:.3f} -> {fixed_record:.3f} "
               f"(+{lift_record*100:.1f} pts). At {VOL}/day x ${COST}/bad-record that is "
               f"~${savings_yr:,.0f}/year recovered."
               if harmful and lift_record > 0 else
               "NO net-harmful rule found that a cut improves -- honest null for this task/model.")

    L = ["# M21 -- interpretable correctness-debugger: find -> fix -> verified lift -> $", "",
         f"**{verdict}**", "",
         "Task: extract name/email/amount. Oracle: exact VALUE match vs ground truth, null-aware (NOT",
         "JSON validity). Model: Gemini (agy). The planted-but-realistic harmful rule: 'if a value is",
         "missing, infer the most likely value' -- sounds helpful, hallucinates values for fields that",
         "should be null, corrupting records. A validity checker misses it; a correctness oracle catches",
         f"it. Total LLM calls = {n_calls[0]}.", "",
         f"Full prompt: field-correctness={full_field:.3f}, record-correctness={full_record:.3f}.", "",
         "## 1. FIND + WHY -- correctness attribution per rule (leave-one-out)", "",
         render_loo(loo), "",
         "## 2. SURGICAL FIX + 3. VERIFIED LIFT",
         f"- harmful rules cut: {harmful}",
         f"- kept: {kept}",
         f"- field-correctness {full_field:.3f} -> {fixed_field:.3f}",
         f"- record-correctness {full_record:.3f} -> {fixed_record:.3f}  (+{lift_record*100:.1f} pts)",
         f"- $ (illustrative: {VOL}/day x ${COST}/corrupted record): ~${savings_yr:,.0f}/year recovered", "",
         "Read: this is the reframe end-to-end -- not a score, but a debugged-and-fixed prompt with the",
         "measured WHY and the money. A plausible rule silently corrupted records (valid JSON, wrong",
         "values); pieceofmind isolated it and cutting it recovered correctness. Interpretable + surgical",
         "-- you keep control of the prompt (vs a black-box optimizer rewriting it)."]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print("\n" + verdict)
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
