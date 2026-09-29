#!/usr/bin/env python3
"""Long->short flip test (pre-registered 2026-09-25, Mike order; prereg commit e709875).

Method (frozen in the prereg — no tuning, no variants):
  Entry: pine_buy_signal imported UNMODIFIED from pine_backtest (with
    add_pine_indicators), applied per timeframe. Signal bar i -> entry at
    next bar open; stop = signal close - ATR*1.5; skip if entry <= stop.
  Arm A: long-only, Mode B exit stack via canonical_baseline.modeb_engine
    (imported UNMODIFIED), realistic_gaps=True, TP1 = entry + ATR*2.0.
  Arm B: same long leg; at the long's exit bar e, reverse SHORT at open of
    bar e+1 with mirrored geometry (stop_S = entry_S + risk_L,
    tp1_S = entry_S - (tp1_L - entry_L)) executed by the UNMODIFIED Mode B
    engine on the price-negated bar series. Mirror proof: with
    x' = -x, High' = -Low, Low' = -High, every engine comparison maps
    exactly (stop touch hi>=stop_S <-> lo'<=-stop'=stop'; TP1 touch
    lo<=tp1_S <-> hi'>=-tp1_S=tp1'; gap fills, PP arming at -1R, 30-bar
    clock all preserved), and R' = (entry_S-exit_S)/(stop_S-entry_S), the
    true short R. One combined record per signal: R_total = R_long + R_short.
  Costs: 50bps round-trip per leg, in R: cost = 0.005 / (risk/entry).
  Eligibility: >=61 bars after the signal bar (entry + 60) so both legs
    complete inside the data; identical signal population for both arms.

Research only. Nothing frozen is modified (all imports read-only).
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/workspace/quality-flow-scanner-v5"))
sys.path.insert(0, os.path.expanduser(
    "~/workspace/quality-flow-scanner-v5/canonical_baseline"))

import pine_backtest as pb  # pine_buy_signal, add_pine_indicators, WARMUP
from modeb_engine import run_trade

BASE = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
OUT = os.path.join(BASE, "selection_edge")

UNIVERSE = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB", "ONDS",
            "DRAM", "SPCX", "BBAI", "NIO", "HOOD", "AMD"]
TFS = {"1h": ("pine_1h/cache", "h1"), "4h": ("backtest_cache", "h4"),
       "1d": ("backtest_cache", "d1")}
BPS = 0.005
WARMUP = pb.WARMUP  # 215
MIN_AFTER = 61     # signal bar + entry bar + 60
MIN_TRADES_FOR_COUNT = 30

SKIP_REASONS = {"gap_below_stop": 0, "degenerate_atr": 0, "untradeable_guard": 0}


def load_bars(sym, tf):
    subdir, pre = TFS[tf]
    path = os.path.join(BASE, subdir, f"{pre}_{sym}.pkl")
    if not os.path.exists(path):
        return None
    df = pd.read_pickle(path)
    need = ["Open", "High", "Low", "Close", "Volume"]
    if any(c not in df.columns for c in need):
        return None
    if df["Volume"].isna().all():
        return None
    df = df[need].dropna()
    if len(df) <= WARMUP + MIN_AFTER:
        return None
    return pb.add_pine_indicators(df)


def invert(bars):
    """Exact short<->long mirror: negate prices, swap high/low after negation."""
    inv = bars.copy()
    inv["Open"] = -bars["Open"]
    inv["Close"] = -bars["Close"]
    inv["High"] = -bars["Low"]
    inv["Low"] = -bars["High"]
    return inv


def run_pair(sdf, i, times):
    """Run Arm A (long-only) and Arm B (long+flip-short) for signal bar i.
    sdf: indicator df with RangeIndex; times: original timestamps."""
    n = len(sdf)
    sig = sdf.iloc[i]
    entry = float(sdf["Open"].iloc[i + 1])
    atrv = float(sig["atr"])
    if not np.isfinite(atrv) or atrv <= 0:
        SKIP_REASONS["degenerate_atr"] += 1
        return None  # degenerate ATR: cannot size risk; skip
    stop_L = float(sig["Close"]) - atrv * 1.5
    if entry <= stop_L:
        SKIP_REASONS["gap_below_stop"] += 1
        return None  # gapped below stop: pine convention skips
    risk_L = entry - stop_L
    if risk_L / entry < BPS:
        SKIP_REASONS["untradeable_guard"] += 1
        # POST-PREREG CORRECTION (documented in report): the planned risk is
        # smaller than the round-trip friction itself (e.g. entry gapped down
        # to microscopically above the stop). Such a signal is untradeable —
        # the prereg's R-denominated cost formula turns it into a -100R
        # artifact. Skip symmetrically for both arms (paired comparison kept).
        return None
    tp1_L = entry + atrv * 2.0
    bars = sdf[["Open", "High", "Low", "Close"]]

    resA = run_trade(i + 1, entry, stop_L, tp1_L, bars,
                     scanner_states=None, realistic_gaps=True)
    assert resA.exit_reason != "OPEN", "long leg ran out of data"
    cost_L = BPS / (risk_L / entry)
    r_long = resA.blended_r - cost_L

    # --- Arm B short leg: reverse at the open after the long's exit bar
    e = int(resA.exit_bar)
    se = e + 1
    entry_S = float(bars["Open"].iloc[se])
    stop_S = entry_S + risk_L
    tp1_S = entry_S - (tp1_L - entry)
    inv = invert(bars)
    resS = run_trade(se, -entry_S, -stop_S, -tp1_S, inv,
                     scanner_states=None, realistic_gaps=True)
    assert resS.exit_reason != "OPEN", "short leg ran out of data"
    cost_S = BPS / (risk_L / entry_S)
    r_short = resS.blended_r - cost_S  # == true short R by the mirror proof

    base = {"symbol": None, "entry_time": str(times[i + 1]),
            "long_exit_time": str(times[e]),
            "long_exit_reason": resA.exit_reason,
            "short_exit_time": str(times[int(resS.exit_bar)]),
            "short_exit_reason": resS.exit_reason,
            "bars_held_long": resA.bars_held,
            "bars_held_short": resS.bars_held,
            "r_long_net": round(r_long, 4),
            "r_short_net": round(r_short, 4)}
    return base


def summarize(trades, key):
    rs = np.array([t[key] for t in trades], dtype=float)
    n = len(rs)
    if n == 0:
        return {"n": 0}
    order = np.argsort([t["exit_time_sort"] for t in trades])
    eq = np.cumsum(rs[order])
    peak = np.maximum.accumulate(eq)
    dd = float(np.max(peak - eq)) if n else 0.0
    gp = float(rs[rs > 0].sum())
    gl = float(-rs[rs < 0].sum())
    pf = gp / gl if gl > 0 else (float("inf") if gp > 0 else 0.0)
    return {
        "n": n,
        "expectancy": round(float(rs.mean()), 4),
        "win_rate": round(float((rs > 0).mean()), 4),
        "profit_factor": round(float(pf), 3),
        "max_dd_R": round(dd, 3),
        "total_R": round(float(rs.sum()), 3),
    }


def main():
    all_trades = []  # each: tf, symbol, r_long_net, r_short_net, r_combo, ...
    skipped_gap = 0
    per_tf_counts = {}
    for tf in TFS:
        for sym in UNIVERSE:
            df = load_bars(sym, tf)
            if df is None:
                continue
            sdf = df.reset_index(drop=True)
            times = df.index
            n = len(sdf)
            cnt = 0
            for i in range(WARMUP, n - MIN_AFTER):
                if not pb.pine_buy_signal(sdf, i):
                    continue
                rec = run_pair(sdf, i, times)
                if rec is None:
                    skipped_gap += 1
                    continue
                rec["symbol"] = sym
                rec["tf"] = tf
                rec["r_combo"] = round(rec["r_long_net"] + rec["r_short_net"], 4)
                # equity ordering: use the LATER of the two legs' exits
                rec["exit_time_sort"] = max(rec["long_exit_time"],
                                           rec["short_exit_time"])
                all_trades.append(rec)
                cnt += 1
            per_tf_counts[f"{tf}_{sym}"] = cnt
            print(f"  {tf} {sym}: {cnt} trades", flush=True)

    # metrics per arm per timeframe + pooled
    results = {"per_timeframe": {}, "pooled": {}, "skipped_gap_below_stop": skipped_gap,
               "skip_reasons": dict(SKIP_REASONS)}
    for tf in TFS:
        tA = [t for t in all_trades if t["tf"] == tf]
        results["per_timeframe"][tf] = {
            "armA_long_only": summarize(tA, "r_long_net"),
            "armB_combo": summarize(tA, "r_combo"),
            "armB_long_leg_only": summarize(tA, "r_long_net"),
            "armB_short_leg_only": summarize(tA, "r_short_net"),
            "short_leg_win_rate": round(float(np.mean(
                [1 if t["r_short_net"] > 0 else 0 for t in tA])), 4) if tA else None,
        }
    results["pooled"] = {
        "armA_long_only": summarize(all_trades, "r_long_net"),
        "armB_combo": summarize(all_trades, "r_combo"),
    }

    # pre-registered decision rule
    def expc(tf, arm):
        return results["per_timeframe"][tf][arm]["expectancy"]
    def n_of(tf, arm):
        return results["per_timeframe"][tf][arm]["n"]
    counted = [tf for tf in TFS
               if n_of(tf, "armA_long_only") >= MIN_TRADES_FOR_COUNT
               and n_of(tf, "armB_combo") >= MIN_TRADES_FOR_COUNT]
    wins = [tf for tf in counted if expc(tf, "armB_combo") > expc(tf, "armA_long_only")]
    poolB = results["pooled"]["armB_combo"]
    poolA = results["pooled"]["armA_long_only"]
    c1 = len(wins) >= 2
    c2 = poolB["expectancy"] > 0
    c3 = poolB["max_dd_R"] <= 1.20 * poolA["max_dd_R"]
    decision = "PASS" if (c1 and c2 and c3) else "FAIL"
    results["decision_rule"] = {
        "timeframes_counted": counted,
        "armB_beats_armA_on": wins,
        "c1_2of3": bool(c1), "c2_pooled_positive": bool(c2),
        "c3_dd_within_20pct": bool(c3),
        "DECISION": decision,
    }

    with open(os.path.join(OUT, "flip_short_trades.json"), "w") as f:
        json.dump(all_trades, f, indent=1)
    with open(os.path.join(OUT, "flip_short_results.json"), "w") as f:
        json.dump(results, f, indent=1)
    with open(os.path.join(OUT, "flip_short_counts.json"), "w") as f:
        json.dump(per_tf_counts, f, indent=1)
    print(json.dumps(results["decision_rule"], indent=1))
    print(json.dumps(results["pooled"], indent=1))


if __name__ == "__main__":
    main()
