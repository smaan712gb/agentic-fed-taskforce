"""
objective.py  -- The dual-mandate objective for the Agentic Fed Task Force.

This is the `val_bpb` analog from karpathy/autoresearch. In autoresearch the
agent edits train.py and is scored on validation bits-per-byte. Here, agents
propose a monetary-policy decision (a policy rate and a forward path) and are
scored on a central-bank loss function: how far the economy is expected to
drift from the dual mandate, period by period, under that decision.

Lower score is better. The number is the single hard metric agents hill-climb.

Design follows Karpathy's "simplicity first": one file, no framework, a small
reduced-form macro model good enough to RANK competing decisions. It is a
decision-support sandbox, NOT a forecast of the real economy.
"""

from __future__ import annotations
from dataclasses import dataclass, field


# ----------------------------------------------------------------------------
# Mandate targets. These are the FOMC's stated longer-run goals.
# ----------------------------------------------------------------------------
INFLATION_TARGET = 2.0          # percent, PCE, the Fed's stated 2% goal
NATURAL_UNEMPLOYMENT = 4.2      # percent, longer-run u* (editable assumption)
NEUTRAL_REAL_RATE = 0.75        # percent, r-star, longer-run real neutral rate

# Loss weight on the employment gap relative to the inflation gap.
# lambda = 1.0 treats both mandates symmetrically. Raising it tilts the
# objective toward protecting jobs; lowering it tilts toward fighting inflation.
EMPLOYMENT_WEIGHT = 1.0

# Penalty on moving the rate aggressively. Central banks value gradualism
# because abrupt moves carry financial-stability and credibility costs.
RATE_CHANGE_PENALTY = 0.25

DISCOUNT = 0.97  # weight on future periods vs. the present


@dataclass
class EconomyState:
    """A minimal snapshot of the economy the agents are reasoning about."""
    inflation: float            # current PCE inflation, percent
    unemployment: float         # current unemployment rate, percent
    policy_rate: float          # current fed funds rate, percent (midpoint)
    inflation_expectations: float = 2.3  # anchored long-run expectation

    # Reduced-form responsiveness of the economy (the "model" the sandbox uses).
    phillips_slope: float = 0.30   # how much an output/employment gap moves inflation
    okun_sensitivity: float = 0.50 # how much a rate gap moves unemployment


@dataclass
class PolicyDecision:
    """What an agent proposes: a rate now and a path for the next quarters."""
    rate_path: list[float] = field(default_factory=list)  # quarterly fed funds path
    rationale: str = ""

    def __post_init__(self):
        if not self.rate_path:
            raise ValueError("A decision must contain at least one quarter.")


def _simulate(state: EconomyState, rate_path: list[float]) -> list[tuple[float, float]]:
    """
    Roll the reduced-form economy forward under a proposed rate path.

    The mechanics are intentionally transparent and standard:
      * A rate above the neutral rate (r-star + target) cools demand, which
        raises unemployment toward and past u*, and pulls inflation down.
      * Inflation is sticky and partly driven by expectations (a Phillips curve).
      * Expectations re-anchor slowly toward realized inflation.

    Returns a list of (inflation, unemployment) for each simulated quarter.
    """
    neutral_nominal = NEUTRAL_REAL_RATE + INFLATION_TARGET
    inflation = state.inflation
    unemployment = state.unemployment
    expectations = state.inflation_expectations
    path = []

    for rate in rate_path:
        # Real policy stance: positive = restrictive, negative = accommodative.
        real_stance = (rate - inflation) - NEUTRAL_REAL_RATE

        # Restriction pushes unemployment up toward/above its natural rate.
        unemployment += state.okun_sensitivity * real_stance * 0.5
        unemployment = max(0.0, unemployment)

        # Phillips curve: an employment gap below u* (tight labor) lifts inflation;
        # slack lowers it. Inflation also tracks expectations.
        employment_gap = NATURAL_UNEMPLOYMENT - unemployment  # >0 means tight labor
        inflation = (
            0.6 * inflation
            + 0.4 * expectations
            + state.phillips_slope * employment_gap
        )

        # Expectations re-anchor slowly toward realized inflation.
        expectations += 0.15 * (inflation - expectations)

        path.append((inflation, unemployment))

    return path


