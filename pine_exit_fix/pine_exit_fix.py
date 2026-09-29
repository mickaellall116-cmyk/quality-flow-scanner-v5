"""Pine V3.6 exit-fix study — Step 2 exploratory.

Pre-specified in PINE_EXIT_FIX_SPEC.md (written before any test). Entries
byte-identical to pine_backtest.gen_pine_trades across all variants; only
exit management varies. Same data/window as the ablation:
backtest_cache/v3/h4_*.pkl (2024-09-16 -> 2026-09-14), UX51, 4H.

Modes:
  baseline : rerun sanity check, must reproduce ~+0.195R.
  fixA     : "wide_stop"  - stop0 = signal close - ATR*2.25, rest = baseline.
  fixB     : "late_arm"   - stop0 = ATR*2.25 always active; baseline management
             (trail 2.5x, EMA55/trendBear) takes over only after MFE >= +1R.
  fixC     : "slow_trail" - baseline stop; trail at 3.5x ATR after TP1;
             EMA55-break kept; trendBear exit removed.

Local-only research. No existing files modified.
"""

import json
import os
import sys
import traceback

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))  # repo root: pine_backtest
import pine_backtest as pb

OUT_JSON = os.path.join(BASE, "pine_exit_fix_results.json")

MODES = ["baseline", "fixA", "fixB", "fixC"]
MODE_LABEL = {
    "baseline": "Pine entries + Pine exits (rerun sanity)",
    "fixA": "wide_stop: stop 2.25x ATR, rest baseline",
    "fixB": "late_arm: 2.25x stop until +1R MFE, then baseline mgmt",
    "fixC": "slow_trail: baseline stop, 3.5x trail, no trendBear exit",
}

SL_MULT = {"baseline": 1.5, "fixA": 2.25, "fixB": 2.25, "fixC": 1.5}
TRAIL_MULT = {"baseline": 2.5, "fixA": 2.5, "fixB": 2.5, "fixC": 3.5}
TREND_BEAR_EXIT = {"baseline": True, "fixA": True, "fixB": True, "fixC": False}


def close_exit(pos, df, i, n, reason):
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
    atr = float(bar["atr"])
    risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]

    # TP1 partial: intrabar limit, as baseline, in every mode
    if not pos["tp_hit"] and hi >= pos["tp1"]:
        pos["tp_hit"] = True
    pos["mfe_r"] = max(pos["mfe_r"],
                       (hi - pos["entry"]) / pos["entry"] / risk_frac)

    if mode == "fixB" and pos["mfe_r"] < 1.0:
        # pre-arm: ONLY the wide disaster stop can exit
        if close < pos["stop"]:
            return close_exit(pos, df, i, n, "stop")
        return (False, None, None, None, None)

    # armed baseline-style management (all modes incl. fixB post-arm)
    if pos["tp_hit"]:
        pos["runner"] = max(pos["runner"], close - atr * TRAIL_MULT[mode])
    trend_bear = bar["e21"] < bar["e55"] and close < bar["e200"]
    if close < pos["runner"]:
        return close_exit(pos, df, i, n, "stop")
    if close < bar["e55"] or (TREND_BEAR_EXIT[mode] and trend_bear):
        return close_exit(pos, df, i, n,
                          "ema55-bear" if trend_bear else "ema55-break")
    return (False, None, None, None, None)


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
                stop0 = float(sig["Close"] - sig["atr"] * SL_MULT[mode])
                if entry <= stop0:
                    skipped_gap += 1
                    i += 1
                    continue
                in_trade = True
                pos = {"symbol": sym, "entry": entry, "stop": stop0,
                       "tp1": entry + float(sig["atr"]) * pb.TP_ATR,
                       "tp_hit": False, "runner": stop0, "mfe_r": 0.0,
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
        rows.append(pb.summarize(f"PINE_V36_exitfix:{mode}:UX51:4h",
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
        "Exit-fix exploratory, pre-specified in PINE_EXIT_FIX_SPEC.md.",
        "Entries byte-identical across variants; only exit management varies.",
        "baseline must reproduce ~+0.195R (sanity check).",
        "fixA: stop 2.25x ATR, rest baseline. fixB: 2.25x stop until +1R MFE,"
        " then baseline mgmt. fixC: baseline stop, 3.5x trail, no trendBear.",
        "Winner criterion: highest expectancy_net_r at 4bps with maxDD <= 40%.",
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
        with open(OUT_JSON, "w") as f:
            json.dump(results, f, indent=1, default=str)
        print(f"  wrote {OUT_JSON}", flush=True)

    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
