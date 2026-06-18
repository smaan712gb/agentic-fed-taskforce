"""
backtest.py -- The keystone experiment for the Agentic Fed Task Force.

THE QUESTION (pre-registered, fixed before running):
  Holding the committee's reasoning constant, does giving it a CURRENT nowcast
  instead of the STALE official data lead to measurably better policy decisions,
  judged against what the economy actually did?

This isolates the one claim that matters: that the Fed's lagging data is costing
it. It is deliberately NOT "agents vs humans." Both committees here are the same
optimizer. The only thing that differs is the freshness of what they see.

PRE-REGISTRATION (set before the run, not tuned to the result):
  * Metric: mean realized total_loss across all decision dates. Lower is better.
  * Decision cadence: every 6 weeks (~8 per year), the FOMC rhythm.
  * Window: the back half of the generated history (the front half is warm-up).
  * Seed: fixed at 7. No tuning of model or noise to the test window.
  * Secondary readouts: share of dates where the decision changed, and the
    win/loss/tie tally of fresh vs stale on realized loss.

NO LOOK-AHEAD is enforced structurally: the stale committee can only read the
lagged official view, and the nowcast committee can only read the current-month
nowcast. Neither can see the future realized path that scores them.

HONEST CAVEAT: the data is synthetic (see nowcast.py). A win here proves the
pipeline and methodology are sound. It does NOT prove the empirical claim. Swap
in real feeds at the marked points in nowcast.py and re-run to test it for real.
"""

from __future__ import annotations
import random
from objective import EconomyState, PolicyDecision, score
from nowcast import generate_true_economy, official_view, nowcast_view


def candidate_decisions(current_rate: float) -> list[PolicyDecision]:
    """
    The menu the committee chooses from. A first move, then either holding or
    gently reverting toward neutral over a 4-quarter horizon. Kept small on
    purpose (simplicity first): the experiment is about information, not about
    an exotic action space.
    """
    moves = [-0.50, -0.25, 0.0, 0.25, 0.50]
    neutral = 0.75 + 2.0  # r* + target
    decisions = []
    for m in moves:
        first = round(max(0.0, current_rate + m), 3)
        # Shape A: hold the new rate.
        decisions.append(PolicyDecision(rate_path=[first] * 4,
                                         rationale=f"move {m:+.2f}, hold"))
        # Shape B: move, then drift halfway to neutral.
        drift = round((first + neutral) / 2, 3)
        decisions.append(PolicyDecision(rate_path=[first, drift, drift, drift],
                                         rationale=f"move {m:+.2f}, drift to neutral"))
    return decisions


def committee_choose(view, current_rate: float, n_samples: int = 200) -> PolicyDecision:
    """
    The committee, reduced to its essence: given what it can SEE, pick the
    candidate that minimizes the dual-mandate loss under that view. In
    production each persona is a frontier-model agent debating; here the choice
    is a transparent optimizer so the experiment is reproducible and the only
    moving part is the information set.
    """
    # Honest uncertainty: the committee does not trust its reading as a point.
    # It samples states from the reading's reported distribution and picks the
    # candidate with the lowest EXPECTED loss across those draws. A noisier view
    # (a fresh nowcast) therefore decides more cautiously, which is exactly how
    # a well-run committee should treat a less certain signal.
    rng = random.Random(1234 + view.as_of_month)
    sampled_states = []
    for _ in range(n_samples):
        sampled_states.append(EconomyState(
            inflation=rng.gauss(view.inflation, view.inflation_sigma),
            unemployment=rng.gauss(view.unemployment, view.unemployment_sigma),
            policy_rate=current_rate,
            inflation_expectations=round(0.5 * view.inflation + 0.5 * 2.3, 3),
        ))

    best, best_loss = None, float("inf")
    for d in candidate_decisions(current_rate):
        expected = sum(score(s, d)["total_loss"] for s in sampled_states) / n_samples
        if expected < best_loss:
            best, best_loss = d, expected
    return best


def realized_loss(truth: dict, month: int, decision: PolicyDecision) -> float:
    """
    Score a chosen decision against the TRUE state of the economy on that date,
    i.e. what actually was, not what either committee believed. This is the
    honest judge neither committee can see at decision time.
    """
    true_state = EconomyState(
        inflation=truth["inflation"][month],
        unemployment=truth["unemployment"][month],
        policy_rate=truth["policy_rate"][month],
        inflation_expectations=round(0.5 * truth["inflation"][month] + 0.5 * 2.3, 3),
    )
    return score(true_state, decision)["total_loss"]


def run(seed: int = 7):
    truth = generate_true_economy(seed=seed)
    n = truth["n_months"]

    # Decision dates: back half only, every 2 months, a monthly-data stand-in
    # for the FOMC's roughly 6-week meeting cadence (8 meetings a year).
    start = n // 2
    decision_months = list(range(start, n, 2))

    stale_losses, fresh_losses = [], []
    changed = 0
    wins = {"fresh": 0, "stale": 0, "tie": 0}

    print("=== KEYSTONE EXPERIMENT: stale data vs fresh data ===")
    print("    (same committee, only the information set differs)\n")
    print(f"{'month':>5} {'rate':>6} {'stale move':>12} {'fresh move':>12} "
          f"{'stale loss':>11} {'fresh loss':>11} {'better':>8}")

    for m in decision_months:
        current_rate = truth["policy_rate"][m]  # the Fed knows its own rate exactly

        stale_view = official_view(truth, m)
        fresh_view = nowcast_view(truth, m)

        stale_dec = committee_choose(stale_view, current_rate)
        fresh_dec = committee_choose(fresh_view, current_rate)

        s_loss = realized_loss(truth, m, stale_dec)
        f_loss = realized_loss(truth, m, fresh_dec)
        stale_losses.append(s_loss)
        fresh_losses.append(f_loss)

        if stale_dec.rate_path != fresh_dec.rate_path:
            changed += 1
        if abs(f_loss - s_loss) < 1e-6:
            wins["tie"] += 1
            better = "tie"
        elif f_loss < s_loss:
            wins["fresh"] += 1
            better = "fresh"
        else:
            wins["stale"] += 1
            better = "stale"

        print(f"{m:>5} {current_rate:>6.2f} "
              f"{stale_dec.rate_path[0]:>12.2f} {fresh_dec.rate_path[0]:>12.2f} "
              f"{s_loss:>11.3f} {f_loss:>11.3f} {better:>8}")

    n_dates = len(decision_months)
    mean_stale = sum(stale_losses) / n_dates
    mean_fresh = sum(fresh_losses) / n_dates
    improvement = (mean_stale - mean_fresh) / mean_stale * 100

    print("\n--- SCORECARD (pre-registered metric: mean realized total_loss) ---")
    print(f"  decision dates evaluated : {n_dates}")
    print(f"  mean realized loss, STALE: {mean_stale:.3f}")
    print(f"  mean realized loss, FRESH: {mean_fresh:.3f}")
    print(f"  improvement from freshness: {improvement:+.1f}%  (positive = fresh better)")
    print(f"  decision changed by freshness: {changed}/{n_dates} dates "
          f"({changed / n_dates * 100:.0f}%)")
    print(f"  per-date tally  fresh/stale/tie: "
          f"{wins['fresh']}/{wins['stale']}/{wins['tie']}")
    print("\n  Reminder: synthetic data. This validates the harness and the")
    print("  methodology, not the real-world magnitude. Swap real feeds in")
    print("  nowcast.py (marked SWAP POINT) and re-run to test the claim.")


if __name__ == "__main__":
    run()
