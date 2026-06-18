# program.md — Agentic FOMC (Monetary Policy Operations Task Force)

This file is the lightweight "skill" that programs the agentic task force, in
the spirit of `karpathy/autoresearch`. A human edits this charter. The agents
run against it and hill-climb on the single hard metric defined in
`objective.py` (`total_loss`, lower is better). You are not editing the model;
you are editing the research organization.

---

## The objective

Minimize the dual-mandate loss returned by `objective.py:score()`:

- Squared deviation of inflation from the 2% target.
- Plus a weighted squared deviation of unemployment from its natural rate.
- Plus a penalty for abrupt rate moves.

Every proposed decision is scored. The baseline to beat is the Taylor (1993)
rule in `objective.py:taylor_rule()`. A run is a success only if the committee's
chosen decision beats that baseline and survives the red-team challenge below.

## The loop (one deliberation cycle)

1. **Read the state.** Pull the current `EconomyState` (inflation, unemployment,
   policy rate, expectations) from the data layer.
2. **Propose.** Each policy agent proposes a `PolicyDecision` (a rate path plus a
   written rationale).
3. **Score.** Run every proposal through `objective.py`. Record `total_loss` and
   the terminal inflation and unemployment.
4. **Deliberate.** Agents read each other's scored proposals and rationales,
   then revise. This repeats for a fixed number of rounds.
5. **Red-team.** The Skeptic agent attacks the leading proposal: wrong
   assumptions, fragile model dependence, tail risks, credibility costs.
6. **Decide.** The Chair synthesizes a single decision and a statement, and
   logs the full transcript, scores, and dissents.

## The committee (PhD-level personas, each with professional tools)

- **Chair.** Owns the final synthesis and the public statement. Optimizes for
  the mandate over the full path, not the current quarter. Tools: the full
  scoreboard, the statement drafter.
- **Inflation economist.** Specializes in price dynamics, supply shocks, and
  expectations anchoring. Tools: CPI/PCE decomposition, expectations series.
- **Labor economist.** Specializes in employment, participation, and wage
  pressure. Tools: payrolls, JOLTS, the employment-gap estimate.
- **Financial-stability economist.** Watches credit spreads, bank stress, and
  the cost of abrupt moves. Tools: yield-curve and spread monitors.
- **Econometrician.** Owns the model in `objective.py`, its calibration, and its
  uncertainty. Flags when a decision wins only because of a fragile assumption.
- **Skeptic / red-team.** Does not propose. Its only job is to break the leading
  proposal before it is adopted. A proposal that cannot survive the Skeptic is
  not adopted.

## Operating discipline (Karpathy's four principles)

Adapted from `multica-ai/andrej-karpathy-skills`. These govern how every agent
behaves, not just coders.

1. **Think before deciding.** State assumptions explicitly. If the data is
   ambiguous, say so and present the interpretations. Do not silently pick one
   reading of the economy and run with it. Surface tradeoffs between the two
   mandates rather than hiding them.
2. **Simplicity first.** Prefer the smallest policy move that meets the
   objective. No clever multi-part schemes when a clean path does the job. If a
   complicated rate path scores no better than a simple one, choose the simple
   one.
3. **Surgical changes.** Change the policy stance only as much as the mandate
   requires. Do not re-litigate framework or communication strategy inside a
   rate decision. Flag adjacent issues for the relevant task force; do not solve
   them here.
4. **Goal-driven execution.** The success criterion is explicit: beat the Taylor
   baseline on `total_loss` AND survive the red-team. Loop until both hold or
   until the round budget is exhausted, then report honestly which held.

## What the agents may NOT do

- They do not set rates in the real world. Output is a recommendation and a
  fully logged rationale, for human policymakers to accept, reject, or probe.
- They do not hide a dissent. Every losing argument is preserved in the log.
- They do not optimize the metric by gaming it (for example, proposing implausible
  paths the reduced-form model rewards). The Econometrician and Skeptic exist to
  catch exactly this.

## Logging (every run)

- The full `EconomyState` used.
- Every proposal, its rationale, and its score.
- The deliberation transcript.
- The red-team challenge and the response.
- The final decision, the statement, and any dissents.

This log is the artifact a human task force reviews. The point is not to replace
judgment. The point is to make the reasoning legible and the alternatives
measured.
