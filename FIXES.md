# FIXES.md — prioritized work list (external code scan, 2026-07-07)

Findings verified empirically. This repo is in the best shape of the three (CI exists, 15/15
tests pass, `measurements/` ships the scripts behind the headline numbers).
**Out of scope for now: PyPI publication** — the owner will handle the release at the end.
Preparing metadata (`py.typed`, description fix) is in scope; uploading is not.

Already fixed, no action needed: `empty_value=None` measures v({}) (`68a932f`); the 2·SE
noise-floor gate replaced the ad-hoc −0.04/0.05 thresholds in the Shapley path (`6811ed7`);
`measurements/` with recorded runs exists (`7bded3b`).

## P1 — the remaining `empty_value` footgun

**`src/pieceofmind/attribution.py:139-140` — the default is still `empty_value=0.0`.**
`empty_value=None` (measure v({})) works correctly now, but a caller who doesn't read the
docstring still gets silently wrong Shapley values for any metric with a non-zero baseline.
Verified repro: v(S) = 10 + |S| with two identical players → default gives 6.0 each,
`empty_value=None` gives the correct 1.0 each — and `efficiency_ok()` returns True either way,
so the error is invisible.

Recommended: flip the default to `None` (one extra `value_fn` evaluation per run — cheap relative
to 2^n coalitions) and keep `0.0` available as an explicit opt-in for callers who *know* their
baseline. If back-compat matters more, at minimum emit a `UserWarning` when `empty_value` is left
at the default and `v_full` suggests a non-zero baseline, and add a prominent README warning.
Either way: add a regression test for the chosen behavior.

## P2 — checker correctness + typing

1. **`src/pieceofmind/checkers.py` inconsistencies (all reproduced):**
   - `no_preamble` (lines ~64-67) rejects ```json-fenced output while `valid_json` tolerates
     fences — the two checkers disagree about the same reply. Make fence policy consistent.
   - `no_refusal` (lines ~55-59) false-positives on "I am sorry to hear that; here is the JSON".
     Anchor the patterns to refusal phrasing (e.g. "I'm sorry, (but) I can't/cannot") rather than
     bare "sorry".
   - line ~23: greedy `\{.*\}` can capture an invalid superstring when the text contains multiple
     braces even though a valid JSON object is present. Prefer scanning candidates with
     `json.JSONDecoder().raw_decode` over positions of `{`.
   - Add tests for each of the three cases above.

2. **Typing polish:** parametrize `per_input: list` (attribution.py ~61, ~125) and
   `values: dict`; add `py.typed`; add `ruff` + `mypy` jobs to the existing
   `.github/workflows/ci.yml`.

## P3 — docs + scaling

3. **`pyproject.toml:7` — stale description** (old "provenance" framing instead of the
   correctness-debugger pitch). This becomes the PyPI page's first line — fix before the owner
   releases.

4. **BENCHMARK.md §3 wording:** the efficiency check is an algebraic identity of the algorithm —
   it always holds and is not "validation on real data". Reword so it isn't oversold (the file
   already half-admits this).

5. **Sampled/permutation Shapley for n > 12** with a confidence interval — real system prompts
   have 30+ rules and exact 2^n is out of reach. Larger feature; design first (separate
   `attribute_shapley_sampled`, reusing the SE/significance machinery).
