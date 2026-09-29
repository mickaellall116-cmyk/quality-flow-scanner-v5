#!/usr/bin/env python3
"""Data-quality audit of the 4H OHLC pipeline (14-stock watchlist).

Checks: splits/adjustment, bad candles, dupes, timezone, missing bars,
premarket contamination, and re-verifies the RKLB +12.98R trade + top-5
P&L trades arithmetically against raw bars.

Writes: data_quality_report.md (summarized findings) + JSON details.
Does NOT modify pine_backtest.py (imports it read-only).
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "research_audit", "data_leakage")
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402 - imported unmodified

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
H1 = os.path.join(BASE, "pine_2h3h_backtest", "cache")
H4 = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
COST = 0.0025

report = {"symbol_checks": {}, "split_checks": {}, "trade_verifications": {}}

print("== per-symbol data quality (h1 source -> h4 backtest cache) ==")
for sym in WATCHLIST:
    h1 = pd.read_pickle(os.path.join(H1, f"h1_{sym}.pkl"))
    h4 = pd.read_pickle(os.path.join(H4, f"h4_{sym}.pkl"))
    c = {}
    c["h1_bars"] = len(h1)
    c["h4_bars"] = len(h4)
    c["h1_tz"] = str(h1.index.tz)
    c["h4_tz"] = str(h4.index.tz)
    c["h1_range"] = [str(h1.index[0]), str(h1.index[-1])]
    c["h4_range"] = [str(h4.index[0]), str(h4.index[-1])]
    # bad candles
    bad_hilo = int(((h4["High"] < h4["Low"]) |
                    (h4["High"] < h4[["Open", "Close"]].max(axis=1)) |
                    (h4["Low"] > h4[["Open", "Close"]].min(axis=1))).sum())
    c["h4_impossible_wick"] = bad_hilo
    c["h4_nan_ohlc"] = int(h4[["Open", "High", "Low", "Close"]].isna().any(axis=1).sum())
    c["h4_zero_volume"] = int((h4["Volume"] == 0).sum())
    c["h4_dup_ts"] = int(h4.index.duplicated().sum())
    c["h1_dup_ts"] = int(h1.index.duplicated().sum())
    # premarket contamination: any 1h bar outside 09:30-16:00 ET?
    local = h1.index.tz_convert("America/New_York")
    mins = local.hour * 60 + local.minute
    c["h1_outside_session"] = int(((mins < 570) | (mins >= 960)).sum())
    # 4h bars outside session starts (should be only 09:30 / 13:30 ET)
    loc4 = h4.index.tz_convert("America/New_York")
    starts = (loc4.hour * 60 + loc4.minute).unique()
    c["h4_bar_starts_et"] = sorted(int(x) for x in starts)
    # bars per day
    per_day = h4.groupby(h4.index.tz_convert("America/New_York").date).size()
    c["days"] = int(per_day.shape[0])
    c["days_with_2_bars_pct"] = round(float((per_day == 2).mean()) * 100, 1)
    c["days_with_1_bar"] = int((per_day == 1).sum())
    c["days_with_0_gt2_bars"] = int(((per_day == 0) | (per_day > 2)).sum())
    c["max_gap_calendar_days"] = float(
        (h4.index.to_series().diff().dropna().dt.total_seconds() / 86400).max())
    report["symbol_checks"][sym] = c
    print(f"  {sym}: tz={c['h4_tz']} h4bars={c['h4_bars']} range={c['h4_range'][0][:10]}..{c['h4_range'][1][:10]} "
          f"badwick={bad_hilo} nan={c['h4_nan_ohlc']} zerovol={c['h4_zero_volume']} dup={c['h4_dup_ts']} "
          f"outside_session={c['h1_outside_session']} starts={c['h4_bar_starts_et']} 2bar_days={c['days_with_2_bars_pct']}%")

print("\n== split / corporate-action continuity ==")
# SMCI 10:1 split effective 2024-10-01; check price continuity
for sym, split_date, ratio in [("SMCI", "2024-10-01", 10),
                               ("ASTX", None, None)]:
    h4 = pd.read_pickle(os.path.join(H4, f"h4_{sym}.pkl"))
    if sym == "SMCI":
        pre = h4[h4.index.tz_convert("America/New_York") < pd.Timestamp("2024-10-01", tz="America/New_York")]
        post = h4[h4.index.tz_convert("America/New_York") >= pd.Timestamp("2024-10-01", tz="America/New_York")]
        pc = float(pre["Close"].iloc[-2:].mean())
        qc = float(post["Close"].iloc[:2].mean())
        print(f"  SMCI: close before split-window ~{pc:.2f}, after ~{qc:.2f} "
              f"(ratio {pc/qc:.2f}x; adjusted data would show ~1.0x)")
        report["split_checks"]["SMCI"] = {"pre_close": pc, "post_close": qc,
                                          "ratio": pc / qc, "split_adjusted": abs(pc / qc - 1.0) < 0.2}
    # scan for overnight jumps > 4x in either direction (possible unadjusted split/rev-split)
    d = h4["Close"]
    logret = np.abs(np.log(d / d.shift(1)))
    big = h4[logret > np.log(4)]
    print(f"  {sym}: overnight jumps >=4x: {len(big)}")
    for ts in big.index[:5]:
        i = h4.index.get_loc(ts)
        print(f"    {ts}: {h4['Close'].iloc[i-1]:.4f} -> {h4['Close'].iloc[i]:.4f}")
    report["split_checks"][f"{sym}_4x_jumps"] = [
        {"date": str(ts), "prev_close": float(h4['Close'].iloc[h4.index.get_loc(ts)-1]),
         "close": float(h4['Close'].iloc[h4.index.get_loc(ts)])} for ts in big.index[:10]]

print("\n== regenerate canonical 14-stock trades (import pb unmodified) ==")
trades, closes = [], {}
for sym in WATCHLIST:
    df = pd.read_pickle(os.path.join(H4, f"h4_{sym}.pkl"))
    df = pb.add_pine_indicators(df)
    closes[sym] = df["Close"]
    ts, _ = pb.gen_pine_trades(sym, df)
    trades.extend(ts)
trades.sort(key=lambda t: t["entry_time"])
print(f"  canonical trades: {len(trades)} (baseline row says 237)")
rows = []
for t in trades:
    _, _, net_r, _ = pb._outcome(t["entry"], t["stop"], t["exit"], COST)
    rows.append((t, net_r))
rows.sort(key=lambda x: x[1], reverse=True)
report["trade_verifications"]["n_trades"] = len(trades)
report["trade_verifications"]["baseline_n_expected"] = 237

print("\n== arithmetic verification: RKLB +12.98R + top-5 P&L ==")
top5 = rows[:5]
check = [("RKLB", "2024-09-09T09:30:00-04:00")] + [(t["symbol"], t["signal_time"]) for t, _ in top5]
seen = set()
for sym, sig_time in check:
    if (sym, sig_time) in seen:
        continue
    seen.add((sym, sig_time))
    # find trade(s) with this symbol+signal_time
    match = [(t, nr) for t, nr in rows
             if t["symbol"] == sym and t["signal_time"] == sig_time]
    if not match:
        print(f"  {sym} {sig_time}: NOT FOUND in regenerated trades")
        report["trade_verifications"][f"{sym}_{sig_time}"] = {"found": False}
        continue
    for t, net_r in match:
        df = pb.add_pine_indicators(pd.read_pickle(os.path.join(H4, f"h4_{sym}.pkl")))
        sig_pos = df.index.get_loc(pd.Timestamp(sig_time))
        entry_pos = sig_pos + 1
        sig_bar = df.iloc[sig_pos]
        entry_bar = df.iloc[entry_pos]
        exp_entry = float(entry_bar["Open"])
        exp_stop = float(sig_bar["Close"] - sig_bar["atr"] * pb.SL_ATR)
        exp_tp1 = exp_entry + float(sig_bar["atr"]) * pb.TP_ATR
        ok_entry = abs(t["entry"] - exp_entry) < 1e-9
        ok_stop = abs(t["stop"] - exp_stop) < 1e-9
        # recompute blended R from stored exit
        risk_frac = (t["entry"] - t["stop"]) / t["entry"]
        _, _, recomputed, _ = pb._outcome(t["entry"], t["stop"], t["exit"], COST)
        ok_r = abs(recomputed - net_r) < 1e-9
        gross = (t["exit"] - t["entry"]) / t["entry"]
        print(f"  {sym} {sig_time}: entry {t['entry']:.4f} (raw open {exp_entry:.4f}, match={ok_entry}) | "
              f"stop {t['stop']:.4f} (raw {exp_stop:.4f}, match={ok_stop}) | "
              f"tp1 {exp_tp1:.4f} | reason={t['reason']} tp1_hit={t['tp1_hit']} | "
              f"exit={t['exit']:.4f} gross_ret={gross*100:.1f}% risk_frac={risk_frac*100:.2f}% | "
              f"net_r stored={net_r:.4f} recomputed={recomputed:.4f} match={ok_r}")
        report["trade_verifications"][f"{sym}_{sig_time}"] = {
            "found": True, "entry": t["entry"], "raw_entry": exp_entry,
            "stop": t["stop"], "raw_stop": exp_stop, "tp1": exp_tp1,
            "exit": t["exit"], "gross_ret_pct": gross * 100,
            "risk_frac_pct": risk_frac * 100, "net_r": net_r,
            "r_recomputed_match": ok_r, "reason": t["reason"],
            "tp1_hit": bool(t["tp1_hit"]),
            "entry_time": str(t["entry_time"]), "exit_time": str(t["exit_time"]),
            "hold_bars": t["hold_bars"],
        }

with open(os.path.join(OUTDIR, "data_quality_details.json"), "w") as f:
    json.dump(report, f, indent=1, default=str)
print(f"\nwrote {OUTDIR}/data_quality_details.json")
