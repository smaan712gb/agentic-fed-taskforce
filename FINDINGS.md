# Findings — the real-data pilot

**What this is.** An end-to-end run of the system on *real* data with the *real*
frontier-model committee: live FRED realized history, genuine ALFRED
release-and-revision vintages, and a real-time signal set — scored against what
the economy actually did. Dates and signals were **pre-registered**
(`PRE-REGISTRATION.md`) before this run.

> **Read this first.** The objective *re-simulates* each rate path from the
> realized state; it does **not** observe post-decision inflation and employment.
> Every number below is a **model-internal ranking on an illustrative pilot**, not
> a measurement of reality. "Beating the Fed" here means "scores better under our
> loss function," which embeds a view of optimal policy — it is **not** evidence
> the committee would do better in the real economy.

## The experiment

At **10 pre-registered FOMC dates** (2022-06 through 2024-09, spanning aggressive
hiking, SVB stress, the hold, the pivot, and the first cuts), three arms decide:

1. **Stale committee** — sees only the ALFRED official vintage as known that day.
2. **Fresh committee** — same, plus the real-time leading signal set (jobless
   claims, job postings, credit spreads, the dollar, energy, volatility).
3. **Fed actual** — the FOMC's realized funds-rate path over the next four
   quarters (observed, not modeled), scored identically.

No look-ahead is structural. Each committee runs twice per date (n = 20 pairs) to
average model noise.

## Result (n = 10, 3 arms)

| Date | Regime | Stale | Fresh | Fed | Best |
| --- | --- | ---: | ---: | ---: | --- |
| 2022-06-15 | +75bp shock | 19.88 | 26.11 | 61.69 | stale |
| 2022-09-21 | hiking | 24.56 | 28.39 | 43.92 | stale |
| 2022-12-14 | hiking slows | 11.68 | 12.42 | 17.81 | stale |
| 2023-03-22 | SVB stress | 9.90 | 11.56 | 13.53 | stale |
| 2023-07-26 | final hike | 6.47 | 6.72 | 7.07 | stale |
| 2023-09-20 | hold begins | 3.30 | 3.51 | 3.61 | stale |
| 2023-12-13 | dovish pivot | 2.12 | 2.11 | 4.05 | fresh |
| 2024-03-20 | sticky hold | 2.78 | 2.25 | 3.89 | fresh |
| 2024-06-12 | hold | 1.21 | 1.92 | 5.71 | stale |
| 2024-09-18 | first cut | 1.14 | 1.35 | 3.33 | stale |

- Mean realized loss — **stale 8.31, fresh 9.63, Fed 16.46**.
- **Fresh is 16% worse than stale.** By-date: stale 8, fresh 2. Best-of-three:
  stale 8 / fresh 2 / Fed 0.

## Robustness (sensitivity sweep, no model calls)

Re-scoring every arm's chosen path under perturbed structural constants —
`r*` in [0.25, 1.5], `u*` in [3.8, 4.6], employment weight in [0.5, 2.0],
Phillips slope in [0.15, 0.45], Okun in [0.3, 0.7]:

- **"Fresh is worse than stale" holds in 100%** of the Monte-Carlo parameter space
  and never flips one-at-a-time. The result is **not** an artifact of the
  calibration.
- **"Both committees beat the Fed (in-model)" also holds in 100%** — robust, but
  still model-internal (see caveat).

## The honest reading

**The freshness thesis does not hold in this pilot — robustly.** Giving the
committee real-time leading indicators on top of the lagged official data did not
improve and modestly *degraded* its decisions (−16%), and that survives both more
dates and the sensitivity sweep. The damage concentrates in the **high-volatility
2022 hiking phase**, where the extra signals amplified over-reaction. The refined
lesson: *more information is not better policy when the reasoning is held fixed* —
simply showing a committee real-time data does not realize its value, and can hurt
when the signals are noisy and the regime is turning fast.

**Correction, stated plainly.** An earlier 4-date run suggested "leading signals
win the turning point (2023-07-26)." That **did not replicate** at n = 10 — stale
wins that date now. The turning-point flip was small-sample noise. This is exactly
why n = 4 was labeled a pilot, and why this run was pre-registered.

**On the Fed comparison.** Both committees score better than the Fed's actual path
under this objective, on every date, robustly. We do **not** claim the committee
would have done better in reality. The objective rewards paths that move toward
neutral faster than the Fed chose to; the Fed weighed financial stability,
credibility, and data this two-equation model does not contain. The comparison is
included for completeness and apples-to-apples scoring — not as a "beats the Fed"
result.

## What is proven, and what is not

- **Proven:** a working, transparent, reproducible, no-look-ahead, pre-registered
  pipeline from real-time signal to scored policy decision, on real data, with a
  real agentic committee and the Fed's own decision as a benchmark; real (not
  faked) inputs; and a **robust** honest finding that this real-time signal set
  does not help.
- **Not proven:** anything about real-world outcomes. The evaluation is
  model-internal (a counterfactual rate path has no observed outcome). Validating
  the objective against an established small New Keynesian model, scoring the
  Fed's *actual* path against *actual* realized macro, and a cross-model committee
  run are the next steps (see `DATA-SOURCES.md` and the audit trail).

## Scope and honesty

Ten dates and one model is a pilot, not a verdict. The reduced-form objective
ranks decisions; it is not the economy. This is decision-support and a red-team —
a tool to make policy reasoning legible and measurable — not a replacement for the
FOMC, and not affiliated with the Federal Reserve.
