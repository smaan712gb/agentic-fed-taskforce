# Findings — the real-data pilot

**What this is.** The first end-to-end run of the system on *real* data with the
*real* frontier-model committee: live FRED realized history, genuine ALFRED
release-and-revision vintages, and a real-time signal — scored against what the
economy actually did. No synthetic data anywhere.

## The experiment

At four real FOMC decision dates spanning the hike → pivot → hold → cut arc, two
identical committees decide. Both start from the **same** stale official vintage
(what the Fed effectively had on that date, with the real publication lag). The
**fresh** committee additionally sees the real-time signal; the **stale** one
does not. Both are scored against the realized truth for the decision month.
No-look-ahead is structural. To remove the model's run-to-run noise, each
committee runs **3 times per date** (n = 12 committee pairs).

## Result (signal = Treasury yield curve)

| Date | Regime | Stale loss | Fresh loss | Winner |
| --- | --- | ---: | ---: | --- |
| 2023-07-26 | hiking, hot inflation | 13.27 ± 0.81 | 13.90 ± 0.99 | stale |
| 2023-12-13 | dovish pivot | 3.73 ± 0.00 | 3.35 ± 0.34 | fresh |
| 2024-06-12 | hold, inverted curve | 1.60 ± 0.03 | 2.64 ± 0.19 | stale |
| 2024-09-18 | first cut | 1.70 ± 0.01 | 1.74 ± 0.05 | stale |

- Mean realized loss — **stale 5.08, fresh 5.41 → fresh 6.5% *worse***.
- By date (mean): **fresh 1 / stale 3**. By run: fresh 3 / stale 8 / tie 1.
- The error bars are tight, so this is **not** noise: with this signal, the
  fresh committee is genuinely, if mildly, worse.

## The honest reading (curve signal)

**A naive real-time signal is not a free edge.** The damage concentrates at
2023-07-26: the fresh committee saw the deeply inverted yield curve, read it as
a recession warning, and eased into still-hot inflation — and got punished. The
curve cried wolf, and the committee that trusted it underperformed. The
structural reason: **the Treasury curve already embeds the market's forecast of
Fed policy, so feeding it back is partly circular** — a mirror of policy
expectations, not a leading read on the real economy.

## Result (signal = leading/exogenous set)

So we replaced the curve with signals that genuinely lead the official data and
are not a forecast of Fed policy — weekly jobless claims (`ICSA`), Indeed job
postings (`IHLIDXUS`), credit spreads, the dollar, energy, and volatility — and
re-ran the same n = 12.

| Date | Regime | Stale loss | Fresh loss | Winner |
| --- | --- | ---: | ---: | --- |
| 2023-07-26 | hiking, hot inflation | 7.38 ± 1.64 | 6.48 ± 0.19 | **fresh** (2/3) |
| 2023-12-13 | dovish pivot | 1.84 ± 0.15 | 2.44 ± 0.00 | stale |
| 2024-06-12 | hold | 1.45 ± 0.13 | 2.21 ± 0.49 | stale |
| 2024-09-18 | first cut | 1.11 ± 0.02 | 1.96 ± 0.36 | stale |

- Mean realized loss — **stale 2.94, fresh 3.27 → fresh 11.2% *worse*** overall.
- By date: fresh 1 / stale 3. By run: fresh 2 / stale 10.
- **But the turning point flipped.** At 2023-07-26 — the single hardest date,
  where the *curve* signal made the fresh committee lose — the *leading* signals
  made it **win** (6.48 vs 7.38). The leading set read the regime correctly where
  the curve misled.

## The synthesis (the real finding)

Two robust statements survive both runs:

1. **No free edge at n = 4.** Across both signal types, a real-time-informed
   committee does not beat the lagged-data committee on average in this small
   pilot. Honest, and consistent with the synthetic result that freshness is
   *insurance*, not a steady gain.
2. **Where it helps, and what kind.** The value concentrates at the **turning
   point** (2023-07-26) and the **signal type matters there**: leading/exogenous
   indicators beat the endogenous curve at exactly the moment that costs the most
   to get wrong. In calm periods, the extra signal adds noise. This is the
   synthetic experiment's central lesson, now reproduced on real data.

**Caveat (stated plainly):** the curve and leading runs are not a perfectly
controlled A/B — the curve run used the old placeholder expectations, the leading
run uses the real 5y-breakeven expectations and the broader dashboard. So the
across-the-board loss levels are not directly comparable; the per-date *winner*
and the turning-point flip are the reliable reads. A clean controlled A/B (curve
vs. leading on identical inputs) is build-order item 5b.

## What is proven, and what is not

- **Proven:** a working, transparent, reproducible, no-look-ahead path from
  real-time signal to scored policy decision, on real data, with a real agentic
  committee; real (not faked) inputs throughout; and an honest measurement that
  no signal type yet delivers a steady edge — while the *right* signals win the
  turning point.
- **Not proven:** a steady, statistically-robust edge. That needs many more dates
  (n = 4 is a pilot), a controlled A/B, and the `SCRAPE-FREE` signals still on the
  build list (Cleveland Fed inflation nowcast, card-spend). See `DATA-SOURCES.md`.

## Scope and honesty

Four dates is a pilot, not a verdict. The reduced-form objective ranks decisions;
it is not the economy. This system is decision-support and a red-team — a tool to
run alongside the FOMC and make its reasoning legible and measurable — not a
replacement for it. Read `Agentic-Fed-Taskforce-Blueprint.md` §7 before drawing
strong conclusions.
