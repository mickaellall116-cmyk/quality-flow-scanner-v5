#!/usr/bin/env python3
"""Priority 9 — Gap behavior (2026-09-24).

Question (pre-registered): do large gaps create continuation (momentum) or
chase risk (reversal) for Quality Flow entries?

METHOD (declared before looking at results):
- Baseline: canonical 4H Hybrid trades, 14-stock watchlist, 4H bars,
  Oct 2023-Sep 2026, frozen Mode B exits, 25bps costs. Engine imported
  unmodified; this is a MEASUREMENT study — no filter is built or proposed.
- Gap is measured at the ENTRY bar (i+1), since entries fill at the next-bar
  open: gap = (Open[i+1] - Close[i]) / atr[i], in ATR units at the signal bar.
  (On 4H bars a "premarket gap" is not separately measurable — the inter-bar
  gap IS the overnight/weekend gap. Noted, not tested separately.)
- Metrics:
    gap        signed gap in ATR units
    gap_up     no gap (|g|<0.15), small up (0.15..0.5), large up (>=0.5)
    gap_down   no gap (|g|<0.15), small down (-0.5..-0.15), large down (<=-0.5)
    abs_gap    quartiles of |gap|
    hold_fade  for |gap|>=0.15: gap-up held (C[i+1]>=O[i+1]) /
               gap-up faded / gap-down held (C[i+1]<=O[i+1]) /
               gap-down faded; plus "no gap"
    open_loc   (Open[i+1]-min Low[i-9:i+1]) / (max High[i-9:i+1]-min Low),
               quartiles — where the entry bar opens inside the prior
               10-bar range (0 = at the lows, 1 = at the highs)
- Per bucket: n, expectancy @25bps, win rate, PF.
- Persistence: cross-tab the most interesting split by year.
- Verdict: broad bucket clearly better/worse across years -> MAYBE with a
  future filter direction; flat or thin -> NO.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_gap_backtest")
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "gap_results.json")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

COST = 0.0025
NO_GAP = 0.15   # |gap| below this = no gap
BIG_GAP = 0.5   # |gap| at/above this = large gap


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
    b = bucket_stats(trades)
    print(f"baseline sanity: n={b['n']} exp={b['expectancy_net_r']}R "
          f"win={b['win_rate_pct']}%", flush=True)

    # ---- gap metrics at the entry bar ------------------------------------
    rows = []
    for t in trades:
        sym = t["symbol"]
        df = data[sym]
        i = sig_index[sym][t["signal_time"]]
        r = df.iloc[i]
        atr = r["atr"]
        e = df.iloc[i + 1]  # entry bar
        gap = (e["Open"] - r["Close"]) / atr
        lo10 = df["Low"].iloc[i - 9:i + 1].min()
        hi10 = df["High"].iloc[i - 9:i + 1].max()
        rng = hi10 - lo10
        open_loc = (e["Open"] - lo10) / rng if rng > 0 else 0.5
        rows.append({
            "symbol": sym, "signal_time": t["signal_time"],
            "year": str(pd.Timestamp(t["signal_time"]).year),
            "r": net_r(t), "gap": float(gap),
            "abs_gap": float(abs(gap)), "open_loc": float(open_loc),
            "entry_open": float(e["Open"]), "entry_close": float(e["Close"]),
        })
    m = pd.DataFrame(rows)

    results = {
        "n_trades": len(trades),
        "baseline": b,
        "definitions": {
            "gap_atr": "(Open[i+1]-Close[i])/atr[i]; entry bar = i+1",
            "no_gap": f"|gap| < {NO_GAP} ATR",
            "large_gap": f"|gap| >= {BIG_GAP} ATR",
            "hold_fade": "gap-up held: entry-bar close >= open; "
                         "gap-up faded: close < open; "
                         "gap-down held: close <= open; "
                         "gap-down faded: close > open",
            "open_loc": "entry-bar open position inside prior 10-bar "
                        "range (0=lows, 1=highs)",
            "premarket_note": "not separately measurable on 4H bars; "
                              "inter-bar gap IS the overnight/weekend gap",
        },
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
            bb = sec["buckets"][lab]
            print(f"  {lab}: n={bb['n']} exp={bb['expectancy_net_r']}R "
                  f"win={bb['win_rate_pct']}% pf={bb['profit_factor']}",
                  flush=True)

    # gap-up size (pre-declared)
    def up_lab(g):
        if g < NO_GAP:
            return "no/neg gap"
        if g < BIG_GAP:
            return "gap-up small (0.15..0.5)"
        return "gap-up large (>=0.5)"
    section("gap_up_size",
            ["no/neg gap", "gap-up small (0.15..0.5)", "gap-up large (>=0.5)"],
            [up_lab(g) for g in m["gap"]])

    # gap-down size (pre-declared)
    def dn_lab(g):
        if g > -NO_GAP:
            return "no/pos gap"
        if g > -BIG_GAP:
            return "gap-down small (-0.5..-0.15)"
        return "gap-down large (<=-0.5)"
    section("gap_down_size",
            ["no/pos gap", "gap-down small (-0.5..-0.15)",
             "gap-down large (<=-0.5)"],
            [dn_lab(g) for g in m["gap"]])

    # absolute gap quartiles
    labels, assigns, edges = quartile_buckets(m["abs_gap"].values)
    section("abs_gap_atr", labels, assigns)
    results["metrics"]["abs_gap_atr"]["quartile_edges"] = edges

    # hold vs fade (pre-declared)
    def hf_lab(row):
        g = row["gap"]
        if abs(g) < NO_GAP:
            return "no gap"
        if g > 0:
            return ("gap-up held" if row["entry_close"] >= row["entry_open"]
                    else "gap-up faded")
        return ("gap-down held" if row["entry_close"] <= row["entry_open"]
                else "gap-down faded")
    hflabels = ["no gap", "gap-up held", "gap-up faded",
                "gap-down held", "gap-down faded"]
    section("gap_hold_fade", hflabels,
            [hf_lab(r) for r in m.to_dict("records")])

    # opening location within prior 10-bar range (quartiles)
    labels, assigns, edges = quartile_buckets(m["open_loc"].values)
    section("open_location_10bar", labels, assigns)
    results["metrics"]["open_location_10bar"]["quartile_edges"] = edges

    # ---- persistence: cross-tab the most interesting split by year -------
    # choose after seeing sections; default to large-gap vs rest
    m["big_gap"] = (m["abs_gap"] >= BIG_GAP)
    yr = {}
    for y, grp in m.groupby("year"):
        big = grp[grp["big_gap"]]["r"]
        rest = grp[~grp["big_gap"]]["r"]
        yr[y] = {
            "n_big": int(len(big)),
            "exp_big_r": round(float(big.mean()), 4) if len(big) else None,
            "n_rest": int(len(rest)),
            "exp_rest_r": round(float(rest.mean()), 4) if len(rest) else None,
        }
    results["persistence_big_gap_vs_rest_by_year"] = yr
    print("\npersistence: |gap|>=0.5 ATR vs rest, by year", flush=True)
    for y in sorted(yr):
        d = yr[y]
        print(f"  {y}: big n={d['n_big']} {d['exp_big_r']}R | "
              f"rest n={d['n_rest']} {d['exp_rest_r']}R", flush=True)

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
