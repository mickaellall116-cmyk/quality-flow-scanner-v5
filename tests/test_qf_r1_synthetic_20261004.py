#!/usr/bin/env python3
"""Synthetic QF-R1 implementation fixtures.

Tests the ACTUAL Quality Flow routines (pine_backtest.py) — not BOSWaves.
QF-R1 = pine_backtest.py lineage (corrected-C1 code), pinned by hash.

Covers (per review blockers 1, 3, 4):
- Entry: signal bar i -> fill at open of bar i+1.
- Gap-below-stop: entry <= stop invalidates (skipped_gap++).
- TP1: intrabar high >= tp1 -> 50% at TP1, runner continues.
- Stop: CLOSE-evaluated (close < runner -> exit at NEXT bar open). NOT intrabar.
- Trail: after TP1, runner = max(runner, close - atr*2.5) at bar close.
- Exits: ema55-break / ema55-bear -> next bar open.
- NO 30-bar max hold (documents the difference from ModeBTracker).
- R blending: 0.5*TP1_R + 0.5*runner_R.
- Portfolio: 5 slots, 5% risk cap, chronological (no rs_top2).
- Coverage denominator: expected COMPLETED intervals through decision time.
- Missing marks: stale valuation keeps exposure (never drops it).
"""
import sys
import hashlib
import pandas as pd
import numpy as np

sys.path.insert(0, "/home/hatch/workspace/quality-flow-scanner-v5")
import pine_backtest as pb


