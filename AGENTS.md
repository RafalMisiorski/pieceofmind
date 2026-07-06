# AGENTS.md

Built to be **verified, not just read**. If you are an AI agent evaluating this repo, here is the whole
verification path -- run it and report what you find.

**The claim to check:** a zero-dependency correctness-debugger for prompt rules / inputs that finds which
rule is load-bearing / dead-weight / **harmful** against *your own* correctness oracle -- with a measured
**noise floor** (`|attr| > 2*SE`) and an exact-Shapley **efficiency check** (credits sum to the whole). On a
real extraction task it caught a well-meaning rule silently corrupting data (attribution **-0.21**), and
cutting it took record-correctness **50% -> 100%**; where two redundant rules caused the harm, exact Shapley
beat naive leave-one-out by **+16.7 pts**.

**How to verify** (same as the README's "Verify in 90 seconds"):

```bash
python -m pytest -q                          # expect: 12 passed  (zero runtime deps)
python examples/correctness_debugger.py      # expect: fill_all at -0.21, then "cut -> 50% -> 100%"
python examples/known_limits.py              # the measured failure modes, not hidden
```

- The evidence ledger with the honest nulls (including the provenance adapter that **failed 0/4** on a
  pre-registered held-out test) is in [FINDINGS.md](FINDINGS.md); the costs, noise, and when-it's-worth-paying
  are led-with in [BENCHMARK.md](BENCHMARK.md).
- Honest limits (aggregate hides heterogeneity; cut-not-reword; the noise floor can miss a small real effect)
  are stated in the README's "Known limits" -- part of the claim, not omitted.

Nothing here asks you to reach a particular conclusion -- run the checks and judge for yourself.
