"""V5 analysis: equity curve, drawdown, effective n, splits, concentration,
overlay. Writes portfolio_results.json and PORTFOLIO.md."""

import bisect
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import simlib
from simlib import sr
from run_ablation import net_r_legs, save_json
from run_portfolio import START_EQUITY

BASE = simlib.BASE
BPS_HEADLINE = 0.005


def load(name):
    with open(os.path.join(BASE, name)) as fh:
        return json.load(fh)


trades = load("canonical_trades.json")
for t in trades:
    t["net_r_50bps"] = net_r_legs(t, BPS_HEADLINE)
    t["net_usd_50bps"] = t["net_r_50bps"] * t["risk_usd"]

print(f"V5 trades: {len(trades)}", flush=True)

# --------------------------------------------------------------------------
# equity curve (marked at 4H closes)
# --------------------------------------------------------------------------

syms = sorted({t["symbol"] for t in trades})
closes = {}
for s in syms:
    df = simlib.load_h4(s)
    m = {}
    for ts, c in zip(df.index, df["Close"].to_numpy()):
        m[sr.bar_close_at(ts, s).isoformat()] = float(c)
    closes[s] = m

marks = set()
tr_bounds = []
for t in trades:
    s = t["symbol"]
    ec = sr.bar_close_at(pd.Timestamp(t["entry_ts"]), s).isoformat()
    xc = sr.bar_close_at(pd.Timestamp(t["exit_ts"]), s).isoformat()
    tr_bounds.append((s, ec, xc))
    cm = closes[s]
    for k in cm:
        if ec <= k <= xc:
            marks.add(k)
tl = sorted(marks)
n = len(tl)
realized = np.zeros(n)
unreal = np.zeros(n)
for t, (s, ec, xc) in zip(trades, tr_bounds):
    i_e = bisect.bisect_left(tl, t["entry_ts"])
    realized[i_e:] -= t["entry_cost"]
    if t["tp1_taken"]:
        i_t = bisect.bisect_left(tl, t["tp1_fill_ts"])
        realized[i_t:] -= t["tp1_cost"]
    i_x = bisect.bisect_left(tl, t["exit_ts"])
    realized[i_x:] += t["gross_usd"] - t["exit_cost"]
    # unreal marks in [ec, xc)
    i0 = bisect.bisect_left(tl, ec)
    i1 = bisect.bisect_left(tl, xc)
    cm = closes[s]
    sh = t["shares"]
    tc = (sr.bar_close_at(pd.Timestamp(t["tp1_fill_ts"]), s).isoformat()
          if t["tp1_taken"] else None)
    entry = t["entry"]
    for i in range(i0, i1):
        px = cm.get(tl[i])
        if px is None:
            continue
        sh_i = sh / 2.0 if (tc is not None and tl[i] >= tc) else sh
        unreal[i] += (px - entry) * sh_i

equity = START_EQUITY + realized + unreal
peak = np.maximum.accumulate(equity)
dd = (equity - peak) / peak
max_dd = float(dd.min())
max_dd_usd = float((equity - peak).min())
t_end_days = (pd.Timestamp(tl[-1]) - pd.Timestamp(tl[0])).days or 1
cagr = float((equity[-1] / START_EQUITY) ** (365.25 / t_end_days) - 1)
print(f"equity: start {equity[0]:.0f} end {equity[-1]:.0f} "
      f"maxDD {max_dd*100:.1f}% (${max_dd_usd:,.0f}) CAGR {cagr*100:.1f}%",
      flush=True)

# --------------------------------------------------------------------------
# effective n: overlap episodes
# --------------------------------------------------------------------------

n_ep, sizes, _assign = simlib.overlap_episodes(trades)
# max concurrent open (sanity: bounded by MAX_OPEN=6 by construction)
ev = []
for t in trades:
    ev.append((t["entry_ts"], 1))
    ev.append((t["exit_ts"], -1))
ev.sort(key=lambda x: (x[0], -x[1]))
cur = mx = 0
for _, d_ in ev:
    cur += d_
    mx = max(mx, cur)

