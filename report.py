"""
report.py -- generate a self-contained, professional HTML report.

Reads the latest real backtest run(s) and a committee transcript from runs/ and
renders a single styled report.html (inline CSS, no external dependencies, no
network). This is the shareable leave-behind; open it in a browser and "Print to
PDF" for a PDF. It presents the honest finding -- not a manufactured edge.

Run:
    python report.py            # -> report.html
"""

from __future__ import annotations

import glob
import html
import json
import datetime
from pathlib import Path

HERE = Path(__file__).parent
RUNS = HERE / "runs"
REPO = "https://github.com/smaan712gb/agentic-fed-taskforce"


def _latest(pattern: str):
    files = sorted(glob.glob(str(RUNS / pattern)), reverse=True)
    return files[0] if files else None


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def _find_backtests():
    """Return (leading_run, curve_run) -- newest of each signal mode."""
    leading = curve = None
    for f in sorted(glob.glob(str(RUNS / "backtest_real-*.json")), reverse=True):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        if "mean_fresh" not in d:
            continue
        mode = d.get("signal_mode", "curve")
        if mode == "leading" and leading is None:
            leading = d
        if mode == "curve" and curve is None:
            curve = d
    return leading, curve


def _scorecard_html(d: dict, title: str) -> str:
    if not d:
        return ""
    bd = d.get("by_date", {})
    rows = "".join(
        f"<tr><td>{html.escape(r['date'])}</td>"
        f"<td>{r['stale_loss_mean']:.3f}</td>"
        f"<td>{r['fresh_loss_mean']:.3f}</td>"
        f"<td class='{ 'win' if r['better_by_mean']=='fresh' else 'lose' }'>{r['better_by_mean']}</td>"
        f"<td>{html.escape(str(r.get('fresh_wins_of_runs','')))}</td></tr>"
        for r in d.get("rows", [])
    )
    edge = d.get("improvement_pct", 0)
    edge_cls = "win" if edge > 0 else "lose"
    return f"""
    <h3>{html.escape(title)} <span class="muted">(signal mode: {html.escape(d.get('signal_mode','?'))}, {d.get('runs_per_date')} runs/date)</span></h3>
    <div class="metrics">
      <div class="metric"><div class="v">{d['mean_stale']:.3f}</div><div class="l">mean loss — stale</div></div>
      <div class="metric"><div class="v">{d['mean_fresh']:.3f}</div><div class="l">mean loss — fresh</div></div>
      <div class="metric"><div class="v {edge_cls}">{edge:+.1f}%</div><div class="l">edge from signals</div></div>
      <div class="metric"><div class="v">{bd.get('fresh',0)}/{bd.get('stale',0)}/{bd.get('tie',0)}</div><div class="l">by-date fresh/stale/tie</div></div>
    </div>
    <table>
      <thead><tr><th>FOMC date</th><th>stale loss</th><th>fresh loss</th><th>winner</th><th>fresh wins of runs</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>"""


def _committee_html(d: dict) -> str:
    if not d:
        return "<p class='muted'>No committee transcript found.</p>"
    dec = d.get("decision", {})
    rt = d.get("red_team", {})
    base = d.get("baseline", {})
    diss = "".join(f"<li>{html.escape(x)}</li>" for x in dec.get("dissents", []))
    chal = "".join(f"<li>{html.escape(x)}</li>" for x in rt.get("challenges", []))
    v = d.get("verdict", {})
    return f"""
    <p><b>Baseline (Taylor rule):</b> <code>{html.escape(str(base.get('rate_path')))}</code>
       — total_loss {base.get('score',{}).get('total_loss')}</p>
    <p><b>Red-team:</b> {'FATAL — not adoptable' if rt.get('fatal') else 'survived'}.
       {html.escape(rt.get('summary',''))}</p>
    <ul>{chal}</ul>
    <p><b>Chair's decision:</b> <code>{html.escape(str(dec.get('rate_path')))}</code>
       — total_loss {dec.get('score',{}).get('total_loss')}</p>
    <p class="stmt">“{html.escape(dec.get('statement',''))}”</p>
    {f'<p><b>Dissents preserved:</b></p><ul>{diss}</ul>' if diss else ''}
    <p class="muted">Verdict — beat baseline: {v.get('beat_baseline')} ·
       survived red-team: {v.get('survived_red_team')} · success: {v.get('success')}</p>"""


