"""Step 3: validate V0 baseline + frozen candidates C1/C2/C3 on 2022 4H.

Protocol (same as pine_exit_fix validation): signals with signal_time >=
2022-01-01 (indicators warmed on 2021-09+ headroom); trades open at data end
liquidated at last close (reason "eod"); identical rule for all variants.
Universe: union of v6_short_v2/cache/d4h_2022_*.pkl and
pine_exit_fix/cache_2022/d4h_2022_*.pkl, deduped by symbol; coverage documented.

Local-only research. No existing files modified.
"""

import glob
import json
import os
import sys
import traceback

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pine_backtest as pb
from pine_entry_ablation import signal_variant, extend_row, VARIANTS

OUT_JSON = os.path.join(HERE, "pine_entry_validate.json")
CACHE_OLD = os.path.join(os.path.dirname(HERE), "v6_short_v2", "cache")
CACHE_NEW = os.path.join(os.path.dirname(HERE), "pine_exit_fix", "cache_2022")
CUTOFF = pd.Timestamp("2022-01-01", tz="UTC")


def base_cfg():
    return {"volume": True, "hot_guard": True, "trend_bull": True,
            "strong_trend": True, "score_gate": True, "breakout": True,
            "ready_prev": True, "modes": {"confirmed", "breakout", "ready"}}


CANDIDATES = {
    "V0_baseline": base_cfg(),
    "C1_drop_harmful": {**base_cfg(), "volume": False, "hot_guard": False},
    "C2_drop_harmful_neutral": {**base_cfg(), "volume": False, "hot_guard": False,
                                "score_gate": False},
    "C3_breakout_pure": {**base_cfg(), "volume": False, "hot_guard": False,
                         "score_gate": False, "modes": {"breakout"}},
}


def gen_trades_2022(sym, df, cfg):
    trades = []
    skipped_gap = 0
    n = len(df)
    i = pb.WARMUP
    in_trade = False
    pos = None
    while i < n - 1:
        if not in_trade:
            if df.index[i] >= CUTOFF and signal_variant(df, i, cfg):
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
            exit_synth = pos["entry"] * (1 + r_blend * risk_frac)
            trades.append({
                "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
                "exit": exit_synth, "reason": reason,
                "tp1_hit": pos["tp_hit"],
                "entry_time": pos["entry_time"], "exit_time": exit_time,
                "hold_bars": exit_idx - pos["entry_idx"],
                "signal_time": pos["signal_time"],
            })
            in_trade = False
            pos = None
        i += 1
    if in_trade:
        exit_px = float(df["Close"].iloc[-1])
        risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
        r1 = (pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac if pos["tp_hit"] else None
        r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
        r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
        exit_synth = pos["entry"] * (1 + r_blend * risk_frac)
        trades.append({
            "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
            "exit": exit_synth, "reason": "eod",
            "tp1_hit": pos["tp_hit"],
            "entry_time": pos["entry_time"], "exit_time": df.index[-1],
            "hold_bars": (n - 1) - pos["entry_idx"],
            "signal_time": pos["signal_time"],
        })
    return trades, skipped_gap


def load_2022():
    paths = {}
    for d in (CACHE_OLD, CACHE_NEW):
        for p in glob.glob(os.path.join(d, "d4h_2022_*.pkl")):
            sym = os.path.basename(p)[len("d4h_2022_"):-len(".pkl")]
            paths.setdefault(sym, p)  # old cache wins ties
    data = {}
    for sym, p in sorted(paths.items()):
        df = pd.read_pickle(p)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"  [warn] no volume for {sym}, skipping", flush=True)
            continue
        if not isinstance(df.index, pd.DatetimeIndex) or df.index.tz is None:
            df.index = pd.to_datetime(df.index, utc=True)
        data[sym] = pb.add_pine_indicators(df)
    return data


def main():
    print("loading 2022 4H caches...", flush=True)
    data = load_2022()
    print(f"  {len(data)} symbols: {sorted(data)}", flush=True)

    results = {"notes": [
        "2022 out-of-sample validation of frozen entry candidates.",
        "Protocol: signals >= 2022-01-01 only; EOD liquidation at last close.",
        "Candidates frozen in CANDIDATES_FROZEN.md before this ran.",
    ], "symbols": sorted(data), "variants": {},
        "candidate_cfgs": {k: {**v, "modes": sorted(v["modes"])}
                           for k, v in CANDIDATES.items()}}

    for vid, cfg in CANDIDATES.items():
        print(f"== {vid} ==", flush=True)
        all_trades, closes, skipped = [], {}, 0
        for sym, df in data.items():
            tr, sg = gen_trades_2022(sym, df, cfg)
            all_trades.extend(tr)
            closes[sym] = df["Close"]
            skipped += sg
        all_trades.sort(key=lambda t: t["entry_time"])
        rows = []
        for cost_name, cost in pb.COSTS.items():
            port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
            row = pb.summarize(f"PINE_V36_entryval:{vid}:2022:4h",
                               all_trades, port, skipped, cost_name)
            rows.append(extend_row(row, all_trades, cost_name))
        results["variants"][vid] = {"runs": rows}
        for r in rows:
            print(f"  [{r['cost']}] n={r['trades']} win={r.get('win_rate_pct', 'n/a')}% "
                  f"exp={r.get('expectancy_net_r', 'n/a')}R PF={r.get('profit_factor', 'n/a')} "
                  f"ret={r.get('total_return_pct', 'n/a')}% dd={r.get('max_drawdown_pct', 'n/a')}% "
                  f"hold={r.get('avg_hold_bars', 'n/a')}", flush=True)
        with open(OUT_JSON, "w") as f:
            json.dump(results, f, indent=1, default=str)
    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