print(f"episodes: {n_ep}, avg size {np.mean(sizes):.1f}, "
      f"largest episode {max(sizes)} trades, max concurrent {mx}", flush=True)

# --------------------------------------------------------------------------
# splits: year, regime
# --------------------------------------------------------------------------

def exit_year(t):
    return pd.Timestamp(t["exit_ts"]).year

reg = simlib.build_regime()


def regime_at_signal(signal_close_iso):
    # last completed daily bar at signal time (regime_at uses side="right",
    # so pass the signal close; a 16:00 signal close coincides with the
    # daily close and is complete at that instant)
    return simlib.regime_at(reg, pd.Timestamp(signal_close_iso))

for t in trades:
    t["exit_year"] = exit_year(t)
    t["regime"] = regime_at_signal(t["signal_bar_close_at"])

def split_stats(key):
    groups = defaultdict(list)
    for t in trades:
        groups[t[key]].append(t["net_r_50bps"])
    return {str(k): {"n": len(v), "expectancy_r": round(float(np.mean(v)), 4),
                     "win_rate_pct": round(float((np.array(v) > 0).mean() * 100), 1),
                     "total_r": round(float(np.sum(v)), 2)}
            for k, v in sorted(groups.items())}

year_stats = split_stats("exit_year")
regime_stats = split_stats("regime")

# --------------------------------------------------------------------------
# concentration
# --------------------------------------------------------------------------

by_r = sorted(trades, key=lambda t: t["net_r_50bps"], reverse=True)
top10 = by_r[:10]
top10_sum = float(sum(t["net_r_50bps"] for t in top10))
rest = by_r[10:]
ex_top10 = {"n": len(rest),
            "expectancy_r": round(float(np.mean([t["net_r_50bps"] for t in rest])), 4)} \
    if rest else {}

sym_tot = defaultdict(float)
sym_n = defaultdict(int)
for t in trades:
    sym_tot[t["symbol"]] += t["net_r_50bps"]
    sym_n[t["symbol"]] += 1
top_syms = sorted(sym_tot.items(), key=lambda x: x[1], reverse=True)[:8]

yr_tot = {k: v["total_r"] for k, v in year_stats.items()}
best_year = max(yr_tot, key=yr_tot.get)
ex_best = [t["net_r_50bps"] for t in trades
           if str(t["exit_year"]) != str(best_year)]
ex_best_year = {"excluded_year": best_year, "n": len(ex_best),
                "expectancy_r": round(float(np.mean(ex_best)), 4)} if ex_best else {}

secraw = load("sectors_raw.json")
secmap = {s: (v.get("sector") or v.get("quoteType") or "Unknown")
          for s, v in secraw.items()}
sec_tot = defaultdict(float)
for t in trades:
    sec_tot[secmap.get(t["symbol"], "Unknown")] += t["net_r_50bps"]
top_secs = sorted(sec_tot.items(), key=lambda x: x[1], reverse=True)[:8]

# hypothetical max-2-per-sector bind frequency on accepted V5 trades
batch_sec = defaultdict(lambda: defaultdict(int))
for t in trades:
    batch_sec[t["signal_bar_close_at"]][secmap.get(t["symbol"], "Unknown")] += 1
bind_batches = sum(1 for b in batch_sec.values()
                   if any(c > 2 for c in b.values()))
excess = sum(max(0, c - 2) for b in batch_sec.values() for c in b.values())

# --------------------------------------------------------------------------
# assemble results
# --------------------------------------------------------------------------

v4 = load("v4_cost_ladder.json")
v0v3 = load("ablation_V0_V3.json")
v5sum = load("v5_summary.json")
ov = load("v5_overlay14.json")