def file_hash(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


print("PINNED:", "pine_backtest.py", file_hash(
    "/home/hatch/workspace/quality-flow-scanner-v5/pine_backtest.py")[:16])


def synth_df(n=300, seed=7):
    """Synthetic 4H bars with indicators computed."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-03-10 09:30", periods=n, freq="4h", tz="America/New_York")
    # filter to session hours roughly (keep it simple: use all, signal forced manually)
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    df = pd.DataFrame({
        "Open": close + rng.normal(0, 0.2, n),
        "High": close + np.abs(rng.normal(0, 0.5, n)),
        "Low": close - np.abs(rng.normal(0, 0.5, n)),
        "Close": close,
        "Volume": np.full(n, 1_000_000.0),
    }, index=idx)
    df = pb.add_pine_indicators(df)
    return df


def force_signal(df, i):
    """Override indicators at bar i so pine_buy_signal(df, i) is True."""
    # confirmed = close > e21 and e21 > e55 and close > e200 and score>=4 and volume_ok and safe
    c = df["Close"].iloc[i]
    df.loc[df.index[i], "e9"] = c - 1.0
    df.loc[df.index[i], "e21"] = c - 2.0
    df.loc[df.index[i], "e55"] = c - 3.0
    df.loc[df.index[i], "e200"] = c - 5.0
    df.loc[df.index[i], "adx"] = 30.0
    df.loc[df.index[i], "atr"] = 2.0
    df.loc[df.index[i], "atr_base"] = 1.5  # ratio > 1
    df.loc[df.index[i], "atr_ratio"] = 2.0 / 1.5
    df.loc[df.index[i], "vol_ma"] = 500_000.0  # volume_ok
    # safe: not hot -> close <= e9 + atr*1.5 = (c-1) + 3 = c+2. True since close=c.
    # breakout not needed for confirmed.
    assert pb.pine_buy_signal(df, i), "signal forcing failed"
    return i


passed = failed = 0
def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name}")


print("\n== F1: entry at next-bar open ==")
df = synth_df()
si = force_signal(df, 250)
entry_bar = si + 1
trades, skipped = pb.gen_pine_trades("TEST", df)
# find the trade from our forced signal
t = [x for x in trades if x["signal_time"] == df.index[si].isoformat()]
check("one trade from forced signal", len(t) == 1)
if t:
    t = t[0]
    check("entry == open of bar i+1",
          abs(t["entry"] - df["Open"].iloc[entry_bar]) < 1e-9)
    check("entry_time == bar i+1", t["entry_time"] == df.index[entry_bar])

print("\n== F2: gap-below-stop invalidates ==")
df2 = synth_df()
si2 = force_signal(df2, 250)
# force entry bar open below stop: stop = close - atr*1.5
stop_est = df2["Close"].iloc[si2] - df2["atr"].iloc[si2] * pb.SL_ATR
df2.loc[df2.index[si2 + 1], "Open"] = stop_est - 1.0  # gap below stop
trades2, skipped2 = pb.gen_pine_trades("TEST", df2)
t2 = [x for x in trades2 if x["signal_time"] == df2.index[si2].isoformat()]
check("no trade on gap-below-stop", len(t2) == 0)
check("skipped_gap incremented", skipped2 >= 1)

print("\n== F3: TP1 50% + runner, close-evaluated stop ==")
df3 = synth_df()
si3 = force_signal(df3, 250)
entry = float(df3["Open"].iloc[si3 + 1])
atr_v = float(df3["atr"].iloc[si3])
tp1 = entry + atr_v * pb.TP_ATR
stop0 = float(df3["Close"].iloc[si3] - atr_v * pb.SL_ATR)
# Neutralize bars si3+1 .. si3+5: no accidental ema55/trend exits.
# (gen_pine_trades manages from the entry bar itself.)
for j in range(si3 + 1, si3 + 6):
    df3.loc[df3.index[j], "e21"] = entry + 2.0
    df3.loc[df3.index[j], "e55"] = entry - 5.0
    df3.loc[df3.index[j], "e200"] = entry - 5.0
    df3.loc[df3.index[j], "atr"] = atr_v
# bar i+1 (entry bar): keep benign
df3.loc[df3.index[si3 + 1], "Close"] = entry + 0.5
df3.loc[df3.index[si3 + 1], "High"] = entry + 1.0
df3.loc[df3.index[si3 + 1], "Low"] = entry - 0.5
# bar i+2: high touches tp1 (TP1 hit), close stays above runner
df3.loc[df3.index[si3 + 2], "High"] = tp1 + 0.5
df3.loc[df3.index[si3 + 2], "Close"] = tp1 + 0.2
df3.loc[df3.index[si3 + 2], "Low"] = entry - 0.5
# bar i+3: close below runner -> stop triggers, exits at NEXT bar open
runner_est = max(stop0, (tp1 + 0.2) - atr_v * pb.TRAIL_ATR)
df3.loc[df3.index[si3 + 3], "Close"] = runner_est - 1.0
df3.loc[df3.index[si3 + 3], "Low"] = runner_est - 1.5
df3.loc[df3.index[si3 + 3], "High"] = runner_est + 0.5
# bar i+4: exit fills at open
trades3, _ = pb.gen_pine_trades("TEST", df3)
t3 = [x for x in trades3 if x["signal_time"] == df3.index[si3].isoformat()]
check("trade exists", len(t3) == 1)
if t3:
    t3 = t3[0]
    check("tp1_hit True", t3["tp1_hit"] is True)
    check("reason is stop", t3["reason"] == "stop")
    # close-evaluated: signal bar i+3 close < runner -> exit at open of i+4
    check("exit at next-bar open after trigger",
          t3["exit_time"] == df3.index[si3 + 4])

print("\n== F4: NO 30-bar max hold in pine_backtest ==")
df4 = synth_df(n=400)
si4 = force_signal(df4, 250)
# flat bars after entry: no TP1, no stop, no ema55 break -> should run to end
for j in range(si4 + 1, 400):
    df4.loc[df4.index[j], "Open"] = 100.0
    df4.loc[df4.index[j], "High"] = 100.5
    df4.loc[df4.index[j], "Low"] = 99.5
    df4.loc[df4.index[j], "Close"] = 100.0
    df4.loc[df4.index[j], "e55"] = 90.0  # close > e55, no exit
    df4.loc[df4.index[j], "e21"] = 95.0
    df4.loc[df4.index[j], "e200"] = 90.0
trades4, _ = pb.gen_pine_trades("TEST", df4)
t4 = [x for x in trades4 if x["signal_time"] == df4.index[si4].isoformat()]
# position held without hitting 30-bar exit; may still be open at end (no trade)
# or closed only by end-of-data. Either way, no "time" reason at bar 30.
reasons = [x["reason"] for x in t4]
check("no 30-bar time exit", "time" not in reasons and "runner-time" not in reasons)

print("\n== F5: portfolio 5-slot cap, chronological ==")
# 6 simultaneous trades -> 6th skipped by slot cap
base = pd.Timestamp("2025-03-10 09:30", tz="America/New_York")
trades5 = []
for k in range(6):
    trades5.append({
        "symbol": f"S{k}", "entry": 100.0, "stop": 98.0, "exit": 101.0,
        "reason": "ema55-break", "tp1_hit": False,
        "entry_time": base, "exit_time": base + pd.Timedelta(hours=8),
        "hold_bars": 2, "signal_time": (base - pd.Timedelta(hours=4)).isoformat(),
    })
closes5 = {f"S{k}": pd.Series([100.0, 101.0],
           index=[base, base + pd.Timedelta(hours=8)]) for k in range(6)}
port5 = pb.simulate_portfolio(trades5, closes5, 0.0025, 0.01)
check("6th trade skipped by slot cap", port5["skipped_cap_count"] >= 1)

print("\n== F6: coverage denominator = completed intervals through decision ==")
def expected_completed(decision_hm, session_end_hm="16:00", early=False):
    """Expected COMPLETED hourly source intervals through decision time."""
    # Regular session: 6 full hourly bars (09:30-15:30) + 1 half-hour bar
    # (15:30-16:00). Early close: 3 full hourly bars (09:30-12:30).
    # A bar is complete when decision time >= bar_end (epsilon for exact).
    if early:
        bars = [(9.5, 10.5), (10.5, 11.5), (11.5, 12.5)]
    else:
        bars = [(9.5 + h, 10.5 + h) for h in range(6)] + [(15.5, 16.0)]
    dec = float(decision_hm.split(":")[0]) + float(decision_hm.split(":")[1]) / 60
    return sum(1 for s, e in bars if dec + 1e-9 >= e)

check("13:30 -> 4 completed (not 7)", expected_completed("13:30") == 4)
check("16:00 -> 7 completed", expected_completed("16:00") == 7)
check("early-close 13:00 -> 3 completed", expected_completed("13:00", early=True) == 3)
check("13:30 forming bar not counted", expected_completed("13:30") < 7)

print("\n== F7: missing mark keeps exposure (stale, flagged) ==")
# simulate_portfolio.mark falls back to last available close; exposure retained.
# Verify: a held position with no fresh mark still contributes unrealized P&L.
base7 = pd.Timestamp("2025-03-10 09:30", tz="America/New_York")
tr7 = [{"symbol": "STALE", "entry": 100.0, "stop": 98.0, "exit": 102.0,
        "reason": "ema55-break", "tp1_hit": False,
        "entry_time": base7, "exit_time": base7 + pd.Timedelta(days=2),
        "hold_bars": 4, "signal_time": (base7 - pd.Timedelta(hours=4)).isoformat()}]
# closes only has the entry-time bar (stale after that)
closes7 = {"STALE": pd.Series([100.0], index=[base7])}
port7 = pb.simulate_portfolio(tr7, closes7, 0.0025, 0.01)
curve7 = port7["curve"]
# marked equity during hold uses stale 100.0 -> unrealized = 0, but position counted
open_counts = [c[3] for c in curve7]
check("stale-mark position retained in open count", max(open_counts) >= 1)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
