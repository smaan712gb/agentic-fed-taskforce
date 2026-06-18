# Data Sources — the target dashboard, ranked and verified

This specifies the full input set the Agentic Fed Task Force should watch, the
exact series IDs, where each comes from, whether it **leads or mirrors** policy,
how no-look-ahead is enforced, and the order to build it. Every ID marked
`wired` or `verified` below was queried against the live API and returned
current data on 2026-06-18; nothing here is aspirational.

## Why this document exists

The first real pilot ran on four series (core PCE, unemployment, fed funds, the
Treasury curve) and found *no edge* from the real-time signal. Two reasons, both
fixable and both addressed here:

1. **Inflation expectations were faked** — computed as `0.5*inflation + 0.5*anchor`.
   Now replaced with the real 5-year TIPS breakeven (`T5YIE`).
2. **The one real-time signal was the wrong kind.** The Treasury yield curve
   *embeds the market's forecast of Fed policy*, so feeding it back into the
   Fed's own decision is partly circular. The freshness thesis must be tested
   with signals that genuinely **lead** the official data and are **exogenous**
   to the policy path. That is the design principle below.

## Availability tiers

| Tier | Meaning |
| --- | --- |
| **FREE-FRED** | Free FRED/ALFRED API (the key we already use). Vintage-accurate. |
| **FMP** | Financial Modeling Prep (key we already use). Real-time/intraday + economic calendar. |
| **SCRAPE-FREE** | Public download/scrape, no paid vendor (Cleveland Fed, Opportunity Insights, NY Fed). |
| **VENDOR-PAID** | Licensed — not wired, and we will not fake it (ISM, S&P PMIs, Truflation, Fiserv). |

## Signal philosophy: leading & exogenous, not a policy mirror

A useful real-time signal must (a) move *before* the official macro print, and
(b) not simply be the market pricing the Fed's own next move. Ranked by how well
they satisfy both:

| Quality | Signal | Why |
| --- | --- | --- |
| Best | jobless claims, card-spend, job postings, PMIs, inflation nowcasts | Real economic activity, days-fresh, not a policy forecast |
| Good | credit spreads, the dollar, oil/gas, VIX | Market-priced but driven by conditions, not chiefly Fed-path |
| Weak (avoid as the edge) | Treasury yield curve, fed funds futures | Largely the market's forecast of Fed policy — circular |

---

## 1. Mandate core — the realized truth & the stale official view  `FREE-FRED` · wired

| Series | ID | Freq | Role |
| --- | --- | --- | --- |
| Core PCE price index | `PCEPILFE` | M | inflation (YoY), truth + ALFRED vintage |
| Unemployment rate | `UNRATE` | M | employment gap |
| Fed funds (effective) | `FEDFUNDS` | M | current policy rate |

No-look-ahead: ALFRED vintage query (`realtime_start=realtime_end=as_of`); the
real publication lag and first-release values fall out of the query.

## 2. Inflation expectations  `FREE-FRED` · wired (replaces the faked formula)

| Series | ID | Freq | Role |
| --- | --- | --- | --- |
| 5y TIPS breakeven | `T5YIE` | D | market expectations (feeds `EconomyState`) |
| 5y5y forward breakeven | `T5YIFR` | D | long-run anchoring |
| 10y breakeven | `T10YIE` | D | cross-check |
| UMich 1y expectations | `MICH` | M | household expectations |
| NY Fed SCE (median 1y/3y) | — | M | survey expectations — `SCRAPE-FREE` (next) |

## 3. Labor market depth  `FREE-FRED` · dashboard wired

| Series | ID | Freq | Lead? |
| --- | --- | --- | --- |
| Initial jobless claims | `ICSA` | **W** | **leading** (in the live signal set) |
| Indeed job postings index | `IHLIDXUS` | W | **leading** (in the live signal set) |
| Nonfarm payrolls | `PAYEMS` | M | coincident |
| Job openings (JOLTS) | `JTSJOL` | M | coincident |
| Quits rate (JOLTS) | `JTSQUR` | M | leading wages |
| Avg hourly earnings | `CES0500000003` | M | wages |
| Participation | `CIVPART` | M | structural |
| Prime-age emp-pop | `LNS12300060` | M | slack |
| Atlanta wage tracker | (verify ID) | M | wages — ID to confirm |

## 4. Financial conditions  `FREE-FRED` · in the leading set

| Series | ID | Freq | Lead? |
| --- | --- | --- | --- |
| High-yield OAS | `BAMLH0A0HYM2` | D | **leading** credit stress |
| Investment-grade OAS | `BAMLC0A0CM` | D | leading |
| Chicago Fed NFCI | `NFCI` | W | conditions composite |
| VIX | `VIXCLS` | D | risk appetite |
| 30y mortgage | `MORTGAGE30US` | W | housing transmission |

