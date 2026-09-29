#!/usr/bin/env python3
"""P7 — Setup age study (2026-09-24).

Question: do setups lose quality as they age? Report the actual expectancy
curve; do not assume fresher is better.

Measurement study on CANONICAL 4H Hybrid baseline trades only (entries and
exits untouched). For each taken trade, compute bars-since-event at the signal
bar for five event types, bucket, and report n / expectancy / win rate / PF.

Event definitions (pre-declared, simple, point-in-time):
  breakout10 : close[i] > max(high[i-10:i])          (same window as the
                                                     signal's breakout_buy)
  bos20      : close[i] > max(high[i-20:i])          (longer structural break)
  choch      : breakout10[i] AND any close[j] < e55[j] for j in [i-10, i)
               (broke the 10-bar high after trading under e55 = character
               change from pullback-weak to strong)
  fvg_formed : new bull FVG formed at bar i: low[i] > high[i-2]
               (same formation rule as the V3.7 Pine port)
  trend_align: e21[i] > e55[i] and close[i] > e200[i]; age = bars since the
               last False->True flip at or before the signal bar

Age buckets: 0-1, 2-5, 6-10, 11+, never (no event in available history).
Signal composition (sub-conditions of pine_buy_signal evaluated at the signal
bar): pure confirmed / pure breakout / pure ready / pairwise overlaps / all3.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_setup_age_backtest")
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "pine_stalefvg_backtest"))
import pine_backtest as pb  # noqa: E402  (canonical engine, unmodified)
from run_stalefvg import add_fvg_columns  # noqa: E402  (FVG port, unmodified)

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
COST = 0.0025  # 25 bps

AGE_BUCKETS = [(0, 1, "0-1"), (2, 5, "2-5"), (6, 10, "6-10"), (11, 10**9, "11+")]


def bucket_age(age):
    if age is None or (isinstance(age, float) and np.isnan(age)):
        return "never"
    for lo, hi, name in AGE_BUCKETS:
        if lo <= age <= hi:
            return name
    return "never"


def last_event_age(ev, pos):
    """Bars since the most recent True in boolean series ev at/before pos."""
    col = ev.to_numpy()[:pos + 1]
    idx = np.flatnonzero(col)
    if len(idx) == 0:
        return None
    return int(pos - idx[-1])


def add_event_columns(df):
    out = df.copy()
    high, low, close = out["High"], out["Low"], out["Close"]
    out["ev_breakout10"] = close > high.shift(1).rolling(10).max()
    out["ev_bos20"] = close > high.shift(1).rolling(20).max()
    under_e55 = (close < out["e55"]).shift(1).rolling(10).max() > 0
    out["ev_choch"] = out["ev_breakout10"] & under_e55.fillna(False)
    out["ev_fvg_formed"] = low > high.shift(2)
    aligned = (out["e21"] > out["e55"]) & (close > out["e200"])
    out["ev_aligned"] = aligned.fillna(False)
    trans = out["ev_aligned"] & (~out["ev_aligned"].shift(1).fillna(False))
    out["ev_align_flip"] = trans
    return out


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
    return "+".join(parts)


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
    all_trades = []
    sym_dfs = {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        df = add_fvg_columns(df)
        df = add_event_columns(df)
        sym_dfs[sym] = df
        tr, _ = pb.gen_pine_trades(sym, df)
        all_trades.extend(tr)
        print(f"  {sym}: {len(tr)} trades", flush=True)

    # sanity: baseline must match
    base_rs = [net_r(t) for t in all_trades]
    print(f"BASELINE CHECK: n={len(all_trades)} exp={np.mean(base_rs):.4f}R")

    rows = []
    for t in all_trades:
        df = sym_dfs[t["symbol"]]
        loc = df.index.get_loc(pd.Timestamp(t["signal_time"]))
        pos = int(loc) if np.isscalar(loc) else int(loc[0])
        r = net_r(t)
        ages = {
            "breakout": last_event_age(df["ev_breakout10"], pos),
            "bos": last_event_age(df["ev_bos20"], pos),
            "choch": last_event_age(df["ev_choch"], pos),
            "fvg": last_event_age(df["ev_fvg_formed"], pos),
        }
        al_age = last_event_age(df["ev_align_flip"], pos)
        aligned_now = bool(df["ev_aligned"].iloc[pos])
        ages["trend_align"] = al_age if aligned_now else "not_aligned"
        rows.append({
            "symbol": t["symbol"], "r": r,
            "year": pd.Timestamp(t["signal_time"]).year,
            "comp": signal_composition(df, pos),
            **{f"age_{k}": (bucket_age(v) if k != "trend_align"
                            else (v if v == "not_aligned" else bucket_age(v)))
               for k, v in ages.items()},
        })

    out = {"baseline_check": {"n": len(all_trades),
                              "exp_r_25bps": round(float(np.mean(base_rs)), 4)},
           "age_curves": {}, "composition": {}, "persistence": {}}

    for dim in ["breakout", "bos", "choch", "fvg", "trend_align"]:
        key = f"age_{dim}"
        buckets = {}
        order = ["0-1", "2-5", "6-10", "11+", "never"] + \
                (["not_aligned"] if dim == "trend_align" else [])
        for b in order:
            rs = [x["r"] for x in rows if x[key] == b]
            buckets[b] = stats(rs)
        out["age_curves"][dim] = buckets

    comp_order = sorted(set(x["comp"] for x in rows))
    for c in comp_order:
        out["composition"][c] = stats([x["r"] for x in rows if x["comp"] == c])

    # persistence: cross-tab the most extreme age buckets by year
    for dim, interesting in [("breakout", ["0-1", "11+"]),
                             ("bos", ["0-1", "11+"]),
                             ("choch", ["0-1", "never"]),
                             ("fvg", ["0-1", "never"]),
                             ("trend_align", ["0-1", "11+"])]:
        key = f"age_{dim}"
        tab = {}
        for b in interesting:
            by_year = {}
            for y in [2023, 2024, 2025, 2026]:
                rs = [x["r"] for x in rows if x[key] == b and x["year"] == y]
                by_year[str(y)] = stats(rs)
            tab[b] = by_year
        out["persistence"][dim] = tab

    with open(os.path.join(OUTDIR, "setup_age_results.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("wrote setup_age_results.json")


if __name__ == "__main__":
    main()
