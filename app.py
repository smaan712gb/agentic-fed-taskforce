"""
app.py -- the analyst-facing UI for the Agentic Fed Task Force.

A local Streamlit app a Fed analyst runs themselves (with their own API key) to:
  * read the honest framing and findings up front,
  * inspect the live real-data dashboard for any date (no look-ahead),
  * browse the backtest scorecard (stale vs fresh, curve vs leading),
  * browse saved committee deliberations AND trigger a fresh live one.

It deliberately presents the honest result -- real-time signals are insurance at
turning points, not a steady edge -- not an "AI beats the Fed" dashboard.

Run:
    uv run --extra ui streamlit run app.py
    # or: pip install -e ".[ui]" && streamlit run app.py
Keys come from .env (ANTHROPIC_API_KEY optional -> stub; FRED_API_KEY + FMP_API_KEY
enable the live data tabs).
"""

from __future__ import annotations

import os
import json
import glob
from dataclasses import asdict
from datetime import date
from pathlib import Path

import config

config.init()  # load .env + corporate TLS before anything touches the network

import streamlit as st

from objective import EconomyState, PolicyDecision, score, taylor_rule
from committee import run_committee, select_backend, RunLog

RUNS = Path(__file__).parent / "runs"

st.set_page_config(page_title="Agentic Fed Task Force", layout="wide", page_icon="🏛")


# ---------------------------------------------------------------- helpers ----
def _have(key: str) -> bool:
    return bool(os.environ.get(key))


@st.cache_data(show_spinner=False, ttl=3600)
def cached_snapshot(d: str):
    from data_real import official_snapshot
    s = official_snapshot(d)
    return asdict(s)


@st.cache_data(show_spinner=False, ttl=3600)
def cached_leading(d: str):
    from data_real import leading_signals
    return leading_signals(d)


@st.cache_data(show_spinner=False, ttl=3600)
def cached_dashboard(d: str):
    from data_real import official_dashboard
    return official_dashboard(d)


def load_runs(pattern: str):
    files = sorted(glob.glob(str(RUNS / pattern)), reverse=True)
    return files


def render_committee(d: dict):
    """Render one committee RunLog (saved dict or live, asdict'd) professionally."""
    base = d.get("baseline", {})
    st.markdown(
        f"**Baseline (must beat):** Taylor rule `{base.get('rate_path')}` "
        f"-> total_loss **{base.get('score', {}).get('total_loss')}**"
    )
    if d.get("context"):
        with st.expander("Real-time signal context shown to this committee"):
            st.text(d["context"])

    for i, rnd in enumerate(d.get("rounds", []), 1):
        st.markdown(f"**Deliberation round {i}**")
        rows = [{
            "persona": p["persona"],
            "rate path": str(p["rate_path"]),
            "total_loss": p["score"]["total_loss"],
            "assumption": p.get("assumption", ""),
        } for p in rnd]
        st.dataframe(rows, use_container_width=True, hide_index=True)

    rt = d.get("red_team", {})
    if rt:
        verdict = "FATAL — not adoptable as-is" if rt.get("fatal") else "survived"
        st.markdown(f"**Red-team (Skeptic):** {verdict}")
        for c in rt.get("challenges", []):
            st.markdown(f"- {c}")
        if rt.get("summary"):
            st.caption(rt["summary"])

    dec = d.get("decision", {})
    if dec:
        st.markdown("**Chair's decision**")
        c1, c2 = st.columns([2, 3])
        with c1:
            st.metric("Final rate path", str(dec.get("rate_path")))
            st.metric("total_loss", dec.get("score", {}).get("total_loss"))
        with c2:
            st.markdown(f"_{dec.get('statement', '')}_")
            if dec.get("dissents"):
                st.markdown("**Dissents preserved:**")
                for x in dec["dissents"]:
                    st.markdown(f"- {x}")

    v = d.get("verdict", {})
    if v:
        cols = st.columns(3)
        cols[0].metric("Beat baseline", "yes" if v.get("beat_baseline") else "no")
        cols[1].metric("Survived red-team", "yes" if v.get("survived_red_team") else "no")
        cols[2].metric("SUCCESS", "yes" if v.get("success") else "no")