results = {
    "universe": "PIT 131-name (strict point-in-time contract, see PIT_FEATURES.md)",
    "window": "signal window per symbol: max(eligible_from, effective_4h_from) "
              "-> min(eligible_to, last 4H bar 2026-09-24)",
    "book": {"start_equity_usd": START_EQUITY, "risk_per_trade_usd": 750.0,
             "max_open": 6, "heat_cap_pct": 5.0,
             "sizing": "shares = floor(750 / (entry - stop))"},
    "cost_model": "round-trip leg-based: cost_$ = (bps/2) x sum(leg notionals); "
                  "entry full-size leg + exit legs (TP1 = half-size leg, "
                  "runner = half-size leg). Headline = 50bps round trip.",
    "ladder": {
        "V0": v0v3["V0"],
        "V1": v0v3["V1"],
        "V2": v0v3["V2"],
        "V2_realistic_gaps": v0v3["V2 realistic-gaps"],
        "V3": v0v3["V3"],
        "V4_cost_ladder": v4,
        "V5_cost_ladder": v5sum["levels"],
        "V5_skip_counts": v5sum["skip_counts"],
    },
    "V5_headline_50bps": {
        "n_trades": len(trades),
        "expectancy_r": round(float(np.mean([t["net_r_50bps"] for t in trades])), 4),
        "win_rate_pct": round(float((np.array([t["net_r_50bps"] for t in trades]) > 0).mean() * 100), 1),
        "profit_factor": (lambda rs: round(float(rs[rs > 0].sum() / -rs[rs <= 0].sum()), 2))(np.array([t["net_r_50bps"] for t in trades])),
        "total_r": round(float(sum(t["net_r_50bps"] for t in trades)), 2),
        "max_drawdown_pct": round(max_dd * 100, 1),
        "max_drawdown_usd": round(max_dd_usd, 0),
        "max_drawdown_r": round(max_dd_usd / 750.0, 1),
        "effective_n_episodes": n_ep,
        "avg_trades_per_episode": round(float(np.mean(sizes)), 1),
        "largest_episode_trades": int(max(sizes)),
        "max_concurrent_positions": int(mx),
        "annualized_return_pct": round(cagr * 100, 1),
        "total_return_pct": round((equity[-1] / START_EQUITY - 1) * 100, 1),
        "equity_start_usd": round(float(equity[0]), 0),
        "equity_end_usd": round(float(equity[-1]), 0),
        "open_at_end": int(sum(1 for t in trades if t.get("open_at_end"))),
    },
    "year_split": year_stats,
    "regime_split": regime_stats,
    "concentration": {
        "top10_trades_net_r": round(top10_sum, 2),
        "top10_share_of_total_pct": round(
            top10_sum / sum(t["net_r_50bps"] for t in trades) * 100, 1)
        if sum(t["net_r_50bps"] for t in trades) != 0 else None,
        "top10_trades": [{"symbol": t["symbol"],
                          "signal_bar_close_at": t["signal_bar_close_at"],
                          "net_r": round(t["net_r_50bps"], 2),
                          "exit_reason": t["exit_reason"]} for t in top10],
        "ex_top10": ex_top10,
        "top_symbols": [{"symbol": s, "n": sym_n[s],
                         "total_r": round(r, 2)} for s, r in top_syms],
        "best_year": best_year,
        "ex_best_year": ex_best_year,
        "top_sectors": [{"sector": s, "total_r": round(r, 2)}
                        for s, r in top_secs],
        "hypothetical_max2_per_sector": {
            "batches_with_gt2_same_sector": bind_batches,
            "excess_trades": excess,
            "note": "no such rule exists in live V5.4; hypothetical only",
        },
    },
    "overlay14": ov["levels"],
    "overlay14_note": "14-name watchlist run separately with identical V5 "
                      "machinery; NOT the canonical universe.",
}
save_json("portfolio_results.json", results)

# --------------------------------------------------------------------------
# PORTFOLIO.md
# --------------------------------------------------------------------------

v = results["ladder"]
h = results["V5_headline_50bps"]
d = lambda a, b: round(a - b, 4)

md = []
md.append("# Canonical Portfolio Baseline — V5 (PIT 131-name universe)")
md.append("")
md.append(f"_Generated 2026-09-24. Universe: PIT 131-name (strict point-in-time "
          f"contract, `PIT_FEATURES.md`)._")
