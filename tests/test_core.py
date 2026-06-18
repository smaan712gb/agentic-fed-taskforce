"""
Unit tests for the Agentic Fed Task Force sandbox.

Run with:  pytest    (or: uv run pytest)

These tests guard the two things that, if broken, would invalidate the whole
experiment: the objective must rank decisions sensibly, and the backtest must
never let a committee see the future (no look-ahead).
"""

from objective import EconomyState, PolicyDecision, score, taylor_rule
from nowcast import generate_true_economy, official_view, nowcast_view


# --- objective ranks decisions sensibly ---------------------------------------

def test_on_target_economy_has_near_zero_loss():
    """An economy already at target, held steady, should score very low."""
    at_target = EconomyState(inflation=2.0, unemployment=4.2, policy_rate=2.75,
                             inflation_expectations=2.0)
    hold = PolicyDecision(rate_path=[2.75] * 4)
    assert score(at_target, hold)["total_loss"] < 0.5


def test_overheating_cut_is_worse_than_restraint():
    """When inflation is hot, a big cut should score worse than leaning against it."""
    hot = EconomyState(inflation=3.5, unemployment=3.6, policy_rate=3.6)
    cut = PolicyDecision(rate_path=[2.5, 2.5, 2.5, 2.5])
    lean = PolicyDecision(rate_path=[3.85, 4.0, 4.0, 3.85])
    assert score(hot, cut)["total_loss"] > score(hot, lean)["total_loss"]


def test_empty_decision_rejected():
    try:
        PolicyDecision(rate_path=[])
        assert False, "empty rate_path should raise"
    except ValueError:
        pass


def test_taylor_rule_returns_full_horizon():
    state = EconomyState(inflation=3.1, unemployment=4.0, policy_rate=3.625)
    dec = taylor_rule(state)
    assert len(dec.rate_path) == 4
    assert all(r >= 0 for r in dec.rate_path)


# --- the no-look-ahead guarantee ----------------------------------------------

def test_official_view_never_sees_the_future():
    """The stale view must be dated to the past, never to or beyond the decision date."""
    truth = generate_true_economy()
    n = truth["n_months"]
    lag = 2
    for as_of in range(lag, n):
        view = official_view(truth, as_of, lag=lag)
        assert view.as_of_month <= as_of - lag


def test_nowcast_view_is_current_not_future():
    """The fresh view may be current, but must never read a future month."""
    truth = generate_true_economy()
    n = truth["n_months"]
    for as_of in range(n):
        view = nowcast_view(truth, as_of)
        assert view.as_of_month == as_of


def test_views_report_positive_uncertainty():
    """Both views must carry an honest, non-zero uncertainty band."""
    truth = generate_true_economy()
    off = official_view(truth, 50)
    now = nowcast_view(truth, 50)
    assert off.inflation_sigma > 0 and now.inflation_sigma > 0


# --- the committee loop runs end to end on the stub backend -------------------

def test_committee_runs_and_scores_against_the_objective():
    """
    The full deliberation loop (propose -> score -> deliberate -> red-team ->
    decide) must run on the stub backend with no API key, and its verdict must
    be computed from the same objective.py score, not self-reported.
    """
    from committee import run_committee, StubBackend

    state = EconomyState(inflation=3.1, unemployment=4.0, policy_rate=3.625,
                         inflation_expectations=2.6)
    log = run_committee(state, rounds=2, backend=StubBackend())

    # The decision is a real 4-quarter path scored by the sandbox.
    assert len(log.decision["rate_path"]) == 4
    # The verdict's loss must equal an independent re-score of the chosen path
    # (the agents never grade themselves).
    chosen = PolicyDecision(rate_path=log.decision["rate_path"])
    assert log.verdict["final_total_loss"] == score(state, chosen)["total_loss"]
    # The stub leans against inflation, so it must clear the Taylor baseline.
    assert log.verdict["beat_baseline"] is True


def test_committee_decision_path_is_non_negative_and_full_horizon():
    from committee import run_committee, StubBackend

    state = EconomyState(inflation=2.0, unemployment=4.2, policy_rate=2.75)
    log = run_committee(state, rounds=1, backend=StubBackend())
    path = log.decision["rate_path"]
    assert len(path) == 4
    assert all(r >= 0 for r in path)
