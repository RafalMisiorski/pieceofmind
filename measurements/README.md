# measurements/ — the scripts behind FINDINGS.md's headline numbers

The two numbers the README leads with were, until now, "on our word". This directory makes them
reproducible with **your own model**:

| headline | script | recorded run |
|---|---|---|
| harmful rule at **−0.21** → cut → record-correctness **50% → 100%** | `m21_correctness_debugger.py` | [`recorded/M21_result.md`](recorded/M21_result.md) + [`recorded/m21.log`](recorded/m21.log) |
| exact Shapley beats naive 1-step LOO by **+16.7 pts** on redundantly-harmful rules | `m22a_interacting_rules.py` | [`recorded/M22a_result.md`](recorded/M22a_result.md) + [`recorded/m22a.log`](recorded/m22a.log) |

## Run them yourself

```bash
# 1) point the seam at ANY model: a command that reads the prompt on stdin, prints the reply
export PIECEOFMIND_LLM_CMD="python my_model.py"     # 5-line SDK example in llm_seam.py

# 2) run
python measurements/m21_correctness_debugger.py     # find -> why -> surgical cut -> verified lift
python measurements/m22a_interacting_rules.py       # Shapley-vs-LOO head-to-head on redundant harm
```

Each writes `M2xa_result.local.md` next to the script with your numbers.

## Honesty notes (read before comparing your numbers to ours)

- **Model-dependence is the point.** The recorded runs used Gemini (M21) and Codex (M22a) via the
  author's CLIs. A different/stronger model may not exhibit the harm at all (M23 in FINDINGS.md:
  strong models often survive harmful rules) — in that case the scripts print an **honest null**,
  not a manufactured win. Both null paths are exercised in CI-adjacent smoke (a constant stub model
  correctly yields "NO net-harmful rule" / "NO EDGE").
- The `recorded/` files are the verbatim outputs of the original runs — including prompts-under-test,
  per-rule attributions, and the LLM call counts.
- `m22a` evaluates `v(empty)` with the value function (now a first-class library option:
  `attribute_shapley(..., empty_value=None)`), so the efficiency receipt is computed against the
  real baseline, not an assumed 0.0.