md.append("")
md.append("## Headline (V5 @ 50bps round trip, $75k book)")
md.append("")
md.append(f"- **Expectancy:** {h['expectancy_r']}R/trade")
md.append(f"- **Win rate:** {h['win_rate_pct']}%")
md.append(f"- **Profit factor:** {h['profit_factor']}")
md.append(f"- **Max drawdown:** {h['max_drawdown_pct']}% "
          f"(${h['max_drawdown_usd']:,.0f}, {h['max_drawdown_r']}R)")
md.append(f"- **Trades:** {h['n_trades']}")
md.append(f"- **Effective n (overlap episodes):** {h['effective_n_episodes']} "
          f"(avg {h['avg_trades_per_episode']} trades/episode, largest "
          f"{h['largest_episode_trades']} trades, max {h['max_concurrent_positions']} "
          f"concurrent). _Note: with a near-continuously occupied book, "
          f"episodes chain into a handful of long clusters._")
md.append(f"- **Annualized return:** {h['annualized_return_pct']}% "
          f"(total {h['total_return_pct']}%, "
          f"${h['equity_start_usd']:,.0f} -> ${h['equity_end_usd']:,.0f})")
md.append(f"- Positions still open at sample end (marked, not force-closed): "
          f"{h['open_at_end']}")
md.append("")
md.append("## Method")
md.append("")
md.append("- **Signals:** frozen V5.4 logic (`v54_engine.v54_classify`), all "
          "grades A/B/C, strict PIT (structural contract, ADX>=20, no scores). "
          "Entry at next 4H bar open; signal bar = last bar before entry.")
md.append("- **Exits:** frozen Mode B (structural stop always on, 50% at TP1, "
          "+1R arms Profit Protect, armed scanner-EXIT fills next-bar open, "
          "runner keeps structural stop, 30-bar max hold, stop wins ties). "
          "Live-faithful convention: stop filled AT the stop on gap-through "
          "bars (optimistic); realistic-gap variant also run.")
md.append("- **Sizing:** $75k book, $750 fixed risk/trade "
          "(shares = floor(750/(entry-stop))), max 6 open, ~5% heat cap "
          "(sum of current position risks / marked equity).")
md.append("- **Slot competition:** when qualified signals exceed free slots, "
          "rank by `rs_top2` (20-bar 4H return minus SPY, strict PIT; "
          "unrankable signals sort last), tie-break by signal timestamp then "
          "symbol. One position per symbol (live `_busy` rule); a signal on a "
          "symbol with an open/pending position is skipped.")
md.append("- **Costs:** round-trip, leg-based: "
          "cost_$ = (bps/2) x sum of leg notionals. Entry = full-size leg; "
          "exits: TP1 = half-size leg, runner = half-size leg (or full-size "
          "leg if no TP1). A standard round trip = 2 leg-equivalents, so cost "
          "= bps x notional. Headline = 50bps.")
md.append("- **Equity:** marked at 4H closes; costs deducted at event legs; "
          "open positions at sample end are marked, not force-closed.")
md.append("")
md.append("## Ablation ladder (expectancy, R/trade)")
md.append("")
md.append("| Variant | n | E[R] | Win% | PF |")
md.append("|---|---|---|---|---|")
for key, label in [("V0", "V0: old system, 14-name (sanity)"),
                   ("V1", "V1: old system, 131-name (UNIVERSE)"),
                   ("V2", "V2: V3.6 entries + Mode B (MODE B)"),
                   ("V3", "V3: v54 entries + Mode B (PIT/entries)")]:
    s = v[key]
    md.append(f"| {label} | {s['n']} | {s['expectancy_r']} | "
              f"{s['win_rate_pct']} | {s['profit_factor']} |")
for bps in ["25bps", "50bps", "75bps", "100bps"]:
    s = v["V4_cost_ladder"][bps]
    md.append(f"| V4 @ {bps} (leg-based costs) | {s['n']} | "
              f"{s['expectancy_r']} | {s['win_rate_pct']} | {s['profit_factor']} |")
