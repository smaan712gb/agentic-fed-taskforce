"""
nowcast.py -- The freshness layer for the Agentic Fed Task Force.

The keystone claim of this project is that the Fed decides on stale data:
official inflation and employment prints arrive with a lag and are later
revised. A real-time nowcast fuses faster signals into a current estimate.

This module provides three things:
  1. An ILLUSTRATIVE economy generator (the unobservable "truth").
  2. An OFFICIAL view: what the Fed effectively sees on a given date, i.e. a
     lagged and revision-noised reading of the truth.
  3. A NOWCAST view: a current-dated estimate with its own (different) noise,
     plus an explicit uncertainty band.

IMPORTANT, READ THIS:
The data here is synthetic and clearly labeled as such. Its ONLY purpose is to
exercise the pipeline end to end and prove the methodology is sound. It does
NOT prove the empirical claim that fresh data beats stale data in the real
world. Proving that requires swapping the generator for real feeds (FRED for
official series, a real-time inflation source such as Truflation, card-spend
and job-posting series for labor). That swap is isolated to the two functions
marked `# SWAP POINT` below; nothing else in the codebase changes.
"""

from __future__ import annotations
import random
import math
from dataclasses import dataclass


@dataclass
class Reading:
    """An observed macro reading with an honest uncertainty band."""
    inflation: float
    unemployment: float
    inflation_sigma: float   # 1-std uncertainty on the inflation estimate
    unemployment_sigma: float
    as_of_month: int         # index of the month this reading is dated to
    source: str              # "official (lagged)" or "nowcast (current)"


# ----------------------------------------------------------------------------
# 1. The unobservable truth. SWAP POINT: replace with real realized history.
# ----------------------------------------------------------------------------
def generate_true_economy(seed: int = 7, n_months: int = 96) -> dict:
    """
    Generate a plausible monthly path of true inflation, unemployment, and the
    prevailing policy rate. Persistent (autocorrelated) with occasional shocks,
    so it behaves like a real macro series rather than white noise.
    """
    rng = random.Random(seed)
    inflation = [2.2]
    unemployment = [4.0]
    policy_rate = [2.5]

    for t in range(1, n_months):
        # Inflation: sticky, mean-reverting to ~2.3, with rare supply shocks.
        shock = rng.gauss(0, 0.12)
        if rng.random() < 0.04:           # ~ one supply shock every 2 years
            shock += rng.choice([-1.0, 1.4])
        infl = 0.92 * inflation[-1] + 0.08 * 2.3 + shock
        inflation.append(round(infl, 3))

        # Unemployment: sticky, drifts with the cycle.
        u = 0.95 * unemployment[-1] + 0.05 * 4.2 + rng.gauss(0, 0.06)
        unemployment.append(round(max(2.5, u), 3))

        # Policy rate: a slow rule-of-thumb response (the prevailing rate the
        # Fed already knows exactly; it is NOT stale).
        target = max(0.0, 0.75 + infl + 0.5 * (infl - 2.0))
        pr = 0.85 * policy_rate[-1] + 0.15 * target
        policy_rate.append(round(pr, 3))

    return {
        "inflation": inflation,
        "unemployment": unemployment,
        "policy_rate": policy_rate,
        "n_months": n_months,
    }


# ----------------------------------------------------------------------------
# 2. The OFFICIAL view. SWAP POINT: replace with real released-and-revised data.
# ----------------------------------------------------------------------------
def official_view(truth: dict, as_of: int, lag: int = 2,
                  rev_sigma: float = 0.20, seed: int = 0) -> Reading:
    """
    What the Fed effectively sees on month `as_of`: the truth from `lag` months
    ago, blurred by revision noise. This is the stale picture.
    """
    rng = random.Random(seed * 1000 + as_of)
    idx = max(0, as_of - lag)
    return Reading(
        inflation=round(truth["inflation"][idx] + rng.gauss(0, rev_sigma), 3),
        unemployment=round(truth["unemployment"][idx] + rng.gauss(0, rev_sigma * 0.5), 3),
        inflation_sigma=rev_sigma,
        unemployment_sigma=rev_sigma * 0.5,
        as_of_month=idx,
        source="official (lagged)",
    )


# ----------------------------------------------------------------------------
# 3. The NOWCAST view. SWAP POINT: replace with fused real-time feeds.
# ----------------------------------------------------------------------------
def nowcast_view(truth: dict, as_of: int,
                 nowcast_sigma: float = 0.28, seed: int = 0) -> Reading:
    """
    A current-dated estimate of THIS month, built from faster signals. It has
    no lag but carries its own noise, and it reports that uncertainty honestly.
    The bet is that being current beats being precise-but-late.
    """
    rng = random.Random(seed * 2000 + as_of)
    idx = as_of
    return Reading(
        inflation=round(truth["inflation"][idx] + rng.gauss(0, nowcast_sigma), 3),
        unemployment=round(truth["unemployment"][idx] + rng.gauss(0, nowcast_sigma * 0.5), 3),
        inflation_sigma=nowcast_sigma,
        unemployment_sigma=nowcast_sigma * 0.5,
        as_of_month=idx,
        source="nowcast (current)",
    )


if __name__ == "__main__":
    truth = generate_true_economy()
    n = truth["n_months"]
    print("=== nowcast sanity check (ILLUSTRATIVE synthetic data) ===\n")
    print(f"{'month':>5} {'TRUE infl':>9} {'OFFICIAL':>9} {'NOWCAST':>9} "
          f"{'off lag':>7}")
    for m in range(n - 6, n):
        off = official_view(truth, m)
        now = nowcast_view(truth, m)
        print(f"{m:>5} {truth['inflation'][m]:>9.2f} {off.inflation:>9.2f} "
              f"{now.inflation:>9.2f} {m - off.as_of_month:>6}mo")

    # How far is each view from the truth, on average, over the back half?
    half = n // 2
    off_err = sum(abs(official_view(truth, m).inflation - truth["inflation"][m])
                  for m in range(half, n)) / (n - half)
    now_err = sum(abs(nowcast_view(truth, m).inflation - truth["inflation"][m])
                  for m in range(half, n)) / (n - half)
    print(f"\nMean absolute error vs TRUE current inflation:")
    print(f"  official (lagged): {off_err:.3f}")
    print(f"  nowcast (current): {now_err:.3f}")
    print("\nNote: the nowcast can be noisier per-reading yet still lead to "
          "better decisions, because it is not systematically late. The "
          "backtest tests exactly that.")
