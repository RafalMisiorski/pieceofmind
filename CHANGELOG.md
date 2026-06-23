# Changelog

## 0.1.0 (unreleased)

First public release: an interpretable correctness-debugger for prompt rules / inputs.

- Generic attribution kernel: `attribute_loo` / `attribute_shapley` / `shapley_from_values` over any
  `value_fn(subset) -> float`, with a noise floor (K-fold averaging + `|attr| > 2*SE` gate) and an
  efficiency self-check (`sum(Shapley) = v(full) - v(empty)`).
- `pieceofmind.checkers`: label-free structural checkers (valid_json, has_keys, under_words,
  no_refusal, no_preamble, all_of) so you can run against your prompt with no labeled eval set.
- Provenance reference adapter (`build_synth_fn`, `provenance_value_fn`) -- documented as
  measured-and-found-wanting (see FINDINGS.md); prefer an objective oracle.
- Offline, no-API examples: `hello.py`, `correctness_debugger.py` (the flagship find->fix->lift->$
  loop), `known_limits.py`, plus `prompt_section_attribution.py`, `marketing_attribution.py`,
  `few_shot_attribution.py`, and `python -m pieceofmind --demo`.
- FINDINGS.md: the measured evidence ledger (including the honest nulls and the named limits).
- Zero runtime dependencies, MIT.
