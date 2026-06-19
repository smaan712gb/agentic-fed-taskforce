"""
sensitivity.py -- do the conclusions survive the structural constants?

The objective hardcodes the parameters economists fight about: r* (neutral real
rate), u* (natural unemployment), the employment weight lambda, the Phillips
slope, and the Okun sensitivity. This script tests whether the backtest's
conclusions are robust to those choices, by re-scoring the committees' and the
Fed's ALREADY-CHOSEN paths under perturbed parameters. No model calls: it reuses
the decisions in a saved run, so it isolates the scoring assumptions.

Two conclusions are tested:
  C1  fresh committee is worse than stale (the pilot's honest headline)
  C2  the better committee beats the Fed's actual path (model-internal)

We report, over plausible ranges: one-at-a-time (OAT) behavior and a Monte-Carlo
fraction of the parameter space that preserves each conclusion. A conclusion that
flips across plausible parameters is fragile and must be reported as such.

Run:
    python sensitivity.py [runs/backtest_real-XXatcz.json]
"""

from __future__ import annotations

import sys
import glob
import json
import random
import datetime
from pathlib import Path

import objective as O

RUNS = Path(__file__).parent / "runs"
SEED = 7  # pre-registered

# Plausible ranges (baseline in parentheses).
RANGES = {
    "rstar": (0.25, 1.50),   # r* (0.75)
    "ustar": (3.80, 4.60),   # u* (4.2)
    "lam":   (0.50, 2.00),   # employment weight (1.0)
    "phil":  (0.15, 0.45),   # Phillips slope (0.30)
    "okun":  (0.30, 0.70),   # Okun sensitivity (0.50)
}
BASE = {"rstar": O.NEUTRAL_REAL_RATE, "ustar": O.NATURAL_UNEMPLOYMENT,
        "lam": O.EMPLOYMENT_WEIGHT, "phil": 0.30, "okun": 0.50}


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _latest_run(path: str | None):
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    # prefer the newest run that has per-run paths; favor a 3-arm (mean_fed) run.
    cand = sorted(glob.glob(str(RUNS / "backtest_real-*.json")), reverse=True)
    best = None
    for f in cand:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        if d.get("rows") and d["rows"][0].get("runs"):
            if "mean_fed" in d:
                return d
            best = best or d
    return best


def agg_losses(run: dict, rstar, ustar, lam, phil, okun):
    """Re-score every saved path under the given params; return (stale, fresh, fed)."""
    O.NEUTRAL_REAL_RATE, O.NATURAL_UNEMPLOYMENT, O.EMPLOYMENT_WEIGHT = rstar, ustar, lam
    s_means, f_means, fed = [], [], []
    for row in run["rows"]:
        t = row["realized_truth"]
        exp = t.get("inflation_expectations") or 2.3

        def sc(path):
            st = O.EconomyState(inflation=t["inflation"], unemployment=t["unemployment"],
                                policy_rate=t["fed_funds"], inflation_expectations=exp,
                                phillips_slope=phil, okun_sensitivity=okun)
            return O.score(st, O.PolicyDecision(rate_path=path))["total_loss"]

        runs = row.get("runs", [])
        if runs:
            s_means.append(_mean([sc(r["stale"]["path"]) for r in runs]))
            f_means.append(_mean([sc(r["fresh"]["path"]) for r in runs]))
        if row.get("fed_actual_path"):
            fed.append(sc(row["fed_actual_path"]))
    return _mean(s_means), _mean(f_means), (_mean(fed) if fed else None)


def conclusions(stale, fresh, fed):
    c1 = fresh > stale  # fresh worse than stale (the honest headline)
    c2 = (min(stale, fresh) < fed) if fed is not None else None  # better committee beats Fed
    return c1, c2


def restore():
    O.NEUTRAL_REAL_RATE, O.NATURAL_UNEMPLOYMENT, O.EMPLOYMENT_WEIGHT = (
        BASE["rstar"], BASE["ustar"], BASE["lam"])


def main():
    arg = next((a for a in sys.argv[1:] if a.endswith(".json")), None)
    run = _latest_run(arg)
    if not run:
        print("No run with per-path detail found. Run backtest_real.py first.")
        return
    try:
        print("=== SENSITIVITY SWEEP (re-scoring saved decisions; no model calls) ===")
        print(f"    source run: signal_mode={run.get('signal_mode')}, "
              f"dates={run.get('dates')}, runs/date={run.get('runs_per_date')}\n")

        s0, f0, fed0 = agg_losses(run, **BASE)
        c1_0, c2_0 = conclusions(s0, f0, fed0)
        print("Baseline (objective's hardcoded constants):")
        print(f"  stale {s0:.3f} | fresh {f0:.3f}" + (f" | fed {fed0:.3f}" if fed0 else ""))
        print(f"  C1 fresh-worse-than-stale: {c1_0} | "
              f"C2 committee-beats-Fed: {c2_0}\n")

        # One-at-a-time: does either conclusion flip across each param's range?
        print("One-at-a-time (does the conclusion ever flip across the range?):")
        K = 7
        for p, (lo, hi) in RANGES.items():
            c1s, c2s = set(), set()
            srange = []
            for i in range(K):
                val = lo + (hi - lo) * i / (K - 1)
                params = dict(BASE, **{p: val})
                s, f, fed = agg_losses(run, **params)
                c1, c2 = conclusions(s, f, fed)
                c1s.add(c1)
                if c2 is not None:
                    c2s.add(c2)
                srange.append((s, f))
            c1_stable = "STABLE" if len(c1s) == 1 else "FLIPS"
            c2_stable = "STABLE" if len(c2s) <= 1 else "FLIPS"
            print(f"  {p:6} [{lo}-{hi}]: C1 {c1_stable}, C2 {c2_stable}")

        # Monte-Carlo over the joint space.
        rng = random.Random(SEED)
        N = 400
        c1_hold = c2_hold = c2_total = 0
        for _ in range(N):
            params = {p: rng.uniform(*RANGES[p]) for p in RANGES}
            s, f, fed = agg_losses(run, **params)
            c1, c2 = conclusions(s, f, fed)
            c1_hold += int(c1 == c1_0)
            if c2 is not None:
                c2_total += 1
                c2_hold += int(c2 == c2_0)
        print(f"\nMonte-Carlo over the joint plausible space (N={N}, seed={SEED}):")
        print(f"  C1 ('{ 'fresh worse' if c1_0 else 'fresh better' }') holds in "
              f"{c1_hold/N*100:.0f}% of parameter settings")
        if c2_total:
            print(f"  C2 ('{ 'committee beats Fed' if c2_0 else 'Fed beats committee' }') "
                  f"holds in {c2_hold/c2_total*100:.0f}% of settings")
        print("\n  Read: a conclusion that holds across most of the plausible space is")
        print("  robust to the calibration; one that flips is fragile and reported as such.")

        out = RUNS / f"sensitivity-{datetime.datetime.now():%Y%m%d-%H%M%S}.json"
        out.write_text(json.dumps({
            "source_signal_mode": run.get("signal_mode"),
            "baseline": {"stale": s0, "fresh": f0, "fed": fed0, "C1": c1_0, "C2": c2_0},
            "mc": {"N": N, "seed": SEED, "C1_hold_pct": c1_hold / N * 100,
                   "C2_hold_pct": (c2_hold / c2_total * 100) if c2_total else None},
            "ranges": RANGES,
        }, indent=2), encoding="utf-8")
        print(f"\n  Saved -> {out}")
    finally:
        restore()


if __name__ == "__main__":
    main()
