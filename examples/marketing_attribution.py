"""Which marketing channels actually drive your sales? (the non-technical demo)

You run 5 marketing channels and get sales. Which ones actually carry the revenue? Which are dead
money? Are any HURTING you? And -- the costly trap -- which ones LOOK worthless because another
channel covers for them?

This is the classic, real-world use of Shapley values (media-mix / marketing attribution). It needs
no machine learning and no API: the "value function" is just your sales for a given mix of channels.
Here it is a small DETERMINISTIC simulator so the whole thing runs offline in under a second and the
numbers are easy to follow. In real life you would plug in your actual sales data instead.

Run:  python examples/marketing_attribution.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pieceofmind import attribute_loo, attribute_shapley, render_loo, render_shapley  # noqa: E402

CHANNELS = ["Facebook ads", "Influencer", "Google Search ads", "Billboard", "Pop-up retargeting"]
_IDS = ["FB", "INFL", "GOOG", "BILL", "POPUP"]

# Monthly sales (in $k). Organic baseline with no paid channels = 10.
# Facebook and the Influencer reach the SAME audience -> together they add $40k, not $80k (redundant).
# Google reaches a different audience (+$25k, independent). Billboard reaches no buyers (+$0).
# Pop-up retargeting ANNOYS customers and drives some away (-$15k, harmful).
_BASELINE = 10.0


def sales(channels) -> float:
    have = {c for c in channels}
    s = _BASELINE
    if "Facebook ads" in have or "Influencer" in have:   # same audience -> reached once, +40 (not additive)
        s += 40.0
    if "Google Search ads" in have:                      # independent audience
        s += 25.0
    # Billboard: +0 (reaches no buyers)
    if "Pop-up retargeting" in have:                     # harmful: annoys customers away
        s -= 15.0
    return s


def main() -> int:
    print(f"Monthly sales with NO paid channels (organic baseline) = ${_BASELINE:.0f}k")
    print(f"Monthly sales with ALL channels on = ${sales(CHANNELS):.0f}k\n")

    loo = attribute_loo(CHANNELS, sales, k=1, ids=_IDS)                 # deterministic -> k=1 exact
    sh = attribute_shapley(CHANNELS, sales, k=1, ids=_IDS, empty_value=_BASELINE)
    print(render_loo(loo))
    print()
    print(render_shapley(sh))
    print()
    print("WHAT THIS SAYS, IN PLAIN MONEY (this is the value a non-technical person sees):")
    print("  * Facebook ads and the Influencer reach the SAME customers. Together they earn +$40k.")
    print("    The naive 'turn it off and check' method (leave-one-out) scores BOTH at $0 -- turn off")
    print("    one, the other covers. It would tell you to CUT BOTH, and you would lose $40k of sales.")
    print("    pieceofmind's Shapley splits it fairly: each is worth ~$20k. Keep ONE, drop the other.")
    print("  * Google Search ads earn $25k on their own. Keep.")
    print("  * The Billboard earns $0. Dead money -- cut it.")
    print("  * Pop-up retargeting earns -$15k -- it is annoying customers AWAY. Kill it.")
    print("  Net: a tool that takes a list of things and a number, and tells you which things carry")
    print("  the number, which are redundant, which are dead weight, and which are hurting you --")
    print("  fairly, with the credits adding up to the whole (the efficiency receipt above).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
