# pieceofmind

**Find the prompt rule that's silently breaking your structured-output / agent correctness -- and fix
it, with the measured why.** *(Which **piece** of your prompt is load-bearing? **Peace of mind**, measured.)*

Your LLM feature produces wrong or unreliable output some % of the time. Your prompt has a dozen
instructions. Which one is the culprit -- and is a well-meaning rule secretly making it worse?
`pieceofmind` ablates each rule against **your** correctness metric, finds which rules are
**load-bearing**, **dead weight**, or **harmful** (a negative contribution), cuts the harmful ones,
and **verifies the lift**. Interpretable and surgical -- you keep control of your prompt (unlike a
black-box optimizer that rewrites it).

```
python examples/correctness_debugger.py     # the whole loop, offline, no API key, <1s
```
```
Your 4-rule extraction prompt: 50% of records are fully correct.
| rule      | attribution | reading      |
| schema    |  +0.58      | load-bearing |
| be_polite |   0.00      | dead weight  |
| fill_all  |  -0.21      | HARMFUL      |
FIX: cut ['fill_all'] -> record-correctness 50% -> 100% (+50 pts).
WHY: "always fill every field" makes the model HALLUCINATE values for fields that should be blank --
     valid JSON, wrong data. A JSON-validity check never catches it; a correctness oracle does.
```
That harmful rule sounds helpful, ships valid JSON, and silently corrupts half your records. No
validity check, no blog tip, and no whole-prompt optimizer tells you it's the one. pieceofmind does --
and on a real run cutting two such redundant rules beat naive "turn-it-off-and-check" by +16.7 pts
(see [BENCHMARK.md](BENCHMARK.md) / FINDINGS.md). Zero dependencies; bring your own LLM. **Read
BENCHMARK.md first** -- it leads with the costs, the noise, and what we measured and KILLED.

## Verify in 90 seconds (zero setup)

Zero dependencies, no API key -- every claim here runs offline in ~1 second on a clean clone.

```bash
python -m pytest -q                          # 12 tests pass
python examples/correctness_debugger.py      # reproduces: fill_all at -0.21 -> cut -> record-correctness 50% -> 100%
python examples/marketing_attribution.py     # exact Shapley splits two redundant channels $20k each; leave-one-out would cut both
python examples/known_limits.py              # where it FAILS (heterogeneity, cut-not-reword) -- measured, not hidden
```

Evidence ledger incl. the honest nulls (e.g. the provenance adapter that failed 0/4 on a held-out test):
[FINDINGS.md](FINDINGS.md). Costs, noise, and how to pick K: [BENCHMARK.md](BENCHMARK.md). The scripts +
raw outputs behind the headline numbers (−0.21/50→100, +16.7 vs LOO) are in
[measurements/](measurements/) — runnable against **your own model** via a one-line stdin/stdout seam.

## What it is (and is not)
- IT IS: a tiny, black-box, model-agnostic **correctness-debugger** for prompt rules / inputs, with a
  **noise floor** (it tells you when a result is below the measurement noise) and an **efficiency
  self-check** (the credits provably sum to the whole). It needs ONE thing from you: an objective
  correctness oracle (a schema, a labeled set, an eval). No oracle -> nothing to attribute.
- IT IS NOT: a generative prompt optimizer (it does surgical cut/keep, not a rewrite), a token/context
  attributor, a bias/sycophancy detector, or "make the model smarter". Those are other tools' jobs or
  did not survive our own measurement (see BENCHMARK.md -> "What this does NOT do").

## Quickstart
```
pip install pieceofmind          # zero dependencies
python examples/hello.py          # the 30-second hello: no LLM, no setup, <1s
python -m pieceofmind --demo      # the built-in offline demo
```
`hello.py` is the whole idea in 6 lines -- a 4-rule prompt scored by a toy function:
```
| input   | Shapley | reading      |
| concise |  0.4    | load-bearing |
| json    |  0.4    | load-bearing |
| polite  |  0.0    | dead weight (delete it) |
| emoji   | -0.5    | HARMFUL (delete it first) |
```
Swap that toy `score` for YOUR prompt's pass-rate, your model's accuracy, or your sales, and it works
the same. The built-in `--demo` shows the redundancy case (leave-one-out masks two redundant inputs
while exact Shapley reveals them and the credits sum to the whole).

### Run it on YOUR prompt (the standard case): which prompt sections actually matter?
```
python examples/prompt_section_attribution.py     # offline stub model, no API, <1s
```
Every bloated system prompt / CLAUDE.md / Cursor-rules file has instructions nobody has verified.
Split it into sections, give a few test inputs + a pass/fail checker, and `pieceofmind` tells you
which sections are load-bearing, which are **redundant** (cut one, save tokens), which are **dead
weight** (delete), and which are **harmful**. The demo's punchline: a 5-rule prompt scores **0%** --
not because it is bad, but because one cargo-culted rule ("end every reply with a smiley") silently
breaks the exact-match output. Delete that one rule and the first rule alone hits 50%, +the hint hits
100%. The 6-line **bring-your-own-LLM** block at the bottom of the file runs it on your real prompt
(use `attribute_loo` -- cost `(n+1)*K*|tests|` calls).

