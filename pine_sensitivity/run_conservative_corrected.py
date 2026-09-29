#!/usr/bin/env python3
"""One-off: Conservative entry mode with corrected trendScore.

TradingView Conservative = confirmedBuy or breakoutBuy (no readyBuy,
no earlyBuy; extraEntry toggles default off). Uses the same corrected
int-cast score as the canonical fix. Frozen files untouched.
"""
import sys, os, json, time
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_sensitivity")
sys.path.insert(0, BASE)
sys.path.insert(0, OUTDIR)
import pine_backtest as pb
from run_corrected import _common


def conservative_signal(df, i):
    r0 = df.iloc[i]
    if pd.isna(r0["e200"]) or pd.isna(r0["atr_base"]) or pd.isna(r0["adx"]):
        return False
    c = _common(df, i)
    r, close = c["r"], c["close"]
    confirmed = close > r["e21"] and r["e21"] > r["e55"] and close > r["e200"] \
        and c["score"] >= 4 and c["volume_ok"] and c["safe"]
    breakout_buy = c["trend_bull"] and c["strong_trend"] and c["breakout"] \
        and c["volume_ok"] and c["safe"]
    return bool(confirmed or breakout_buy)


def main():
    t0 = time.time()
    pb.pine_buy_signal = conservative_signal
    rows, trades = pb.run_universe(pb.UNIVERSE_X, "UX51", "4h")
    rec = {"config": "Conservative (corrected score)", "seconds": round(time.time() - t0, 1)}
    for r in rows:
        rec[r["cost"]] = {
            "trades": r["trades"], "win_rate_pct": r["win_rate_pct"],
            "expectancy_r": r["expectancy_net_r"], "profit_factor": r["profit_factor"],
            "return_pct": r["total_return_pct"], "max_dd_pct": r["max_drawdown_pct"],
        }
        print(f"Conservative [{r['cost']}]: n={r['trades']} win={r['win_rate_pct']}% "
              f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
              f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}%", flush=True)
    with open(os.path.join(OUTDIR, "conservative_corrected.json"), "w") as f:
        json.dump(rec, f, indent=1)
    print("wrote pine_sensitivity/conservative_corrected.json")


if __name__ == "__main__":
    main()