for bps in ["25bps", "50bps", "75bps", "100bps"]:
    s = v["V5_cost_ladder"][bps]
    md.append(f"| V5 @ {bps} (portfolio) | {s['n']} | {s['expectancy_r']} | "
              f"{s['win_rate_pct']} | {s['profit_factor']} |")
md.append("")
md.append("### Deltas (isolated step effects)")
md.append("")
md.append(f"- **V0 -> V1 (universe only):** {v['V0']['expectancy_r']} -> "
          f"{v['V1']['expectancy_r']} = **{d(v['V1']['expectancy_r'], v['V0']['expectancy_r'])}R**. "
          f"The old system's edge does not survive the neutral PIT universe "
          f"(n: {v['V0']['n']} -> {v['V1']['n']}).")
md.append(f"- **V1 -> V2 (Mode B exits):** {v['V1']['expectancy_r']} -> "
          f"{v['V2']['expectancy_r']} = **{d(v['V2']['expectancy_r'], v['V1']['expectancy_r'])}R** "
          f"(same V3.6 entries; exit change only).")
md.append(f"- **V2 -> V3 (v54 entries, strict PIT):** {v['V2']['expectancy_r']} -> "
          f"{v['V3']['expectancy_r']} = **{d(v['V3']['expectancy_r'], v['V2']['expectancy_r'])}R** "
          f"(structural-contract entries, ADX>=20, no scores; n: {v['V2']['n']} -> {v['V3']['n']}).")
md.append(f"- **Gap realism (V2 live-faithful vs realistic):** "
          f"{v['V2']['expectancy_r']} -> {v['V2_realistic_gaps']['expectancy_r']} = "
          f"**{d(v['V2_realistic_gaps']['expectancy_r'], v['V2']['expectancy_r'])}R**. "
          f"Live-faithful stop fills at the stop on gap-through bars are "
          f"optimistic by ~0.04R.")
md.append(f"- **V3 -> V4 @50bps (costs):** {v['V3']['expectancy_r']} -> "
          f"{v['V4_cost_ladder']['50bps']['expectancy_r']} = "
          f"**{d(v['V4_cost_ladder']['50bps']['expectancy_r'], v['V3']['expectancy_r'])}R** "
          f"(25bps-once convention -> 50bps leg-based round trip).")
md.append(f"- **V4 -> V5 @50bps (portfolio):** "
          f"{v['V4_cost_ladder']['50bps']['expectancy_r']} -> "
          f"{v['V5_cost_ladder']['50bps']['expectancy_r']} = "
          f"**{d(v['V5_cost_ladder']['50bps']['expectancy_r'], v['V4_cost_ladder']['50bps']['expectancy_r'])}R** "
          f"(slots/heat/ranking filter {v['V3']['n']} -> {v['V5_cost_ladder']['50bps']['n']} trades).")
md.append("")
md.append("_Bridge note:_ V0 mixes legacy V3.6 entries/exits with the 14-name "
          "watchlist; V1..V5 use the PIT 131-universe. The V0->V1 step is a "
          "universe-only comparison (same engine/exits/costs); the V2->V3 step "
          "changes the entry definition (V3.6 Hybrid -> v54 structural "
          "contract), so it is not a pure PIT effect — it bundles the "
          "entry-definition change with strict-PIT enforcement.")
md.append("")
md.append("### V5 signal funnel")
md.append("")
sc = v["V5_skip_counts"]
md.append(f"- Candidate v54 signals: {sc['candidates']}")
md.append(f"- Skipped (symbol busy — live `_busy` rule): {sc['busy']}")
md.append(f"- Skipped (no free slot, lost rs_top2 rank): {sc['slot']}")
md.append(f"- Skipped (5% heat cap): {sc['heat']}")
md.append(f"- **Accepted: {v['V5_cost_ladder']['50bps']['n']}**")
md.append("")
md.append("## Splits")
md.append("")
md.append("### By exit year (@50bps)")
md.append("")
md.append("| Year | n | E[R] | Win% | Total R |")
md.append("|---|---|---|---|---|")
for y, s in results["year_split"].items():
    md.append(f"| {y} | {s['n']} | {s['expectancy_r']} | {s['win_rate_pct']} | "
              f"{s['total_r']} |")
