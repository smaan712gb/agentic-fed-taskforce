# Agentic Fed Task Force — one-page brief

**What it is.** A working, fully transparent decision-support and red-team system
that mirrors the structure of the five task forces announced June 17, 2026. It is
**not** a replacement for the FOMC and makes no claim to beat it. It is a tool the
Fed (or outside researchers) can run alongside the human process to see what a
tireless, fully-logged, adversarially-tested committee would conclude, and why.

**The premise.** The dual mandate is already a loss function — squared deviations
of inflation from target plus weighted squared deviations of employment from full
employment. Once the objective is a hard, agreed metric, a committee's decisions
can be scored, replayed, and stress-tested. The system asks one falsifiable
question first: *the Fed decides on stale data — would being current change and
improve decisions?*

**What is built (and runnable today).**

- **A dual-mandate objective** (`objective.py`) — the single hard metric, plus a
  Taylor-rule baseline every proposal must beat. Agents never grade themselves.
- **A real agentic committee** (`committee.py`) — frontier-model personas
  (inflation, labor, financial-stability, econometrician), a Skeptic that
  red-teams the leading proposal, and a Chair that synthesizes a logged decision.
- **A real-data layer** (`data_real.py`) with no look-ahead: FRED realized truth,
  genuine ALFRED release-and-revision vintages (the real publication lag, not
  synthetic noise), and a real-time signal set.
- **A backtest** (`backtest_real.py`) that isolates one variable — the
  information set — and scores both committees against what the economy actually
  did, averaging over runs to remove model noise.

**The honest finding.** On real FOMC dates, the first signal tested — the
Treasury yield curve — gave **no edge** (the fresh committee was ~6.5% worse),
because the curve embeds the market's forecast of Fed policy and is therefore
partly circular. Replacing it with **leading, exogenous** indicators (weekly
jobless claims, job postings, credit spreads, the dollar, energy, volatility)
also showed no across-the-board edge in this 4-date pilot (~11% worse on
average) — **but the turning point flipped**: at the single hardest date
(July 2023, hot inflation), where the curve had made the fresh committee lose,
the leading indicators made it *win*. The robust, honest read: real-time data is
**insurance that pays off at turning points**, not a steady gain — and the *kind*
of signal matters most exactly when it matters most. This is the synthetic
experiment's lesson, reproduced on real data. Four dates is a pilot, not a
verdict; a larger, controlled study is the next step (`DATA-SOURCES.md`).

**Why this is credible rather than a demo.** Every data series is verified live;
no inputs are faked (inflation expectations use real TIPS breakevens, not a
formula); no-look-ahead is structural, not promised; the metric is fixed and
public; and the result is reported honestly, including when the signal does not
help. The full target data dashboard — with exact series IDs, what leads vs.
mirrors policy, and an honest free/paid tiering — is specified in
`DATA-SOURCES.md`.

**Fit with the five task forces.** The dual-mandate engine is the core (monetary
policy operations). The same charter-plus-metric pattern extends to the other
four: causes of inflation (supply/demand/expectations decomposition), productivity
and labor (employment-gap and r-star inputs), communications (statement clarity
and market-surprise prediction), and data sources (which inputs actually move
decisions). Each is a new charter and a new metric on the same loop.

**Honest limits.** The reduced-form objective ranks decisions; it is not the
economy. The current pilot is a handful of dates, not a verdict. This is
decision-support and a red-team, valued for transparency and tireless adversarial
testing — not authority.

**Reproduce it.** Public repository, MIT-licensed, runs from a clean checkout with
free/standard API keys: <https://github.com/smaan712gb/agentic-fed-taskforce>.
Every number in `FINDINGS.md` regenerates with one command.
