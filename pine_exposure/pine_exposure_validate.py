"""2022 out-of-sample validation for the frozen exposure candidate C1 (E1 sector2).
Protocol mirrors pine_ranking_validate.py: 32 symbols, signals with
signal_time >= 2022-01-01, EOD liquidation at last close, identical rule for
all variants. C1 frozen in CANDIDATES_FROZEN.md before this ran. No refit.
"""
import glob
import json
import os
import sys
import traceback

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))
sys.path.insert(0, BASE)
import pine_backtest as pb
from pine_exposure import SECTOR, ExposureSim, summarize

OUT_JSON = os.path.join(BASE, "exposure_validate.json")
CACHE_OLD = os.path.join(os.path.dirname(BASE), "v6_short_v2", "cache")
CACHE_NEW = os.path.join(os.path.dirname(BASE), "pine_exit_fix", "cache_2022")
CUTOFF = pd.Timestamp("2022-01-01", tz="UTC")

SECTOR_2022 = dict(SECTOR)
SECTOR_2022.update({"COST": "STAPLES", "WMT": "STAPLES", "JPM": "BANKS",
                    "LLY": "HEALTHCARE", "ORCL": "AI_SOFTWARE",
                    "QQQ": "ETF", "XOM": "ENERGY"})


def gen_trades_2022(sym, df):
    trades = []
    skipped_gap = 0
    n = len(df)
    i = pb.WARMUP
    in_trade = False
    pos = None
    while i < n - 1:
        if not in_trade:
            if df.index[i] >= CUTOFF and pb.pine_buy_signal(df, i):
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
        bar = df.iloc[i]
        lo, hi, close = float(bar["Low"]), float(bar["High"]), float(bar["Close"])
        if not pos["tp_hit"] and hi >= pos["tp1"]:
            pos["tp_hit"] = True
        if pos["tp_hit"]:
            pos["runner"] = max(pos["runner"], close - float(bar["atr"]) * pb.TRAIL_ATR)
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
        if done:
            risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
            r1 = (pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac if pos["tp_hit"] else None
            r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
            r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
            net_ret_blend = r_blend * risk_frac
            exit_synth = pos["entry"] * (1 + net_ret_blend)
            trades.append({
                "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
                "exit": exit_synth, "reason": reason,
                "tp1_hit": pos["tp_hit"],
                "entry_time": pos["entry_time"], "exit_time": exit_time,
                "hold_bars": exit_idx - pos["entry_idx"],
                "signal_time": pos["signal_time"]})
            in_trade = False
            pos = None
        i += 1
    if in_trade:
        exit_px = float(df["Close"].iloc[-1])
        risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
        r1 = (pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac if pos["tp_hit"] else None
        r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
        r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
        net_ret_blend = r_blend * risk_frac
        exit_synth = pos["entry"] * (1 + net_ret_blend)
        trades.append({
            "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
            "exit": exit_synth, "reason": "eod",
            "tp1_hit": pos["tp_hit"],
            "entry_time": pos["entry_time"], "exit_time": df.index[-1],
            "hold_bars": (n - 1) - pos["entry_idx"],
            "signal_time": pos["signal_time"]})
    return trades, skipped_gap


def load_2022():
    paths = {}
    for d in (CACHE_OLD, CACHE_NEW):
        for p in glob.glob(os.path.join(d, "d4h_2022_*.pkl")):
            sym = os.path.basename(p)[len("d4h_2022_"):-len(".pkl")]
            paths.setdefault(sym, p)
    data = {}
    for sym, p in sorted(paths.items()):
        df = pd.read_pickle(p)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            continue
        if not isinstance(df.index, pd.DatetimeIndex) or df.index.tz is None:
            df.index = pd.to_datetime(df.index, utc=True)
        data[sym] = pb.add_pine_indicators(df)
    return data


def gate_sector2_2022(tr, open_trades, t):
    s = SECTOR_2022[tr["symbol"]]
    n = sum(1 for o in open_trades if SECTOR_2022[o["symbol"]] == s)
    return (n < 2, "sector2")


def main():
    print("loading 2022 4H caches...", flush=True)
    data = load_2022()
    print(f"  {len(data)} symbols", flush=True)
    all_trades, closes_4h, skipped = [], {}, 0
    for sym, df in data.items():
        closes_4h[sym] = df["Close"]
        tr, sg = gen_trades_2022(sym, df)
        all_trades.extend(tr)
        skipped += sg
    all_trades.sort(key=lambda t: t["entry_time"])
    print(f"  {len(all_trades)} candidates", flush=True)

    results = {"notes": ["2022 validation of frozen C1 (E1 sector2).",
                         "C1 frozen before this ran. No refit on 2022."],
               "symbols": sorted(data.keys()), "variants": {}}
    for vname, gate in [("V0_control", None), ("C1_sector2", gate_sector2_2022)]:
        results["variants"][vname] = {}
        for cost_name, cost in pb.COSTS.items():
            sim = ExposureSim(closes_4h, {}, cost, gate=gate, gate_name=vname)
            port = sim.run(all_trades)
            s = summarize(f"PINE_V36_expval:{vname}", port, cost_name)
            s["fill_rate_pct"] = round(len(port["taken"]) / len(all_trades) * 100, 1)
            results["variants"][vname][cost_name] = s
            print(f"{vname} [{cost_name}]: n={s['trades']} exp={s['expectancy_net_r']}R "
                  f"PF={s['profit_factor']} ret={s['total_return_pct']}% "
                  f"dd={s['max_drawdown_pct']}% gate_skip={s['skipped_gate']}",
                  flush=True)
    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT_JSON}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
