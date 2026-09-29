"""Exit-ablation study on Mike's Pine V3.6 reimplementation.

Question: how much of the baseline +0.195R expectancy (PINE_V36_hybrid:UX51:4h,
4bps) comes from the EXIT logic vs the entries?

Variants keep the ENTRY logic byte-identical to pine_backtest.gen_pine_trades
(same signals, entry prices/timing, gap-below-stop skip rule, universe UX51,
4H bars, costs, portfolio constraints). Only exit management changes:

  baseline : Pine exits verbatim -- sanity-check rerun, must reproduce ~+0.195R.
  time20   : exit entire position at open of entry_bar+20. No stop, no TP1,
             no trailing. The structural stop is retained SYNTHETICALLY for
             position sizing and R-denomination only -- it never triggers.
             Isolates the value of ALL Pine exit logic.
  stop_tp1 : structural stop + 50%-at-TP1 exactly as Pine (TP1 intrabar limit,
             stop close-evaluated -> next-bar open). Runner keeps the INITIAL
             stop (no trail ratchet), no EMA55/trend-bear exits, 30-bar time
             cap (exit at open of entry_bar+30). Isolates the value of the
             active trade-management exits (trail + EMA55/bear exits).

Honest caveat: with the one-position-per-symbol rule, different exit timing
shifts when the symbol becomes available for the next entry, so realized
trade LISTS can diverge after the first exit difference. Entry LOGIC is
identical; the measured gap is the economic value of the exit component
inclusive of downstream entry-availability effects.

Local-only research. No live rules modified. No existing files overwritten.
"""

import json
import os
import sys
import traceback

import pandas as pd

import pine_backtest as pb

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(BASE, "pine_exit_ablation_results.json")

MODES = ["baseline", "time20", "stop_tp1"]
MODE_LABEL = {
    "baseline": "Pine entries + Pine exits (rerun)",
    "time20": "Pine entries + fixed 20-bar exit, no stop/TP1/trail",
    "stop_tp1": "Pine entries + stop & 50%-TP1 only, no trail/EMA55, 30-bar cap",
}


def close_exit(pos, df, i, n, reason):
    """Close-evaluated exit -> fill at next bar open (baseline convention)."""
    if i + 1 < n:
        exit_px = float(df["Open"].iloc[i + 1])
        exit_idx, exit_time = i + 1, df.index[i + 1]
    else:
        exit_px, exit_time = float(df.iloc[i]["Close"]), df.index[i]
        exit_idx = i
    return True, reason, exit_px, exit_idx, exit_time


def manage(pos, df, i, n, mode):
    bar = df.iloc[i]
    hi, close = float(bar["High"]), float(bar["Close"])
    if mode == "baseline":
        if not pos["tp_hit"] and hi >= pos["tp1"]:
            pos["tp_hit"] = True  # 50% filled at TP1 limit
        if pos["tp_hit"]:
            pos["runner"] = max(pos["runner"],
                                close - float(bar["atr"]) * pb.TRAIL_ATR)
        trend_bear = bar["e21"] < bar["e55"] and close < bar["e200"]
        if close < pos["runner"]:
            return close_exit(pos, df, i, n, "stop")
        if close < bar["e55"] or trend_bear:
            return close_exit(pos, df, i, n,
                              "ema55-bear" if trend_bear else "ema55-break")
        return (False, None, None, None, None)
    if mode == "time20":
        # decided at close of entry_bar+19 -> exit at open of entry_bar+20
        if i - pos["entry_idx"] >= 19:
            return close_exit(pos, df, i, n, "time-20")
        return (False, None, None, None, None)
    if mode == "stop_tp1":
        if not pos["tp_hit"] and hi >= pos["tp1"]:
            pos["tp_hit"] = True
        if close < pos["stop"]:  # initial stop only, never ratcheted
            return close_exit(pos, df, i, n, "stop")
        # 30-bar cap: decided at close of entry_bar+29 -> open of +30
        if i - pos["entry_idx"] >= 29:
            return close_exit(pos, df, i, n, "timecap-30")
        return (False, None, None, None, None)
    raise ValueError(f"unknown mode {mode}")


