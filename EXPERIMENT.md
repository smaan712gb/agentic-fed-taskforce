# Keystone Experiment: does stale data cost the Fed?

**What this is.** The first runnable end-to-end test of the project's central claim, that the Fed decides on lagging data and that being current would change and improve decisions. It is built wedge-first: one narrow, falsifiable question, proven cold, rather than the full system sketched at once.

## The design

The experiment isolates a single variable. Two committees use **identical reasoning** (the same optimizer choosing from the same menu of rate paths against the same dual-mandate objective). The **only** difference is what they are allowed to see:

- The **stale committee** sees the official data as the Fed effectively sees it: lagged by two months and blurred by revision noise.
- The **fresh committee** sees a current-dated nowcast, with no lag but its own honest uncertainty.

Both choose a rate path on each decision date. Both are then scored against the **true** state of the economy on that date, which neither could see when deciding. The judge is blind to both.

Everything was pre-registered before the run: the metric (mean realized loss, lower is better), the cadence (every six weeks, the FOMC rhythm), the window (the back half of the series, front half is warm-up), and the seed (fixed at 7). No-look-ahead is enforced structurally, not by promise: the stale committee literally cannot read the current month.

## The result (illustrative run)

| Readout | Value |
| --- | --- |
| Decision dates evaluated | 24 |
| Mean realized loss, stale | 0.681 |
| Mean realized loss, fresh | 0.628 |
| Improvement from freshness | +7.8% |
| Decisions changed by freshness | 16 of 24 (67%) |
| Per-date win tally (fresh / stale / tie) | 5 / 11 / 8 |

## The honest reading

The headline is that freshness improved the average outcome by about 8%, and it changed the actual decision two times out of three. But the per-date tally is the more important and more honest story: **the stale committee won more individual dates than the fresh one.** Fresh data won the experiment by winning big on the few dates that mattered most, above all the shock around month 92, where the stale committee scored 3.06 against the fresh committee's 1.23.

So the real finding is not "fresh data is always better." It is:

> The value of real-time data is concentrated at turning points and shocks. In calm periods the extra noise of a nowcast can slightly hurt. Freshness is insurance against being late when it is most expensive to be late.

That is a more credible claim than a clean sweep would have been, and it directly shapes the product: the nowcast layer earns its keep through the event-triggered alerts described in the blueprint, not by twitching at every quiet print.

## What this proves, and what it does not

- **It proves** the pipeline is sound: the objective, the nowcast, the committee, and the no-look-ahead backtest run together and produce a coherent, reproducible scorecard.
- **It does not prove** the real-world magnitude. The data is synthetic and clearly labeled. Any backtest where official data is lagged by construction will tend to favor freshness, so the synthetic number is a methodology check, not evidence.

## How to make it real (one swap)

The synthetic generator is isolated behind three functions in `nowcast.py`, each marked `# SWAP POINT`:

1. `generate_true_economy` becomes real realized history (FRED: PCE, unemployment, the funds rate).
2. `official_view` becomes the actual first-release-and-revision vintages (the ALFRED real-time database).
3. `nowcast_view` becomes fused real-time feeds (a real-time inflation source, card-spend, job postings).

Nothing else changes. Re-run `backtest.py` and the same scorecard now reports a real result. That is the next milestone worth funding.

## Files

- `objective.py` -- the dual-mandate metric and Taylor baseline.
- `nowcast.py` -- the freshness layer and the swap points.
- `backtest.py` -- the keystone experiment.
- `program.md` -- the agentic committee charter.
- `Agentic-Fed-Taskforce-Blueprint.md` -- the full design and strategy.
