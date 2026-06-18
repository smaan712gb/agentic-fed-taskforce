"""
committee.py -- The agent layer for the Agentic Fed Task Force.

This is the piece program.md describes and the blueprint defers as "the next
milestone": a real committee of frontier-model personas that runs ONE full
deliberation cycle against objective.py and produces a logged decision.

The loop is exactly program.md's:

    1. Read the state.
    2. Propose      -- each economist persona proposes a PolicyDecision.
    3. Score        -- objective.py scores every proposal (the HARD metric;
                       agents never grade their own work).
    4. Deliberate   -- personas see the scored board and revise, for N rounds.
    5. Red-team     -- the Skeptic attacks the leading proposal.
    6. Decide       -- the Chair synthesises a final decision + statement and
                       logs the full transcript, scores, and dissents.

Success criterion (from program.md): the chosen decision must BEAT the Taylor
baseline on total_loss AND survive the Skeptic (no fatal challenge).

Runtime: the committee runs on the strongest available frontier model
(Claude Opus 4.8 by default) via the Anthropic SDK -- this is the blueprint's
key correction: autoresearch is the inspiration for the LOOP, not the runtime;
policy reasoning wants the best model. If no ANTHROPIC_API_KEY is set, a clearly
labelled deterministic STUB backend runs the same loop end to end so the
plumbing is demonstrable without a key.

Run:
    python committee.py                 # uses the model if a key is set, else stub
    FED_FORCE_STUB=1 python committee.py   # force the stub even with a key
"""

from __future__ import annotations

import json
import os
import sys
import datetime
from dataclasses import dataclass, asdict, field
from pathlib import Path

from objective import (
    EconomyState,
    PolicyDecision,
    score,
    taylor_rule,
    INFLATION_TARGET,
    NATURAL_UNEMPLOYMENT,
    NEUTRAL_REAL_RATE,
    EMPLOYMENT_WEIGHT,
)

MODEL = os.environ.get("FED_MODEL", "claude-opus-4-8")
HORIZON = 4  # quarters in a rate path, matching objective.py's candidates


# ----------------------------------------------------------------------------
# The charter, lifted from program.md so the agents obey the same document a
# human task force would edit. Kept inline so this file runs standalone.
# ----------------------------------------------------------------------------
OBJECTIVE_BRIEF = f"""\
You are scored by a fixed, transparent dual-mandate loss function (lower is
better). For a proposed {HORIZON}-quarter fed funds path it rolls a reduced-form
economy forward and sums, per quarter:

    (inflation - {INFLATION_TARGET})^2 + {EMPLOYMENT_WEIGHT} * (unemployment - {NATURAL_UNEMPLOYMENT})^2

plus a penalty for abrupt quarter-to-quarter rate moves. Targets: {INFLATION_TARGET}% PCE
inflation, {NATURAL_UNEMPLOYMENT}% natural unemployment, {NEUTRAL_REAL_RATE}% neutral real rate
(so a ~{NEUTRAL_REAL_RATE + INFLATION_TARGET}% nominal rate is roughly neutral). You do NOT score yourself:
the sandbox scores every path you propose and reports it back to you."""

OPERATING_DISCIPLINE = """\
Operating discipline (you MUST follow all four):
1. Think before deciding. State your key assumption. If the data is ambiguous,
   say which reading you chose and why; do not hide the tradeoff between the two
   mandates.
2. Simplicity first. Prefer the smallest move that meets the objective. Do not
   propose a clever multi-part path when a clean one scores as well.
3. Surgical changes. Move the stance only as much as the mandate requires. Do
   not re-litigate framework or communications inside a rate decision.
4. Goal-driven. The success criterion is explicit: beat the Taylor baseline on
   total_loss AND survive the red-team. Aim for that, honestly."""

