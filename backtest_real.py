"""
backtest_real.py -- the keystone experiment on REAL data, with the REAL agent
committee. Signal to decision, measured for a competitive edge.

THE QUESTION (same as backtest.py, now real):
  At real historical FOMC dates, does giving the agentic committee real-time
  financial signals -- on top of the lagged official data the Fed actually had
  -- lead to measurably better policy decisions, judged against what the economy
  truly did?

DESIGN (isolates exactly one variable: the information set):
  * Both committees are the SAME frontier-model committee (committee.py).
  * Both start from the SAME stale official snapshot -- the ALFRED vintage as it
    was really known on the decision date (real publication lag, first-release
    values).
  * The FRESH committee additionally sees the real-time FMP signals available on
    that date (the Treasury curve and its slope). The STALE one does not.
  * Both are scored against the REALIZED truth (FRED latest vintage) for the
    decision month -- the honest judge neither could see when deciding.

NO LOOK-AHEAD is structural: every input is pinned to the as-of date; realized
truth is fetched separately and used only to score.

COST: each committee run is ~6 model calls at rounds=1 (4 economists + Skeptic +
Chair); two committees per date. Keep the date list short while iterating.

Run:
    python backtest_real.py                 # default date set, rounds=1
    python backtest_real.py 2024-06-12 2024-09-18      # explicit dates
    FED_BACKTEST_ROUNDS=2 python backtest_real.py
"""

from __future__ import annotations

import os
import sys
import json
import datetime
from pathlib import Path

import config

config.init()

from objective import EconomyState, PolicyDecision, score
from committee import run_committee, select_backend
from data_real import (
    official_snapshot, realtime_signals, realized_truth, leading_signals,
    fed_actual_path,
)

# Which real-time signal the FRESH committee gets:
#   "leading" = jobless claims, job postings, credit spreads, dollar, oil, VIX
#               (high-frequency, leading, largely exogenous to the Fed path)
#   "curve"   = the original Treasury yield curve (endogenous; the pilot's signal)
SIGNAL_MODE = os.environ.get("FED_SIGNAL_MODE", "leading")

# Pre-registered FOMC decision dates (see PRE-REGISTRATION.md), chosen to span
# regimes -- aggressive hiking, banking stress, the hold, the pivot, the cuts --
# BEFORE looking at results, to remove date-cherry-picking degrees of freedom.
DEFAULT_DATES = [
    "2022-06-15",  # +75bp, peak hawkish surprise
    "2022-09-21",  # mid hiking cycle
    "2022-12-14",  # hiking pace slows
    "2023-03-22",  # banking stress (SVB) meeting
    "2023-07-26",  # final hike of the cycle
    "2023-09-20",  # extended hold begins
    "2023-12-13",  # the dovish pivot
    "2024-03-20",  # hold, sticky inflation
    "2024-06-12",  # hold, deeply inverted curve
    "2024-09-18",  # first cut
]

ANCHOR = 2.3  # long-run inflation-expectations anchor, as in backtest.py


def _expectations(inflation: float) -> float:
    return round(0.5 * inflation + 0.5 * ANCHOR, 3)


def stale_state(snap) -> EconomyState:
    """The official vintage as known on the decision date -> an EconomyState."""
    return EconomyState(
        inflation=snap.inflation,
        unemployment=snap.unemployment,
        policy_rate=snap.fed_funds,  # the Fed knows its own rate exactly
        # Real market-based expectations (5y breakeven); fall back only if absent.
        inflation_expectations=snap.inflation_expectations or _expectations(snap.inflation),
    )


def truth_state(truth: dict) -> EconomyState:
    """The realized economy for the decision month -> the scoring state."""
    return EconomyState(
        inflation=truth["inflation"],
        unemployment=truth["unemployment"],
        policy_rate=truth["fed_funds"],
        inflation_expectations=truth.get("inflation_expectations") or _expectations(truth["inflation"]),
    )


def curve_signals_text(sig: dict) -> str:
    """The original (endogenous) Treasury-curve signal. Kept for A/B comparison."""
    if not sig.get("available"):
        return "Real-time market data is unavailable for this date."
    yc = sig["yield_curve"]
    spread = sig["term_spread_10y_3m"]
    shape = "inverted (10y below 3m)" if spread is not None and spread < 0 else "upward-sloping"

    def _mv(x):
        return "n/a" if x is None else f"{x:+} pp"

    return (
        f"As of {sig['curve_date']}, the Treasury yield curve was: "
        f"3-month {yc['month3']}%, 2-year {yc['year2']}%, 10-year {yc['year10']}%, "
        f"30-year {yc['year30']}%. The 10-year minus 3-month term spread was "
        f"{spread} percentage points -- {shape}. Over the prior ~10 trading days "
        f"the 3-month moved {_mv(sig.get('change_3m_10d'))} and the 10-year moved "
        f"{_mv(sig.get('change_10y_10d'))}. Weigh as one input, applying your own "
        f"judgment about how much it should move the decision in the current regime."
    )


