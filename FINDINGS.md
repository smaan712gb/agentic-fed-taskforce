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

## The honest reading

**A naive real-time signal is not a free edge.** The damage concentrates at
2023-07-26: the fresh committee saw the deeply inverted yield curve, read it as
a recession warning, and eased into still-hot inflation — and got punished. The
curve cried wolf, and the committee that trusted it underperformed.

There is a deeper, structural reason, and it is the most important finding here:

> **The Treasury yield curve is the wrong kind of signal.** It already embeds the
> market's forecast of what the Fed will do, so feeding it back into the Fed's own
> decision is partly circular. It is a noisy, endogenous mirror of policy
> expectations — not a leading read on the real economy. That is very likely why
> there was "no edge."

This is a more useful result than a manufactured win. It says the freshness
thesis is not refuted — it was tested with the wrong instrument.

## What changed in response (now in the repo)

1. **Inflation expectations are now real** — the 5-year TIPS breakeven (`T5YIE`),
   not the old `0.5*inflation + 0.5*anchor` placeholder.
2. **The signal set is now leading and exogenous** — weekly jobless claims
   (`ICSA`), Indeed job postings (`IHLIDXUS`), credit spreads, the dollar, oil,
   and VIX: series that move *before* the official prints and are not chiefly a
   forecast of Fed policy. See `DATA-SOURCES.md`.
3. **The committee now sees a real dashboard** — labor depth, financial
   conditions, activity, and the balance sheet — instead of three numbers.

## What is proven, and what is not

- **Proven:** a working, transparent, reproducible, no-look-ahead path from
  real-time signal to scored policy decision, on real data, with a real agentic
  committee — and an honest measurement that a circular signal does not help.
- **Not proven:** that the *right* (leading, exogenous) signals deliver an edge.
  That is the next experiment (build-order item 5 in `DATA-SOURCES.md`), now that
  the leading-signal layer exists.

## Scope and honesty

Four dates is a pilot, not a verdict. The reduced-form objective ranks decisions;
it is not the economy. This system is decision-support and a red-team — a tool to
run alongside the FOMC and make its reasoning legible and measurable — not a
replacement for it. Read `Agentic-Fed-Taskforce-Blueprint.md` §7 before drawing
strong conclusions.