md.append("")
md.append("### By market regime at signal (@50bps)")
md.append("")
md.append("_Regime: bull = SPY close > EMA200 and EMA200 rising vs 20 daily "
          "bars ago; bear = below and falling; else sideways. Joined on the "
          "last completed daily bar at signal time._")
md.append("")
md.append("| Regime | n | E[R] | Win% | Total R |")
md.append("|---|---|---|---|---|")
for r, s in results["regime_split"].items():
    md.append(f"| {r} | {s['n']} | {s['expectancy_r']} | {s['win_rate_pct']} | "
              f"{s['total_r']} |")
md.append("")
md.append("## Concentration")
md.append("")
c = results["concentration"]
md.append(f"- **Top 10 trades:** {c['top10_trades_net_r']}R total "
          f"({c['top10_share_of_total_pct']}% of total). "
          f"Ex-top-10 expectancy: {c['ex_top10']['expectancy_r']}R "
          f"(n={c['ex_top10']['n']}).")
for t in c["top10_trades"]:
    md.append(f"  - {t['symbol']} {t['signal_bar_close_at'][:10]}: "
              f"{t['net_r']}R ({t['exit_reason']})")
md.append(f"- **Top symbols by total R:** " +
          ", ".join(f"{s['symbol']} ({s['total_r']}R, n={s['n']})"
                    for s in c["top_symbols"]))
md.append(f"- **Best year:** {c['best_year']}. Ex-best-year expectancy: "
          f"{c['ex_best_year']['expectancy_r']}R (n={c['ex_best_year']['n']}).")
md.append(f"- **Top sectors by total R:** " +
          ", ".join(f"{s['sector']} ({s['total_r']}R)"
                    for s in c["top_sectors"]))
hb = c["hypothetical_max2_per_sector"]
md.append(f"- **Hypothetical max-2-per-sector rule:** would have bound on "
          f"{hb['batches_with_gt2_same_sector']} signal batches "
          f"({hb['excess_trades']} excess trades). No such rule exists in "
          f"live V5.4 — hypothetical only.")
md.append("")
md.append("## 14-name watchlist overlay (separate — NOT canonical)")
md.append("")
md.append("_Same V5 machinery, restricted to the 14-name watchlist. "
          "Reported for comparison only._")
md.append("")
md.append("| Cost | n | E[R] | Win% | PF |")
md.append("|---|---|---|---|---|")
for bps in ["25bps", "50bps", "75bps", "100bps"]:
    s = results["overlay14"][bps]
    md.append(f"| {bps} | {s['n']} | {s['expectancy_r']} | {s['win_rate_pct']} | "
              f"{s['profit_factor']} |")
md.append("")
md.append("## Caveats")
md.append("")
md.append("- Live-faithful Mode B fills stops AT the stop on gap-through "
          "bars (optimistic by ~0.04R vs realistic gap fills).")
md.append("- No capital-availability constraint beyond slots/heat; notional "
          "tied up is tracked but not enforced.")
md.append("- Regime join uses the last completed daily SPY bar at signal time.")
md.append("- Effective n uses overlap-episode clustering (connected "
          "components of overlapping holding intervals).")
md.append("- 4H bars for US names cover 09:30-16:00 ET only; crypto is 24/7.")
md.append("")
md.append("## Files")
md.append("")
for f in ["portfolio_results.json", "canonical_trades.json",
          "v0_trades.json", "v1_trades.json", "v2_trades.json",
          "v3_trades.json", "v4_cost_ladder.json", "v5_summary.json",
          "v5_overlay14.json", "ablation_V0_V3.json", "simlib.py",
          "run_ablation.py", "run_portfolio.py", "analyze.py"]:
    md.append(f"- `canonical_baseline/{f}`")
md.append("")

with open(os.path.join(BASE, "PORTFOLIO.md"), "w") as fh:
    fh.write("\n".join(md))
print("wrote PORTFOLIO.md + portfolio_results.json", flush=True)
