"""
data_real.py -- the real-data layer for the Agentic Fed Task Force.

This replaces nowcast.py's synthetic generator with live sources, at the three
points the blueprint marked `# SWAP POINT`:

  1. REALIZED TRUTH  -> FRED latest-vintage history (the judge neither committee
     can see at decision time): core PCE inflation, unemployment, fed funds.
  2. STALE OFFICIAL  -> ALFRED vintage *as it was known on a given date*. The
     real publication lag and first-release values fall out of the vintage query
     itself -- no synthetic lag, no fabricated revision noise.
  3. FRESH SIGNALS   -> FMP real-time financial data available on that same date
     (the Treasury yield curve, equity level/vol proxies). These are genuinely
     real-time and never revised, so they LEAD the lagged official macro prints.
     This is the "signal" in signal-to-decision: the competitive edge the fresh
     committee gets and the stale one does not.

Everything here is no-look-ahead by construction: every query is pinned to an
as-of date, and the realized truth is pulled separately and only used to SCORE.

Requires FRED_API_KEY (free) and FMP_API_KEY in .env. Run `python data_real.py`
for a self-test once both keys are set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import config

config.init()  # load .env + enable corporate TLS before any network call

import requests  # noqa: E402  (after config so TLS trust is set first)

FRED_BASE = "https://api.stlouisfed.org/fred"
FMP_BASE = "https://financialmodelingprep.com/stable"

# FRED series IDs for the three mandate inputs.
SERIES = {
    "pce_index": "PCEPILFE",  # core PCE price index (compute YoY inflation from it)
    "unemployment": "UNRATE",  # unemployment rate, percent
    "fed_funds": "FEDFUNDS",  # effective fed funds rate, monthly average, percent
}


def _fred_key() -> str:
    key = os.environ.get("FRED_API_KEY")
    if not key or key == "abcdefghijklmnopqrstuvwxyz123456":
        raise RuntimeError(
            "FRED_API_KEY is missing or still the docs placeholder. Paste your "
            "real key into .env (free: "
            "https://fred.stlouisfed.org/docs/api/api_key.html)."
        )
    return key


def _fmp_key() -> str:
    key = os.environ.get("FMP_API_KEY")
    if not key:
        raise RuntimeError("FMP_API_KEY is not set. Add it to .env.")
    return key


# ----------------------------------------------------------------------------
# FRED / ALFRED access.
# ----------------------------------------------------------------------------
def _fred_observations(series_id: str, *, as_of: str | None = None,
                       start: str | None = None, end: str | None = None) -> list[dict]:
    """
    Fetch observations for a series. If `as_of` is given, this becomes an ALFRED
    vintage query: only data that existed on `as_of` is returned (real lag +
    first-release values). Otherwise it returns the latest (realized) vintage.
    """
    params = {
        "series_id": series_id,
        "api_key": _fred_key(),
        "file_type": "json",
    }
    if as_of:
        params["realtime_start"] = as_of
        params["realtime_end"] = as_of
    if start:
        params["observation_start"] = start
    if end:
        params["observation_end"] = end
    r = requests.get(f"{FRED_BASE}/series/observations", params=params, timeout=30)
    r.raise_for_status()
    obs = r.json().get("observations", [])
    return [o for o in obs if o.get("value") not in (".", "", None)]


def _latest_value(obs: list[dict]) -> tuple[str, float] | None:
    """Most recent (date, value) from an observation list."""
    if not obs:
        return None
    o = obs[-1]
    return o["date"], float(o["value"])


def _yoy_from_index(obs: list[dict], ref_date: str) -> float | None:
    """Year-over-year percent change of an index series at ref_date."""
    by_date = {o["date"]: float(o["value"]) for o in obs}
    if ref_date not in by_date:
        return None
    ref_dt = datetime.strptime(ref_date, "%Y-%m-%d")
    prior = ref_dt.replace(year=ref_dt.year - 1).strftime("%Y-%m-%d")
    if prior not in by_date:
        return None
    return round(100.0 * (by_date[ref_date] / by_date[prior] - 1.0), 3)


def _fred_latest_asof(series_id: str, as_of: str, lookback_days: int = 500):
    """Latest (date, value) for a series no later than as_of, as known at as_of
    (ALFRED vintage). Fully no-look-ahead. Returns None if nothing available."""
    start = (datetime.strptime(as_of, "%Y-%m-%d")
             - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    obs = _fred_observations(series_id, as_of=as_of, start=start, end=as_of)
    return _latest_value(obs)


def _fred_change_asof(series_id: str, as_of: str, lookback_days: int = 35):
    """
    (latest_value, change_over_window, latest_date) for a series as known at
    as_of -- the recent momentum a real-time watcher would see. Window defaults
    to ~5 weeks (good for weekly series like jobless claims). No look-ahead.
    """
    start = (datetime.strptime(as_of, "%Y-%m-%d")
             - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    obs = _fred_observations(series_id, as_of=as_of, start=start, end=as_of)
    if not obs:
        return None
    latest_v = float(obs[-1]["value"])
    first_v = float(obs[0]["value"])
    return latest_v, round(latest_v - first_v, 4), obs[-1]["date"]


@dataclass
class MacroSnapshot:
    """Inflation / unemployment / fed funds as known on a given date, with the
    reference month each figure actually describes (exposes the real lag)."""
    inflation: float
    unemployment: float
    fed_funds: float
    inflation_ref_month: str
    unemployment_ref_month: str
    as_of: str
    source: str
    inflation_expectations: float | None = None  # real, from 5y breakeven (T5YIE)
    signals: dict = field(default_factory=dict)


def official_snapshot(as_of: str) -> MacroSnapshot:
    """
    SWAP POINT 2: the STALE official view -- what the Fed effectively saw on
    `as_of`, via ALFRED vintage queries. The lag is real, not synthetic.
    """
    # Pull ~2 years of vintage index history so YoY can be computed as-known.
    start = (datetime.strptime(as_of, "%Y-%m-%d") - timedelta(days=900)).strftime("%Y-%m-%d")
    pce = _fred_observations(SERIES["pce_index"], as_of=as_of, start=start, end=as_of)
    unemp = _fred_observations(SERIES["unemployment"], as_of=as_of, start=start, end=as_of)
    ffr = _fred_observations(SERIES["fed_funds"], as_of=as_of, start=start, end=as_of)

    pce_latest = _latest_value(pce)
    unemp_latest = _latest_value(unemp)
    ffr_latest = _latest_value(ffr)
    if not (pce_latest and unemp_latest and ffr_latest):
        raise RuntimeError(f"insufficient vintage data as of {as_of}")

    infl = _yoy_from_index(pce, pce_latest[0])
    if infl is None:
        raise RuntimeError(f"could not compute core-PCE YoY as of {as_of}")

    # Real, market-based inflation expectations: the 5-year TIPS breakeven as it
    # stood on the decision date (daily, never revised) -- replaces the old
    # 0.5*inflation+0.5*anchor placeholder.
    be = _fred_latest_asof("T5YIE", as_of)
    expectations = be[1] if be else None

    return MacroSnapshot(
        inflation=infl,
        unemployment=unemp_latest[1],
        fed_funds=ffr_latest[1],
        inflation_ref_month=pce_latest[0],
        unemployment_ref_month=unemp_latest[0],
        as_of=as_of,
        source="official (ALFRED vintage)",
        inflation_expectations=expectations,
    )


def realized_truth(ref_month: str) -> dict:
    """
    SWAP POINT 1: the REALIZED truth for a calendar month, from FRED's latest
    vintage. Used only to SCORE decisions -- never shown to a committee.
    """
    start = (datetime.strptime(ref_month, "%Y-%m-%d") - timedelta(days=420)).strftime("%Y-%m-%d")
    end = (datetime.strptime(ref_month, "%Y-%m-%d") + timedelta(days=40)).strftime("%Y-%m-%d")
    pce = _fred_observations(SERIES["pce_index"], start=start, end=end)
    unemp = _fred_observations(SERIES["unemployment"], start=ref_month, end=end)
    ffr = _fred_observations(SERIES["fed_funds"], start=ref_month, end=end)

    # Find the index value for ref_month (or the nearest prior available).
    by_date = {o["date"]: float(o["value"]) for o in pce}
    ref = ref_month if ref_month in by_date else (max(d for d in by_date if d <= ref_month) if by_date else None)
    infl = _yoy_from_index(pce, ref) if ref else None
    unemp_v = next((float(o["value"]) for o in unemp if o["date"] >= ref_month), _latest_value(unemp)[1] if unemp else None)
    ffr_v = next((float(o["value"]) for o in ffr if o["date"] >= ref_month), _latest_value(ffr)[1] if ffr else None)

    # Realized expectations: 5y breakeven for the same month (latest vintage).
    be = _fred_observations("T5YIE", start=ref_month, end=end)
    exp_v = _latest_value(be)[1] if be else None

    return {
        "ref_month": ref_month,
        "inflation": infl,
        "unemployment": unemp_v,
        "fed_funds": ffr_v,
        "inflation_expectations": exp_v,
    }


def _add_months(d: datetime, n: int) -> datetime:
    m = d.month - 1 + n
    return d.replace(year=d.year + m // 12, month=m % 12 + 1, day=1)


def fed_actual_path(decision_date: str, horizon: int = 4, step_months: int = 3) -> list[float]:
    """
    The Fed's ACTUAL realized funds-rate path over the `horizon` quarters after
    the decision date (effective fed funds, latest vintage). This is the
    human-committee benchmark: what the FOMC actually did, scored by the same
    objective as the agentic committees. The funds rate the Fed set is observed,
    not modeled.
    """
    base = datetime.strptime(decision_date, "%Y-%m-%d").replace(day=1)
    end = _add_months(base, horizon * step_months + 2).strftime("%Y-%m-%d")
    obs = _fred_observations("FEDFUNDS", start=base.strftime("%Y-%m-%d"), end=end)
    by_month = {o["date"][:7]: float(o["value"]) for o in obs}
    if not by_month:
        raise RuntimeError(f"no fed funds data for {decision_date}")

    path = []
    for q in range(horizon):
        target = _add_months(base, q * step_months)
        key = target.strftime("%Y-%m")
        if key in by_month:
            path.append(round(by_month[key], 3))
        else:  # nearest available month at or before the target
            earlier = [m for m in by_month if m <= key]
            path.append(round(by_month[max(earlier)], 3) if earlier else path[-1])
    return path


# ----------------------------------------------------------------------------
# The broader official dashboard (what a real reaction function watches) and
# the LEADING real-time signal set (the fix for the endogenous yield curve).
# ----------------------------------------------------------------------------

# Series the official committee should see (lagged/revised, like the core three).
# id -> (label, kind) where kind hints at how to read it.
DASHBOARD_SERIES = {
    "PAYEMS": ("nonfarm payrolls (000s)", "level"),
    "JTSJOL": ("job openings, JOLTS (000s)", "level"),
    "JTSQUR": ("quits rate, JOLTS (%)", "level"),
    "CIVPART": ("labor force participation (%)", "level"),
    "LNS12300060": ("prime-age employment-pop ratio (%)", "level"),
    "CES0500000003": ("avg hourly earnings ($)", "level"),
    "RSAFS": ("retail sales ($M)", "level"),
    "INDPRO": ("industrial production (index)", "level"),
    "GDPNOW": ("Atlanta Fed GDPNow (%, annualized)", "level"),
    "WRESBAL": ("bank reserves ($M)", "level"),
    "RRPONTSYD": ("overnight reverse repo ($B)", "level"),
    "WALCL": ("Fed total assets ($M)", "level"),
}

# Genuinely LEADING / real-time signals: high-frequency, little or no revision,
# and -- unlike the Treasury curve -- not just a mirror of expected Fed policy.
# id -> (label, window_days, momentum_matters)
LEADING_SERIES = {
    "ICSA": ("initial jobless claims (weekly)", 35, True),
    "IHLIDXUS": ("Indeed job postings index", 45, True),
    "BAMLH0A0HYM2": ("high-yield credit spread (OAS, %)", 14, True),
    "BAMLC0A0CM": ("investment-grade credit spread (OAS, %)", 14, True),
    "VIXCLS": ("equity volatility (VIX)", 14, True),
    "DTWEXBGS": ("broad trade-weighted US dollar", 21, True),
    "DCOILWTICO": ("WTI crude oil ($/bbl)", 14, True),
    "DHHNGSP": ("Henry Hub natural gas ($/MMBtu)", 14, True),
    "MICH": ("UMich 1y inflation expectations (%)", 60, False),
    "T5YIFR": ("5y5y forward inflation breakeven (%)", 14, True),
}


def official_dashboard(as_of: str) -> dict:
    """The broader lagged/official picture as known on as_of (vintage-aware)."""
    out = {}
    for sid, (label, _kind) in DASHBOARD_SERIES.items():
        try:
            lv = _fred_latest_asof(sid, as_of, lookback_days=500)
            out[sid] = {"label": label, "date": lv[0], "value": lv[1]} if lv else None
        except Exception:
            out[sid] = None
    return out


def leading_signals(as_of: str) -> dict:
    """
    SWAP POINT 3, done right: the real-time LEADING signal set. High-frequency,
    barely-revised series that move ahead of the official macro prints and are
    largely exogenous to the Fed's own policy path -- the opposite of the
    Treasury curve, which embeds the market's forecast of Fed policy itself.
    """
    out = {"as_of": as_of}
    for sid, (label, window, _mom) in LEADING_SERIES.items():
        try:
            ch = _fred_change_asof(sid, as_of, lookback_days=window)
            if ch:
                out[sid] = {"label": label, "value": ch[0],
                            "change": ch[1], "date": ch[2], "window_days": window}
            else:
                out[sid] = None
        except Exception:
            out[sid] = None
    return out


# ----------------------------------------------------------------------------
# FMP real-time signals.
# ----------------------------------------------------------------------------
def realtime_signals(as_of: str) -> dict:
    """
    SWAP POINT 3 (the edge): real-time financial signals available on `as_of`.
    The Treasury yield curve and its slope/level move daily and are never
    revised, so they carry information about conditions before the official
    macro prints land. Returned as a feature dict for the fresh committee.
    """
    key = _fmp_key()
    window_start = (datetime.strptime(as_of, "%Y-%m-%d") - timedelta(days=10)).strftime("%Y-%m-%d")
    r = requests.get(
        f"{FMP_BASE}/treasury-rates",
        params={"from": window_start, "to": as_of, "apikey": key},
        timeout=30,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return {"as_of": as_of, "available": False}
    # Sort by date explicitly so a feed reordering cannot silently flip the
    # signal (do not assume FMP returns newest-first).
    rows = sorted(rows, key=lambda x: x.get("date", ""))
    latest = rows[-1]
    oldest = rows[0]
    curve = {k: latest.get(k) for k in ("month3", "year2", "year10", "year30")}
    slope = None
    if latest.get("year10") is not None and latest.get("month3") is not None:
        slope = round(latest["year10"] - latest["month3"], 3)  # 10y-3m term spread
    # Momentum over the lookback window (real-time, never revised): which way
    # the market repriced the short and long end just before the decision.
    def _chg(field):
        a, b = latest.get(field), oldest.get(field)
        return round(a - b, 3) if (a is not None and b is not None) else None

    return {
        "as_of": as_of,
        "available": True,
        "curve_date": latest.get("date"),
        "yield_curve": curve,
        "term_spread_10y_3m": slope,  # <0 = inversion, a classic recession signal
        "short_rate_3m": latest.get("month3"),  # level: market's read on policy stance
        "change_3m_10d": _chg("month3"),  # short-end momentum over the window
        "change_10y_10d": _chg("year10"),  # long-end momentum over the window
        "window_start": oldest.get("date"),
    }


# ----------------------------------------------------------------------------
# FMP leverage: things FRED cannot do. (1) same-day / intraday market quotes for
# the LIVE tool; (2) the economic calendar with consensus, so the committee can
# react to data SURPRISES (actual vs expected) -- a real, non-circular signal.
# ----------------------------------------------------------------------------
_FMP_MARKETS = {
    "DX=F": "broad US dollar index (DXY)",
    "CLUSD": "WTI crude oil",
    "^VIX": "equity volatility (VIX)",
    "HYG": "high-yield credit ETF",
    "LQD": "investment-grade credit ETF",
}


def live_market_signals() -> dict:
    """
    Real-time market quotes from FMP for the LIVE tool (intraday, fresher than
    FRED's end-of-day). NOT historical: /quote returns the current price, so this
    is for live decisions, not backtests (which use the FRED vintage path).
    """
    key = _fmp_key()
    out = {}
    for sym, label in _FMP_MARKETS.items():
        try:
            r = requests.get(f"{FMP_BASE}/quote", params={"symbol": sym, "apikey": key},
                             timeout=20)
            rows = r.json() if r.ok else []
            if rows:
                q = rows[0]
                out[sym] = {"label": label, "price": q.get("price"),
                            "change_pct": q.get("changePercentage")}
            else:
                out[sym] = None
        except Exception:
            out[sym] = None
    return out


def economic_surprises(frm: str, to: str, country: str = "US") -> list[dict]:
    """
    US releases between two dates with consensus vs actual, from the FMP economic
    calendar. surprise = actual - estimate is a genuinely leading, non-circular
    signal (unlike the Treasury curve). Release dates also pin no-look-ahead.
    """
    key = _fmp_key()
    r = requests.get(f"{FMP_BASE}/economic-calendar",
                     params={"from": frm, "to": to, "apikey": key}, timeout=30)
    r.raise_for_status()
    out = []
    for ev in r.json():
        if ev.get("country") not in (country, "USD", "United States"):
            continue
        actual, est = ev.get("actual"), ev.get("estimate")
        surprise = None
        if isinstance(actual, (int, float)) and isinstance(est, (int, float)):
            surprise = round(actual - est, 4)
        out.append({"date": ev.get("date"), "event": ev.get("event"),
                    "estimate": est, "actual": actual, "surprise": surprise})
    return out


if __name__ == "__main__":
    print("=== data_real.py self-test ===\n")
    sample_date = "2024-06-12"  # an FOMC decision date

    print(f"Real-time financial signals as of {sample_date} (FMP):")
    try:
        sig = realtime_signals(sample_date)
        print(f"  {sig}\n")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}\n")

    print(f"Official macro snapshot as known on {sample_date} (ALFRED vintage):")
    try:
        snap = official_snapshot(sample_date)
        print(f"  inflation (core PCE YoY): {snap.inflation}%  "
              f"[ref month {snap.inflation_ref_month}]")
        print(f"  unemployment            : {snap.unemployment}%  "
              f"[ref month {snap.unemployment_ref_month}]")
        print(f"  fed funds               : {snap.fed_funds}%")
        lag_days = (datetime.strptime(sample_date, "%Y-%m-%d")
                    - datetime.strptime(snap.inflation_ref_month, "%Y-%m-%d")).days
        print(f"  --> real publication lag on inflation: ~{lag_days} days\n")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}\n")

    print(f"Realized truth for the same reference month (FRED latest vintage):")
    try:
        truth = realized_truth("2024-04-01")
        print(f"  {truth}")
        print("  (note: revised values differ from the first-release vintage above"
              " -- that gap is exactly what the experiment measures.)")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