# --------------------------------------------------------------- sidebar -----
st.sidebar.title("🏛 Agentic Fed Task Force")
st.sidebar.caption("Decision-support & red-team sandbox for the dual mandate")
st.sidebar.markdown("**Backends**")
st.sidebar.write("Committee model:", "Claude Opus 4.8" if _have("ANTHROPIC_API_KEY") else "stub (no key)")
st.sidebar.write("FRED / ALFRED:", "ready" if _have("FRED_API_KEY") else "missing key")
st.sidebar.write("FMP signals:", "ready" if _have("FMP_API_KEY") else "missing key")
st.sidebar.info("This is decision-support and a red-team — not a replacement for "
                "the FOMC, and not a claim to beat it.")

overview, livedata, scorecard, committee = st.tabs(
    ["Overview", "Live data", "Backtest scorecard", "Committee deliberation"]
)

# -------------------------------------------------------------- Overview -----
with overview:
    st.title("Agentic Fed Task Force")
    st.markdown(
        "A transparent, reproducible decision-support and red-team system that "
        "treats the **dual mandate as a loss function**, lets a logged, "
        "adversarially-tested committee of model personas propose and defend rate "
        "paths, and scores every decision against **real outcomes with no "
        "look-ahead**."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("What it does")
        st.markdown(
            "- Frontier-model committee: four economists, a Skeptic that "
            "red-teams, a Chair that synthesizes.\n"
            "- Agents never grade themselves — a fixed objective scores every path.\n"
            "- Real data: FRED truth, ALFRED release-and-revision vintages, FMP "
            "real-time signals.\n"
            "- Honest, reproducible backtest against realized outcomes."
        )
    with c2:
        st.subheader("The honest finding")
        st.markdown(
            "On real FOMC dates, real-time signals show **no steady edge** at this "
            "small sample — but at the **turning point** (July 2023), leading "
            "indicators (jobless claims, job postings, credit) made the fresh "
            "committee *win* where the endogenous yield curve made it *lose*.\n\n"
            "**Read:** real-time data is *insurance at turning points*, not a free "
            "gain — and signal type matters most where it matters most."
        )
    st.warning("Four FOMC dates is a pilot, not a verdict. See the Backtest tab "
               "for the numbers and FINDINGS.md for the full, unspun reading.")

# ------------------------------------------------------------- Live data -----
with livedata:
    st.header("Live data dashboard (no look-ahead)")
    if not _have("FRED_API_KEY"):
        st.error("FRED_API_KEY not set — add it to .env to enable live data.")
    else:
        d = st.date_input("As-of date", value=date(2024, 6, 12)).isoformat()
        if st.button("Load data as known on this date", type="primary"):
            with st.spinner("Querying FRED/ALFRED vintages and FMP signals..."):
                snap = cached_snapshot(d)
                lead = cached_leading(d)
                dash = cached_dashboard(d)
            st.subheader("Official view (ALFRED vintage — what the Fed effectively had)")
            cols = st.columns(4)
            cols[0].metric("Core PCE YoY", f"{snap['inflation']}%", help=f"ref month {snap['inflation_ref_month']}")
            cols[1].metric("Unemployment", f"{snap['unemployment']}%")
            cols[2].metric("Fed funds", f"{snap['fed_funds']}%")
            cols[3].metric("5y breakeven (expectations)", f"{snap.get('inflation_expectations')}%")

            st.subheader("Real-time leading signals (the fresh committee's edge)")
            rows = [{"signal": v["label"], "value": v["value"],
                     "recent change": v.get("change"), "as of": v["date"]}
                    for k, v in lead.items() if k != "as_of" and v]
            st.dataframe(rows, use_container_width=True, hide_index=True)

            st.subheader("Broader official dashboard")
            drows = [{"series": v["label"], "value": v["value"], "as of": v["date"]}
                     for v in dash.values() if v]
            st.dataframe(drows, use_container_width=True, hide_index=True)

# -------------------------------------------------------- Backtest scorecard -
with scorecard:
    st.header("Backtest scorecard")
    files = load_runs("backtest_real-*.json")
    if not files:
        st.info("No backtest runs found in runs/. Run backtest_real.py first.")
    else:
        pick = st.selectbox("Run file", files, format_func=lambda p: Path(p).name)
        data = json.loads(Path(pick).read_text(encoding="utf-8"))
        mode = data.get("signal_mode", "?")
        st.caption(f"signal mode: **{mode}** · model: {data.get('model')} · "
                   f"runs/date: {data.get('runs_per_date')}")
        cols = st.columns(4)
        cols[0].metric("Mean loss — STALE", f"{data['mean_stale']:.3f}")
        cols[1].metric("Mean loss — FRESH", f"{data['mean_fresh']:.3f}")
        cols[2].metric("Edge from signals", f"{data['improvement_pct']:+.1f}%")
        bd = data.get("by_date", {})
        cols[3].metric("By-date fresh/stale/tie", f"{bd.get('fresh',0)}/{bd.get('stale',0)}/{bd.get('tie',0)}")

        rows, chart = [], {}
        for r in data.get("rows", []):
            rows.append({
                "date": r["date"],
                "stale loss": round(r["stale_loss_mean"], 3),
                "fresh loss": round(r["fresh_loss_mean"], 3),
                "winner": r["better_by_mean"],
                "fresh wins of runs": r.get("fresh_wins_of_runs"),
            })
            chart[r["date"]] = {"stale": r["stale_loss_mean"], "fresh": r["fresh_loss_mean"]}
        st.dataframe(rows, use_container_width=True, hide_index=True)
        try:
            import pandas as pd
            st.bar_chart(pd.DataFrame(chart).T)
        except Exception:
            pass
        if data['improvement_pct'] < 0:
            st.info("No across-the-board edge here — read the per-date winners and "
                    "the turning-point story, not just the headline.")

# ----------------------------------------------------- Committee deliberation
with committee:
    st.header("Committee deliberation")
    browse, live = st.tabs(["Browse saved", "Run live"])

    with browse:
        cfiles = load_runs("committee-*.json")
        if not cfiles:
            st.info("No saved committee transcripts. Use 'Run live' or run committee.py.")
        else:
            pick = st.selectbox("Transcript", cfiles, format_func=lambda p: Path(p).name)
            render_committee(json.loads(Path(pick).read_text(encoding="utf-8")))

    with live:
        st.markdown("Run one full deliberation now. Uses your API key; a single "
                    "run is ~6–12 model calls (about a minute) and costs a few cents.")
        col = st.columns(3)
        infl = col[0].number_input("Inflation (PCE YoY %)", value=3.1, step=0.1)
        unemp = col[1].number_input("Unemployment %", value=4.0, step=0.1)
        rate = col[2].number_input("Fed funds %", value=3.625, step=0.125)
        give_signal = st.checkbox("Give the committee a real-time signal note (fresh mode)")
        signal_note = ""
        if give_signal:
            signal_note = st.text_area(
                "Signal context",
                "Weekly jobless claims rising; job postings softening; credit "
                "spreads stable; the dollar firm.",
            )
        if st.button("Run deliberation", type="primary"):
            state = EconomyState(inflation=infl, unemployment=unemp, policy_rate=rate)
            with st.spinner("The committee is deliberating..."):
                backend = select_backend()
                log: RunLog = run_committee(
                    state, rounds=1, backend=backend,
                    extra_context=signal_note or None, verbose=False,
                )
            if "stub" in backend.name:
                st.warning("No ANTHROPIC_API_KEY — this ran the labelled stub, not "
                           "the real model.")
            render_committee(asdict(log))