def score(state: EconomyState, decision: PolicyDecision) -> dict:
    """
    The single hard metric. Lower total_loss is a better decision.

    total_loss = discounted sum over the path of:
        (inflation gap)^2 + lambda * (employment gap)^2
      + a penalty for large quarter-to-quarter rate changes.
    """
    path = _simulate(state, decision.rate_path)

    mandate_loss = 0.0
    for t, (inflation, unemployment) in enumerate(path):
        infl_gap = inflation - INFLATION_TARGET
        empl_gap = unemployment - NATURAL_UNEMPLOYMENT
        period_loss = infl_gap ** 2 + EMPLOYMENT_WEIGHT * (empl_gap ** 2)
        mandate_loss += (DISCOUNT ** t) * period_loss

    # Smoothness penalty across the whole path, including the first move.
    smoothness = 0.0
    prev = state.policy_rate
    for rate in decision.rate_path:
        smoothness += (rate - prev) ** 2
        prev = rate
    smoothness *= RATE_CHANGE_PENALTY

    total = mandate_loss + smoothness
    return {
        "total_loss": round(total, 4),
        "mandate_loss": round(mandate_loss, 4),
        "smoothness_penalty": round(smoothness, 4),
        "terminal_inflation": round(path[-1][0], 2),
        "terminal_unemployment": round(path[-1][1], 2),
    }


def taylor_rule(state: EconomyState) -> PolicyDecision:
    """
    The baseline every agent must beat: the classic Taylor (1993) rule.

        rate = r* + inflation + 1.5*(inflation - target) + 0.5*(output gap proxy)

    We proxy the output gap with the negative employment gap (Okun's law).
    This is the 'do nothing clever' control, like autoresearch's bare baseline.
    """
    output_gap_proxy = NATURAL_UNEMPLOYMENT - state.unemployment  # tight labor = positive gap
    prescribed = (
        NEUTRAL_REAL_RATE
        + state.inflation
        + 1.5 * (state.inflation - INFLATION_TARGET)
        + 0.5 * output_gap_proxy
    )
    prescribed = max(0.0, prescribed)
    # Hold the prescribed rate flat across a 4-quarter horizon.
    return PolicyDecision(
        rate_path=[round(prescribed, 2)] * 4,
        rationale="Taylor (1993) baseline, held flat for 4 quarters.",
    )


if __name__ == "__main__":
    # Calibrated to the June 2026 setting: funds rate 3.5-3.75% (midpoint 3.625),
    # inflation running hot on energy, labor still firm.
    today = EconomyState(
        inflation=3.1,
        unemployment=4.0,
        policy_rate=3.625,
        inflation_expectations=2.6,
    )

    print("=== Agentic Fed Task Force :: objective sandbox ===\n")
    print(f"Starting state: inflation={today.inflation}%  "
          f"unemployment={today.unemployment}%  funds rate={today.policy_rate}%\n")

    # Baseline: the Taylor rule.
    baseline = taylor_rule(today)
    base_score = score(today, baseline)
    print(f"[BASELINE] Taylor rule path: {baseline.rate_path}")
    print(f"           {base_score}\n")

    # Three candidate "agent" decisions to rank against the baseline.
    candidates = {
        "Hold (Warsh: no cruel choice)": PolicyDecision(
            rate_path=[3.625, 3.625, 3.625, 3.625],
            rationale="Hold steady, let supply-side energy shock pass through.",
        ),
        "Gradual hikes": PolicyDecision(
            rate_path=[3.875, 4.125, 4.125, 4.0],
            rationale="Lean against inflation, then ease as it cools.",
        ),
        "Aggressive cut": PolicyDecision(
            rate_path=[3.0, 2.5, 2.5, 2.5],
            rationale="Front-load support for the labor market.",
        ),
    }

    ranked = []
    for name, decision in candidates.items():
        s = score(today, decision)
        ranked.append((s["total_loss"], name, s))

    ranked.sort()
    print("Candidate decisions, ranked best-to-worst by total_loss:\n")
    for loss, name, s in ranked:
        print(f"  {loss:>8.3f}  {name}")
        print(f"            terminal inflation {s['terminal_inflation']}%, "
              f"terminal unemployment {s['terminal_unemployment']}%")
    print(f"\n  (Taylor baseline for reference: {base_score['total_loss']})")
