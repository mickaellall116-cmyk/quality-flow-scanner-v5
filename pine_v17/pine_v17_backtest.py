"""Faithful backtest of Mike's older Pine strategy 'Quality Flow System V1.7 AUTO
Hybrid' (all defaults, STOCK branch for all UX51 symbols), on the same data and
portfolio assumptions as pine_backtest.py (V3.6), so results are directly
head-to-head comparable.

Pre-specified in V17_SPEC.md (frozen before any test). Local-only research.

V1.7 logic (defaults):
- Entries: confirmedBuy OR stockEarly (STOCK branch), with trend-leg control
  (entriesThisTrend reset on EMA21/55 crossover, 7-bar cooldown, max 3/trend leg).
- Exits: TP1 50% intrabar limit at close+1.5*ATR; breakeven after TP1; runner
  trails close-ATR*3.5 (4.5 in strong trend: EMA21>EMA55 & ADX>=20); close-evaluated
  exits filled next-bar-open: cmfExit, trendExit (2 closes < EMA55), stopExit
  (close < finalStop), stockWeakExit; strong trend gates to stopExit only;
  exit needs 2 consecutive bars (useExitConfirm). MFI exit OFF.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))
from pine_backtest import (  # noqa: E402  (import, not modification)
    ema, atr, adx, simulate_portfolio, summarize, _outcome,
    CACHE, UNIVERSE_X, WARMUP, RISK_PCT, COSTS,
)

# V1.7 defaults (STOCK branch)
ADX_MIN, RUNNER_ATR = 15.0, 3.5
STRONG_ADX_BONUS = 5.0
EXTRA_TRAIL_ATR = 1.0
COOLDOWN, MAX_ENTRIES = 7, 3
BREAKOUT_BARS = 20
TP_ATR, SL_ATR = 1.5, 2.0


def mfi(df, l=14):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3.0
    mf = tp * df["Volume"]
    pos = pd.Series(np.where(tp > tp.shift(1), mf, 0.0), index=df.index)
    neg = pd.Series(np.where(tp < tp.shift(1), mf, 0.0), index=df.index)
    mr = pos.rolling(l).sum() / neg.rolling(l).sum().replace(0, np.nan)
    return 100 - 100 / (1 + mr)


def add_v17_indicators(df):
    out = df.copy()
    c = out["Close"]
    out["e21"] = ema(c, 21)
    out["e55"] = ema(c, 55)
    out["e50"] = ema(c, 50)
    out["e200"] = ema(c, 200)
    out["atr"] = atr(out, 14)
    out["atr_base"] = out["atr"].rolling(50).mean()
    out["atr_ratio"] = out["atr"] / out["atr_base"]
    out["adx"] = adx(out, 14)
    # CMF
    mf_mult = ((c - out["Low"]) - (out["High"] - c)) / (out["High"] - out["Low"]).clip(lower=1e-9)
    mf_vol = mf_mult * out["Volume"]
    out["cmf"] = mf_vol.rolling(20).mean() / out["Volume"].rolling(20).mean()
    out["cmf_falling"] = (out["cmf"] < out["cmf"].shift(1)) & (out["cmf"].shift(1) < out["cmf"].shift(2))
    out["mfi"] = mfi(out, 14)
    obv = pd.Series(np.where(c > c.shift(1), out["Volume"],
                             np.where(c < c.shift(1), -out["Volume"], 0.0)), index=df.index).cumsum()
    out["obv_up"] = ema(obv, 5) > ema(obv, 20)
    # signal components (stateful gates applied in loop)
    out["trend_bull"] = out["e21"] > out["e55"]
    out["flow_ok"] = out["cmf"] > 0
    out["mfi_ok"] = (out["mfi"] >= 40) & (out["mfi"] <= 75)
    out["atr_ok"] = out["atr_ratio"] >= 0.85
    out["adx_ok"] = out["adx"] >= ADX_MIN
    out["slope_ok"] = (out["e50"] - out["e50"].shift(5)) > 0
    out["breakout"] = c > out["High"].rolling(BREAKOUT_BARS).max().shift(1)
    out["e200_ok"] = c > out["e200"] * 0.98
    out["spread"] = (out["e21"] - out["e55"]).abs() / c
    out["trend_regime"] = (out["adx"] >= ADX_MIN) & (out["atr_ratio"] >= 0.85) & (out["spread"] > 0.006)
    out["trade_allowed"] = out["trend_regime"] | (out["trend_bull"] & out["slope_ok"] & out["atr_ok"])
    out["ext"] = (c - out["e21"]).abs() / out["atr"]
    out["ext_ok"] = out["ext"] < 3.2
    out["controlled_pb"] = (out["Low"] <= out["e21"]) & (c > out["e21"]) & (c > out["e55"])
    out["bull_candle"] = (c > out["Open"]) & (c > c.shift(1))
    out["reclaim"] = (c > out["e21"]) & (c.shift(1) < out["e21"].shift(1)) & (c > out["Open"])
    out["trend_start"] = (out["e21"] > out["e55"]) & (out["e21"].shift(1) <= out["e55"].shift(1))
    # exits (close-evaluated)
    out["trend_strong"] = (out["e21"] > out["e55"]) & (out["adx"] >= ADX_MIN + STRONG_ADX_BONUS)
    out["cmf_exit"] = (out["cmf"] < 0) & out["cmf_falling"]
    out["trend_exit"] = (c < out["e55"]) & (c.shift(1) < out["e55"].shift(1))
    out["weak_exit"] = (~out["trend_strong"]) & ((out["cmf"] < 0) | (c < out["e21"]))
    return out


def finalize_trade(pos, df, exit_px, exit_idx, exit_time, reason):
    # R math uses INITIAL risk (signal stop), like V3.6
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
        "tp1_hit": pos["tp_hit"], "entry_type": pos["entry_type"],
        "entry_time": pos["entry_time"], "exit_time": exit_time,
        "hold_bars": exit_idx - pos["entry_idx"],
        "signal_time": df.index[pos["entry_idx"] - 1].isoformat(),
    }


def gen_v17_trades(sym, df, cutoff=None, eod_liquidate=False):
    trades = []
    skipped_gap = skipped_early = 0
    n = len(df)
    i = WARMUP
    in_trade = False
    entries_this_trend = 0
    last_entry_idx = None
    while i < n - 1:
        r = df.iloc[i]
        if bool(r["trend_start"]):
            entries_this_trend = 0
        if not in_trade:
            if cutoff is not None and df.index[i] < cutoff:
                if (r["trend_bull"] and bool(r["breakout"])):
                    skipped_early += 1
                i += 1
                continue
            cooldown_ok = last_entry_idx is None or (i - last_entry_idx) >= COOLDOWN
            entry_limit_ok = entries_this_trend < MAX_ENTRIES
            gates = cooldown_ok and entry_limit_ok
            confirmed = (r["trend_bull"] and r["breakout"] and r["flow_ok"] and r["mfi_ok"]
                         and r["atr_ok"] and r["adx_ok"] and r["e200_ok"]
                         and r["trade_allowed"] and r["ext_ok"])
            early_allowed = (r["trend_bull"] and r["flow_ok"] and r["mfi_ok"]
                             and r["atr_ok"] and r["e200_ok"]
                             and r["trade_allowed"] and r["ext_ok"])
            early = (early_allowed and r["adx_ok"] and r["slope_ok"]
                     and (r["controlled_pb"] or r["reclaim"]) and r["bull_candle"])
            if gates and (confirmed or early):
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
                       "tp_hit": False, "entry_idx": i + 1,
                       "entry_time": df.index[i + 1],
                       "entry_type": "confirmed" if confirmed else "early"}
                entries_this_trend += 1
                last_entry_idx = i
                prev_smart_exit = False
                trend_exit_armed = False
                i += 1
                continue
            i += 1
            continue
        # ---- manage open position (entry bar included, like Pine) ----
        bar = df.iloc[i]
        hi, close = float(bar["High"]), float(bar["Close"])
        if not pos["tp_hit"] and hi >= pos["tp1"]:
            pos["tp_hit"] = True  # 50% filled at TP1 limit
        trend_strong = bool(bar["trend_strong"])
        smart_atr = RUNNER_ATR + (EXTRA_TRAIL_ATR if trend_strong else 0.0)
        if pos["tp_hit"]:
            # breakeven at actual fill, then ratcheting ATR trail
            trail = close - float(bar["atr"]) * smart_atr
            pos["stop"] = max(pos["stop"] if pos.get("trailed") else pos["entry"], trail)
            pos["trailed"] = True
            final_stop = pos["stop"]
        else:
            final_stop = pos["stop"]
        stop_exit = close < final_stop
        if trend_strong:
            smart_exit = stop_exit
            reason = "stop"
        else:
            if stop_exit:
                smart_exit, reason = True, "stop"
            elif bool(bar["cmf_exit"]):
                smart_exit, reason = True, "cmf"
            elif bool(bar["trend_exit"]):
                smart_exit, reason = True, "trend2"
            elif bool(bar["weak_exit"]):
                smart_exit, reason = True, "weak"
            else:
                smart_exit, reason = False, None
        done = smart_exit and prev_smart_exit  # useExitConfirm: 2 consecutive bars
        prev_smart_exit = smart_exit
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
        # end-of-data liquidation at last close (used by 2022 validation)
        exit_px = float(df["Close"].iloc[-1])
        trades.append(finalize_trade(pos, df, exit_px, n - 1, df.index[-1], "eod"))
    return trades, skipped_gap, skipped_early


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
        df = add_v17_indicators(df)
        closes[sym] = df["Close"]
        tr, sg, _ = gen_v17_trades(sym, df)
        all_trades.extend(tr)
        skipped += sg
        n_e = sum(1 for t in tr if t["entry_type"] == "early")
        print(f"  {sym}: {len(tr)} trades ({n_e} early)", flush=True)
    all_trades.sort(key=lambda t: t["entry_time"])
    results = {"spec": "V17_SPEC.md (frozen pre-test)", "runs": []}
    for cost_name, cost in COSTS.items():
        port = simulate_portfolio(all_trades, closes, cost, RISK_PCT)
        row = summarize("PINE_V17_hybrid:UX51:4h", all_trades, port, skipped, cost_name)
        # extra: avg winner/loser R, stop-out %, entry-type split
        t = pd.DataFrame(all_trades)
        net_r = []
        for tr in all_trades:
            _, _, nr, _ = _outcome(tr["entry"], tr["stop"], tr["exit"], COSTS[cost_name])
            net_r.append(nr)
        t["net_r"] = net_r
        row["avg_winner_r"] = round(float(t.loc[t.net_r > 0, "net_r"].mean()), 3)
        row["avg_loser_r"] = round(float(t.loc[t.net_r <= 0, "net_r"].mean()), 3)
        row["stop_out_pct"] = round(float((t["reason"] == "stop").mean()) * 100, 1)
        row["early_trades"] = int((t["entry_type"] == "early").sum())
        row["confirmed_trades"] = int((t["entry_type"] == "confirmed").sum())
        for et in ("early", "confirmed"):
            sub = t[t["entry_type"] == et]["net_r"]
            row[f"exp_{et}_r"] = round(float(sub.mean()), 3) if len(sub) else None
        results["runs"].append(row)
        print(f"[{cost_name}] trades={row['trades']} exp={row['expectancy_net_r']}R "
              f"PF={row['profit_factor']} ret={row['total_return_pct']}% "
              f"dd={row['max_drawdown_pct']}% hold={row['avg_hold_bars']} "
              f"tp1={row['tp1_hit_rate_pct']}% stopout={row['stop_out_pct']}% "
              f"reasons={row['exit_reasons']}", flush=True)
    with open(os.path.join(BASE, "v17_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print("wrote v17_results.json", flush=True)


if __name__ == "__main__":
    main()