# Each proposing persona: (key, display name, charter focus from program.md).
PROPOSERS = [
    (
        "inflation",
        "Inflation economist",
        "You specialise in price dynamics, supply shocks, and expectations "
        "anchoring. Weigh whether the current inflation is supply-driven (which "
        "may fade) or demand-driven (which a rate path must lean against), and "
        "watch for expectations un-anchoring.",
    ),
    (
        "labor",
        "Labor economist",
        "You specialise in employment, participation, and wage pressure. Protect "
        "the labor side of the mandate: weigh how far a restrictive path would "
        "push unemployment above its natural rate, and how persistent that "
        "damage is.",
    ),
    (
        "finstab",
        "Financial-stability economist",
        "You watch credit spreads, bank stress, and the cost of abrupt moves. "
        "You are the strongest voice for gradualism: abrupt rate changes carry "
        "financial-stability and credibility costs the loss function only "
        "partly captures.",
    ),
    (
        "econometrician",
        "Econometrician",
        "You own the model and its uncertainty. Flag when a proposal wins only "
        "because it exploits a fragile assumption of the reduced-form sandbox "
        "rather than because it is good economics. Prefer paths that are robust, "
        "not paths that merely score well.",
    ),
]


# ----------------------------------------------------------------------------
# Structured-output schemas. Agents return these via a forced tool call, which
# is robust across SDK versions and avoids the thinking/tool_choice conflict.
# ----------------------------------------------------------------------------
_PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "rate_path": {
            "type": "array",
            "items": {"type": "number"},
            "description": f"The proposed fed funds rate (percent) for each of "
            f"the next {HORIZON} quarters.",
        },
        "assumption": {
            "type": "string",
            "description": "The single key assumption behind this path (principle 1).",
        },
        "rationale": {
            "type": "string",
            "description": "Concise economic argument for the path (2-4 sentences).",
        },
    },
    "required": ["rate_path", "assumption", "rationale"],
    "additionalProperties": False,
}

_SKEPTIC_SCHEMA = {
    "type": "object",
    "properties": {
        "challenges": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific attacks: wrong assumptions, fragile model "
            "dependence, tail risks, credibility costs.",
        },
        "fatal": {
            "type": "boolean",
            "description": "True only if at least one challenge is severe enough "
            "that the proposal should NOT be adopted as-is.",
        },
        "summary": {"type": "string"},
    },
    "required": ["challenges", "fatal", "summary"],
    "additionalProperties": False,
}

_CHAIR_SCHEMA = {
    "type": "object",
    "properties": {
        "rate_path": {
            "type": "array",
            "items": {"type": "number"},
            "description": f"The committee's final {HORIZON}-quarter fed funds path.",
        },
        "statement": {
            "type": "string",
            "description": "The public-facing policy statement (3-5 sentences).",
        },
        "dissents": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Every losing argument worth preserving, one per item.",
        },
    },
    "required": ["rate_path", "statement", "dissents"],
    "additionalProperties": False,
}


