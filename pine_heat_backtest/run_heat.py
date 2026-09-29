"""Priority 12: Portfolio heat — do later trades added to an already-loaded
portfolio have worse expectancy?

Question: does performance depend on total portfolio heat at the moment a new
trade is taken? Measurement study only — NO new filter, no threshold tuning.

Setup: 14-stock watchlist, 4H bars Oct 2023-Sep 2026, canonical pine_buy_signal
+ gen_pine_trades (pine_backtest imported UNMODIFIED), frozen Mode B exits,
25bps costs, full portfolio sim with heat recording (custom sim is a
line-for-line copy of pine_backtest.simulate_portfolio plus heat hooks).

Heat at entry = sum(risk_dollars of open positions) / marked equity * 100,
recorded BEFORE the new position is added. Buckets pre-declared:
<2%, 2-3%, 3-4%, 4-5%, 5% (cap).

Also recorded per taken trade: portfolio-level MAE while the trade was open
(min marked equity between entry and exit, relative to entry equity).

Verdict standard: are high-heat entries clearly worse across years (MAYBE,
supports a future heat-based admission rule) or flat (NO)?

Research only. No frozen files modified.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_heat_backtest")
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, BASE)
import pine_backtest as pb

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
H4CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
COST = 0.0025  # 25 bps
RISK_PCT = pb.RISK_PCT  # 0.01


def simulate_with_heat(trades, closes, cost, risk_pct):
    """Line-for-line copy of pb.simulate_portfolio, plus per-trade heat
    recording at entry and portfolio-MAE tracking while open."""
    events = []
    for t in trades:
        events.append((t["exit_time"], 0, t))
        events.append((t["entry_time"], 1, t))
    events.sort(key=lambda e: (e[0], e[1]))
    realized = pb.START_EQUITY
    open_pos, by_id = [], {}
    skipped_cap_count = skipped_cap_risk = 0
    peak, max_dd = realized, 0.0
    curve, prev_t = [], None
    open_time = total_time = pd.Timedelta(0)

    def mark(sym, t):
        s = closes[sym]
        idx = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[idx]) if idx >= 0 else float(s.iloc[0])

    def marked_equity(t):
        unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
                     for p, tr in ((p, p["trade"]) for p in open_pos))
        return realized + unreal

    for t, kind, tr in events:
        if prev_t is not None and t > prev_t:
            dt = t - prev_t
            total_time += dt
            if open_pos:
                open_time += dt
        prev_t = t
        if kind == 1:
            eq = marked_equity(t)
            open_risk = sum(p["risk_dollars"] for p in open_pos) / eq if eq > 0 else 1
            if len(open_pos) >= pb.MAX_CONCURRENT:
                skipped_cap_count += 1
                continue
            if open_risk + risk_pct > pb.MAX_PORTFOLIO_RISK + 1e-9:
                skipped_cap_risk += 1
                continue
            risk_dollars = risk_pct * eq
            risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
            # --- heat hook: heat BEFORE this position is added ---
            tr["_heat_pct"] = round(float(open_risk * 100), 3)
            tr["_entry_eq"] = float(eq)
            tr["_n_open_at_entry"] = len(open_pos)
            pos = {"trade": tr, "risk_dollars": risk_dollars,
                   "size": risk_dollars / risk_frac, "risk_frac": risk_frac,
                   "_min_eq": float(eq)}
            open_pos.append(pos)
            by_id[id(tr)] = pos
        else:
            pos = by_id.pop(id(tr), None)
            if pos is None:
                continue
            _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
            realized += pos["risk_dollars"] * net_r
            open_pos.remove(pos)
        eq = marked_equity(t)
        for p in open_pos:
            if eq < p["_min_eq"]:
                p["_min_eq"] = eq
        # portfolio MAE for the trade that just exited
        if kind == 0 and pos is not None:
            entry_eq = tr.get("_entry_eq")
            tr["_port_mae_pct"] = round((pos["_min_eq"] / entry_eq - 1) * 100, 3) \
                if entry_eq else None
        curve.append((t, eq, realized, len(open_pos)))
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    exposure = float(open_time / total_time) if total_time > pd.Timedelta(0) else 0.0
    return {"final_equity": realized, "max_drawdown": max_dd,
            "skipped_cap_count": skipped_cap_count,
            "skipped_cap_risk": skipped_cap_risk,
            "exposure": exposure, "curve": curve}


def heat_bin(h):
    if h < 2:
        return "<2%"
    if h < 3:
        return "2-3%"
    if h < 4:
        return "3-4%"
    if h < 5:
        return "4-5%"
    return "5% (cap)"


def bucket_stats(trades):
    t = pd.DataFrame(trades)
    n = len(t)
    wins = t[t["net_r"] > 0]
    gw = wins["net_r"].sum()
    gl = -t[t["net_r"] <= 0]["net_r"].sum()
    mae = t["_port_mae_pct"].dropna() if "_port_mae_pct" in t.columns \
        else pd.Series(dtype=float)
    return {
        "n": n,
        "expectancy_r": round(float(t["net_r"].mean()), 3),
        "win_rate_pct": round(len(wins) / n * 100, 1),
        "profit_factor": round(gw / gl, 2) if gl > 0 else None,
        "total_r": round(float(t["net_r"].sum()), 2),
        "avg_port_mae_pct": round(float(mae.mean()), 3) if len(mae) else None,
        "avg_n_open_at_entry": round(float(t["_n_open_at_entry"].mean()), 2),
    }


def main():
    print("generating baseline trades...", flush=True)
    all_trades, closes = [], {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(H4CACHE, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        closes[sym] = df["Close"]
        tr, sg = pb.gen_pine_trades(sym, df)
        all_trades.extend(tr)
        print(f"  {sym}: {len(tr)} trades", flush=True)
    all_trades.sort(key=lambda t: t["entry_time"])
    print(f"generated: {len(all_trades)}", flush=True)

    for t in all_trades:
        t["net_r"] = pb._outcome(t["entry"], t["stop"], t["exit"], COST)[2]

    print("running portfolio sim with heat recording...", flush=True)
    port = simulate_with_heat(all_trades, closes, COST, RISK_PCT)
    taken = [t for t in all_trades if "_heat_pct" in t]
    print(f"taken: {len(taken)} (skipped cap={port['skipped_cap_count']}, "
          f"risk={port['skipped_cap_risk']})", flush=True)
    print(f"total_return={(port['final_equity']/pb.START_EQUITY-1)*100:.2f}% "
          f"max_dd={port['max_drawdown']*100:.2f}%", flush=True)

    # sanity: match known baseline (56.28% / 21.63%)
    for t in taken:
        t["_heat_bin"] = heat_bin(t["_heat_pct"])
        t["_year"] = pd.to_datetime(t["entry_time"]).year

    results = {
        "setup": {"universe": WATCHLIST, "cost_bps": 25,
                  "generated": len(all_trades), "taken": len(taken),
                  "total_return_pct": round((port["final_equity"]/pb.START_EQUITY-1)*100, 2),
                  "max_drawdown_pct": round(port["max_drawdown"]*100, 2),
                  "skipped_cap_count": port["skipped_cap_count"],
                  "skipped_cap_risk": port["skipped_cap_risk"]},
        "heat_buckets": {},
        "heat_distribution": {},
        "year_xtab": {},
    }

    bins = ["<2%", "2-3%", "3-4%", "4-5%", "5% (cap)"]
    for b in bins:
        sub = [t for t in taken if t["_heat_bin"] == b]
        results["heat_buckets"][b] = bucket_stats(sub) if sub else {"n": 0}
        results["heat_distribution"][b] = len(sub)

    # persistence: year x heat-bin expectancy
    for yr in sorted({t["_year"] for t in taken}):
        results["year_xtab"][str(yr)] = {}
        for b in bins:
            sub = [t for t in taken if t["_year"] == yr and t["_heat_bin"] == b]
            if len(sub) >= 5:
                results["year_xtab"][str(yr)][b] = {
                    "n": len(sub),
                    "exp_r": round(float(np.mean([x["net_r"] for x in sub])), 3)}
            else:
                results["year_xtab"][str(yr)][b] = {"n": len(sub), "exp_r": None}

    # heat histogram detail (0.5% bins) to show the discrete structure
    hist = {}
    for t in taken:
        k = f"{int(t['_heat_pct']*2)/2:.1f}"
        hist[k] = hist.get(k, 0) + 1
    results["heat_histogram_0.5pct"] = dict(sorted(hist.items()))

    with open(os.path.join(OUTDIR, "heat_results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("wrote heat_results.json", flush=True)

    print("\n=== heat buckets ===")
    for b in bins:
        s = results["heat_buckets"][b]
        print(f"{b:10s} n={s.get('n',0):4d} exp={s.get('expectancy_r')}R "
              f"win={s.get('win_rate_pct')}% pf={s.get('profit_factor')} "
              f"avg_port_mae={s.get('avg_port_mae_pct')}%")
    return results


if __name__ == "__main__":
    main()
