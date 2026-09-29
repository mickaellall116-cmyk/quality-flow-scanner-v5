#!/usr/bin/env python3
"""Priority 6 — Entry extension / chasing (2026-09-24).

Question (pre-registered): do entries get worse when price is already extended?
Is there a measurable chase penalty — i.e. do extended entries perform worse
because the move has already consumed its short-term momentum?

METHOD (declared before looking at results):
- Baseline: canonical 4H Hybrid trades, 14-stock watchlist, 4H bars,
  Oct 2023-Sep 2026, frozen Mode B exits, 25bps costs. Engine imported
  unmodified; this is a MEASUREMENT study — no filter is built or proposed.
- For each trade, compute extension metrics at the SIGNAL bar i (point-in-time,
  the information available when the signal fires), in ATR units:
    d9    = (close[i] - e9[i]) / atr[i]
    d21   = (close[i] - e21[i]) / atr[i]          (= ATR extension; same metric)
    dbrk  = (close[i] - max(high[i-10:i])) / atr[i]   (10 = BREAKOUT_BARS)
    gap   = (open[i+1] - close[i]) / atr[i]       (entry-bar gap)
    greens = consecutive close>open bars ending at signal bar i
- Bucketing (pre-declared, no tuning):
    d9, d21, dbrk -> quartiles across the 237 trades
    gap           -> down (<-0.2), flat (-0.2..0.2), up-small (0.2..0.6),
                     up-large (>0.6) ATR
    greens        -> 0-1, 2-3, 4+
- Per bucket: n, expectancy @25bps, win rate, PF.
- Persistence: cross-tab the most interesting split by year.
- Verdict: broad extended bucket clearly worse across years -> MAYBE with a
  future filter direction; flat -> NO chase penalty.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_chase_backtest")
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "chase_results.json")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

COST = 0.0025


def net_r(tr, cost=COST):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]


def bucket_stats(trades):
    if not trades:
        return {"n": 0}
    rs = np.array([net_r(t) for t in trades])
    wins = rs[rs > 0]
    losses = rs[rs <= 0]
    gw, gl = wins.sum(), -losses.sum()
    return {
        "n": len(trades),
        "expectancy_net_r": round(float(rs.mean()), 4),
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1),
        "profit_factor": round(float(gw / gl), 2) if gl > 0 else None,
    }


def quartile_buckets(vals):
    q = np.quantile(vals, [0.25, 0.5, 0.75])
    labels = ["Q1 (least)", "Q2", "Q3", "Q4 (most)"]
    edges = [-np.inf, q[0], q[1], q[2], np.inf]
    out = []
    for v in vals:
        for bi in range(4):
            if edges[bi] < v <= edges[bi + 1]:
                out.append(labels[bi])
                break
    return labels, out, [round(float(x), 3) for x in q]


def main():
    data, sig_index = {}, {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        data[sym] = df
        sig_index[sym] = {df.index[i].isoformat(): i for i in range(len(df))}

    # ---- baseline trades (canonical engine, unmodified) ------------------
    trades = []
    for sym in WATCHLIST:
        tr, _ = pb.gen_pine_trades(sym, data[sym])
        trades.extend(tr)
    trades.sort(key=lambda t: t["entry_time"])
    print(f"baseline trades: {len(trades)}", flush=True)

    # ---- extension metrics at the signal bar ----------------------------
    rows = []
    for t in trades:
        sym = t["symbol"]
        df = data[sym]
        i = sig_index[sym][t["signal_time"]]
        r = df.iloc[i]
        atr = r["atr"]
        close = r["Close"]
        d9 = (close - r["e9"]) / atr
        d21 = (close - r["e21"]) / atr
        brk = df["High"].iloc[i - pb.BREAKOUT_BARS:i].max()
        dbrk = (close - brk) / atr
        gap = (df["Open"].iloc[i + 1] - close) / atr
        greens = 0
        j = i
        while j >= 0 and df["Close"].iloc[j] > df["Open"].iloc[j]:
            greens += 1
            j -= 1
        rows.append({
            "symbol": sym, "signal_time": t["signal_time"],
            "year": str(pd.Timestamp(t["signal_time"]).year),
            "r": net_r(t), "d9": float(d9), "d21": float(d21),
            "dbrk": float(dbrk), "gap": float(gap), "greens": int(greens),
        })
    m = pd.DataFrame(rows)

    results = {
        "n_trades": len(trades),
        "baseline": bucket_stats(trades),
        "metrics": {},
    }

    def section(name, labels, assigns):
        sec = {"labels": labels, "buckets": {}}
        for lab in labels:
            sec["buckets"][lab] = bucket_stats(
                [t for t, a in zip(trades, assigns) if a == lab])
        results["metrics"][name] = sec
        print(f"\n== {name} ==", flush=True)
        for lab in labels:
            b = sec["buckets"][lab]
            print(f"  {lab}: n={b['n']} exp={b['expectancy_net_r']}R "
                  f"win={b['win_rate_pct']}% pf={b['profit_factor']}", flush=True)

    # continuous metrics -> quartiles
    for col, name in [("d9", "dist_9ema_atr"), ("d21", "dist_20ema_atr"),
                      ("dbrk", "dist_breakout_atr")]:
        labels, assigns, edges = quartile_buckets(m[col].values)
        results["metrics_will_set_edges"] = True
        section(name, labels, assigns)
        results["metrics"][name]["quartile_edges"] = edges

    # gap buckets (pre-declared)
    def gap_lab(g):
        if g < -0.2:
            return "gap-down (<-0.2)"
        if g <= 0.2:
            return "flat (-0.2..0.2)"
        if g <= 0.6:
            return "gap-up small (0.2..0.6)"
        return "gap-up large (>0.6)"
    glabels = ["gap-down (<-0.2)", "flat (-0.2..0.2)",
               "gap-up small (0.2..0.6)", "gap-up large (>0.6)"]
    section("gap_atr", glabels, [gap_lab(g) for g in m["gap"]])

    # consecutive greens (pre-declared)
    def gr_lab(g):
        return "0-1" if g <= 1 else ("2-3" if g <= 3 else "4+")
    section("consec_greens", ["0-1", "2-3", "4+"],
            [gr_lab(g) for g in m["greens"]])

    # ---- persistence: cross-tab the most extreme split by year ----------
    # most-extended quartile of d21 vs the rest
    labels, assigns, _ = quartile_buckets(m["d21"].values)
    m["d21_q"] = assigns
    yr = {}
    for y, grp in m.groupby("year"):
        ext = grp[grp["d21_q"] == "Q4 (most)"]["r"]
        rest = grp[grp["d21_q"] != "Q4 (most)"]["r"]
        yr[y] = {
            "n_ext": int(len(ext)), "exp_ext_r": round(float(ext.mean()), 4),
            "n_rest": int(len(rest)), "exp_rest_r": round(float(rest.mean()), 4),
        }
    results["persistence_d21_Q4_vs_rest_by_year"] = yr
    print("\npersistence: d21 Q4 (most extended) vs rest, by year", flush=True)
    for y in sorted(yr):
        d = yr[y]
        print(f"  {y}: ext n={d['n_ext']} {d['exp_ext_r']}R | "
              f"rest n={d['n_rest']} {d['exp_rest_r']}R", flush=True)

    # descriptive implied-filter effect (measurement only, not proposed)
    ext_trades = [t for t, a in zip(trades, m["d21_q"]) if a == "Q4 (most)"]
    rest_trades = [t for t, a in zip(trades, m["d21_q"]) if a != "Q4 (most)"]
    results["implied_drop_Q4_effect"] = {
        "note": "descriptive only — what dropping the most-extended quartile "
                "would have done; NOT a proposed filter",
        "kept": bucket_stats(rest_trades),
        "dropped": bucket_stats(ext_trades),
    }

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