# ----------------------------------------------------------------------------
# Backends: the real frontier model, or a labelled deterministic stub.
# ----------------------------------------------------------------------------
class ModelBackend:
    """Calls a frontier model and forces a structured tool response."""

    name = MODEL

    def __init__(self):
        import anthropic  # imported lazily so the stub path needs no install

        self.client = anthropic.Anthropic()

    def invoke(self, system: str, user: str, tool_name: str, schema: dict) -> dict:
        resp = self.client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=[
                {
                    "name": tool_name,
                    "description": "Submit your structured response.",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
            messages=[{"role": "user", "content": user}],
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == tool_name:
                return dict(block.input)
        raise RuntimeError(f"{tool_name}: model returned no tool call")


class StubBackend:
    """
    A deterministic stand-in so the full loop runs with no API key. It is NOT a
    model: it grid-searches the same kind of path a sensible committee would
    consider and labels every rationale [STUB] so no one mistakes it for real
    reasoning. Its only job is to exercise the pipeline end to end.
    """

    name = "STUB (no model; deterministic)"

    def invoke(self, system: str, user: str, tool_name: str, schema: dict) -> dict:
        state = self._state  # set by the committee before each call

        if tool_name == "submit_proposal":
            # Lean against the inflation gap, then drift toward neutral -- the
            # same shape objective.py's own candidates explore.
            neutral = NEUTRAL_REAL_RATE + INFLATION_TARGET
            gap = state.inflation - INFLATION_TARGET
            first = max(0.0, round(state.policy_rate + 0.5 * gap, 2))
            drift = round((first + neutral) / 2, 2)
            return {
                "rate_path": [first, drift, drift, drift],
                "assumption": "Inflation gap is partly demand-driven and worth "
                "leaning against.",
                "rationale": "[STUB] Lean against the inflation gap on the first "
                "move, then drift halfway to neutral as it cools.",
            }

        if tool_name == "submit_critique":
            return {
                "challenges": [
                    "[STUB] The reduced-form model may overstate how fast the "
                    "Phillips curve responds; the win could be model-fragile.",
                ],
                "fatal": False,
                "summary": "[STUB] Plausible but model-dependent; adopt with a "
                "watch on realised inflation.",
            }

        # submit_decision (Chair)
        return {
            "rate_path": list(self._leader_path),
            "statement": "[STUB] The Committee adopts the leading scored path, "
            "leaning gently against inflation while protecting employment and "
            "moving gradually.",
            "dissents": [
                "[STUB] The financial-stability view preferred an even smaller "
                "first move on gradualism grounds.",
            ],
        }


def select_backend():
    force_stub = os.environ.get("FED_FORCE_STUB") == "1"
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if force_stub or not has_key:
        if not has_key and not force_stub:
            print(
                "No ANTHROPIC_API_KEY found -> running the labelled STUB backend.\n"
                "Set ANTHROPIC_API_KEY to run the real frontier-model committee.\n",
                file=sys.stderr,
            )
        return StubBackend()
    try:
        return ModelBackend()
    except ImportError:
        print(
            "The 'anthropic' package is not installed -> falling back to the STUB.\n"
            "Install it with:  pip install anthropic   (or: uv add anthropic)\n",
            file=sys.stderr,
        )
        return StubBackend()


# ----------------------------------------------------------------------------
# Helpers.
# ----------------------------------------------------------------------------
def _coerce_path(raw) -> list[float]:
    """Normalise a model-proposed path to HORIZON non-negative rounded floats."""
    try:
        path = [max(0.0, round(float(x), 3)) for x in raw]
    except (TypeError, ValueError):
        raise ValueError(f"un-parseable rate_path: {raw!r}")
    if not path:
        raise ValueError("empty rate_path")
    if len(path) < HORIZON:
        path += [path[-1]] * (HORIZON - len(path))
    return path[:HORIZON]


def _state_brief(state: EconomyState) -> str:
    return (
        f"Current economy (EconomyState):\n"
        f"  PCE inflation        : {state.inflation}%\n"
        f"  unemployment         : {state.unemployment}%\n"
        f"  fed funds rate (now) : {state.policy_rate}%\n"
        f"  inflation expectations: {state.inflation_expectations}%"
    )


def _scoreboard(proposals: list[dict]) -> str:
    lines = ["Scored proposals so far (lower total_loss is better):"]
    for p in sorted(proposals, key=lambda x: x["score"]["total_loss"]):
        s = p["score"]
        lines.append(
            f"  [{p['persona']}] path={p['decision'].rate_path}  "
            f"total_loss={s['total_loss']}  "
            f"(terminal infl {s['terminal_inflation']}%, "
            f"unemp {s['terminal_unemployment']}%)"
        )
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# The committee.
# ----------------------------------------------------------------------------
@dataclass
class RunLog:
    model: str
    state: dict
    baseline: dict
    context: str = ""  # real-time signal context the committee was given, if any
    rounds: list = field(default_factory=list)
    red_team: dict = field(default_factory=dict)
    decision: dict = field(default_factory=dict)
    verdict: dict = field(default_factory=dict)


def run_committee(state: EconomyState, rounds: int = 2, backend=None,
                  extra_context: str | None = None, verbose: bool = True) -> RunLog:
    backend = backend or select_backend()
    say = print if verbose else (lambda *a, **k: None)
    if isinstance(backend, StubBackend):
        backend._state = state

    baseline = taylor_rule(state)
    base_score = score(state, baseline)

    log = RunLog(
        model=backend.name,
        state=asdict(state),
        baseline={"rate_path": baseline.rate_path, "score": base_score},
        context=extra_context or "",
    )

    # Real-time signal context, given only to the "fresh" committee.
    ctx = ""
    if extra_context:
        ctx = (
            "\n\nReal-time signals available to you right now. These LEAD the "
            "official data above, which is lagged and subject to revision. Weigh "
            "whether they imply conditions differ from the stale official print:\n"
            + extra_context
        )

    say("=== Agentic Fed Task Force :: live committee ===")
    say(f"Backend: {backend.name}\n")
    say(_state_brief(state))
    if extra_context:
        say(ctx)
    say(
        f"\n[BASELINE] Taylor rule {baseline.rate_path}  "
        f"total_loss={base_score['total_loss']}  (the bar to beat)\n"
    )

    # --- Steps 2-4: propose, score, deliberate ------------------------------
    latest: dict[str, dict] = {}  # persona -> most recent scored proposal
    for r in range(rounds):
        say(f"--- Deliberation round {r + 1}/{rounds} ---")
        round_record = []
        board = list(latest.values())  # snapshot the board from the prior round

        for key, name, charter in PROPOSERS:
            system = (
                f"You are the {name} on an agentic FOMC committee.\n{charter}\n\n"
                f"{OBJECTIVE_BRIEF}\n\n{OPERATING_DISCIPLINE}"
            )
            user = _state_brief(state) + ctx + (
                f"\n\nThe Taylor (1993) baseline path is {baseline.rate_path} "
                f"with total_loss {base_score['total_loss']}. You must try to beat it."
            )
            if r > 0 and board:
                user += (
                    "\n\n" + _scoreboard(board) +
                    "\n\nRevise your proposal in light of the board. If a simpler "
                    "path scores as well as a complex one, prefer the simple one."
                )
            else:
                user += "\n\nPropose your rate path now."

            if isinstance(backend, StubBackend):
                backend._state = state
            raw = backend.invoke(system, user, "submit_proposal", _PROPOSAL_SCHEMA)
            try:
                path = _coerce_path(raw["rate_path"])
            except ValueError as e:
                say(f"  [{name}] invalid proposal ({e}); skipping this round.")
                continue
            decision = PolicyDecision(
                rate_path=path,
                rationale=raw.get("rationale", ""),
            )
            s = score(state, decision)
            entry = {
                "persona": name,
                "decision": decision,
                "assumption": raw.get("assumption", ""),
                "score": s,
            }
            latest[key] = entry
            round_record.append(
                {
                    "persona": name,
                    "rate_path": path,
                    "assumption": entry["assumption"],
                    "rationale": decision.rationale,
                    "score": s,
                }
            )
            beat = "beats baseline" if s["total_loss"] < base_score["total_loss"] else "worse than baseline"
            say(f"  [{name}] {path}  total_loss={s['total_loss']}  ({beat})")
        log.rounds.append(round_record)
        say("")

    if not latest:
        raise RuntimeError("no valid proposals were produced")

    # --- Step 5: red-team the leader ----------------------------------------
    leader = min(latest.values(), key=lambda e: e["score"]["total_loss"])
    say(
        f"--- Red-team (Skeptic) attacks the leader: [{leader['persona']}] "
        f"{leader['decision'].rate_path}  total_loss={leader['score']['total_loss']} ---"
    )
    skeptic_system = (
        "You are the Skeptic / red-team on an agentic FOMC committee. You do NOT "
        "propose. Your only job is to break the leading proposal before it is "
        "adopted: wrong assumptions, fragile model dependence, tail risks, "
        "credibility costs. A proposal that cannot survive you is not adopted.\n\n"
        + OBJECTIVE_BRIEF
    )
    skeptic_user = (
        _state_brief(state)
        + ctx
        + f"\n\nLeading proposal from the {leader['persona']}:\n"
        + f"  path={leader['decision'].rate_path}\n"
        + f"  assumption: {leader['assumption']}\n"
        + f"  rationale: {leader['decision'].rationale}\n"
        + f"  scored total_loss: {leader['score']['total_loss']} "
        + f"(terminal inflation {leader['score']['terminal_inflation']}%, "
        + f"unemployment {leader['score']['terminal_unemployment']}%)\n\n"
        + "Attack it. Mark `fatal` true only if it should not be adopted as-is."
    )
    if isinstance(backend, StubBackend):
        backend._state = state
        backend._leader_path = leader["decision"].rate_path
    crit = backend.invoke(skeptic_system, skeptic_user, "submit_critique", _SKEPTIC_SCHEMA)
    log.red_team = {"target": leader["persona"], **crit}
    for c in crit.get("challenges", []):
        say(f"  - {c}")
    say(f"  fatal: {crit.get('fatal')}  | {crit.get('summary', '')}\n")

    # --- Step 6: Chair decides and logs -------------------------------------
    say("--- Chair synthesises the decision ---")
    chair_system = (
        "You are the Chair of an agentic FOMC committee. You own the final "
        "synthesis and the public statement, optimising for the mandate over the "
        "whole path, not just the current quarter. You may adopt a proposal as-is "
        "or blend them, but justify any move away from the lowest-scoring path.\n\n"
        + OBJECTIVE_BRIEF
        + "\n\nDo not hide a dissent: preserve every losing argument worth keeping."
    )
    chair_user = (
        _state_brief(state)
        + ctx
        + "\n\n"
        + _scoreboard(list(latest.values()))
        + f"\n\nTaylor baseline: {baseline.rate_path} total_loss {base_score['total_loss']}."
        + "\n\nThe Skeptic's challenge to the leader:\n"
        + f"  fatal={crit.get('fatal')}; {crit.get('summary', '')}\n"
        + "\n".join(f"  - {c}" for c in crit.get("challenges", []))
        + "\n\nDecide the final path and write the statement."
    )
    if isinstance(backend, StubBackend):
        backend._state = state
        backend._leader_path = leader["decision"].rate_path
    raw_dec = backend.invoke(chair_system, chair_user, "submit_decision", _CHAIR_SCHEMA)

    final_path = _coerce_path(raw_dec["rate_path"])
    final = PolicyDecision(rate_path=final_path, rationale=raw_dec.get("statement", ""))
    final_score = score(state, final)

    beat_baseline = final_score["total_loss"] < base_score["total_loss"]
    survived = not crit.get("fatal", False)
    success = beat_baseline and survived

    log.decision = {
        "rate_path": final_path,
        "statement": raw_dec.get("statement", ""),
        "dissents": raw_dec.get("dissents", []),
        "score": final_score,
    }
    log.verdict = {
        "beat_baseline": beat_baseline,
        "survived_red_team": survived,
        "success": success,
        "final_total_loss": final_score["total_loss"],
        "baseline_total_loss": base_score["total_loss"],
    }

    say(f"  Final path : {final_path}")
    say(f"  total_loss : {final_score['total_loss']}  "
        f"(baseline {base_score['total_loss']})")
    say(f"  Statement  : {raw_dec.get('statement', '')}")
    if raw_dec.get("dissents"):
        say("  Dissents preserved:")
        for d in raw_dec["dissents"]:
            say(f"    - {d}")

    say("\n--- VERDICT (program.md success criterion) ---")
    say(f"  beat Taylor baseline : {beat_baseline}")
    say(f"  survived the red-team: {survived}")
    say(f"  SUCCESS              : {success}")

    return log


def _write_log(log: RunLog) -> Path:
    runs = Path(__file__).parent / "runs"
    runs.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = runs / f"committee-{stamp}.json"
    # PolicyDecision objects are not JSON-serialisable; the log already stores
    # plain dicts for everything that leaves this module, so dump directly.
    path.write_text(json.dumps(asdict(log), indent=2, default=str), encoding="utf-8")
    return path


if __name__ == "__main__":
    # Calibrated to the June 2026 setting used throughout the repo.
    today = EconomyState(
        inflation=3.1,
        unemployment=4.0,
        policy_rate=3.625,
        inflation_expectations=2.6,
    )
    result = run_committee(today, rounds=2)
    log_path = _write_log(result)
    print(f"\nFull transcript logged to: {log_path}")
