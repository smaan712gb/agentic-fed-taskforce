# The Agentic Fed Task Force

### A decision-support and red-team system for the Federal Reserve's policy process

**Status:** Design blueprint, v0.1
**Date:** June 17, 2026
**Author's framing:** A working counterpart to the human task forces Chair Kevin Warsh announced today, built to stress-test the Fed's reasoning rather than to replace it.

---

## 1. The opportunity

On June 17, 2026, at the conclusion of his first FOMC meeting as Chair, Kevin Warsh announced **five task forces** to review the Fed from first principles: monetary policy operations, Fed communications, data sources, productivity and the labor market, and the causes of inflation. Each will mix Fed staff with outside professionals, and most are expected to report by the end of the year. Warsh also rejected the idea of a "cruel choice" between fighting inflation and protecting employment.

That announcement creates a natural opening. The Fed has just framed its own process as something worth rebuilding from scratch, and it has invited outside professionals into the room. An agentic system that mirrors those five task forces is therefore not a gimmick. It is a parallel, measurable, fully-logged counterpart that can do three things a human committee cannot do cheaply:

- Run the same decision hundreds of times under different assumptions, overnight.
- Preserve every alternative considered and every dissent, with a number attached.
- Be adversarially attacked by a dedicated red-team on every single decision.

The honest pitch is not "agents beat the Fed." It is "here is a tool the Fed can run alongside its own people to see what a tireless, transparent, adversarial committee would have concluded, and why."

## 2. The core insight

The two open-source tools this design is built on are not the obvious ones, and that is the point.

**autoresearch (Karpathy, 2026)** gives us the engine pattern. In autoresearch, a human writes a short `program.md` that defines a research organization, an agent proposes an experiment by editing one file, the experiment is scored on a single hard metric (`val_bpb`), and the agent keeps or discards the change and loops, roughly a hundred times overnight. The human programs the context, not the code. The agent climbs the metric.

**andrej-karpathy-skills (2026)** gives us the behavioral discipline: think before acting, keep it simple, make surgical changes, and above all, "don't tell it what to do, give it success criteria and watch it go."

The reason this maps cleanly onto the Fed is that **the dual mandate is already a loss function.** Academic monetary economics has, for decades, written the central bank's objective as the minimization of squared deviations of inflation from target plus weighted squared deviations of employment from full employment. That quadratic loss is the direct analog of `val_bpb`. Once you have a hard, agreed metric, the autoresearch loop applies almost without modification:

| autoresearch | Agentic Fed Task Force |
| --- | --- |
| `program.md` defines the research org | `program.md` defines each task force's charter |
| Agent edits `train.py` | Agent proposes a `PolicyDecision` (rate path + rationale) |
| Score on `val_bpb` (lower better) | Score on dual-mandate `total_loss` (lower better) |
| Fixed 5-minute training budget | Fixed deliberation-round budget |
| ~100 experiments overnight | Hundreds of scored policy scenarios overnight |
| Keep/discard, loop | Deliberate, red-team, decide, log |

## 3. What is already built

This blueprint ships with two runnable starter files so the idea is concrete, not just narrated.

**`objective.py`** is the dual-mandate metric, the `val_bpb` analog. It contains:

- A central-bank loss function: discounted sum of squared inflation gap plus weighted squared employment gap, plus a penalty for abrupt rate moves.
- A small, transparent reduced-form macro model (a Phillips curve, an Okun's-law channel, and slow-anchoring expectations) that rolls the economy forward under a proposed rate path. It is good enough to *rank* competing decisions, and it is deliberately not a forecast of the real economy.
- A Taylor (1993) rule baseline, the control that every agent proposal must beat.

Calibrated to today's setting (funds rate 3.5 to 3.75%, inflation running hot on an energy shock, labor still firm), the sandbox already produces a coherent ranking: a gradual-hike-then-ease path beats a steady hold, an aggressive cut overheats the economy and scores worst, and the rigid Taylor rule overshoots to a 5.6% policy rate that drives unemployment to 6.2%. That last result is the whole argument in miniature: a mechanical rule fails in a way a deliberating, red-teamed committee should catch.

**`program.md`** is the FOMC charter, in the autoresearch style. It defines the objective, the deliberation loop, the committee of PhD-level personas, the four operating principles borrowed from the Karpathy guidelines, and a strict logging requirement so every decision is auditable.

## 3a. Build strategy: the wedge, not the cathedral

The full system, a real-time agentic task force that mirrors all five Warsh charges, is the destination, not the first build. A system that claims everything proves nothing, and a central bank dismisses it on sight. The discipline is to prove one narrow, falsifiable claim cold, then let it pull the rest into existence.

The claim chosen is the keystone: **the Fed decides on stale data, and being current would change and improve decisions.** The first experiment isolates exactly that, by holding the committee's reasoning fixed and varying only the freshness of what it sees. This is deliberately not "agents versus humans," which is an argument the project would lose and does not need to have.

That experiment is already built and runnable (`nowcast.py`, `backtest.py`, documented in `EXPERIMENT.md`). On illustrative synthetic data it shows freshness improving the average outcome and, more tellingly, shows the value of real-time data concentrated at shocks and turning points rather than spread evenly. The synthetic run validates the methodology, not the magnitude; the real result comes from swapping in live feeds at the marked points, which is the next milestone.

Everything deferred (the physical-economy breadth, the AI-reflexivity lens, the other four task forces) waits behind this proof. Deferring is the strategy, not a limitation.

## 4. System architecture

The system has five layers. The first three exist today; the last two are the build plan.

1. **Objective layer** (`objective.py`, built). The hard metric and the sandbox economy. This is the contract everything else agrees on.
2. **Charter layer** (`program.md`, built). One charter per task force. Humans edit these; agents obey them.
3. **Agent layer** (`committee.py`, built). The committee. Each persona is a frontier LLM given its charter section and the live state; the four economist personas propose a `PolicyDecision`, the sandbox scores every proposal (agents never grade themselves), they deliberate over the scored board, the Skeptic red-teams the leader, and the Chair synthesises a logged decision. Built directly on the Anthropic SDK, running Claude Opus 4.8 by default; a labelled deterministic stub runs the same loop with no key. This is the key correction to the original idea: nanochat and autoresearch are for *training small models and automating ML research*; the committee itself runs on the strongest available frontier models, because policy reasoning is exactly where model quality matters most. autoresearch is the inspiration for the *loop*, not the runtime.
4. **Data layer** (to build). Live and historical feeds: inflation series, payrolls, JOLTS, financial conditions, expectations surveys. In a desktop or analyst setting these arrive through connectors and APIs. This layer turns the toy `EconomyState` into the real one.
5. **Evaluation and governance layer** (to build). The benchmark harness that pits the agentic committee against a held-out record of real FOMC decisions, plus the audit log, dissents, and human-override controls.

## 5. The benchmark: can the agentic task force do better?

This is the question that makes the project worth doing, and it has to be answered honestly, which means defining "better" before running anything.

- **Backtest against history.** Replay actual FOMC meetings from a held-out period. At each meeting, give the agentic committee only the data that was available on that date (no look-ahead), record its decision, then score both the committee's decision and the Fed's actual decision against realized outcomes over the following year. Report where the agents would have done better, where worse, and by how much.
- **Beat the rule, not just the Fed.** The first bar is the Taylor baseline in `objective.py`. A committee that cannot consistently beat a mechanical rule has earned no trust. The second bar is the Fed's own record.
- **Stability and dissent quality.** Measure not just the average loss but the variance, the worst-case quarter, and whether the red-team's flagged risks actually materialized. A good committee is one whose dissents were prescient.
- **Ablations.** Remove the Skeptic, or swap the model, or change the employment weight, and watch the metric move. This is the autoresearch instinct applied to governance: the organization itself is the thing being tuned.

A credible result is not "the agents won." A credible result is a clear, reproducible scorecard that shows under which conditions the agentic process adds value and under which it does not.

## 6. Mapping to all five Warsh task forces

The dual-mandate engine is the deep core. The architecture generalizes, because every one of Warsh's five charges can be written as a charter plus a metric:

- **Monetary policy operations.** The core, already specified above. Metric: dual-mandate loss.
- **Causes of inflation.** A diagnostic committee that decomposes inflation into supply, demand, and expectations components. Metric: out-of-sample decomposition accuracy.
- **Productivity and the labor market.** A committee estimating the employment gap and r-star inputs that the core engine consumes. Metric: forecast error on labor series.
- **Fed communications.** A committee that drafts and tests policy statements for clarity and market reaction. Metric: predicted versus realized market surprise.
- **Data sources.** A committee that audits which inputs actually move decisions and which are noise. Metric: decision sensitivity to each data source.

Each is a new `program.md` and a new metric, plugged into the same loop.

## 7. Honest risks and limits

A blueprint that hides its own weaknesses fails the first Karpathy principle, so here they are plainly.

- **The model is a sandbox, not the economy.** Rankings are only as good as the reduced-form macro model. The Econometrician persona and the ablation tests exist to keep this honest, but no committee can out-reason a badly mis-specified world. This is the single largest caveat.
- **Metric gaming.** Agents optimize what you measure. A proposal can score well by exploiting model quirks rather than good economics. The red-team and the plausibility constraints in `program.md` are the defense, and they need ongoing scrutiny.
- **Adoption reality.** The Fed will not hand monetary policy to an external tool, nor should it. The realistic path is decision-support: a system Fed staff or outside researchers run alongside the human process, valued for its transparency and its tireless red-teaming, not its authority.
- **Tool fit.** nanochat and autoresearch are the right *inspiration* and the wrong *runtime* for the committee itself. Using them to train the reasoning models would be a category error. They earn their place as the loop pattern and, optionally, in the data layer for cheap specialized sub-models.

## 8. Recommended next steps

1. **Wire the loop.** *(Done — `committee.py`.)* A real committee of frontier-model personas runs one full deliberation cycle against `objective.py` and produces a logged decision, with a stub fallback so the loop runs without a key.
2. **Replace the toy state.** Connect the data layer to real inflation, employment, and financial series so the `EconomyState` is current rather than hand-coded.
3. **Run the backtest.** Stand up the evaluation harness and produce the first honest scorecard against a held-out stretch of FOMC history — ideally driving the *agent* committee, not just the optimizer stand-in, at each historical meeting.
4. **Package for the audience.** Once there is a scorecard, turn this blueprint and the results into a short deck and a one-page brief aimed at the people staffing Warsh's task forces.

With step 1 done, the natural next move is step 2: give the committee real, current data to reason about instead of a hand-coded snapshot.

---

## Sources

- [Fed holds interest rates steady as Warsh era begins (Fox Business)](https://www.foxbusiness.com/economy/federal-reserve-interest-rate-decision-june-17-2026)
- [The Fed Maintains Rates: What It Means for Your Money (Newsweek)](https://www.newsweek.com/federal-reserve-interest-rates-june-2026-warsh-12085463)
- [Warsh's first interest rate meeting (CBS News)](https://www.cbsnews.com/news/federal-reserve-interest-rates-kevin-warsh-june-2026/)
- [Fed leaves rates unchanged, signals higher rates ahead (CNN Business)](https://www.cnn.com/2026/06/17/business/live-news/federal-reserve-interest-rate-kevin-warsh)
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
- [karpathy/nanochat](https://github.com/karpathy/nanochat)
- [andrej-karpathy-skills (Karpathy-inspired agent guidelines)](https://github.com/multica-ai/andrej-karpathy-skills)
