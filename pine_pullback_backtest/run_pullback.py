"""Pullback-entry backtest: does waiting for a retest beat chasing the breakout?

Idea (Mike-approved, from the shadowinteltrades reel): don't chase the breakout;
wait for price to pull back to the breakout level, then enter. The reel uses the
Fixed Range Volume Profile Point of Control; adapted here as the signal bar's
close -- the level the breakout printed from. Pre-defined, no tuning.

- BASE: standard Hybrid pine_buy_signal, rerun in-study (never reuse numbers
  across studies).
- RETEST_SKIP (Variant A): on a signal, work a limit at the signal bar's close
  for up to 5 bars. Touch (bar low <= level <= bar high) -> fill AT the level.
  Stop = fill - 1.5*ATR, TP1 = fill + 2.0*ATR (same risk definition as BASE;
  ATR from the signal bar). No touch within 5 bars -> skip the trade entirely.
- RETEST_CHASE (Variant B): same wait, but if no touch within 5 bars, enter at
  the 5th bar's close with levels recomputed from the actual entry (entry-bar
  ATR).

pine_backtest.py is imported UNMODIFIED. Signal detection uses the original
pb.pine_buy_signal; only entry timing changes. The management block (Mode B:
TP1 limit intrabar, +1R Profit Protect arming via runner trail, close-evaluated
exits filled next-bar open, stop wins ties) is mirrored bar-for-bar in a local
helper -- frozen mechanics untouched. Costs, portfolio sim untouched.
Local-only research. No frozen files modified.

Notes/limitations (stated, not hidden):
- A limit fill is modeled at exactly the limit price even if the bar gapped
  below it (standard simplification; slightly flatters Variant A fills).
- While a limit is being worked (pending), new signals on that name are
  ignored -- one working order per name at a time.
- The 30-bar max hold is part of the frozen Mode B spec; the canonical
  gen_pine_trades engine (baseline included) manages via the Pine-truth exits
  (stop/trail/EMA55) with no separate bar-count exit, so all variants share
  whatever the engine does -- apples to apples.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_pullback_backtest")
sys.path.insert(0, BASE)
import pine_backtest as pb

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "pullback_results.json")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

WAIT_BARS = 5  # max bars to wait for the retest touch


def _manage(pos, df, i, n, sym):
    """Mode B management block, mirrored from gen_pine_trades.

    Returns (done, trade_dict_or_None).
    """
    bar = df.iloc[i]
    lo, hi, close = float(bar["Low"]), float(bar["High"]), float(bar["Close"])
    if not pos["tp_hit"] and hi >= pos["tp1"]:
        pos["tp_hit"] = True  # 50% filled at TP1 limit
    if pos["tp_hit"]:
        pos["runner"] = max(pos["runner"],
                            close - float(bar["atr"]) * pb.TRAIL_ATR)
    trend_bear = bar["e21"] < bar["e55"] and close < bar["e200"]
    done = False
    if close < pos["runner"]:
        reason = "stop"
        done = True
    elif close < bar["e55"] or trend_bear:
        reason = "ema55-bear" if trend_bear else "ema55-break"
        done = True
    if done:
        if i + 1 < n:
            exit_px = float(df["Open"].iloc[i + 1])
            exit_idx, exit_time = i + 1, df.index[i + 1]
        else:
            exit_px, exit_time = close, df.index[i]
            exit_idx = i
        risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
        r1 = ((pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac
              if pos["tp_hit"] else None)
        r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
        r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
        net_ret_blend = r_blend * risk_frac
        exit_synth = pos["entry"] * (1 + net_ret_blend)
        trade = {
            "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
            "exit": exit_synth, "reason": reason,
            "tp1_hit": pos["tp_hit"],
            "entry_time": pos["entry_time"], "exit_time": exit_time,
            "hold_bars": exit_idx - pos["entry_idx"],
            "signal_time": pos["signal_time"],
        }
        return True, trade
    return False, None


def _open_pos(sym, df, entry, atr, entry_idx, sig_idx):
    stop0 = float(entry - atr * pb.SL_ATR)
    return {
        "symbol": sym, "entry": float(entry), "stop": stop0,
        "tp1": float(entry + atr * pb.TP_ATR),
        "tp_hit": False, "runner": stop0,
        "entry_idx": entry_idx,
        "entry_time": df.index[entry_idx],
        "signal_time": df.index[sig_idx].isoformat(),
    }


def gen_retest_trades(sym, df, mode):
    """Variant trade generator. mode in {"skip", "chase"}.

    Returns (trades, stats) where stats = {signals, fills, no_retest_skips,
    chases, skipped_gap}.
    """
    assert mode in ("skip", "chase")
    trades = []
    stats = {"signals": 0, "fills": 0, "no_retest_skips": 0,
             "chases": 0, "skipped_gap": 0}
    n = len(df)
    i = pb.WARMUP
    in_trade = False
    pending = None  # {"sig_i", "level", "atr", "deadline"}
    pos = None
    while i < n - 1:
        if in_trade:
            done, trade = _manage(pos, df, i, n, sym)
            if done:
                trades.append(trade)
                in_trade = False
                pos = None
            i += 1
            continue
        if pending is not None:
            sig_i = pending["sig_i"]
            level = pending["level"]
            bar = df.iloc[i]
            lo, hi = float(bar["Low"]), float(bar["High"])
            if lo <= level <= hi:
                # limit filled at the retest level
                pos = _open_pos(sym, df, level, pending["atr"], i, sig_i)
                stats["fills"] += 1
                pending = None
                in_trade = True
                done, trade = _manage(pos, df, i, n, sym)
                if done:
                    trades.append(trade)
                    in_trade = False
                    pos = None
            elif i >= pending["deadline"]:
                if mode == "chase":
                    close = float(bar["Close"])
                    atr = float(bar["atr"])
                    if close <= close - atr * pb.SL_ATR:  # never true; guard
                        stats["skipped_gap"] += 1
                    else:
                        pos = _open_pos(sym, df, close, atr, i, sig_i)
                        stats["chases"] += 1
                        in_trade = True
                        done, trade = _manage(pos, df, i, n, sym)
                        if done:
                            trades.append(trade)
                            in_trade = False
                            pos = None
                else:
                    stats["no_retest_skips"] += 1
                pending = None
            i += 1
            continue
        # flat and nothing pending: look for a signal
        if pb.pine_buy_signal(df, i):
            sig = df.iloc[i]
            deadline = i + WAIT_BARS
            if deadline <= n - 2:  # deadline bar must exist and be manageable
                pending = {"sig_i": i,
                           "level": float(sig["Close"]),
                           "atr": float(sig["atr"]),
                           "deadline": deadline}
                stats["signals"] += 1
        i += 1
    return trades, stats


def per_ticker_stats(sym, trades):
    out = {"symbol": sym, "trades": len(trades)}
    if not trades:
        return out
    t = pd.DataFrame(trades)
    for cost_name, cost in pb.COSTS.items():
        net_rs = [pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]
                  for tr in trades]
        s = pd.Series(net_rs)
        wins = s[s > 0]
        losses = s[s <= 0]
        gw, gl = float(wins.sum()), float(-losses.sum())
        out[cost_name] = {
            "trades": len(trades),
            "win_rate_pct": round(float((s > 0).mean()) * 100, 1),
            "expectancy_net_r": round(float(s.mean()), 3),
            "profit_factor": round(gw / gl, 2) if gl > 0 else None,
        }
    return out


def main():
    data, closes = {}, {}
    dropped = []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        if "Volume" not in df.columns or df["Volume"].isna().all():
            dropped.append(sym)
            continue
        df = pb.add_pine_indicators(df)
        data[sym] = df
        closes[sym] = df["Close"]
    used = [s for s in WATCHLIST if s in data]
    print(f"loaded {len(used)} tickers; dropped: {dropped}", flush=True)
    for s in used:
        d = data[s]
        print(f"  {s}: {d.index.min()} -> {d.index.max()} ({len(d)} bars)",
              flush=True)

    results = {"variants": [], "wait_bars": WAIT_BARS,
               "deployment_gate_r": 0.15}

    # BASE: canonical engine, rerun in-study
    base_trades, base_per, base_skipped = [], {}, 0
    for sym in used:
        tr, sg = pb.gen_pine_trades(sym, data[sym])
        base_per[sym] = tr
        base_trades.extend(tr)
        base_skipped += sg
    base_trades.sort(key=lambda t: t["entry_time"])
    pooled = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(base_trades, closes, cost, pb.RISK_PCT)
        pooled.append(pb.summarize("PULLBACK:BASE:4h", base_trades, port,
                                   base_skipped, cost_name))
    results["variants"].append({
        "name": "BASE", "trades": len(base_trades),
        "pooled": pooled,
        "per_ticker": [per_ticker_stats(s, base_per.get(s, [])) for s in used],
    })
    for p in pooled:
        print(f"BASE [{p['cost']}]: n={p['trades']} "
              f"win={p['win_rate_pct']}% exp={p['expectancy_net_r']}R "
              f"PF={p['profit_factor']} maxDD={p.get('max_drawdown_pct', '?')}%",
              flush=True)

    # Variants A and B
    for vname, mode in (("RETEST_SKIP", "skip"), ("RETEST_CHASE", "chase")):
        all_trades, per_sym = [], {}
        agg = {"signals": 0, "fills": 0, "no_retest_skips": 0,
               "chases": 0, "skipped_gap": 0}
        for sym in used:
            tr, st = gen_retest_trades(sym, data[sym], mode)
            per_sym[sym] = tr
            all_trades.extend(tr)
            for k in agg:
                agg[k] += st[k]
        all_trades.sort(key=lambda t: t["entry_time"])
        pooled = []
        for cost_name, cost in pb.COSTS.items():
            port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
            s = pb.summarize(f"PULLBACK:{vname}:4h", all_trades, port,
                             agg["skipped_gap"], cost_name)
            pooled.append(s)
        sig = agg["signals"]
        fill_pct = round(agg["fills"] / sig * 100, 1) if sig else 0.0
        skip_pct = round(agg["no_retest_skips"] / sig * 100, 1) if sig else 0.0
        results["variants"].append({
            "name": vname, "trades": len(all_trades),
            "attribution": {**agg, "fill_pct": fill_pct,
                            "no_retest_skip_pct": skip_pct},
            "pooled": pooled,
            "per_ticker": [per_ticker_stats(s, per_sym.get(s, []))
                           for s in used],
        })
        for p in pooled:
            print(f"{vname} [{p['cost']}]: n={p['trades']} "
                  f"win={p['win_rate_pct']}% exp={p['expectancy_net_r']}R "
                  f"PF={p['profit_factor']} maxDD={p.get('max_drawdown_pct', '?')}% "
                  f"| signals={sig} filled={fill_pct}% skipped={skip_pct}% "
                  f"chased={agg['chases']}", flush=True)

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
