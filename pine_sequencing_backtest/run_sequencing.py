#!/usr/bin/env python3
"""P13 — Signal sequencing study (2026-09-24).

Question: does the first signal in a move perform differently from repeated
signals? Do overlapping signal conditions dilute the edge?

Lead from two independent sightings (P6 chase, P7 setup age): the
confirmed+ready OVERLAP bucket (n=52) runs -0.053R vs pure confirmed +0.286R
(n=146) and pure ready +0.463R (n=19). This is the third, confirmatory test —
be extra skeptical.

Measurement study on CANONICAL 4H Hybrid baseline trades only (entries and
exits untouched; pine_backtest imported unmodified).

Parts:
 1. Signal composition: which sub-conditions of pine_buy_signal fired at the
    signal bar: pure_breakout / pure_confirmed / pure_ready / pairwise
    overlaps / all3. n / expectancy / win rate / PF, year cross-tab.
 2. Sequencing: prior signal bars in the same symbol within trailing 20 bars
    (ALL signal bars, not just taken ones): 0 = first, 1 = second, 2+ = third+.
 3. Re-entry: taken trade whose signal bar is within 10 bars after a prior
    taken trade's exit in the same symbol: after stop vs after TP1-hit exit
    vs fresh (no prior exit within 10 bars).

Buckets pre-declared. No tuning. Thin buckets don't count.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_sequencing_backtest")
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402  (canonical engine, unmodified)

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB", "ONDS", "DRAM",
             "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
COST = 0.0025  # 25 bps
SEQ_WINDOW = 20     # trailing bars for prior-signal count
REENTRY_WINDOW = 10  # bars after a prior exit


def signal_composition(df, i):
    """Which sub-conditions of pine_buy_signal fired at bar i."""
    r = df.iloc[i]
    rp = df.iloc[i - 1]
    close, vol = r["Close"], r["Volume"]
    volume_ok = vol > r["vol_ma"]
    hot = close > r["e9"] + r["atr"] * pb.HOT_ATR
    safe = not hot
    trend_bull = r["e21"] > r["e55"] and close > r["e200"]
    strong_trend = r["adx"] > 20 and r["atr_ratio"] > 0.85
    score = int(r["e9"] > r["e21"]) + int(r["e21"] > r["e55"]) \
        + int(close > r["e200"]) + int(r["adx"] > 25) + int(r["atr_ratio"] > 1)
    breakout = close > df["High"].iloc[i - 10:i].max()
    ready_prev = rp["Close"] < rp["e21"] and rp["Close"] > rp["e55"] \
        and rp["e21"] > rp["e55"] and rp["atr_ratio"] > 0.85
    confirmed = close > r["e21"] and r["e21"] > r["e55"] and close > r["e200"] \
        and score >= 4 and volume_ok and safe
    breakout_buy = trend_bull and strong_trend and breakout and volume_ok and safe
    ready_buy = ready_prev and close > r["e21"] and score >= 3 and volume_ok and safe
    parts = []
    if confirmed:
        parts.append("confirmed")
    if breakout_buy:
        parts.append("breakout")
    if ready_buy:
        parts.append("ready")
    if not parts:
        return "none?!"
    if len(parts) == 1:
        return "pure_" + parts[0]
    return "+".join(sorted(parts))


def net_r(tr):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], COST)[2]


def stats(rs):
    rs = np.asarray(rs, dtype=float)
    n = len(rs)
    if n == 0:
        return {"n": 0}
    wins = rs[rs > 0]
    losses = rs[rs <= 0]
    pf = float(wins.sum() / abs(losses.sum())) if losses.sum() != 0 else float("inf")
    return {"n": n, "exp_r": round(float(rs.mean()), 4),
            "win_rate": round(float((rs > 0).mean() * 100), 1),
            "pf": round(pf, 3) if pf != float("inf") else None}


def main():
    sym_dfs = {}
    all_trades = []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        sym_dfs[sym] = df
        tr, _ = pb.gen_pine_trades(sym, df)
        all_trades.extend(tr)
        print(f"  {sym}: {len(tr)} trades", flush=True)

    base_rs = [net_r(t) for t in all_trades]
    print(f"BASELINE CHECK: n={len(all_trades)} exp={np.mean(base_rs):.4f}R")

    # All signal bars per symbol (taken or not) for sequencing counts.
    sig_pos = {}
    for sym, df in sym_dfs.items():
        n = len(df)
        pos = []
        for i in range(pb.WARMUP, n - 1):
            if pb.pine_buy_signal(df, i):
                pos.append(i)
        sig_pos[sym] = pos

    # Enrich each taken trade.
    rows = []
    by_sym = {}
    for t in all_trades:
        by_sym.setdefault(t["symbol"], []).append(t)
    for sym, trades in by_sym.items():
        df = sym_dfs[sym]
        sigs = sig_pos[sym]
        # prior taken-trade exits for re-entry analysis
        exits = sorted(
            [(df.index.get_loc(pd.Timestamp(x["exit_time"])), x)
             for x in trades],
            key=lambda z: int(z[0]) if np.isscalar(z[0]) else int(z[0][0]))
        for t in all_trades:
            if t["symbol"] != sym:
                continue
            loc = df.index.get_loc(pd.Timestamp(t["signal_time"]))
            pos = int(loc) if np.isscalar(loc) else int(loc[0])
            r = net_r(t)
            comp = signal_composition(df, pos)
            n_prior = sum(1 for s in sigs if pos - SEQ_WINDOW <= s < pos)
            seq = "first" if n_prior == 0 else ("second" if n_prior == 1 else "3rd+")
            # re-entry: most recent prior exit within window
            reentry = "fresh"
            epos = int(df.index.get_loc(pd.Timestamp(t["exit_time"]))) \
                if np.isscalar(df.index.get_loc(pd.Timestamp(t["exit_time"]))) \
                else int(df.index.get_loc(pd.Timestamp(t["exit_time"]))[0])
            for (xpos_raw, xt) in exits:
                xpos = int(xpos_raw) if np.isscalar(xpos_raw) else int(xpos_raw[0])
                if xpos == epos and xt is t:
                    continue
                if 0 < pos - xpos <= REENTRY_WINDOW:
                    if xt["reason"] == "stop":
                        reentry = "after_stop"
                    elif xt["tp1_hit"]:
                        reentry = "after_tp1"
                    else:
                        reentry = "after_other_exit"
                    break  # exits sorted? ensure most recent: take min gap
            rows.append({"symbol": sym, "r": r,
                         "year": pd.Timestamp(t["signal_time"]).year,
                         "comp": comp, "seq": seq, "reentry": reentry,
                         "n_prior_signals": n_prior})

    # Fix re-entry: pick the CLOSEST prior exit, not the first found.
    # (Redo cleanly below — exits list rebuilt per trade.)
    rows = []
    for t in all_trades:
        sym = t["symbol"]
        df = sym_dfs[sym]
        loc = df.index.get_loc(pd.Timestamp(t["signal_time"]))
        pos = int(loc) if np.isscalar(loc) else int(loc[0])
        r = net_r(t)
        comp = signal_composition(df, pos)
        sigs = sig_pos[sym]
        n_prior = sum(1 for s in sigs if pos - SEQ_WINDOW <= s < pos)
        seq = "first" if n_prior == 0 else ("second" if n_prior == 1 else "3rd+")
        best = None  # (gap, kind)
        for xt in by_sym[sym]:
            if xt is t:
                continue
            xloc = df.index.get_loc(pd.Timestamp(xt["exit_time"]))
            xpos = int(xloc) if np.isscalar(xloc) else int(xloc[0])
            gap = pos - xpos
            if 0 < gap <= REENTRY_WINDOW:
                kind = "after_stop" if xt["reason"] == "stop" \
                    else ("after_tp1" if xt["tp1_hit"] else "after_other_exit")
                if best is None or gap < best[0]:
                    best = (gap, kind)
        reentry = best[1] if best else "fresh"
        rows.append({"symbol": sym, "r": r,
                     "year": pd.Timestamp(t["signal_time"]).year,
                     "comp": comp, "seq": seq, "reentry": reentry,
                     "n_prior_signals": n_prior})

    out = {"baseline_check": {"n": len(all_trades),
                              "exp_r_25bps": round(float(np.mean(base_rs)), 4)},
           "composition": {}, "composition_yearly": {},
           "sequencing": {}, "sequencing_yearly": {},
           "reentry": {}, "reentry_yearly": {},
           "overlap_symbols": {}}

    for c in sorted(set(x["comp"] for x in rows)):
        rs = [x["r"] for x in rows if x["comp"] == c]
        out["composition"][c] = stats(rs)
        out["composition_yearly"][c] = {
            str(y): stats([x["r"] for x in rows
                            if x["comp"] == c and x["year"] == y])
            for y in [2023, 2024, 2025, 2026]}
        out["overlap_symbols"][c] = sorted(
            set(x["symbol"] for x in rows if x["comp"] == c))

    for s in ["first", "second", "3rd+"]:
        rs = [x["r"] for x in rows if x["seq"] == s]
        out["sequencing"][s] = stats(rs)
        out["sequencing_yearly"][s] = {
            str(y): stats([x["r"] for x in rows
                            if x["seq"] == s and x["year"] == y])
            for y in [2023, 2024, 2025, 2026]}

    for k in ["fresh", "after_stop", "after_tp1", "after_other_exit"]:
        rs = [x["r"] for x in rows if x["reentry"] == k]
        out["reentry"][k] = stats(rs)
        out["reentry_yearly"][k] = {
            str(y): stats([x["r"] for x in rows
                            if x["reentry"] == k and x["year"] == y])
            for y in [2023, 2024, 2025, 2026]}

    with open(os.path.join(OUTDIR, "sequencing_results.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("wrote sequencing_results.json")


if __name__ == "__main__":
    main()
