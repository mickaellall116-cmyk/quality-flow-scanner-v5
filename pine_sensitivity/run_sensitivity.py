#!/usr/bin/env python3
"""V3.6 parameter sensitivity (robustness) check — research only.

Monkey-patches pine_backtest module constants at runtime; the frozen
strategy file itself is never edited. One parameter nudged at a time,
all others at default. Pass bar: expectancy stays > +0.15R/trade on
every nudge (same bar as the real-money gate).
"""
import sys, os, json, time

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_sensitivity")
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, BASE)
import pine_backtest as pb

ORIG_ATR, ORIG_ADX = pb.atr, pb.adx

VARIANTS = [
    ("baseline", {}),
    ("SL_ATR 1.25", {"SL_ATR": 1.25}),
    ("SL_ATR 1.75", {"SL_ATR": 1.75}),
    ("TP_ATR 1.5", {"TP_ATR": 1.5}),
    ("TP_ATR 2.5", {"TP_ATR": 2.5}),
    ("EMA9 8", {"EMA9_L": 8}),
    ("EMA21 25", {"EMA21_L": 25}),
    ("ADX_L 12", {"ADX_L": 12}),
    ("ADX_L 16", {"ADX_L": 16}),
    ("BREAKOUT 8", {"BREAKOUT_BARS": 8}),
    ("BREAKOUT 12", {"BREAKOUT_BARS": 12}),
    ("VOL_MA 15", {"VOL_L": 15}),
    ("VOL_MA 25", {"VOL_L": 25}),
]

def apply(patches):
    saved = {}
    for k, v in patches.items():
        if k in ("ATR_L", "ADX_L"):
            continue
        saved[k] = getattr(pb, k)
        setattr(pb, k, v)
    if "ATR_L" in patches:
        l = patches["ATR_L"]
        pb.atr = lambda df, _l=None, _o=ORIG_ATR, _n=l: _o(df, _n)
    if "ADX_L" in patches:
        l = patches["ADX_L"]
        pb.adx = lambda df, _l=None, _o=ORIG_ADX, _n=l: _o(df, _n)
    return saved

def restore(saved):
    for k, v in saved.items():
        setattr(pb, k, v)
    pb.atr, pb.adx = ORIG_ATR, ORIG_ADX

results = []
for name, patches in VARIANTS:
    t0 = time.time()
    saved = apply(patches)
    try:
        rows, trades = pb.run_universe(pb.UNIVERSE_X, "UX51", "4h")
    finally:
        restore(saved)
    dt = time.time() - t0
    rec = {"variant": name, "patches": patches, "seconds": round(dt, 1)}
    for r in rows:
        rec[r["cost"]] = {
            "trades": r["trades"],
            "win_rate_pct": r["win_rate_pct"],
            "expectancy_r": r["expectancy_net_r"],
            "profit_factor": r["profit_factor"],
            "return_pct": r["total_return_pct"],
            "max_dd_pct": r["max_drawdown_pct"],
        }
    results.append(rec)
    e4 = rec["4bps"]["expectancy_r"]
    e25 = rec["25bps"]["expectancy_r"]
    print(f"[{name}] 4bps exp={e4}R (n={rec['4bps']['trades']}) | "
          f"25bps exp={e25}R | {dt:.0f}s", flush=True)

with open(os.path.join(OUTDIR, "sensitivity_results.json"), "w") as f:
    json.dump(results, f, indent=1)
print("wrote pine_sensitivity/sensitivity_results.json")
