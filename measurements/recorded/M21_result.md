# M21 -- interpretable correctness-debugger: find -> fix -> verified lift -> $

**FIX: cut ['guess'] -> record-correctness 0.500 -> 1.000 (+50.0 pts). At 10000/day x $0.5/bad-record that is ~$912,500/year recovered.**

## What this PROVES (and, honestly, what it does NOT)
PROVES: the reframe loop works end-to-end -- a CORRECTNESS oracle (right values, null-aware) catches a
harm a JSON-validity checker cannot; pieceofmind isolates the single responsible rule (`guess` -0.21,
all others 0.0); the surgical cut recovers correctness with the measured WHY and a money number.
The harmful rule is PLANTED but REALISTIC -- "if a value is missing, infer the most likely value" is
the kind of well-meaning instruction people actually write, and it corrupts nullable fields by
hallucinating. That honest failure mode is the point.

DOES NOT prove (state plainly):
1. **Magnitude is test-design-dependent.** Exactly 4 of 8 docs have a missing field, so the harm is
   4/8 = 50 pts by construction; the $912k uses illustrative knobs (10k/day, $0.50/record). This is
   NOT "guess rules cost 50% / $912k" in general -- it is a clean mechanism + money-translation demo.
2. **It does NOT yet beat naive 1-step LOO.** On this SINGLE-harmful-rule task, plain leave-one-out
   already flags `guess` (-0.21) -- our K-fold/Shapley adds nothing here. pieceofmind's edge over naive
   LOO only shows up when rules INTERACT or are REDUNDANT (LOO masks those; Shapley splits them). So
   M22's task set MUST include an interacting/redundant-harmful-rule case, or we honestly concede that
   for the simple single-rule case naive LOO suffices and our value is the noise-floor + packaging.
3. Single model (Gemini), 8 docs, K=1 -> a clean read, not a generalization.

Net: the LOOP and the $ story are real and demonstrable; the differentiation-vs-the-field question is
open and is exactly what M22 (interacting-rules + DSPy/llmSHAP/naive-LOO contestants) must answer.

Task: extract name/email/amount. Oracle: exact VALUE match vs ground truth, null-aware (NOT
JSON validity). Model: Gemini (agy). The planted-but-realistic harmful rule: 'if a value is
missing, infer the most likely value' -- sounds helpful, hallucinates values for fields that
should be null, corrupting records. A validity checker misses it; a correctness oracle catches
it. Total LLM calls = 56.

Full prompt: field-correctness=0.792, record-correctness=0.500.

## 1. FIND + WHY -- correctness attribution per rule (leave-one-out)

# Leave-one-out attribution (baseline 0.7917 +/- 0.0, K=1)

| input | attribution | significant | reading |
|---|---|---|---|
| schema | 0.0 +/- 0.0 | no | not load-bearing (below noise floor) |
| json_only | 0.0 +/- 0.0 | no | not load-bearing (below noise floor) |
| quotes | 0.0 +/- 0.0 | no | not load-bearing (below noise floor) |
| amount_fmt | 0.0 +/- 0.0 | no | not load-bearing (below noise floor) |
| explain | 0.0 +/- 0.0 | no | not load-bearing (below noise floor) |
| guess | -0.2083 +/- 0.0 | YES | removing it RAISES the score (noise/redundancy) |

NOTE: significance is |attr| > 2*SE over K reruns. Negative or sub-noise attributions are the signature of redundancy/noise -- use attribute_shapley for the redundancy-correct number.

## 2. SURGICAL FIX + 3. VERIFIED LIFT
- harmful rules cut: ['guess']
- kept: ['schema', 'json_only', 'quotes', 'amount_fmt', 'explain']
- field-correctness 0.792 -> 1.000
- record-correctness 0.500 -> 1.000  (+50.0 pts)
- $ (illustrative: 10000/day x $0.5/corrupted record): ~$912,500/year recovered

Read: this is the reframe end-to-end -- not a score, but a debugged-and-fixed prompt with the
measured WHY and the money. A plausible rule silently corrupted records (valid JSON, wrong
values); pieceofmind isolated it and cutting it recovered correctness. Interpretable + surgical
-- you keep control of the prompt (vs a black-box optimizer rewriting it).