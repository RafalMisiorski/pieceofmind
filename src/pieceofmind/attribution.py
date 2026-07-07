"""pieceofmind.attribution -- measured input attribution via averaged ablation + exact Shapley.

You supply a value function ``v(subset_of_inputs) -> float`` (a possibly-NOISY score, e.g. an LLM
call). This module averages it over K reruns to beat the per-call noise, then attributes the total
to each input two ways:

  attribute_loo     -- leave-one-out: cheap ((n+1)*K calls), but UNDER-counts redundant inputs (two
                       inputs that cover for each other each look unimportant; LOO can even go NEGATIVE).
  attribute_shapley -- exact Shapley over all 2^n coalitions (2^n*K calls): splits credit fairly among
                       redundant inputs and satisfies the efficiency axiom (sum of credits = the whole).

The value function is the ONLY seam -- bring your own LLM. Pure stdlib, zero dependencies. Output is
ASCII-only.
"""

from __future__ import annotations

import itertools
import statistics
from dataclasses import dataclass, field
from math import factorial
from typing import Callable, Optional, Sequence

# v(subset_of_inputs) -> float. One (noisy) draw; the kernel averages it K times.
ValueFn = Callable[[Sequence], float]


def _stats(xs: list) -> dict:
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0, "mean": None, "std": None, "se": None}
    m = statistics.mean(xs)
    sd = statistics.pstdev(xs) if len(xs) > 1 else 0.0
    return {"n": len(xs), "mean": m, "std": sd, "se": sd / (len(xs) ** 0.5)}


def _avg(value_fn: ValueFn, subset: Sequence, k: int) -> dict:
    """Average the value function over K reruns (the noise floor: a single draw is unreliable)."""
    return _stats([value_fn(subset) for _ in range(k)])


# ---------------------------------------------------------------------------
# Leave-one-out
# ---------------------------------------------------------------------------


@dataclass
class Attribution:
    id: str
    attr: float          # v(full) - v(full without this input), averaged
    se: float            # combined standard error of the two averaged estimates
    significant: bool    # |attr| > 2*se -- above the noise floor


@dataclass
class AttributionReport:
    method: str
    baseline_mean: float
    baseline_se: float
    k: int
    per_input: list  # list[Attribution]

    def significant(self) -> list:
        return [a for a in self.per_input if a.significant]

    def to_dict(self) -> dict:
        return {"method": self.method, "baseline_mean": self.baseline_mean,
                "baseline_se": self.baseline_se, "k": self.k,
                "per_input": [vars(a) for a in self.per_input]}


def attribute_loo(inputs: Sequence, value_fn: ValueFn, *, k: int = 8,
                  ids: Optional[list] = None) -> AttributionReport:
    """Leave-one-out attribution: how much each input changes the K-averaged value when removed.

    Cheap ((n+1)*K calls) but masks redundancy. A |attr| <= 2*se result is below the noise floor --
    raise K or treat as not-load-bearing. Negative attr means removing the input RAISED the score
    (usually noise; with strong redundancy LOO can genuinely go negative -- that's the signal to use
    attribute_shapley instead)."""
    inputs = list(inputs)
    n = len(inputs)
    ids = ids or [f"x{i + 1}" for i in range(n)]
    full = _avg(value_fn, inputs, k)
    per = []
    for i in range(n):
        without = _avg(value_fn, [x for j, x in enumerate(inputs) if j != i], k)
        attr = full["mean"] - without["mean"]
        se = (full["se"] ** 2 + without["se"] ** 2) ** 0.5
        per.append(Attribution(ids[i], round(attr, 4), round(se, 4), abs(attr) > 2 * se))
    per.sort(key=lambda a: -a.attr)
    return AttributionReport("leave-one-out", round(full["mean"], 4), round(full["se"], 4), k, per)


# ---------------------------------------------------------------------------
# Exact Shapley
# ---------------------------------------------------------------------------


def _shapley_weight(s: int, n: int) -> float:
    """Weight of a coalition of size s when adding a player: s!(n-s-1)!/n!."""
    return factorial(s) * factorial(n - s - 1) / factorial(n)


def shapley_from_values(values: dict, n: int) -> list:
    """Exact Shapley values from a full coalition->value map (keys = frozenset of input indices).

    Shapley_i = sum over S subset of N\\{i} of weight(|S|) * (v(S u {i}) - v(S)). Splits credit for
    redundant players (where leave-one-out gives each 0 because the other covers). By the efficiency
    axiom, sum(Shapley) == v(full) - v(empty)."""
    sh = [0.0] * n
    for i in range(n):
        others = [j for j in range(n) if j != i]
        for r in range(len(others) + 1):
            for combo in itertools.combinations(others, r):
                S = frozenset(combo)
                sh[i] += _shapley_weight(len(combo), n) * (values[S | {i}] - values[S])
    return [round(x, 4) for x in sh]


@dataclass
class ShapleyReport:
    v_full: float
    v_empty: float
    k: int
    per_input: list   # list[dict]: {id, shapley, loo}
    efficiency_sum: float  # sum(shapley) -- should equal v_full - v_empty (the receipt)

    def efficiency_ok(self, tol: float = 0.01) -> bool:
        return abs(self.efficiency_sum - (self.v_full - self.v_empty)) <= tol

    def to_dict(self) -> dict:
        return {"v_full": self.v_full, "v_empty": self.v_empty, "k": self.k,
                "per_input": self.per_input, "efficiency_sum": self.efficiency_sum,
                "v_full_minus_empty": round(self.v_full - self.v_empty, 4),
                "efficiency_ok": self.efficiency_ok()}


