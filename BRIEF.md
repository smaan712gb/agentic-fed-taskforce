# Agentic Fed Task Force — one-page brief

> **Independent and unsolicited.** Not affiliated with, sponsored by, or endorsed
> by the Federal Reserve. The name is descriptive, not official.

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

**The honest finding (pre-registered, n = 10, robustness-checked).** Across ten
real FOMC dates spanning aggressive hiking, the SVB stress, the hold, the pivot,
and the first cuts, giving the committee a real-time leading-indicator signal set
(jobless claims, job postings, credit spreads, the dollar, energy, volatility) on
top of the lagged official data **did not help** — it was **16% worse** on
average, with the damage concentrated in the volatile 2022 hiking phase. That
result is robust: it holds across the full plausible range of the model's
structural constants (r\*, u\*, the Phillips and Okun slopes, the employment
weight) — not a calibration artifact. An earlier four-date hint that real-time
signals win at turning points **did not replicate and is retracted**. Both
committees score better than the Fed's actual path under our objective on every
date, but that is a **model-internal** ranking (the objective rewards faster
normalization than the Fed chose), **not** a real-world claim. The robust, honest
read: *simply showing a committee more real-time data does not improve policy when
the reasoning is held fixed* — and we report that straight.

**What the numbers are — read this.** The objective *re-simulates* each rate path
from the realized state; it does **not** observe post-decision macro outcomes. So
results are a **model-internal ranking on an illustrative pilot**, not a
measurement of reality. The experiment includes the Fed's actual decision as a
third arm for an apples-to-apples comparison, but a committee "beating the Fed" in
this metric reflects the objective's own neutral-rate calibration — it is **not**
evidence the committee would do better in the real economy. Dates and signals are
**pre-registered** (`PRE-REGISTRATION.md`).

**Why this is credible rather than a demo.** Every data series is verified live;
no inputs are faked (inflation expectations use real TIPS breakevens, not a
formula); no-look-ahead is structural, not promised; the metric is fixed and
public; the backend model is **swappable** (the committee runs on Claude today,
but the runtime is an interface, not a dependency); and results are reported
honestly, including when the signal does not help. The full target data dashboard
— exact series IDs, what leads vs. mirrors policy, an honest free/paid tiering —
is in `DATA-SOURCES.md`.

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