def build() -> Path:
    leading, curve = _find_backtests()
    transcript = _load(_latest("committee-*.json"))
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agentic Fed Task Force — Report</title>
<style>
  :root {{ --ink:#1a1a2e; --muted:#6b7280; --line:#e5e7eb; --accent:#1f3a5f;
           --win:#0a7d34; --lose:#b4232b; }}
  * {{ box-sizing:border-box; }}
  body {{ font:16px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
          color:var(--ink); max-width:880px; margin:0 auto; padding:48px 28px; }}
  h1 {{ font-size:30px; margin:0 0 4px; }}
  h2 {{ font-size:22px; margin:40px 0 10px; border-bottom:2px solid var(--accent);
        padding-bottom:6px; color:var(--accent); }}
  h3 {{ font-size:17px; margin:24px 0 8px; }}
  .sub {{ color:var(--muted); margin:0 0 8px; }}
  .muted {{ color:var(--muted); font-weight:normal; font-size:14px; }}
  .callout {{ background:#f6f8fb; border-left:4px solid var(--accent);
              padding:14px 18px; border-radius:6px; margin:16px 0; }}
  .metrics {{ display:flex; gap:12px; flex-wrap:wrap; margin:14px 0; }}
  .metric {{ flex:1; min-width:150px; background:#fafbfc; border:1px solid var(--line);
             border-radius:8px; padding:12px 14px; text-align:center; }}
  .metric .v {{ font-size:22px; font-weight:700; }}
  .metric .l {{ font-size:12px; color:var(--muted); margin-top:2px; }}
  table {{ border-collapse:collapse; width:100%; margin:10px 0; font-size:14px; }}
  th,td {{ border:1px solid var(--line); padding:7px 10px; text-align:left; }}
  th {{ background:#f3f5f8; }}
  .win {{ color:var(--win); font-weight:700; }}
  .lose {{ color:var(--lose); font-weight:700; }}
  code {{ background:#f3f5f8; padding:1px 5px; border-radius:4px; font-size:13px; }}
  .stmt {{ font-style:italic; color:#333; }}
  footer {{ margin-top:48px; padding-top:14px; border-top:1px solid var(--line);
            color:var(--muted); font-size:13px; }}
</style></head><body>

<h1>Agentic Fed Task Force</h1>
<p class="sub">A transparent decision-support &amp; red-team system for the dual mandate · generated {now}</p>

<div class="callout">
<b>What this is.</b> A working, reproducible tool that treats the dual mandate as
a loss function, lets a logged and adversarially-tested committee of model
personas propose and defend rate paths, and scores every decision against real
outcomes with no look-ahead. It is decision-support and a red-team — <b>not</b> a
replacement for the FOMC and not a claim to beat it.
</div>

<h2>The honest finding</h2>
<p>On real FOMC dates, real-time signals show <b>no steady edge</b> at this small
sample. But at the <b>turning point</b> (July 2023, hot inflation), leading
indicators — jobless claims, job postings, credit spreads — made the fresh
committee <b>win</b>, where the endogenous Treasury yield curve had made it
<b>lose</b>. The robust read: real-time data is <b>insurance at turning points,
not a free gain</b>, and the <i>kind</i> of signal matters most exactly when it
matters most. Four dates is a pilot, not a verdict.</p>

<h2>Backtest scorecard (real data, real committee, no look-ahead)</h2>
{_scorecard_html(leading, "Leading / exogenous signal set") or "<p class='muted'>No leading-mode run found.</p>"}
{_scorecard_html(curve, "Treasury yield curve (endogenous — for comparison)")}
<p class="muted">Note: the curve and leading runs are not a perfectly controlled
A/B (expectations/dashboard differ). The per-date winners and the turning-point
flip are the reliable reads. Lower loss is better.</p>

<h2>A committee deliberation (sample transcript)</h2>
{_committee_html(transcript)}

<h2>Method &amp; integrity</h2>
<ul>
  <li><b>No look-ahead</b>, structurally: official data is the ALFRED vintage as
      known on the date; realized truth is fetched separately and used only to score.</li>
  <li><b>Agents never grade themselves</b> — a fixed objective scores every path.</li>
  <li><b>No faked inputs</b> — inflation expectations use real TIPS breakevens, not a formula.</li>
  <li><b>Honest reporting</b> — negative and nuanced results are shown, not hidden.</li>
</ul>

<footer>
Reproducible from a clean checkout: <a href="{REPO}">{REPO}</a> ·
full reading in FINDINGS.md · data dashboard in DATA-SOURCES.md · MIT licensed.
</footer>
</body></html>"""

    out = HERE / "report.html"
    out.write_text(doc, encoding="utf-8")
    return out


if __name__ == "__main__":
    path = build()
    print(f"Report written to {path}")
    print("Open it in a browser; use Print -> Save as PDF for a PDF.")