def attribute_shapley(inputs: Sequence, value_fn: ValueFn, *, k: int = 4,
                      ids: Optional[list] = None, empty_value: float = 0.0) -> ShapleyReport:
    """Exact Shapley attribution over all 2^n coalitions, each K-averaged, WITH a noise floor.

    Cost is 2^n*K value-function calls -- exact and affordable for small n (<=~12); for larger n use
    sampled/permutation Shapley (not yet shipped). ``empty_value`` is v({}) (default 0.0: with no
    inputs there is nothing to attribute).

    Same significance discipline as attribute_loo: each per-input Shapley value carries an SE
    propagated from the K-rerun SEs of every coalition it touches
    (Var(phi_i) = sum_S w(|S|)^2 * (se(S+i)^2 + se(S)^2), coalitions treated as independent
    estimates), and ``significant`` is |shapley| > 2*se. With a deterministic value_fn (or k=1)
    all SEs are 0 and any nonzero attribution is significant; for noisy value functions use k>=4."""
    inputs = list(inputs)
    n = len(inputs)
    ids = ids or [f"x{i + 1}" for i in range(n)]
    values: dict = {}
    ses: dict = {}
    for r in range(n + 1):
        for combo in itertools.combinations(range(n), r):
            S = frozenset(combo)
            if not combo:
                values[S], ses[S] = empty_value, 0.0   # v({}) is a constant, not an estimate
                continue
            st = _avg(value_fn, [inputs[i] for i in combo], k)
            values[S], ses[S] = st["mean"], (st["se"] or 0.0)
    sh = shapley_from_values(values, n)
    full = frozenset(range(n))
    per = []
    for i in range(n):
        var_i = 0.0
        for r in range(n):
            for combo in itertools.combinations([j for j in range(n) if j != i], r):
                S = frozenset(combo)
                w = _shapley_weight(len(combo), n)
                var_i += (w ** 2) * (ses[S | {i}] ** 2 + ses[S] ** 2)
        se_i = var_i ** 0.5
        loo_i = values[full] - values[full - {i}]
        loo_se_i = (ses[full] ** 2 + ses[full - {i}] ** 2) ** 0.5
        per.append({"id": ids[i], "shapley": sh[i], "se": round(se_i, 4),
                    "significant": abs(sh[i]) > 2 * se_i,
                    "loo": round(loo_i, 4), "loo_se": round(loo_se_i, 4),
                    "shapley_minus_loo": round(sh[i] - loo_i, 4)})
    per.sort(key=lambda p: -p["shapley"])
    return ShapleyReport(round(values[full], 4), round(values[frozenset()], 4), k, per, round(sum(sh), 4))


# ---------------------------------------------------------------------------
# Render (ASCII markdown)
# ---------------------------------------------------------------------------


def render_loo(r: AttributionReport) -> str:
    L = [f"# Leave-one-out attribution (baseline {r.baseline_mean} +/- {r.baseline_se}, K={r.k})", "",
         "| input | attribution | significant | reading |", "|---|---|---|---|"]
    for a in r.per_input:
        reading = ("LOAD-BEARING" if (a.significant and a.attr > 0)
                   else "removing it RAISES the score (noise/redundancy)" if a.attr < 0
                   else "not load-bearing (below noise floor)")
        L.append(f"| {a.id} | {a.attr} +/- {a.se} | {'YES' if a.significant else 'no'} | {reading} |")
    L.append("")
    L.append("NOTE: significance is |attr| > 2*SE over K reruns. Negative or sub-noise attributions are "
             "the signature of redundancy/noise -- use attribute_shapley for the redundancy-correct number.")
    return "\n".join(L)


def render_shapley(r: ShapleyReport) -> str:
    L = [f"# Exact Shapley attribution (K={r.k})", "",
         f"- v(full)={r.v_full}  v(empty)={r.v_empty}  -> total to attribute = {round(r.v_full - r.v_empty, 4)}",
         f"- efficiency check: sum(Shapley)={r.efficiency_sum} {'==' if r.efficiency_ok() else '!='} "
         f"v(full)-v(empty)={round(r.v_full - r.v_empty, 4)}  (the receipt)", "",
         "| input | Shapley | LOO | Shapley-LOO | reading |", "|---|---|---|---|---|"]
    for p in r.per_input:
        sig = p.get("significant", abs(p["shapley"]) > 0)
        if not sig:
            reading = "below the noise floor (|Shapley| <= 2*SE) -- dead weight at this K"
        elif p["shapley"] < 0:
            reading = "HARMFUL -- lowers the metric (e.g. a misleading input)"
        elif abs(p["loo"]) <= 2 * p.get("loo_se", 0.0):
            reading = "load-bearing -- LOO MISSED it (redundancy/noise)"
        else:
            reading = "load-bearing"
        se_txt = f" +/- {p['se']}" if p.get("se") is not None else ""
        L.append(f"| {p['id']} | {p['shapley']}{se_txt} | {p['loo']} | {p['shapley_minus_loo']} | {reading} |")
    L.append("")
    L.append("NOTE: EXACT Shapley over all 2^n coalitions; splits credit among redundant inputs that "
             "leave-one-out zeroes (or makes negative). Significance is |Shapley| > 2*SE, with SE "
             "propagated from the K-rerun SEs of every coalition (same noise-floor discipline as LOO). "
             "Cost ~ 2^n*K value-fn calls.")
    return "\n".join(L)
