"""Final signal-quality study: H1/H2/H3 as additional filters on unchanged V3.6.
Research window only (UX51 4H 2024-09-16 -> 2026-09-14). Spec: SIGNAL_QUALITY_SPEC.md
Control fidelity: must reproduce baseline (263 trades, +0.195R @4bps)."""
import json
import os
import sys
import traceback

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pine_backtest as pb

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(BASE, "signal_quality_results.json")

SECTOR_TO_ETF = {
    "Technology": "XLK", "Financial Services": "XLF", "Financial": "XLF",
    "Healthcare": "XLV", "Energy": "XLE", "Industrials": "XLI",
    "Consumer Defensive": "XLP", "Utilities": "XLU", "Consumer Cyclical": "XLY",
    "Communication Services": "XLC", "Communication": "XLC",
    "Real Estate": "XLRE", "Basic Materials": "XLB",
}
CRYPTO = {"BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "AVAX-USD", "LINK-USD", "XRP-USD"}
ETF_SYMS = {"SPY", "IWM", "SMH", "ARKK", "XLF"}
RS_LOOKBACK = 20  # 4H bars, pre-registered


def load_benchmarks():
    man = json.load(open(os.path.join(BASE, "benchmark_manifest.json")))
    secmap = json.load(open(os.path.join(BASE, "sector_map.json")))
    bench = {}
    for etf, m in man.items():
        if m["file"]:
            df = pd.read_pickle(m["file"])
            df.index = df.index.tz_convert("UTC")
            bench[etf] = df.sort_index()
    # per-symbol sector ETF (frozen mapping)
    sym_sector_etf = {}
    for sym, sec in secmap.items():
        if sym in CRYPTO or sym in ETF_SYMS:
            sym_sector_etf[sym] = None
        else:
            sym_sector_etf[sym] = SECTOR_TO_ETF.get(sec)
    return bench, sym_sector_etf


def bench_ret(bdf, t0, t1):
    """Return of benchmark over [t0, t1] using last daily bar <= each timestamp.
    None if unavailable (no lookahead)."""
    idx = bdf.index
    j1 = idx.searchsorted(t1, side="right") - 1
    j0 = idx.searchsorted(t0, side="right") - 1
    if j1 < 0 or j0 < 0 or j1 <= j0:
        return None
    c1 = float(bdf["Close"].iloc[j1])
    c0 = float(bdf["Close"].iloc[j0])
    if c0 <= 0 or np.isnan(c0) or np.isnan(c1):
        return None
    return c1 / c0 - 1.0


def make_filters(bench, sym_sector_etf):
    def h1(sym, df, i):
        """Relative strength: symbol 20-bar return beats SPY, QQQ (+sector)."""
        sym_ret = float(df["Close"].iloc[i] / df["Close"].iloc[i - RS_LOOKBACK] - 1.0)
        t1 = df.index[i].tz_convert("UTC")
        t0 = df.index[i - RS_LOOKBACK].tz_convert("UTC")
        for etf in ("SPY", "QQQ"):
            bdf = bench.get(etf)
            if bdf is None:
                return False
            br = bench_ret(bdf, t0, t1)
            if br is None or not (sym_ret > br):
                return False
        setf = sym_sector_etf.get(sym)
        if setf:
            bdf = bench.get(setf)
            if bdf is None:
                return False
            br = bench_ret(bdf, t0, t1)
            if br is None or not (sym_ret > br):
                return False
        return True

    def h2(sym, df, i):
        """Volatility contraction: ATR14 below its 50-bar baseline."""
        return bool(df["atr_ratio"].iloc[i] < 1.0)

    def h3(sym, df, i):
        """Tight base: prior 10-bar range < 2.0 * ATR14."""
        hi = float(df["High"].iloc[i - 10:i].max())
        lo = float(df["Low"].iloc[i - 10:i].min())
        return bool((hi - lo) < 2.0 * float(df["atr"].iloc[i]))

    return {"H1_rs": h1, "H2_contraction": h2, "H3_tightbase": h3}


def gen_trades(sym, df, filt):
    """Trade loop identical to ablation gen_variant_trades; signal = baseline AND filt."""
    trades = []
    skipped_gap = 0
    n = len(df)
    i = pb.WARMUP
    in_trade = False
    while i < n - 1:
        if not in_trade:
            if pb.pine_buy_signal(df, i) and (filt is None or filt(sym, df, i)):
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
                       "entry_time": df.index[i + 1]}
                i += 1
                continue
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
                "signal_time": df.index[pos["entry_idx"] - 1].isoformat(),
            })
            in_trade = False
        i += 1
    return trades, skipped_gap


def extend_row(row, all_trades, cost_name):
    cost = pb.COSTS[cost_name]
    rs = [pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2] for tr in all_trades]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    n = len(rs)
    row["avg_winner_r"] = round(sum(wins) / len(wins), 3) if wins else None
    row["avg_loser_r"] = round(sum(losses) / len(losses), 3) if losses else None
    row["stop_out_pct"] = round(sum(1 for tr in all_trades if tr["reason"] == "stop") / n * 100, 1) if n else None
    return row


def run_variant(vid, filt, data, label):
    all_trades, closes, skipped = [], {}, 0
    for sym, df in data.items():
        tr, sg = gen_trades(sym, df, filt)
        all_trades.extend(tr)
        closes[sym] = df["Close"]
        skipped += sg
    all_trades.sort(key=lambda t: t["entry_time"])
    rows = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
        row = pb.summarize(label, all_trades, port, skipped, cost_name)
        rows.append(extend_row(row, all_trades, cost_name))
    return rows


def load_4h_cache():
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
    return data


def main():
    print("loading 4H cache...", flush=True)
    data = load_4h_cache()
    print(f"  {len(data)} symbols", flush=True)
    print("loading benchmarks...", flush=True)
    bench, sym_sector_etf = load_benchmarks()
    print(f"  benchmarks: {sorted(bench)}", flush=True)
    n_sector = sum(1 for v in sym_sector_etf.values() if v)
    print(f"  symbols with sector ETF: {n_sector}/{len(sym_sector_etf)}", flush=True)
    filters = make_filters(bench, sym_sector_etf)

    variants = {"V0_control": None, "H1_rs": filters["H1_rs"],
                "H2_contraction": filters["H2_contraction"],
                "H3_tightbase": filters["H3_tightbase"]}
    results = {"notes": [
        "Final signal-quality study. Spec SIGNAL_QUALITY_SPEC.md frozen before testing.",
        "Each H-variant = unchanged V3.6 signal AND the pre-registered filter. Exits byte-identical.",
        "Benchmark returns measured over the symbol's own prior-20-bar calendar span (daily bars, Amendment A).",
    ], "variants": {}}
    for vid, filt in variants.items():
        print(f"== {vid} ==", flush=True)
        rows = run_variant(vid, filt, data, f"PINE_V36_sigqual:{vid}:UX51:4h")
        results["variants"][vid] = {"runs": rows}
        for r in rows:
            print(f"  [{r['cost']}] n={r.get('trades')} win={r.get('win_rate_pct')}% "
                  f"exp={r.get('expectancy_net_r')}R PF={r.get('profit_factor')} "
                  f"ret={r.get('total_return_pct')}% dd={r.get('max_drawdown_pct')}% "
                  f"hold={r.get('avg_hold_bars')} tp1={r.get('tp1_hit_rate_pct')}% "
                  f"stopout={r.get('stop_out_pct')}%", flush=True)
        json.dump(results, open(OUT_JSON, "w"), indent=1, default=str)
    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
