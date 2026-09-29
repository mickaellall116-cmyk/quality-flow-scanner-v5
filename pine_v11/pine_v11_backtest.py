"""Faithful backtest of Mike's older Pine strategy 'Quality Flow System V1.1 -
Better Runner Exits' (reference: v1_1_reference.pine), on the same data and
portfolio assumptions as pine_backtest.py (V3.6), so results are directly
head-to-head comparable.

Pre-specified in V11_SPEC.md (frozen before any test). Local-only research.

V1.1 logic (exactly as coded):
- Entry: buySignal = EMA21>EMA55 & close>highest(high,20)[1] & CMF>0 &
  40<=MFI<=75 & ATRratio>=0.85. No ADX, no EMA200, no volume filter,
  no cooldown, no early entries. pyramiding=0.
- Exits: TP1 50% intrabar limit at signal-close+1.5*ATR; before TP1 stop =
  signal-close-2.0*ATR (close-evaluated); after TP1 stop = max(fill breakeven,
  close-3.5*ATR) ratcheting up; close-evaluated exits filled next-bar-open:
  cmfExit, trendExit (2 closes < EMA55), stopExit. MFI exit OFF.
  Single-bar exit confirmation. Tie priority: stop > cmf > trend2.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))
from pine_backtest import (  # noqa: E402  (import, not modification)
    ema, atr, simulate_portfolio, summarize, _outcome,
    CACHE, UNIVERSE_X, WARMUP, RISK_PCT, COSTS,
)

BREAKOUT_BARS = 20
TP_ATR, SL_ATR, RUNNER_ATR = 1.5, 2.0, 3.5


def mfi(df, l=14):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3.0
    mf = tp * df["Volume"]
    pos = pd.Series(np.where(tp > tp.shift(1), mf, 0.0), index=df.index)
    neg = pd.Series(np.where(tp < tp.shift(1), mf, 0.0), index=df.index)
    mr = pos.rolling(l).sum() / neg.rolling(l).sum().replace(0, np.nan)
    return 100 - 100 / (1 + mr)


def add_v11_indicators(df):
    out = df.copy()
    c = out["Close"]
    out["e21"] = ema(c, 21)
    out["e55"] = ema(c, 55)
    out["atr"] = atr(out, 14)
    out["atr_base"] = out["atr"].rolling(50).mean()
    out["atr_ratio"] = out["atr"] / out["atr_base"]
    # CMF
    mf_mult = ((c - out["Low"]) - (out["High"] - c)) / (out["High"] - out["Low"]).clip(lower=1e-9)
    mf_vol = mf_mult * out["Volume"]
    out["cmf"] = mf_vol.rolling(20).mean() / out["Volume"].rolling(20).mean()
    out["cmf_falling"] = (out["cmf"] < out["cmf"].shift(1)) & (out["cmf"].shift(1) < out["cmf"].shift(2))
    out["mfi"] = mfi(out, 14)
    # entry components
    out["trend_bull"] = out["e21"] > out["e55"]
    out["breakout"] = c > out["High"].rolling(BREAKOUT_BARS).max().shift(1)
    out["flow_ok"] = out["cmf"] > 0
    out["mfi_ok"] = (out["mfi"] >= 40) & (out["mfi"] <= 75)
    out["atr_ok"] = out["atr_ratio"] >= 0.85
    # exits (close-evaluated)
    out["cmf_exit"] = (out["cmf"] < 0) & out["cmf_falling"]
    out["trend_exit"] = (c < out["e55"]) & (c.shift(1) < out["e55"].shift(1))
    return out


def finalize_trade(pos, df, exit_px, exit_idx, exit_time, reason):
    # R math uses INITIAL risk (signal stop), like V3.6/V1.7
    sig = df.iloc[pos["entry_idx"] - 1]
    init_stop = float(sig["Close"]) - float(sig["atr"]) * SL_ATR
    risk_frac = (pos["entry"] - init_stop) / pos["entry"]
    r1 = (pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac if pos["tp_hit"] else None
    r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
    r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
    exit_synth = pos["entry"] * (1 + r_blend * risk_frac)
    return {
        "symbol": pos["symbol"], "entry": pos["entry"], "stop": init_stop,
        "exit": exit_synth, "reason": reason,
        "tp1_hit": pos["tp_hit"],
        "entry_time": pos["entry_time"], "exit_time": exit_time,
        "hold_bars": exit_idx - pos["entry_idx"],
        "signal_time": df.index[pos["entry_idx"] - 1].isoformat(),
    }


def gen_v11_trades(sym, df, cutoff=None, eod_liquidate=False):
    trades = []
    skipped_gap = 0
    n = len(df)
    i = WARMUP
    in_trade = False
    while i < n - 1:
        r = df.iloc[i]
        if not in_trade:
            if cutoff is not None and df.index[i] < cutoff:
                i += 1
                continue
            buy = (bool(r["trend_bull"]) and bool(r["breakout"]) and bool(r["flow_ok"])
                   and bool(r["mfi_ok"]) and bool(r["atr_ok"]))
            if buy:
                entry = float(df["Open"].iloc[i + 1])
                sig_close = float(r["Close"])
                stop0 = sig_close - float(r["atr"]) * SL_ATR
                if entry <= stop0:
                    skipped_gap += 1
                    i += 1
                    continue
                in_trade = True
                pos = {"symbol": sym, "entry": entry, "stop": stop0,
                       "tp1": sig_close + float(r["atr"]) * TP_ATR,
                       "tp_hit": False, "trailed": False,
                       "entry_idx": i + 1, "entry_time": df.index[i + 1]}
                i += 1
                continue
            i += 1
            continue
        # ---- manage open position ----
        bar = df.iloc[i]
        hi, close = float(bar["High"]), float(bar["Close"])
        if not pos["tp_hit"] and hi >= pos["tp1"]:
            pos["tp_hit"] = True  # 50% filled at TP1 limit
        if pos["tp_hit"]:
            trail = close - float(bar["atr"]) * RUNNER_ATR
            pos["stop"] = max(pos["entry"] if not pos["trailed"] else pos["stop"], trail)
            pos["trailed"] = True
        final_stop = pos["stop"]
        if close < final_stop:
            done, reason = True, "stop"
        elif bool(bar["cmf_exit"]):
            done, reason = True, "cmf"
        elif bool(bar["trend_exit"]):
            done, reason = True, "trend2"
        else:
            done, reason = False, None
        if done:
            if i + 1 < n:
                exit_px = float(df["Open"].iloc[i + 1])
                exit_idx, exit_time = i + 1, df.index[i + 1]
            else:
                exit_px, exit_time = close, df.index[i]
                exit_idx = i
            trades.append(finalize_trade(pos, df, exit_px, exit_idx, exit_time, reason))
            in_trade = False
        i += 1
    if in_trade and eod_liquidate:
        exit_px = float(df["Close"].iloc[-1])
        trades.append(finalize_trade(pos, df, exit_px, n - 1, df.index[-1], "eod"))
    return trades, skipped_gap


def main():
    all_trades, closes, skipped = [], {}, 0
    for sym in UNIVERSE_X:
        path = os.path.join(CACHE, f"h4_{sym}.pkl")
        if not os.path.exists(path):
            print(f"  [warn] no cache for {sym}, skipping", flush=True)
            continue
        df = pd.read_pickle(path)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"  [warn] no volume for {sym}, skipping", flush=True)
            continue
        df = add_v11_indicators(df)
        closes[sym] = df["Close"]
        tr, sg = gen_v11_trades(sym, df)
        all_trades.extend(tr)
        skipped += sg
        print(f"  {sym}: {len(tr)} trades", flush=True)
    all_trades.sort(key=lambda t: t["entry_time"])
    results = {"spec": "V11_SPEC.md (frozen pre-test)", "runs": []}
    for cost_name, cost in COSTS.items():
        port = simulate_portfolio(all_trades, closes, cost, RISK_PCT)
        row = summarize("PINE_V11:UX51:4h", all_trades, port, skipped, cost_name)
        t = pd.DataFrame(all_trades)
        net_r = []
        for tr in all_trades:
            _, _, nr, _ = _outcome(tr["entry"], tr["stop"], tr["exit"], COSTS[cost_name])
            net_r.append(nr)
        t["net_r"] = net_r
        row["avg_winner_r"] = round(float(t.loc[t.net_r > 0, "net_r"].mean()), 3)
        row["avg_loser_r"] = round(float(t.loc[t.net_r <= 0, "net_r"].mean()), 3)
        row["stop_out_pct"] = round(float((t["reason"] == "stop").mean()) * 100, 1)
        results["runs"].append(row)
        print(f"[{cost_name}] trades={row['trades']} exp={row['expectancy_net_r']}R "
              f"PF={row['profit_factor']} ret={row['total_return_pct']}% "
              f"dd={row['max_drawdown_pct']}% hold={row['avg_hold_bars']} "
              f"tp1={row['tp1_hit_rate_pct']}% stopout={row['stop_out_pct']}% "
              f"reasons={row['exit_reasons']}", flush=True)
    with open(os.path.join(BASE, "v11_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print("wrote v11_results.json", flush=True)


if __name__ == "__main__":
    main()
