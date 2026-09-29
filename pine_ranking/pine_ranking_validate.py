"""2022 out-of-sample validation: unchanged V3.6 control + frozen C1 (rs_top2)
and C2 (vol_top1). Protocol mirrors pine_signal_quality_validate.py:
signals with signal_time >= 2022-01-01 only; trades open at data end
liquidated at last close (reason "eod"); identical rule for all variants.
Ranking features use the same daily benchmark caches (cover 2021-06 -> 2026-09)
and the same bench_ret machinery — no methodology change between windows.
Candidates frozen in CANDIDATES_FROZEN.md before this ran. No refit on 2022."""
import glob
import json
import os
import sys
import traceback

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(os.path.dirname(BASE), "pine_signal_quality"))
import pine_backtest as pb
from pine_signal_quality import load_benchmarks, extend_row
from pine_ranking import compute_features, simulate_portfolio_ranked

OUT_JSON = os.path.join(BASE, "ranking_validate.json")
CACHE_OLD = os.path.join(os.path.dirname(BASE), "v6_short_v2", "cache")
CACHE_NEW = os.path.join(os.path.dirname(BASE), "pine_exit_fix", "cache_2022")
CUTOFF = pd.Timestamp("2022-01-01", tz="UTC")

CANDIDATES = {"C1_rs_top2": ("rs", 2), "C2_vol_top1": ("vol", 1)}


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
                       "entry_idx": i + 1, "signal_idx": i,
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
                "tp1": pos["tp1"], "exit": exit_synth, "reason": reason,
                "tp1_hit": pos["tp_hit"],
                "entry_time": pos["entry_time"], "exit_time": exit_time,
                "hold_bars": exit_idx - pos["entry_idx"],
                "signal_time": pos["signal_time"],
                "signal_idx": pos["signal_idx"],
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
            "tp1": pos["tp1"], "exit": exit_synth, "reason": "eod",
            "tp1_hit": pos["tp_hit"],
            "entry_time": pos["entry_time"], "exit_time": df.index[-1],
            "hold_bars": (n - 1) - pos["entry_idx"],
            "signal_time": pos["signal_time"],
            "signal_idx": pos["signal_idx"],
        })
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
    print("generating 2022 candidates...", flush=True)
    all_trades, closes, skipped_gap = [], {}, 0
    for sym, df in data.items():
        tr, sg = gen_trades_2022(sym, df)
        all_trades.extend(tr)
        closes[sym] = df["Close"]
        skipped_gap += sg
    all_trades.sort(key=lambda t: t["entry_time"])
    print(f"  {len(all_trades)} candidate trades", flush=True)
    print("loading benchmarks + features...", flush=True)
    bench, _ = load_benchmarks()
    feats = compute_features(all_trades, data, bench)

    # fidelity: takeall == pb control on 2022
    port_pb = pb.simulate_portfolio(all_trades, closes, pb.COSTS["4bps"], pb.RISK_PCT)
    port_mine = simulate_portfolio_ranked(all_trades, closes, pb.COSTS["4bps"],
                                          pb.RISK_PCT, feats, "takeall", None)
    ok = (abs(port_pb["final_equity"] - port_mine["final_equity"]) < 1e-6
          and port_pb["skipped_cap_count"] == port_mine["skipped_cap_count"])
    print(f"2022 fidelity check: {'PASS' if ok else 'FAIL'}", flush=True)
    if not ok:
        sys.exit(2)

    results = {"notes": [
        "2022 out-of-sample validation of frozen ranking candidates.",
        "Protocol: signals >= 2022-01-01; EOD liquidation; identical features.",
        "C1/C2 frozen in CANDIDATES_FROZEN.md before this ran. No refit on 2022.",
    ], "symbols": sorted(data), "variants": {}}

    variants = [("V0_control", "takeall", None)] + \
               [(vid, s, n) for vid, (s, n) in CANDIDATES.items()]
    for vid, scheme, n_cap in variants:
        print(f"== {vid} ==", flush=True)
        results["variants"][vid] = {}
        for cost_name, cost in pb.COSTS.items():
            taken_idx = []
            port = simulate_portfolio_ranked(all_trades, closes, cost, pb.RISK_PCT,
                                             feats, scheme, n_cap,
                                             taken_out=taken_idx)
            taken = [all_trades[i] for i in taken_idx]
            row = pb.summarize(f"PINE_V36_rankval:{vid}", taken, port,
                               skipped_gap, cost_name)
            row["fill_rate_pct"] = round(len(taken) / len(all_trades) * 100, 1)
            row["candidates_available"] = len(all_trades)
            row = extend_row(row, taken, cost_name)
            if vid == "V0_control":
                # all-candidate stats too, for comparability with prior studies
                # (which reported 2022 control over all candidates, +0.287R)
                row_all = pb.summarize(f"PINE_V36_rankval:{vid}:allcand",
                                       all_trades, port, skipped_gap, cost_name)
                row_all = extend_row(row_all, all_trades, cost_name)
                row["all_candidates"] = {k: row_all[k] for k in
                                         ("trades", "expectancy_net_r", "profit_factor",
                                          "win_rate_pct")}
            results["variants"][vid][cost_name] = row
            print(f"  [{cost_name}] n={row['trades']} exp={row.get('expectancy_net_r')}R "
                  f"PF={row.get('profit_factor')} ret={row.get('total_return_pct')}% "
                  f"dd={row.get('max_drawdown_pct')}%", flush=True)
        json.dump(results, open(OUT_JSON, "w"), indent=1, default=str)
    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
