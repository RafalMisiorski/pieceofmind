"""python -m pieceofmind --demo : reproduce the headline OFFLINE (no API key, <1s).

The demo uses a DETERMINISTIC stub value function so the redundancy result is visible with zero LLM
calls: F1 and F2 are a redundant decisive pair (either one grounds the decision), F3 is an
independent minor contributor, F4/F5 are inert. Leave-one-out masks the redundant pair (each looks
unimportant because the other covers); exact Shapley reveals it and the credits sum to the whole.
"""

from __future__ import annotations

import argparse

from pieceofmind.attribution import attribute_loo, attribute_shapley, render_loo, render_shapley

_DEMO_FINDINGS = [
    "F1 Regulatory: needs an 18-month license and EUR 2M we do not have.",
    "F2 Top 3 incumbents hold 85 percent share under 10-year contracts.",
    "F3 Our founders each have a prior exit in an adjacent vertical.",
    "F4 The market grew last year.",
    "F5 One pilot contact said 'interesting' but signed nothing.",
]


def _stub_value_fn(subset) -> float:
    """Deterministic: F1||F2 redundant decisive pair (+0.30 if either present), F3 independent
    (+0.05), F4/F5 inert. No LLM -- shows the attribution math offline."""
    def has(tag: str) -> bool:
        return any(str(f).startswith(tag + " ") for f in subset)
    v = 0.0
    if has("F1") or has("F2"):
        v += 0.30
    if has("F3"):
        v += 0.05
    return v


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="pieceofmind")
    p.add_argument("--demo", action="store_true", help="run the offline deterministic demo (no API)")
    p.add_argument("-k", "--reps", type=int, default=4)
    args = p.parse_args(argv)
    if not args.demo:
        p.error("v0.1 CLI ships only --demo (offline). Use the library API for real runs; see README.")
        return 2

    ids = [f"F{i + 1}" for i in range(len(_DEMO_FINDINGS))]
    loo = attribute_loo(_DEMO_FINDINGS, _stub_value_fn, k=args.reps, ids=ids)
    sh = attribute_shapley(_DEMO_FINDINGS, _stub_value_fn, k=args.reps, ids=ids)
    print(render_loo(loo))
    print()
    print(render_shapley(sh))
    print()
    print("READING: leave-one-out gives F1 and F2 ~0 (each masked by the other -- redundancy); exact "
          "Shapley reveals F1=F2=0.15 (split fairly), F3=0.05, F4/F5 inert; sum(Shapley)=v(full). The "
          "redundancy fix, reproduced offline with a deterministic value function. On a REAL LLM the "
          "value function is noisy -- that is what K-fold averaging is for; see BENCHMARK.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