### See the value in 10 seconds (no ML, no API): marketing attribution
```
python examples/marketing_attribution.py     # offline, deterministic, < 1s
```
You run 5 marketing channels and get sales. The naive "turn it off and check" method (leave-one-out)
scores Facebook **and** the Influencer at **$0** -- because they reach the same customers, so turning
off one, the other covers. It would tell you to cut both, losing $40k. `pieceofmind`'s Shapley splits
the credit fairly ($20k each -- keep one), flags the Billboard as **dead money** ($0), and the Pop-up
ads as **harmful** (-$15k, annoying customers away). The credits sum to the whole (the efficiency
receipt). This is the classic real-world use of Shapley values -- here on plain sales, so anyone can
read it.

### Headline example: which few-shot examples carry your accuracy?
```
python examples/few_shot_attribution.py     # offline, deterministic stub model, no API
```
Attributes an 8-item sentiment task's accuracy to 5 candidate few-shot examples. The result tells the
whole story at once: two redundant helpful examples **split** the credit under Shapley (leave-one-out
mis-counts them), an off-topic example sits at **0**, and a **mislabelled** example gets a
**negative** Shapley value -- a real "this example is hurting your accuracy" signal. The credits sum
to `v(full) - baseline` (the efficiency receipt). This is the strongest use because the value function
is OBJECTIVE (accuracy), so the attribution measures a real property of the prompt.

### The generic kernel (any metric)
```python
from pieceofmind import attribute_loo, attribute_shapley

# value_fn(subset_of_inputs) -> float : any metric (accuracy, a score, ...). pieceofmind averages it.
report = attribute_loo(inputs, value_fn, k=8)       # cheap read; masks redundancy
report = attribute_shapley(inputs, value_fn, k=4)   # rigorous; redundancy-correct, sums to the whole
print(report.to_dict())
```

### Reference adapter: provenance (with an honest caveat)
A value function for "how much does a recommendation rest on each finding (data-grounded vs
model-prior)?" -- the model's self-reported data-share:
```python
from pieceofmind import build_synth_fn, provenance_value_fn, attribute_shapley
synth_fn = build_synth_fn(my_llm_call)               # (system, user) -> str; SDK snippets in the docstring
v = provenance_value_fn(synth_fn, situation="...", question="...")
print(attribute_shapley(findings, v, k=8).to_dict())
```
**Caveat (measured, not hidden -- this is the honest part):** the data-share value function is a
model SELF-REPORT, and on a pre-registered held-out test (4 diverse decisions, each with a planted
clearly-decisive finding) it **FAILED 0/4** -- the decisive finding was never flagged significant and
usually got a *negative* attribution (removing the decisive finding *raises* data-share, because the
model then leans on the remaining findings). So the provenance adapter does NOT reliably tell you
which finding a decision rests on outside a hand-seeded case. **Prefer an OBJECTIVE value function**
(accuracy, sales, a score -- like the two examples above), where the attribution measures a real
property and negative values are meaningful. The provenance adapter ships as a documented reference
that we measured and found wanting -- not a guarantee. See BENCHMARK.md.

## How it works
- **Value function = the only seam.** You supply a (noisy) `v(subset) -> float`. `pieceofmind` owns the
  averaging, the standard error, the `|attr| > 2*SE` significance gate, the exact Shapley, the
  efficiency check, and the rendering. (This mirrors `sealeval`'s `judge_fn` design.)
- **Two methods.** Leave-one-out is cheap (`(n+1)*K` calls) but UNDER-counts redundant inputs -- two
  inputs that cover for each other each look unimportant, and LOO can even go **negative**. Exact
  Shapley (`2^n*K` calls) evaluates every coalition, so it splits redundant credit fairly and satisfies
  the efficiency axiom (`sum(Shapley) = v(full) - v(empty)`).
- **Noise floor.** A single value-function draw is unreliable; `pieceofmind` averages `K` times and
  reports significance against the standard error. See BENCHMARK.md for how to pick `K`.

## Known limits (we went looking -- `python examples/known_limits.py`)
- **Aggregate attribution hides heterogeneity.** A rule that helps one input segment and hurts another
  nets to ~0 and reads "dead weight" -- cutting it then silently destroys the segment it was helping.
  Mitigation: attribute PER SEGMENT, not just in aggregate.
- **It can cut/keep, never reword.** When a rule is right for some inputs and wrong for others, the
  optimum is "apply it only where it helps" (a reword reaching 100%); cut/keep is stuck at the 50/50
  trade-off. pieceofmind points at the rule; you or an optimizer must reword it. (In practice this
  bites rarely on strong models -- they handle the good cases without the rule, so harmful rules are
  usually just removable; see FINDINGS.md / M23.)
- **The noise floor can miss a small real effect** -- by design it won't cry wolf below `2*SE`. Raise K.

## vs the field (honest)
- **llmSHAP** (the one truly adjacent OSS): same exact-Shapley backbone, but it handles LLM
  stochasticity by **caching one draw** and treating it as deterministic. Caching *freezes* the noise;
  it does not remove it. `pieceofmind` K-fold averages to push noise below the signal.
- **ContextCite / AttriBoT**: attribute to input *spans*, with no data-vs-model framing.
- **LEA**: does the data-vs-model split, but is *white-box* (needs model hidden states) -- not a
  drop-in over an arbitrary API/CLI.
- **SHAP / Captum**: feature/tensor level, not LLM-evidence-aware.
- **promptfoo / ragas / LangSmith**: LLM-as-judge over datasets -- they report what the model *says*
  about its grounding; they do not *ablate* to measure it.

The algorithm is ~150 lines of stdlib and reimplementable in a weekend. The contribution is the
**discipline**: the measured noise floor + the published efficiency check + the honest scope.

## License
MIT (c) 2026 Rafal Misiorski. Sibling project: `sealeval` (sealed-ground-truth eval).