def leading_signals_text(ls: dict) -> str:
    """Format the leading/exogenous signal set (the fixed edge)."""
    lines = [
        "Real-time leading indicators available now. These are high-frequency, "
        "barely revised, and move BEFORE the official prints -- and unlike the "
        "Treasury curve they are not just the market's forecast of your own next "
        "move. Weigh them with your own judgment:"
    ]
    for sid, v in ls.items():
        if sid == "as_of" or not v:
            continue
        chg = f" (change {v['change']:+} over ~{v['window_days']}d)" if v.get("change") is not None else ""
        lines.append(f"  - {v['label']}: {v['value']}{chg}  [as of {v['date']}]")
    return "\n".join(lines)


def signal_context(date: str):
    """Return (text, raw) for the configured signal mode."""
    if SIGNAL_MODE == "curve":
        raw = realtime_signals(date)
        return curve_signals_text(raw), raw
    raw = leading_signals(date)
    return leading_signals_text(raw), raw


def _committee_loss(state: EconomyState, extra_context, backend, rounds, ts):
    """Run one committee to a decision and score it against the realized truth."""
    log = run_committee(state, rounds=rounds, backend=backend,
                        extra_context=extra_context, verbose=False)
    path = log.decision["rate_path"]
    loss = score(ts, PolicyDecision(rate_path=path))["total_loss"]
    return path, loss, log.decision["statement"]


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def run(dates: list[str], rounds: int = 1, runs_per_date: int = 1) -> dict:
    backend = select_backend()
    print("=== KEYSTONE EXPERIMENT (REAL data, REAL committee) ===")
    print(f"    Backend: {backend.name}   rounds/committee: {rounds}   "
          f"runs/date: {runs_per_date}")
    print(f"    Signal mode: {SIGNAL_MODE}  "
          f"({'leading/exogenous indicators' if SIGNAL_MODE == 'leading' else 'Treasury yield curve (endogenous)'})")
    print("    Three arms: STALE committee, FRESH committee, and the FED's actual")
    print("    realized funds-rate path -- all scored by the same objective.")
    print("    CAVEAT: the objective re-simulates each path from the realized")
    print("    state; it does NOT observe post-decision macro. This is a")
    print("    model-internal ranking, not a measurement of real outcomes.\n")
    print(f"{'date':>11} {'stale':>9} {'fresh':>9} {'FED':>9} {'best':>8}")

    rows = []
    date_means_s, date_means_f, fed_losses = [], [], []
    run_wins = {"fresh": 0, "stale": 0, "tie": 0}  # across every date x run
    date_better = {"fresh": 0, "stale": 0, "tie": 0}  # by per-date mean
    best_arm = {"stale": 0, "fresh": 0, "fed": 0}  # which of the 3 wins per date
    beats_fed = {"stale": 0, "fresh": 0}  # committees that beat the Fed, by date

    for d in dates:
        snap = official_snapshot(d)
        sig_text, sig = signal_context(d)
        st = stale_state(snap)

        month = d[:7] + "-01"
        truth = realized_truth(month)
        if truth["inflation"] is None or truth["unemployment"] is None:
            print(f"{d:>11}  realized truth incomplete; skipping")
            continue
        ts = truth_state(truth)

        s_losses, f_losses, run_detail = [], [], []
        fresh_run_wins = 0
        for _ in range(runs_per_date):
            sp, sl, sstmt = _committee_loss(st, None, backend, rounds, ts)
            fp, fl, fstmt = _committee_loss(st, sig_text, backend, rounds, ts)
            s_losses.append(sl)
            f_losses.append(fl)
            if abs(fl - sl) < 1e-6:
                run_wins["tie"] += 1
            elif fl < sl:
                run_wins["fresh"] += 1
                fresh_run_wins += 1
            else:
                run_wins["stale"] += 1
            run_detail.append({
                "stale": {"path": sp, "loss": sl, "statement": sstmt},
                "fresh": {"path": fp, "loss": fl, "statement": fstmt},
            })

        # Fed-actual benchmark: what the FOMC actually did, scored identically.
        fed_path = fed_actual_path(d)
        fed_loss = score(ts, PolicyDecision(rate_path=fed_path))["total_loss"]
        fed_losses.append(fed_loss)

        m_s, m_f = _mean(s_losses), _mean(f_losses)
        date_means_s.append(m_s)
        date_means_f.append(m_f)
        if abs(m_f - m_s) < 1e-6:
            db = "tie"
        elif m_f < m_s:
            db = "fresh"
        else:
            db = "stale"
        date_better[db] += 1

        # Three-way: which arm had the lowest realized loss this date.
        arms = {"stale": m_s, "fresh": m_f, "fed": fed_loss}
        winner = min(arms, key=arms.get)
        best_arm[winner] += 1
        if m_s < fed_loss:
            beats_fed["stale"] += 1
        if m_f < fed_loss:
            beats_fed["fresh"] += 1

        rows.append({
            "date": d,
            "official_snapshot": {
                "inflation": snap.inflation, "unemployment": snap.unemployment,
                "fed_funds": snap.fed_funds,
                "inflation_ref_month": snap.inflation_ref_month,
            },
            "realtime_signal": sig,
            "realized_truth": truth,
            "stale_loss_mean": m_s, "stale_loss_sd": _stdev(s_losses),
            "fresh_loss_mean": m_f, "fresh_loss_sd": _stdev(f_losses),
            "fed_actual_path": fed_path, "fed_loss": fed_loss,
            "fresh_wins_of_runs": f"{fresh_run_wins}/{runs_per_date}",
            "better_by_mean": db, "best_of_three": winner,
            "runs": run_detail,
        })
        print(f"{d:>11} {m_s:>9.3f} {m_f:>9.3f} {fed_loss:>9.3f} {winner:>8}")

    n = len(date_means_s)
    if n == 0:
        print("\nNo scorable dates.")
        return {}

    mean_s = _mean(date_means_s)
    mean_f = _mean(date_means_f)
    mean_fed = _mean(fed_losses)
    improvement = (mean_s - mean_f) / mean_s * 100 if mean_s else 0.0
    total_runs = sum(run_wins.values())

    print("\n--- SCORECARD (mean realized total_loss across dates; lower is better) ---")
    print(f"  dates scored                : {n}   (x{runs_per_date} runs = {total_runs} committee pairs)")
    print(f"  mean realized loss, STALE   : {mean_s:.3f}")
    print(f"  mean realized loss, FRESH   : {mean_f:.3f}")
    print(f"  mean realized loss, FED     : {mean_fed:.3f}   <- the human benchmark")
    print(f"  edge from real-time signals : {improvement:+.1f}%  (positive = fresh better)")
    print(f"  best of three (s/f/fed)     : {best_arm['stale']}/{best_arm['fresh']}/{best_arm['fed']}")
    print(f"  committee beats Fed (by date): stale {beats_fed['stale']}/{n}, fresh {beats_fed['fresh']}/{n}")
    print(f"  by-date (mean) fresh/stale/tie : {date_better['fresh']}/{date_better['stale']}/{date_better['tie']}")
    print("\n  Real data, real committee, run-to-run noise averaged out.")
    print("  CAVEAT (read this): the objective re-simulates each path from the")
    print("  realized state -- it is a model-internal ranking, NOT a measurement of")
    print("  post-decision macro outcomes. Treat as an illustrative pilot.")

    summary = {
        "model": backend.name, "rounds": rounds, "runs_per_date": runs_per_date,
        "signal_mode": SIGNAL_MODE,
        "dates": n, "mean_stale": mean_s, "mean_fresh": mean_f, "mean_fed": mean_fed,
        "improvement_pct": improvement,
        "best_of_three": best_arm, "beats_fed": beats_fed,
        "by_date": date_better, "by_run": run_wins, "rows": rows,
        "caveat": "model-internal ranking; objective re-simulates from realized "
                  "state and does not observe post-decision macro outcomes.",
    }
    runs = Path(__file__).parent / "runs"
    runs.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = runs / f"backtest_real-{stamp}.json"
    out.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n  Full transcript -> {out}")
    return summary


if __name__ == "__main__":
    dates = [a for a in sys.argv[1:] if a.startswith("20")]
    if not dates:
        dates = DEFAULT_DATES
    rounds = int(os.environ.get("FED_BACKTEST_ROUNDS", "1"))
    runs_per_date = int(os.environ.get("FED_BACKTEST_RUNS", "1"))
    run(dates, rounds=rounds, runs_per_date=runs_per_date)
