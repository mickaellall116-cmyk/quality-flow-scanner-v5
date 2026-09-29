"""Trend-filter study: 6 drop-in replacements for trendBull, tested exactly once each.

Candidate set was FIXED UP FRONT (parent task, 2026-09-23). No candidates added
after results, no parameter tuning. Each candidate replaces ONLY the trendBull
computation in the entry signal; exits, costs, portfolio sim, and every other
component are byte-identical to the canonical engine.

Method mirrors pine_entry_ablation/pine_entry_ablation.py:
- Universe: UX51 4H cache (pb.CACHE h4_*.pkl), 2024-09-16 -> 2026-09-14.
- Signal replicated from pb.pine_buy_signal (Hybrid) with trendBull swapped.
- CURRENT variant fidelity-verified bar-for-bar against pb.pine_buy_signal.
- Trade loop copied from the ablation (mirrors gen_pine_trades); exit stack
  identical for all candidates, INCLUDING the trend_bear exit mirror
  (e21<e55 and close<e200) which is deliberately NOT varied: clean isolation of
  the ENTRY filter effect.
- Portfolio: 4bps and 25bps costs, $10k, 1%/trade, max 5 concurrent, 5% risk,
  next-bar-open entries, stop-first ties, gap-below-stop skips (pb defaults).

Local-only research. pine_backtest.py is imported UNMODIFIED. Nothing frozen touched.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pine_backtest as pb

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(BASE, "trend_filter_results.json")

ST_MULT, ST_ATR_L, ST_DONCH_L, ST_RISE_L = 3.0, 10, 55, 10


def add_trend_columns(df):
    """Extra columns needed by the challenger trend definitions. Causal only."""
    out = df.copy()
    out["e55_prev10"] = out["e55"].shift(ST_RISE_L)
    # Donchian: highest high of the prior 55 bars, excluding the current bar
    # (same convention as the engine's 10-bar breakout).
    out["donch55"] = out["High"].shift(1).rolling(ST_DONCH_L).max()
    # Supertrend(10, 3.0): standard formulation, causal loop, no lookahead.
    atr10 = pb.atr(out, ST_ATR_L)
    hl2 = (out["High"] + out["Low"]) / 2.0
    bub = (hl2 + ST_MULT * atr10).to_numpy()
    blb = (hl2 - ST_MULT * atr10).to_numpy()
    close = out["Close"].to_numpy()
    n = len(out)
    fub = np.full(n, np.nan)
    flb = np.full(n, np.nan)
    st_line = np.full(n, np.nan)
    direction = np.zeros(n, dtype=np.int8)
    for i in range(1, n):
        prev_close = close[i - 1]
        if np.isnan(fub[i - 1]) or prev_close > fub[i - 1]:
            fub[i] = bub[i]
        else:
            fub[i] = bub[i] if np.isnan(fub[i - 1]) else max(bub[i], fub[i - 1])
        if np.isnan(flb[i - 1]) or prev_close < flb[i - 1]:
            flb[i] = blb[i]
        else:
            flb[i] = blb[i] if np.isnan(flb[i - 1]) else min(blb[i], flb[i - 1])
        if not np.isnan(fub[i - 1]) and close[i] > fub[i - 1]:
            direction[i] = 1
        elif not np.isnan(flb[i - 1]) and close[i] < flb[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]
        st_line[i] = flb[i] if direction[i] == 1 else fub[i]
    out["st_line"] = st_line
    return out


def trend_bull(df, i, variant):
    r = df.iloc[i]
    close = r["Close"]
    if variant == "CURRENT":
        return bool(r["e21"] > r["e55"] and close > r["e200"])
    if variant == "FULL_STACK":
        return bool(r["e9"] > r["e21"] > r["e55"] and close > r["e200"])
    if variant == "PRICE_STRUCTURE":
        return bool(close > r["e55"] and r["e55"] > r["e55_prev10"]
                    and close > r["e200"])
    if variant == "DONCHIAN":
        return bool(close >= r["donch55"])
    if variant == "SUPERTREND_DIR":
        return bool(close > r["st_line"])
    if variant == "LOOSE":
        return bool(close > r["e55"])
    raise ValueError(variant)


VARIANTS = ["CURRENT", "FULL_STACK", "PRICE_STRUCTURE",
            "DONCHIAN", "SUPERTREND_DIR", "LOOSE"]


def signal_variant(df, i, variant):
    """pb.pine_buy_signal with trendBull swapped for the candidate."""
    r = df.iloc[i]
    rp = df.iloc[i - 1]
    if pd.isna(r["e200"]) or pd.isna(r["atr_base"]) or pd.isna(r["adx"]):
        return False
    close = r["Close"]
    volume_ok = r["Volume"] > r["vol_ma"]
    hot = close > r["e9"] + r["atr"] * pb.HOT_ATR
    safe = not hot
    tb = trend_bull(df, i, variant)
    strong_trend = r["adx"] > 20 and r["atr_ratio"] > 0.85
    score = int(r["e9"] > r["e21"]) + int(r["e21"] > r["e55"]) \
        + int(close > r["e200"]) + int(r["adx"] > 25) + int(r["atr_ratio"] > 1)
    breakout = close > df["High"].iloc[i - pb.BREAKOUT_BARS:i].max()
    ready_prev = rp["Close"] < rp["e21"] and rp["Close"] > rp["e55"] \
        and rp["e21"] > rp["e55"] and rp["atr_ratio"] > 0.85
    confirmed = close > r["e21"] and r["e21"] > r["e55"] and close > r["e200"] \
        and score >= 4 and volume_ok and safe
    breakout_buy = tb and strong_trend and breakout and volume_ok and safe
    ready_buy = ready_prev and close > r["e21"] and score >= 3 and volume_ok and safe
    return bool(confirmed or breakout_buy or ready_buy)


def verify_baseline_fidelity(data):
    for sym, df in data.items():
        for i in range(pb.WARMUP, len(df)):
            a = pb.pine_buy_signal(df, i)
            b = signal_variant(df, i, "CURRENT")
            if a != b:
                raise AssertionError(f"fidelity mismatch {sym} bar {i}: {a} vs {b}")
    print("  baseline fidelity verified (CURRENT == pine_buy_signal, all bars)",
          flush=True)


def gen_variant_trades(sym, df, variant):
    """Trade loop copied from pine_entry_ablation (mirrors gen_pine_trades)."""
    trades = []
    skipped_gap = 0
    n = len(df)
    i = pb.WARMUP
    in_trade = False
    while i < n - 1:
        if not in_trade:
            if signal_variant(df, i, variant):
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
    rs = [pb._outcome(t["entry"], t["stop"], t["exit"], cost)[2] for t in all_trades]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    n = len(rs)
    row["avg_winner_r"] = round(sum(wins) / len(wins), 3) if wins else None
    row["avg_loser_r"] = round(sum(losses) / len(losses), 3) if losses else None
    n_stop = sum(1 for t in all_trades if t["reason"] == "stop")
    row["stop_out_pct"] = round(n_stop / n * 100, 1) if n else None
    return row


def per_ticker_25bps(sym, trades):
    cost = pb.COSTS["25bps"]
    rs = [pb._outcome(t["entry"], t["stop"], t["exit"], cost)[2] for t in trades]
    s = pd.Series(rs)
    return {"trades": len(trades),
            "expectancy_25bps_r": round(float(s.mean()), 3) if len(s) else None}


def run_variant(variant, data, label):
    all_trades, closes, skipped = [], {}, 0
    per_sym = {}
    for sym, df in data.items():
        tr, sg = gen_variant_trades(sym, df, variant)
        per_sym[sym] = tr
        all_trades.extend(tr)
        closes[sym] = df["Close"]
        skipped += sg
    all_trades.sort(key=lambda t: t["entry_time"])
    rows = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
        row = pb.summarize(label, all_trades, port, skipped, cost_name)
        rows.append(extend_row(row, all_trades, cost_name))
    pt = {s: per_ticker_25bps(s, per_sym[s]) for s in sorted(per_sym)}
    return rows, pt


def load_4h():
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
        df = pb.add_pine_indicators(df)
        data[sym] = add_trend_columns(df)
    return data


def main():
    print("loading UX51 4H cache...", flush=True)
    data = load_4h()
    print(f"  {len(data)} symbols", flush=True)
    starts = [df.index.min().isoformat() for df in data.values()]
    ends = [df.index.max().isoformat() for df in data.values()]
    verify_baseline_fidelity(data)

    results = {
        "universe": "UX51 4H",
        "data_window": {"start": min(starts), "end": max(ends)},
        "symbols_used": sorted(data),
        "code": "canonical pine_backtest.py UNMODIFIED; only trendBull swapped per variant; "
                "exits (incl. trend_bear mirror) identical across variants",
        "candidates_frozen_up_front": VARIANTS,
        "notes": [
            "Candidate set fixed before any results were seen; each tested once; no tuning.",
            "CURRENT fidelity-verified bar-for-bar == pb.pine_buy_signal.",
            "Judge candidates vs in-test CURRENT only (different universe/window from other studies).",
        ],
        "variants": {},
    }
    for v in VARIANTS:
        print(f"== {v} ==", flush=True)
        rows, pt = run_variant(v, data, f"PINE_V36_trendfilter:{v}:UX51:4h")
        results["variants"][v] = {"pooled": rows, "per_ticker_25bps": pt}
        for r in rows:
            print(f"  [{r['cost']}] n={r['trades']} win={r.get('win_rate_pct')}% "
                  f"exp={r.get('expectancy_net_r')}R PF={r.get('profit_factor')} "
                  f"dd={r.get('max_drawdown_pct')}%", flush=True)
        with open(OUT_JSON, "w") as f:
            json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
