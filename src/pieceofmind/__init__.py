"""pieceofmind -- measured input attribution for LLM decisions.

Don't trust the model's footnotes. Measure which evidence a recommendation actually rests on -- via
K-fold averaged ablation (to beat the noise floor) + exact Shapley (to split credit fairly among
redundant inputs). Zero dependencies; you bring the LLM call (the value function is the only seam).

    from pieceofmind import attribute_loo, attribute_shapley, provenance_value_fn, build_synth_fn

See BENCHMARK.md for the honest cost/noise gate. `python -m pieceofmind --demo` reproduces the
headline offline (no API key).
"""

from pieceofmind import checkers
from pieceofmind.attribution import (
    Attribution,
    AttributionReport,
    ShapleyReport,
    ValueFn,
    attribute_loo,
    attribute_shapley,
    render_loo,
    render_shapley,
    shapley_from_values,
)
from pieceofmind.provenance import LLMCall, build_synth_fn, provenance_value_fn

__version__ = "0.1.0"

__all__ = [
    "attribute_loo", "attribute_shapley", "shapley_from_values",
    "AttributionReport", "ShapleyReport", "Attribution", "ValueFn",
    "render_loo", "render_shapley",
    "build_synth_fn", "provenance_value_fn", "LLMCall",
    "checkers",
]
