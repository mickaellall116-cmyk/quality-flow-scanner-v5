#!/usr/bin/env python3
"""Verify the RKLB 2024-09-09 +12.98R FVG-only trade against raw bars.

Replicates the attribution study's FVG-variant signal (from
pine_entry_timing_backtest/run_entry_timing.py's add_fvg_columns + the
FVG OR-signal used by run_fvg_attribution.py) then walks the trade with
the UNMODIFIED pine_backtest engine, and re-derives the blended R.
"""
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "research_audit", "data_leakage")
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402 - unmodified

# load add_fvg_columns + FVG signal from run_entry_timing
spec = importlib.util.spec_from_file_location(
    "ret", os.path.join(BASE, "pine_entry_timing_backtest", "run_entry_timing.py"))
ret = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ret)

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
COST = 0.0025

sym = "RKLB"
df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
df = pb.add_pine_indicators(df)
df = ret.add_entry_timing_columns(df)

sig_ts = pd.Timestamp("2024-09-09T09:30:00-04:00")
i = df.index.get_loc(sig_ts)
bar = df.iloc[i]
entry_bar = df.iloc[i + 1]

print("signal bar:", sig_ts, "O/H/L/C:", round(bar.Open, 4), round(bar.High, 4),
      round(bar.Low, 4), round(bar.Close, 4))
print("  base hybrid signal:", pb.pine_buy_signal(df, i))
print("  FVG sub-signal:", ret.sub_signals(df, i)["fvg"])
print("  inBullFvgSupport:", bar.get("inBullFvgSupport"), " e21:", round(bar.e21, 4),
      " close>e21:", bar.Close > bar.e21)
print("  vol_ok:", bar.Volume > bar.vol_ma, " safe:", not (bar.Close > bar.e9 + bar.atr * pb.HOT_ATR))

sig_close = float(bar["Close"])
sig_atr = float(bar["atr"])
exp_entry = float(entry_bar["Open"])
exp_stop = sig_close - sig_atr * pb.SL_ATR
exp_tp1 = exp_entry + sig_atr * pb.TP_ATR
print(f"\nsignal close={sig_close:.4f} atr={sig_atr:.4f}")
print(f"expected entry (next bar open)={exp_entry:.4f} (study: 6.23)")
print(f"expected stop (close-1.5*ATR)={exp_stop:.4f} (study: 5.7943)")
print(f"expected tp1 (entry+2.0*ATR)={exp_tp1:.4f}")

# Walk the trade with the unmodified engine's trade management by monkey-
# patching only the signal (exactly what the attribution study does).
orig = pb.pine_buy_signal
fvg_cols = {c for c in df.columns}
def fvg_signal(df2, j):
    r = df2.iloc[j]
    if pd.isna(r["e200"]) or pd.isna(r["atr_base"]) or pd.isna(r["adx"]):
        return False
    close, vol = r["Close"], r["Volume"]
    volume_ok = vol > r["vol_ma"]
    safe = not (close > r["e9"] + r["atr"] * pb.HOT_ATR)
    trend_bull = r["e21"] > r["e55"] and close > r["e200"]
    fvg = bool(trend_bull and r["inBullFvgSupport"] and close > r["e21"]
               and volume_ok and safe)
    return bool(orig(df2, j) or fvg)
pb.pine_buy_signal = fvg_signal
trades, _ = pb.gen_pine_trades(sym, df)
pb.pine_buy_signal = orig

match = [t for t in trades if t["signal_time"] == sig_ts.isoformat()]
print(f"\nregenerated FVG-variant trades for {sym}: {len(trades)}; "
      f"matching 2024-09-09 signal: {len(match)}")
out = {}
if match:
    t = match[0]
    print("trade:", json.dumps({k: (str(v) if k.endswith('time') else v)
                                for k, v in t.items()}, indent=1, default=str)[:1200])
    _, _, recomputed, _ = pb._outcome(t["entry"], t["stop"], t["exit"], COST)
    print(f"\nentry match: {abs(t['entry'] - exp_entry) < 1e-9} | "
          f"stop match: {abs(t['stop'] - exp_stop) < 1e-9}")
    print(f"study net_r=12.9809 recomputed={recomputed:.4f} match={abs(recomputed - 12.980891882514046) < 1e-6}")
    # manual blended-R derivation
    risk_frac = (t["entry"] - t["stop"]) / t["entry"]
    tp1 = t["entry"] + sig_atr * pb.TP_ATR
    # 50% at TP1 limit, 50% at final exit
    r1 = ((tp1 - t["entry"]) / t["entry"]) / risk_frac
    r2 = ((t["exit_px"] if "exit_px" in t else t["exit"]) - t["entry"]) / t["entry"] / risk_frac \
        if False else None
    # in pb the trade stores a blended synthetic exit
    print(f"risk_frac={risk_frac*100:.3f}%  tp1={tp1:.4f}  tp1_hit={t['tp1_hit']}")
    print(f"exit(synth)={t['exit']:.4f} reason={t['reason']} hold_bars={t['hold_bars']}")
    out = {"found": True, "entry_match": abs(t["entry"] - exp_entry) < 1e-9,
           "stop_match": abs(t["stop"] - exp_stop) < 1e-9,
           "recomputed_net_r": recomputed, "study_net_r": 12.980891882514046,
           "match": abs(recomputed - 12.980891882514046) < 1e-6,
           "reason": t["reason"], "tp1_hit": bool(t["tp1_hit"]),
           "exit": t["exit"], "entry_time": str(t["entry_time"]),
           "exit_time": str(t["exit_time"]), "hold_bars": t["hold_bars"]}
else:
    out = {"found": False}
with open(os.path.join(OUTDIR, "rklb_trade_verification.json"), "w") as f:
    json.dump(out, f, indent=1, default=str)
print("\nwrote rklb_trade_verification.json")
