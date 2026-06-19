# Pre-registration

Fixed **before** running the real-data backtest, to remove researcher degrees of
freedom. A referee should be able to confirm that the dates, signals, metric, and
arms below were committed in advance (git history dates this file), not chosen
after seeing which combination looked best.

## Hypothesis

Holding the committee's reasoning constant, giving it a **real-time, leading,
exogenous** signal set on top of the lagged official data improves its policy
decisions, judged against the realized state, relative to the same committee
seeing only the lagged official data.

## Decision dates (pre-registered, regime-spanning)

```
2022-06-15  2022-09-21  2022-12-14  2023-03-22  2023-07-26
2023-09-20  2023-12-13  2024-03-20  2024-06-12  2024-09-18
```

Chosen to span aggressive hiking, banking stress (SVB), the extended hold, the
dovish pivot, and the first cuts. All have realized data available as of the run.

## Signal set (pre-registered)

The **leading/exogenous** set (`FED_SIGNAL_MODE=leading`): initial jobless claims
(`ICSA`), Indeed job postings (`IHLIDXUS`), high-yield and investment-grade credit
spreads (`BAMLH0A0HYM2`, `BAMLC0A0CM`), broad dollar (`DTWEXBGS`), WTI and Henry
Hub (`DCOILWTICO`, `DHHNGSP`), VIX (`VIXCLS`), and inflation-expectation series
(`MICH`, `T5YIFR`). The endogenous Treasury-curve set is retained only as a
labeled comparison (`FED_SIGNAL_MODE=curve`).

**Prior result that motivated the switch (disclosed):** an earlier run used the
Treasury yield curve and found no edge. We switched to the leading set because the
curve is endogenous (it embeds the market's forecast of Fed policy). That switch
is the one researcher choice made after seeing a result; everything in this file
is fixed going forward.

## Metric (pre-registered)

Mean realized `total_loss` across dates from `objective.py` (dual-mandate
quadratic loss + rate-smoothness penalty). Lower is better. Secondary: per-date
winner, by-run win tally, and three-arm "best of three."

## Arms (pre-registered)

1. **Stale committee** — sees only the ALFRED official vintage as known on the date.
2. **Fresh committee** — same, plus the leading signal set.
3. **Fed actual** — the FOMC's realized funds-rate path over the next four
   quarters (observed, not modeled), scored identically.

## Runs and seed

`runs/date = 2` (averages model run-to-run noise; the committee is stochastic and
has no temperature/seed control on the model). `objective.py` and the sampling in
`backtest.py` use fixed seeds; the agentic committee does not, so exact committee
losses are not bit-reproducible — see the reproducibility note in `FINDINGS.md`.

## Loud caveat (pre-committed)

The objective **re-simulates** each path from the realized state; it does **not**
observe post-decision macro outcomes. Results are a **model-internal ranking**,
not a measurement of reality. "Beating the Fed" in this metric reflects the
objective's own neutral-rate/calibration assumptions and is **not** evidence the
committee would do better in the real economy. This is an illustrative pilot.
