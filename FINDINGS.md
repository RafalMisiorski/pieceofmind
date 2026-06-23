# FINDINGS -- what we measured (including where pieceofmind does NOT help)

pieceofmind was built by measuring its own value at every step and killing what didn't hold. This file
is the evidence ledger. Every claim links to a result; the honest nulls are here too.

## The headline: a well-meaning rule that silently corrupts your data
On a real extraction task with a CORRECTNESS oracle (right values vs ground truth, null-aware -- not
mere JSON validity), the rule **"if a value is missing, infer the most likely value"** -- which sounds
helpful -- made the model hallucinate values for fields that should be blank. Valid JSON, wrong data.
Record-correctness sat at **50%**. pieceofmind attributed correctness to each rule (the culprit at
-0.21, everything else ~0), we cut the one rule, and record-correctness went **50% -> 100%**. A
JSON-validity check would never catch this; only a correctness oracle does. (M21)

## We beat the baseline a practitioner actually uses
The dumb way to find a bad rule is "turn it off and check" (single-step leave-one-out). It FAILS when
rules overlap: two completeness rules that each independently cause the harm -- removing one alone
doesn't fix it, so leave-one-out scores it ~0 and tells you to keep it. On a real model (Codex), naive
leave-one-out caught one rule and stayed stuck at **83.3%**; pieceofmind's exact Shapley caught BOTH
and reached **100%** -- **+16.7 points the naive method leaves on the table**, with the redundancy
emerging from the model's behavior, not planted. The credits provably summed to the whole. (M22a)

## As correct as an optimizer -- but you keep your prompt and learn the why
Against an automatic prompt optimizer (a minimal APE-style rewrite) on held-out test docs: full and
naive-leave-one-out both stuck at **50%**, pieceofmind and the optimizer both reached **100%** -- a TIE
on correctness. But the optimizer rewrote the prompt into an opaque new block ("use null... do not
infer/guess"), rediscovering the same root cause at more LLM calls and with no explanation.
pieceofmind names the exact rules to cut (`fill_all`, `infer`) and you keep your prompt's structure. So
on outcome we match the optimizer; our edge is interpretability + control + cost. (Honest: a minimal
optimizer, not full DSPy/MIPRO; on this task both hit the ceiling, so it separates us only on those
axes, not on raw correctness.) (M22b)

## Where it breaks (we went looking)
We built a HARD case to expose pieceofmind's structural ceiling: it can only CUT or KEEP a rule, never
REWORD it -- so a rule that's right for some inputs and wrong for others should let a rewriting
optimizer beat us. On agent tool-routing with an over-broad "if it mentions a time, use the calendar"
rule: pieceofmind correctly diagnosed the rule as harmful (-0.117), but cutting it was ENOUGH (the
capable model routed the scheduling requests correctly without it), so we TIED the optimizer at 1.000.
The ceiling did NOT bind. Honest residual limits, stated not hidden:
- **The cut/keep ceiling is real but bites rarely on capable models** (M23): a strong model often does
  the "good" cases without the rule, so harmful rules are usually just removable and our cut is optimal.
  When the optimal fix genuinely needs rewording, we DIAGNOSE the culprit but cannot fix it -- you or an
  optimizer must reword.
- **Aggregate attribution can hide heterogeneity**: a rule that helps one input type and hurts another
  nets to ~0 and would read "dead". The honest mitigation is per-segment attribution, not just aggregate.
- **The noise floor will mark a small real effect not-significant** -- by design it refuses to cry wolf,
  so it can miss a small-but-real harmful rule. Raise K to tighten.

## Which rule matters depends entirely on what you measure
The same rule "output only JSON" was DEAD under a lenient check (valid JSON anywhere) and the #1
LOAD-BEARING rule under a strict one (JSON-first). Confirmed across 2 models x 2 tasks (4/4 cells).
You cannot answer "which rule matters" without first stating what you optimize for. (M19b / M20)

## Harm is model-specific -- no general prompt advice catches it
"Be warm and greet the user" cost **-33%** of JSON-first success on Gemini and **0%** on Codex. A blog
rule ("always be polite to your LLM") would have you ship the bug on one model and waste effort on the
other. The only way to know is to measure your own stack. (M20)

## Where it found real structure on real, sealed data
On a sealed code-review benchmark (AST-injected bugs, ground truth committed before any run), zero-LLM
replay: one lens carried almost all recall, two only corroborated it (leave-one-out masked them,
Shapley revealed them), and four were provably dead weight -- a bankable "drop 4-6 of 7" cut. (M17)

## What we MEASURED and KILLED (the honest part)
- **Provenance attribution by the model's self-report FAILED.** Asking the model "which finding does
  this rest on" and attributing its self-tagged data-share did NOT generalize: on 4 held-out decisions
  it was 0/4 -- the decisive finding never scored significant and usually inverted. So pieceofmind
  ships on OBJECTIVE oracles only; the provenance adapter is documented as measured-and-found-wanting,
  not a headline. (M16)
- **It does NOT manufacture importance.** On a crypto return-predictor, every feature group attributed
  to ~0 because the model had no out-of-sample edge above a coin flip (independently confirmed by a
  second model family). When nothing is load-bearing, pieceofmind says so. (M18)

## Honest scope & limits
- **Needs an objective correctness oracle** (schema / labels / eval). No measurable success -> nothing
  to attribute. This is the precondition.
- **Beats the NAIVE baseline (single-step LOO); the algorithm itself is not novel** -- Shapley-for-LLM
  exists (llmSHAP, TokenSHAP). Our distinct slice: rule-level attribution against a correctness oracle,
  the noise floor, the find->fix->verified-lift loop, and zero-dependency clone-and-run -- not the math.
- **Not a generative optimizer** (DSPy/TextGrad rewrite the whole prompt; we do surgical, interpretable
  cut/keep). Different tool, different audience (you keep control).
- Single-task/single-model results are clean reads, not proofs; magnitudes ($ figures) use illustrative
  volume/cost knobs. Treat results as your-stack-specific until you run it on yours.

Reproduce the headline offline: `python examples/correctness_debugger.py` (deterministic, <1s, no API).
The same loops on a real model: `data/measurements/m21_correctness_debugger.py`, `m22a_*.py`.
