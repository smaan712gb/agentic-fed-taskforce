# Agentic Fed Task Force

A decision-support and red-team sandbox for the Federal Reserve's dual mandate, inspired by the structure of the task forces Chair Kevin Warsh announced on June 17, 2026, and built on two patterns from Andrej Karpathy's 2026 open-source work: the `autoresearch` hill-climbing loop and the `andrej-karpathy-skills` agent discipline.

This repository is the wedge-first proof of one narrow, falsifiable claim: **the Fed decides on stale data, and being current would change and improve decisions.**

## What is here

| File | Role |
| --- | --- |
| `objective.py` | The dual-mandate loss function and a Taylor-rule baseline. The single hard metric, the `val_bpb` analog. |
| `nowcast.py` | The freshness layer: an illustrative economy, a lagged "official" view, and a current nowcast, with marked real-data swap points. |
| `backtest.py` | The keystone experiment: same committee, stale data vs. fresh data, with structural no-look-ahead. |
| `committee.py` | The agent layer: real frontier-model personas run one full deliberation cycle (propose, score, deliberate, red-team, decide) against `objective.py`, with a logged transcript. |
| `data_real.py` | The real-data layer: FRED realized truth, ALFRED release-and-revision vintages, and FMP real-time financial signals — the three `# SWAP POINT`s, made live. |
| `backtest_real.py` | The keystone experiment on **real** data with the **real** committee: stale official vintage vs. the same committee also given real-time signals, scored against realized outcomes, with multi-run averaging. |
| `config.py` | Loads `.env` and trusts the OS certificate store so HTTPS works behind a corporate proxy. |
| `program.md` | The agentic committee charter, in the `autoresearch` style. |
| `Agentic-Fed-Taskforce-Blueprint.md` | The full design, architecture, and build strategy. |
| `EXPERIMENT.md` | What the synthetic experiment proves and does not. |
| `FINDINGS.md` | The real-data result: what the live pilot showed, honestly. |
| `tests/` | Unit tests for the objective, the no-look-ahead guarantee, and the committee loop. |

## Quickstart

With [uv](https://docs.astral.sh/uv/):

```bash
uv run objective.py     # see the objective rank candidate decisions
uv run nowcast.py       # see the freshness layer on illustrative data
uv run backtest.py      # run the keystone experiment and print the scorecard
uv run committee.py     # run one live deliberation cycle of the agent committee
```

The committee runs on a frontier model (Claude Opus 4.8 by default) when
`ANTHROPIC_API_KEY` is set:

```bash
export ANTHROPIC_API_KEY=...     # then:
uv run --extra agent committee.py
```

Without a key it runs a clearly-labelled deterministic stub of the same loop, so
the pipeline is demonstrable with no install and no key. Every run writes a full
transcript (proposals, scores, the red-team challenge, the decision, dissents,
and the verdict) to `runs/`.

With a plain virtual environment (the core needs only the standard library):

```bash
python objective.py
python nowcast.py
python backtest.py
```

Run the tests:

```bash
uv run --extra dev pytest
# or: pip install pytest && pytest
```

## Running it on real data

The synthetic swap points are now implemented live in `data_real.py`:

1. **Realized truth** — FRED latest-vintage core PCE, unemployment, fed funds (the judge).
2. **Stale official view** — ALFRED vintage *as known on each historical date* (the real publication lag and first-release values fall out of the vintage query — no synthetic noise).
3. **Real-time signal** — the FMP Treasury yield curve, its slope, level, and momentum, available on that same date and never revised.

Set up keys in `.env` (copy the format already there), then:

```bash
# .env needs: ANTHROPIC_API_KEY, FRED_API_KEY (free), FMP_API_KEY
uv run --extra data python config.py          # self-test: keys + connectivity
uv run --extra data python data_real.py       # self-test: real vintages vs. truth
uv run --extra data python backtest_real.py   # the real experiment

# average out model run-to-run noise (recommended):
FED_BACKTEST_RUNS=3 uv run --extra data python backtest_real.py
```

A free FRED key is instant ([request one here](https://fred.stlouisfed.org/docs/api/api_key.html));
it also unlocks the ALFRED vintages. `config.py` trusts your OS certificate
store, so it works behind a corporate TLS proxy.

## The result

On illustrative **synthetic** data, the fresh committee improves the average outcome by ~8% and changes the decision about two-thirds of the time, with the value concentrated at shocks and turning points (see `EXPERIMENT.md`).

On **real** data with the **real** committee, the honest finding is different and more useful: a naive real-time signal is **not** a free edge — see `FINDINGS.md` for the full, unspun result. The point the pilot establishes is the *machinery*: a working, transparent, reproducible path from real-time signal to scored policy decision, with no look-ahead.

## Scope and honesty

This is a sandbox, not a forecast of the economy, and it is decision-support, not a replacement for the FOMC. The reduced-form model is good enough to rank competing decisions and to expose where the Fed's lag costs it, no more. Read the risks section of the blueprint before drawing strong conclusions.

## License

MIT. See `LICENSE`.
