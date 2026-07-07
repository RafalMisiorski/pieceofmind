# M22a -- pieceofmind (Shapley) vs naive 1-step LOO on REDUNDANTLY-harmful rules

**pieceofmind WINS the discriminator: Shapley-fix record-correctness 1.000 > naive-LOO-fix 0.833. naive LOO masked the redundant harmful pair (cut ['infer']); Shapley caught it (cut ['fill_all', 'infer']).**

## Considered read (the win is real; here is exactly what it is and isn't)
On a CLEAN channel (Codex; the first Gemini run was timeout-contaminated and discarded), the
redundant-harm structure EMERGED EMPIRICALLY -- it was not forced. `fill_all` and `infer` partially
cover for each other, so naive 1-step leave-one-out scored `fill_all` at exactly 0.0 (MASKED) and only
flagged `infer` (-0.111). Exact Shapley split the blame and flagged BOTH (`fill_all` -0.069, `infer`
-0.171). Consequence on the FIX: naive LOO cut only `infer` and stayed stuck at 0.833 record-correctness
(`fill_all` kept hallucinating); pieceofmind cut both and reached 1.000. **+16.7 pts of correctness
that the dumbest baseline leaves on the table** -- and the efficiency receipt holds (sum(Shapley)=0.1111
= v(full)-v(empty)).

PRE-REGISTERED VERDICT: **VALIDATED vs naive LOO** -- pieceofmind's edge (Shapley over single-step
ablation) is real on interacting/redundant harmful rules, on a real model, with the masking emerging
from the model's behavior rather than planted.

Honest caveats: (1) the masking was PARTIAL (LOO did catch `infer`; only `fill_all` was masked) -- a
real, not textbook-perfect, redundancy. (2) Single model (Codex), 6 docs, K=1 -- clean read, not
multi-task proof; the +16.7 magnitude is test-design-dependent. (3) This beats only the NAIVE baseline;
the harder contestants (llmSHAP/TokenSHAP Shapley, DSPy optimizer) are M22b -- and llmSHAP/TokenSHAP
also do Shapley, so they could TIE us on the attribution (our remaining edge there would be the
noise-floor + the find->fix->$ loop + zero-dep packaging, not the algorithm).

The test that can refute us: two completeness rules (fill_all, infer) that each independently
make the model hallucinate nullable fields. If the harm is redundant, naive 1-step LOO masks
BOTH (each ~0) and fixes nothing; exact Shapley splits the blame and cuts both. Real model:
codex (retry-on-empty). Oracle: exact value match vs ground truth, null-aware. Total LLM calls = 96.

Full prompt: field-correctness=0.833, record-correctness=0.500.

# Exact Shapley attribution (K=1)

- v(full)=0.8333  v(empty)=0.7222  -> total to attribute = 0.1111
- efficiency check: sum(Shapley)=0.1111 == v(full)-v(empty)=0.1111  (the receipt)

| input | Shapley | LOO | Shapley-LOO | reading |
|---|---|---|---|---|
| schema | 0.3657 | 0.3333 | 0.0324 | load-bearing |
| amount_fmt | -0.0139 | 0.0 | -0.0139 | not load-bearing |
| fill_all | -0.0694 | 0.0 | -0.0694 | HARMFUL -- lowers the metric (e.g. a misleading input) |
| infer | -0.1713 | -0.1111 | -0.0602 | HARMFUL -- lowers the metric (e.g. a misleading input) |

NOTE: EXACT Shapley over all 2^n coalitions; splits credit among redundant inputs that leave-one-out zeroes (or makes negative). Cost ~ 2^n*K value-fn calls.

## The head-to-head fix
- naive 1-step LOO would cut ['infer'] -> kept ['schema', 'fill_all', 'amount_fmt'] -> record-correctness 0.833
- pieceofmind Shapley cuts ['fill_all', 'infer'] -> kept ['schema', 'amount_fmt'] -> record-correctness 1.000
- per-rule (Shapley | LOO): schema=0.3657|0.3333, fill_all=-0.0694|0.0, infer=-0.1713|-0.1111, amount_fmt=-0.0139|0.0

Read: if fill_all and infer both show NEGATIVE Shapley but ~0 LOO, that is the masking naive
LOO cannot see -- and cutting both (Shapley's call) recovers correctness that cutting per-LOO
does not. If instead LOO already flags them, the harm was not redundant and we concede.