"""pieceofmind.provenance -- the reference value function for the headline use case:
how much an LLM RECOMMENDATION rests on its evidence (data-grounded) vs the model's prior (model).

The value is the model's self-reported "data share" -- the fraction of load-bearing claims it tags as
grounded in a provided finding rather than its own world-knowledge. A SINGLE reading is
noise-dominated (that is the whole point; see BENCHMARK.md) -- pieceofmind's K-fold ablation is what
turns it into a measured attribution.

This is a REFERENCE adapter. The attribution kernel works with ANY value_fn; provenance is one. You
inject the LLM call -- bring your own provider (Anthropic SDK, OpenAI SDK, a CLI subprocess, ...).
"""

from __future__ import annotations

import json
import re
from typing import Callable, Sequence

# (system_prompt, user_prompt) -> raw model text. You supply this.
LLMCall = Callable[[str, str], str]

_SYSTEM = (
    "You turn EVALUATION FINDINGS into a single corrective recommendation. For every load-bearing "
    "claim, tag provenance='data' (grounded in a specific provided finding -- cite which) or "
    "provenance='model' (your own reasoning / world-knowledge). Return ONLY a JSON object: "
    '{"recommendation": "<one sentence>", "claims": [{"claim": "<sentence>", '
    '"provenance": "data"|"model", "source": "<finding id or reasoning>"}]}'
)


def _build_prompt(findings: Sequence, situation: str, question: str) -> str:
    fb = "\n".join(f"  [F{i + 1}] {f}" for i, f in enumerate(findings))
    return (f"=== FINDINGS (cite these by Fn for 'data' provenance) ===\n{fb}\n\n"
            f"=== SITUATION ===\n{situation}\n\n=== QUESTION ===\n{question}\n\nReturn ONLY the JSON.")


def _parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    obj: dict = {}
    if m:
        try:
            obj = json.loads(m.group(0))
        except Exception:
            obj = {}
    claims = obj.get("claims") or []
    n = len([c for c in claims if isinstance(c, dict)])
    d = sum(1 for c in claims if isinstance(c, dict) and c.get("provenance") == "data")
    obj.setdefault("recommendation", "")
    obj.setdefault("claims", [])
    obj["_provenance_summary"] = {"n_claims": n, "data_grounded": d,
                                  "data_share": round(d / n, 4) if n else 0.0}
    return obj


def build_synth_fn(llm_call: LLMCall):
    """Build a ``synth_fn(findings, situation, question) -> dict`` from a (system, user) -> str call.

    Example wirings:
        # Anthropic SDK
        client = anthropic.Anthropic()
        def llm_call(system, user):
            return client.messages.create(model="claude-sonnet-4-6", max_tokens=1200,
                system=system, messages=[{"role": "user", "content": user}]).content[0].text
        synth_fn = build_synth_fn(llm_call)

        # OpenAI SDK
        def llm_call(system, user):
            return openai.OpenAI().chat.completions.create(model="gpt-4o",
                messages=[{"role":"system","content":system},{"role":"user","content":user}]
                ).choices[0].message.content
    """
    def synth_fn(findings, situation, question):
        return _parse(llm_call(_SYSTEM, _build_prompt(findings, situation, question)))
    return synth_fn


def provenance_value_fn(synth_fn, situation: str, question: str):
    """Wrap a synth_fn into a ``value_fn(subset_of_findings) -> data_share`` for the kernel.

        v = provenance_value_fn(synth_fn, situation, question)
        report = attribute_shapley(findings, v, k=4)   # how much each finding the rec rests on
    """
    def v(subset: Sequence) -> float:
        rec = synth_fn(list(subset), situation, question)
        return (rec.get("_provenance_summary") or {}).get("data_share") or 0.0
    return v
