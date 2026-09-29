import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import pine_backtest as pb

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(BASE, "pine_entry_ablation_results.json")


def all_on():
    return {"volume": True, "hot_guard": True, "trend_bull": True,
            "strong_trend": True, "score_gate": True, "breakout": True,
            "ready_prev": True,
            "modes": {"confirmed", "breakout", "ready"}}


VARIANTS = {
    "V0_baseline": all_on(),
    "V1_no_volume": {**all_on(), "volume": False},
    "V2_no_hot_guard": {**all_on(), "hot_guard": False},
    "V3_no_trend_bull": {**all_on(), "trend_bull": False},
    "V4_no_strong_trend": {**all_on(), "strong_trend": False},
    "V5_no_score_gate": {**all_on(), "score_gate": False},
    "V6_no_breakout": {**all_on(), "breakout": False},
    "V7_no_ready_prev": {**all_on(), "ready_prev": False},
    "V8_confirmed_only": {**all_on(), "modes": {"confirmed"}},
    "V9_breakout_only": {**all_on(), "modes": {"breakout"}},
    "V10_ready_only": {**all_on(), "modes": {"ready"}},
    "V11_no_confirmed": {**all_on(), "modes": {"breakout", "ready"}},
    "V12_no_breakout_mode": {**all_on(), "modes": {"confirmed", "ready"}},
    "V13_no_ready_mode": {**all_on(), "modes": {"confirmed", "breakout"}},
}


def signal_variant(df, i, cfg):
    """Entry with components toggled per cfg. Baseline cfg == pine_buy_signal."""
    r = df.iloc[i]
    rp = df.iloc[i - 1]
    if pd.isna(r["e200"]) or pd.isna(r["atr_base"]) or pd.isna(r["adx"]):
        return False
    close = r["Close"]
    volume_ok = (r["Volume"] > r["vol_ma"]) if cfg["volume"] else True
    hot = close > r["e9"] + r["atr"] * pb.HOT_ATR
    safe = (not hot) if cfg["hot_guard"] else True
    trend_bull = (r["e21"] > r["e55"] and close > r["e200"]) if cfg["trend_bull"] else True
    strong_trend = (r["adx"] > 20 and r["atr_ratio"] > 0.85) if cfg["strong_trend"] else True
    score = (r["e9"] > r["e21"]) + (r["e21"] > r["e55"]) + (close > r["e200"]) \
        + (r["adx"] > 25) + (r["atr_ratio"] > 1)
    breakout = (close > df["High"].iloc[i - pb.BREAKOUT_BARS:i].max()) if cfg["breakout"] else True
    ready_prev = (rp["Close"] < rp["e21"] and rp["Close"] > rp["e55"]
                  and rp["e21"] > rp["e55"] and rp["atr_ratio"] > 0.85) if cfg["ready_prev"] else True

    confirmed = False
    if "confirmed" in cfg["modes"]:
        score_ok = score >= 4 if cfg["score_gate"] else True
        confirmed = close > r["e21"] and r["e21"] > r["e55"] and close > r["e200"] \
            and score_ok and volume_ok and safe
    breakout_buy = False
    if "breakout" in cfg["modes"]:
        breakout_buy = trend_bull and strong_trend and breakout and volume_ok and safe
    ready_buy = False
    if "ready" in cfg["modes"]:
        score_ok = score >= 3 if cfg["score_gate"] else True
        ready_buy = ready_prev and close > r["e21"] and score_ok and volume_ok and safe
    return bool(confirmed or breakout_buy or ready_buy)


def verify_baseline_fidelity(data):
    """Prove V0 cfg reproduces pine_buy_signal exactly on all bars."""
    cfg = VARIANTS["V0_baseline"]
    for sym, df in data.items():
        for i in range(pb.WARMUP, len(df)):
            a = pb.pine_buy_signal(df, i)
            b = signal_variant(df, i, cfg)
            if a != b:
                raise AssertionError(f"fidelity mismatch {sym} bar {i}: {a} vs {b}")
    print("  baseline fidelity verified (V0 == pine_buy_signal on all bars)", flush=True)


def gen_variant_trades(sym, df, cfg):
    """Trade loop identical to pine_backtest.gen_pine_trades; signal varies."""
    trades = []
    skipped_gap = 0
    n = len(df)
    i = pb.WARMUP
    in_trade = False
    while i < n - 1:
        if not in_trade:
            if signal_variant(df, i, cfg):
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
    """Add avg winner/loser (R) and stop-out % to a summarize() row."""
    cost = pb.COSTS[cost_name]
    rs = []
    for tr in all_trades:
        _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
        rs.append(net_r)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    n = len(rs)
    row["avg_winner_r"] = round(sum(wins) / len(wins), 3) if wins else None
    row["avg_loser_r"] = round(sum(losses) / len(losses), 3) if losses else None
    n_stop = sum(1 for tr in all_trades if tr["reason"] == "stop")
    row["stop_out_pct"] = round(n_stop / n * 100, 1) if n else None
    return row


def run_variant(vid, cfg, data, label):
    all_trades, closes, skipped = [], {}, 0
    for sym, df in data.items():
        tr, sg = gen_variant_trades(sym, df, cfg)
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
    print("loading 4H cache (2024-09-16 -> 2026-09-14)...", flush=True)
    data = load_4h_cache()
    print(f"  {len(data)} symbols", flush=True)
    verify_baseline_fidelity(data)

    results = {"notes": [
        "Entry ablation on Pine V3.6 reimplementation. Exits byte-identical to baseline.",
        "V0 baseline fidelity verified bar-for-bar against pine_buy_signal.",
        "V1-V7: one component removed. V8-V10: modes standalone. V11-V13: modes removed.",
        "Interpretation: d = exp_variant - exp_baseline @4bps. d < -0.03R: component helps. d > +0.02R: dead weight.",
    ], "variants": {}}

    for vid, cfg in VARIANTS.items():
        print(f"== {vid} ==", flush=True)
        rows = run_variant(vid, cfg, data, f"PINE_V36_entryabl:{vid}:UX51:4h")
        results["variants"][vid] = {"runs": rows}
        for r in rows:
            wr = r.get("win_rate_pct", "n/a")
            ex = r.get("expectancy_net_r", "n/a")
            pf = r.get("profit_factor", "n/a")
            ret = r.get("total_return_pct", "n/a")
            dd = r.get("max_drawdown_pct", "n/a")
            hold = r.get("avg_hold_bars", "n/a")
            print(f"  [{r['cost']}] n={r['trades']} win={wr}% "
                  f"exp={ex}R PF={pf} ret={ret}% dd={dd}% hold={hold}", flush=True)
        with open(OUT_JSON, "w") as f:
            json.dump(results, f, indent=1, default=str)

    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
