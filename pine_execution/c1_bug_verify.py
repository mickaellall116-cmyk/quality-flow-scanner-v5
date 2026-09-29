"""Verify the forensic claim: the canonical 143-trade C1 figures are reproducible
ONLY with the pre-Sep-20 numpy-boolean trendScore bug.

Restores the buggy score computation (plain NumPy boolean addition, no int()
casts) via monkeypatch in a COPY of the code path — does NOT modify any
frozen file — and runs the E0_4bps/C1 leg. If the gate (143 / 0.337R /
52.25% / 31.63%) passes with the bug and fails without it, the claim is
proven: Mike's canonical numbers are the buggy artifact.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "pine_stack"))
sys.path.insert(0, os.path.join(HERE, "pine_ranking"))
sys.path.insert(0, os.path.join(HERE, "pine_signal_quality"))

import numpy as np
import pandas as pd
import pine_backtest as pb
import pine_stack as st
from pine_ranking import compute_features
from pine_signal_quality import load_benchmarks

GATE = {"trades": 143, "expectancy_net_r": 0.337,
        "total_return_pct": 52.25, "max_drawdown_pct": 31.63}

BREAKOUT_BARS = pb.BREAKOUT_BARS


def buggy_pine_buy_signal(df, i):
    """Pre-Sep-20 version: plain NumPy boolean addition for trendScore."""
    r = df.iloc[i]
    rp = df.iloc[i - 1]
    if pd.isna(r["e200"]) or pd.isna(r["atr_base"]) or pd.isna(r["adx"]):
        return False
    close, vol = r["Close"], r["Volume"]
    volume_ok = vol > r["vol_ma"]
    hot = close > r["e9"] + r["atr"] * pb.HOT_ATR
    safe = not hot
    trend_bull = r["e21"] > r["e55"] and close > r["e200"]
    strong_trend = r["adx"] > 20 and r["atr_ratio"] > 0.85
    # BUGGY: numpy bool_ addition collapses to a single boolean
    score = (r["e9"] > r["e21"]) + (r["e21"] > r["e55"]) \
        + (close > r["e200"]) + (r["adx"] > 25) + (r["atr_ratio"] > 1)
    breakout = close > df["High"].iloc[i - BREAKOUT_BARS:i].max()
    ready_prev = rp["Close"] < rp["e21"] and rp["Close"] > rp["e55"] \
        and rp["e21"] > rp["e55"] and rp["atr_ratio"] > 0.85
    confirmed = close > r["e21"] and r["e21"] > r["e55"] and close > r["e200"] \
        and score >= 4 and volume_ok and safe
    breakout_buy = trend_bull and strong_trend and breakout and volume_ok and safe
    ready_buy = ready_prev and close > r["e21"] and score >= 3 and volume_ok and safe
    return bool(confirmed or breakout_buy or ready_buy)


def main():
    # patch the signal used by gen_candidates (module attr lookup at call time)
    import pine_ranking as pr
    pr.pb.pine_buy_signal = buggy_pine_buy_signal

    bench, _ = load_benchmarks()
    all_trades, closes, data, order_of, skipped_gap = st.load_bull()
    print(f"candidates with buggy signal: {len(all_trades)}", flush=True)

    feats = compute_features(all_trades,
                             {s: df for s, df in data.items()}, bench)
    rs_by_id = {id(tr): feats[i]["rs"] for i, tr in enumerate(all_trades)}
    st.rs = rs_by_id
    cost = pb.COSTS["4bps"]
    port = st.simulate_stack(all_trades, closes, cost, True, True, False,
                             st.SECTOR)
    taken = [all_trades[i] for i in port["taken"]]
    row = pb.summarize("bull-E0_4bps-C1-buggy", taken, port, skipped_gap,
                       "4bps")
    got = {k: row[k] for k in GATE}
    ok = all(got[k] == GATE[k] for k in GATE)
    print(f"BUGGY-RUN GATE: got {got}, want {GATE} -> {'PASS' if ok else 'FAIL'}",
          flush=True)


if __name__ == "__main__":
    main()