def finalize(pos, exit_px, exit_idx, exit_time, reason):
    risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
    r1 = ((pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac
          if pos["tp_hit"] else None)
    r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
    r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
    exit_synth = pos["entry"] * (1 + r_blend * risk_frac)
    return {
        "symbol": pos["symbol"], "entry": pos["entry"], "stop": pos["stop"],
        "exit": exit_synth, "reason": reason,
        "tp1_hit": pos["tp_hit"],
        "entry_time": pos["entry_time"], "exit_time": exit_time,
        "hold_bars": exit_idx - pos["entry_idx"],
        "signal_time": pos["signal_time"],
    }


def gen_variant_trades(sym, df, mode):
    """Entry block identical to pine_backtest.gen_pine_trades; exits vary."""
    trades = []
    skipped_gap = 0
    n = len(df)
    i = pb.WARMUP
    in_trade = False
    while i < n - 1:
        if not in_trade:
            if pb.pine_buy_signal(df, i):
                sig = df.iloc[i]
                entry = float(df["Open"].iloc[i + 1])
                stop0 = float(sig["Close"] - sig["atr"] * pb.SL_ATR)
                if entry <= stop0:
                    skipped_gap += 1
                    i += 1
                    continue
                in_trade = True
                pos = {"symbol": sym, "entry": entry, "stop": stop0,
                       "tp1": entry + float(sig["atr"]) * pb.TP_ATR,
                       "tp_hit": False, "runner": stop0,
                       "entry_idx": i + 1,
                       "entry_time": df.index[i + 1],
                       "signal_time": df.index[i].isoformat()}
                i += 1
                continue
            i += 1
            continue
        done, reason, exit_px, exit_idx, exit_time = manage(pos, df, i, n, mode)
        if done:
            trades.append(finalize(pos, exit_px, exit_idx, exit_time, reason))
            in_trade = False
        i += 1
    return trades, skipped_gap


def run_variant(mode, data):
    all_trades, closes, skipped = [], {}, 0
    for sym, df in data.items():
        tr, sg = gen_variant_trades(sym, df, mode)
        all_trades.extend(tr)
        closes[sym] = df["Close"]
        skipped += sg
    all_trades.sort(key=lambda t: t["entry_time"])
    rows = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
        rows.append(pb.summarize(f"PINE_V36_ablation:{mode}:UX51:4h",
                                 all_trades, port, skipped, cost_name))
    return rows


def main():
    print("loading cache + indicators (once, shared across variants)...", flush=True)
    data = {}
    for sym in pb.UNIVERSE_X:
        path = os.path.join(pb.CACHE, f"h4_{sym}.pkl")
        if not os.path.exists(path):
            print(f"  [warn] no cache for {sym}, skipping", flush=True)
            continue
        df = pd.read_pickle(path)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"  [warn] no volume for {sym}, skipping", flush=True)
            continue
        data[sym] = pb.add_pine_indicators(df)
    print(f"  {len(data)} symbols ready", flush=True)

    results = {"notes": [
        "Exit-ablation on the Pine V3.6 reimplementation (pine_backtest.py).",
        "Entries byte-identical across variants (same signal logic, entry px, "
        "gap-skip rule, universe UX51, 4H bars, costs, portfolio constraints).",
        "baseline must reproduce ~+0.195R (sanity check).",
        "time20: fixed 20-bar exit at next-bar open; structural stop kept "
        "SYNTHETICALLY for sizing/R-denomination only, never triggered.",
        "stop_tp1: stop + 50%-TP1 as Pine; runner keeps initial stop (no "
        "trail), no EMA55/trend-bear exits, 30-bar cap.",
        "Caveat: one-position-per-symbol means exit timing shifts subsequent "
        "entry availability, so realized trade lists can diverge; entry LOGIC "
        "is identical and the gap is the economic value of the exit component.",
    ], "variants": {}}

    for mode in MODES:
        print(f"== variant {mode}: {MODE_LABEL[mode]} ==", flush=True)
        rows = run_variant(mode, data)
        results["variants"][mode] = {"label": MODE_LABEL[mode], "runs": rows}
        for r in rows:
            print(f"  [{r['cost']}] n={r['trades']} win={r['win_rate_pct']}% "
                  f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
                  f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}% "
                  f"hold={r['avg_hold_bars']} tp1={r['tp1_hit_rate_pct']}% "
                  f"reasons={r['exit_reasons']}", flush=True)
        # incremental write: never lose completed variants if we die
        with open(OUT_JSON, "w") as f:
            json.dump(results, f, indent=1, default=str)
        print(f"  wrote {OUT_JSON}", flush=True)

    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        # best-effort partial write already happened per-variant
        sys.exit(1)