## 5. FX / the dollar  `FREE-FRED` (history) + `FMP` (intraday) · in the leading set

| Series | ID / symbol | Source | Role |
| --- | --- | --- | --- |
| Broad trade-weighted USD | `DTWEXBGS` | FRED D | import-price pass-through, conditions |
| Advanced-economy USD | `DTWEXAFEGS` | FRED D | cross-check |
| DXY / EURUSD (live) | `DX=F` / `EURUSD` | FMP | intraday for the live tool |

## 6. Energy & commodities  `FREE-FRED` (history) + `FMP` (intraday) · in the leading set

| Series | ID / symbol | Source | Role |
| --- | --- | --- | --- |
| WTI crude | `DCOILWTICO` / `CLUSD` | FRED D / FMP | supply-shock inflation (acute in 2026) |
| Henry Hub gas | `DHHNGSP` | FRED D | energy |
| Regular gasoline | `GASREGW` | FRED W | headline pass-through |

## 7. Real activity & growth  `FREE-FRED` · dashboard wired

| Series | ID | Freq | Role |
| --- | --- | --- | --- |
| Atlanta Fed GDPNow | `GDPNOW` | ~W | growth nowcast |
| Retail sales | `RSAFS` | M | demand |
| Industrial production | `INDPRO` | M | output |
| Philly Fed mfg | `GACDFSA066MSFRBPHI` | M | **leading** (free ISM substitute) |
| Empire State mfg | `GACDISA066MSFRBNY` | M | **leading** (free ISM substitute) |
| Dallas Fed mfg | `BACTSAMFRBDAL` | M | **leading** (free ISM substitute) |

## 8. Money, reserves & the balance sheet  `FREE-FRED` · dashboard wired

| Series | ID | Freq | Role |
| --- | --- | --- | --- |
| Bank reserves | `WRESBAL` | W | liquidity / QT pace |
| Overnight reverse repo | `RRPONTSYD` | D | money-market plumbing |
| Fed total assets | `WALCL` | W | balance sheet |

(Warsh's financial-plumbing focus lands here; this section answers the audit's
"nothing on reserves/balance sheet" gap.)

---

## Where FMP and scraping fit (verified 2026-06-18)

**FMP — two things FRED cannot do:**
- **Economic calendar with consensus + actual** (`/economic-calendar`): gives
  `estimate` and `actual` per release → **surprise = actual − estimate**, a
  leading, non-circular signal, plus exact release dates to pin no-look-ahead.
  Wired: `data_real.economic_surprises()`.
- **Same-day/intraday quotes** (`/quote`): DXY, WTI, `^VIX`, HYG, LQD — fresher
  than FRED's end-of-day for the **live** tool. Wired: `data_real.live_market_signals()`.

**SCRAPE-FREE — the genuinely-missing leading indicators, no vendor:**
- **Cleveland Fed Inflation Nowcasting** — real-time CPI/PCE nowcast with a
  historical archive (clevelandfed.org). *The* real-time inflation signal.
- **Opportunity Insights Economic Tracker** — daily card-spend (Affinity), open
  on GitHub. Free card-spend proxy.
- **NY Fed SCE** — monthly aggregate medians (xlsx, newyorkfed.org).

**VENDOR-PAID — not wired, deliberately not faked:**
- ISM & S&P Global PMIs (licensed; substitute free regional Fed surveys above),
  Truflation API, Fiserv/affinity high-frequency card networks, SCE micro-data.

---

## Build order (highest leverage first)

1. ✅ **Real expectations** (`T5YIE`) — done; kills the faked formula.
2. ✅ **Leading/exogenous signal set** (`ICSA`, `IHLIDXUS`, OAS, VIX, USD, oil) —
   done; replaces the endogenous curve as the freshness edge.
3. ✅ **Broader official dashboard** (labor depth, financial conditions, activity,
   money/balance sheet) — done; un-starves the personas.
4. ✅ **FMP surprise + live-quote helpers** — done.
5. ✅ **Re-ran the edge experiment** with the leading set vs the curve — see
   `FINDINGS.md`. Result: no steady edge at n=4, but leading signals win the
   turning point where the curve loses.
   - ⬜ **5b. Clean controlled A/B** — curve vs leading on identical inputs
     (the two runs differ in expectations/dashboard; not yet a controlled test).
6. ⬜ **Cleveland Fed inflation nowcast** (`SCRAPE-FREE`) — add the real-time
   inflation signal.
7. ⬜ **Opportunity Insights card-spend** (`SCRAPE-FREE`) — add demand nowcast.
8. ⬜ **More dates** across regimes (n is still small) for a real scorecard.

Items 1–4 are implemented in `data_real.py` and verified against the live APIs.
Items 5–8 are the path from "credible demonstrator" to "scorecard."
