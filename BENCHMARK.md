# BENCHMARK -- the costs and the noise, first

This file leads with the limitations on purpose. `pieceofmind` is honest about being noisy and
expensive, and tells you exactly when it is worth paying. Every number below was measured during
development on a real market-entry decision (5 findings, model = Claude Sonnet).

## 1. The value function is noisy -- a single reading is not trustworthy
The reference value function (the model's self-reported "data share" -- the fraction of load-bearing
claims it tags as grounded in a finding) is **noise-dominated**. Measured: the SAME input, re-run 5
times, gave data_share = `0.71, 0.71, 0.38, 0.71, 0.57` -- a **0.33 range**. Removing a whole finding
moved it ~`0.116`. So a single reading is ~**3x noisier** than the effect it is supposed to measure.

This is why `pieceofmind` averages over `K` reruns instead of caching one draw (the approach the
nearest comparator, llmSHAP, uses -- caching freezes the noise, it does not remove it).

## 2. Picking K (the noise floor)
To push the averaged noise below the ablation signal: `SE = noise / sqrt(K)`, so you need
`sqrt(K) > 0.33 / 0.116 ~ 2.85`, i.e. **K ~ 8**. After averaging at K=8, the decisive finding's effect
came out **1.72x** the noise floor while a filler control stayed within noise -- a real, separable
signal. Below that K the result is below the noise floor and `pieceofmind` will mark it not-significant
(by design).

## 3. The receipt: exact Shapley satisfies the efficiency axiom on real LLM data
On the real decision, at K=8, `sum(Shapley) = 0.5438` and `v(full) - v(empty) = 0.5437` -- the
attributions provably sum to the whole, to 4 decimals, on noisy real-model output. That self-check is
how you know the implementation is right, not just internally consistent.

## 4. The hook: leave-one-out LIES; Shapley does not
At K=8 on the same decision, naive leave-one-out gives **NEGATIVE** contributions to several findings
-- nonsense (removing a reason cannot make a decision *more* grounded except by noise) -- while exact
Shapley keeps every finding positive and well-ordered:

| finding | Shapley | leave-one-out |
|---|---|---|
| F1 (the decisive regulatory blocker) | **0.263** (dominant) | 0.164 |
| F3 | 0.083 | **-0.010** |
| F2 | 0.067 | **-0.080** |
| F4 | 0.067 | 0.024 |
| F5 | 0.064 | **-0.025** |

F2 is the sharpest case: leave-one-out says **-0.080** (it looks like F2 *hurts* the grounding),
Shapley says **+0.067**. F1 and F2 both support the same conclusion, so leave-one-out lets each cover
for the other and under-counts (here, drives negative) both. Use exact Shapley when inputs are
redundant.

## 5. The cost
- Leave-one-out: `(n+1) * K` value-function calls. (n=5, K=8 -> 48 calls.)
- Exact Shapley: `2^n * K` calls. (n=5, K=8 -> **248 calls** for one decision.)
Exact Shapley is affordable for small `n` (<= ~12). Sampled/permutation Shapley for larger `n` is
**not yet shipped** -- treat `n > ~12` as out of scope for now.

## 6. When it is worth it
**Worth it** when: (a) the decision is contested / high-stakes and you must defend *which* evidence
carried it; (b) the inputs are redundant (leave-one-out will under-count or go negative); (c) you
suspect provenance theatre (claims tagged "data" that the decision does not actually move on.
**NOT worth it** for a quick gut-check -- a single cheap pass is fine for that; you do not need this.

## 7. What this does NOT do (stated plainly)
During development the following were measured and did NOT hold -- `pieceofmind` makes none of these
claims:
- It does NOT catch sycophancy or "remove bias." A cross-family-judge approach ceilinged in testing
  (both model families scored identically -- no edge to measure).
- It does NOT make better decisions, and multi-agent / orchestration approaches showed no edge.
- The provenance value function rests on the model's OWN claim-tagging (data vs model); the reliability
  of that tagging is unmeasured. `pieceofmind` measures whether a tagged claim is *load-bearing*, not
  whether the tag is *correct*.
- Generalization is demonstrated on a small number of decisions; treat results as decision-specific
  until you have run it on your own.

## 8. Additive vs ratio metrics (use the right value function)
Exact Shapley DECOMPOSES an additive total: `sum(Shapley) = v(full) - v(empty)`. So the cleanest
value functions are ADDITIVE -- recall (distinct bugs found), sales, accuracy-count, total return.
RATIO metrics (precision = confirmed/flagged, win-rate, $-per-unit) are NOT additive, so attributing
them directly does not decompose cleanly (a real run on a code-review benchmark gave a lens
+0.22 under Shapley yet -0.08 under leave-one-out on precision). For a ratio metric: read
LEAVE-ONE-OUT for the harmful/helpful direction, or attribute the additive numerator and denominator
separately (e.g. confirmed-count and false-flag-count) and combine. Additive in, clean attribution
out.

## 9. Reproduce
`python -m pieceofmind --demo` reproduces the redundancy result (LOO masks, Shapley reveals, credits
sum to the whole) offline with a deterministic value function, in under a second, no API key.
