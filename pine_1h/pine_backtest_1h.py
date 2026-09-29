"""1H backtest of Mike's TradingView strategy 'Quality Flow System V3.6'.

Reuses pine_backtest.py logic UNMODIFIED (entries + exits imported, never
copied): add_pine_indicators, pine_buy_signal, gen_pine_trades,
simulate_portfolio, summarize, COSTS, RISK_PCT, UNIVERSE_X, WARMUP.

Timeframe-transfer test: indicator lookback lengths are in BARS, identical
to the 4H run (EMA 9/21/55/200, ATR 14, vol SMA 20, breakout 10). On 1H bars
this means the strategy looks back ~4x less clock time than on 4H — the
parameters were tuned for 4H, so this is an honest unmodified-transfer test,
not a re-tuned 1H system.

Local-only research. No existing files modified.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pine_backtest as pb

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache")
OUT = os.path.join(BASE, "pine_1h_results.json")


def main():
    with open(os.path.join(BASE, "fetch_1h_log.json")) as f:
        fetch_log = json.load(f)
    ok_syms = [s for s, v in fetch_log.items() if v["ok"]]

    all_trades, closes, skipped = [], {}, 0
    used, dropped = [], []
    for sym in pb.UNIVERSE_X:
        path = os.path.join(CACHE, f"h1_{sym}.pkl")
        if sym not in ok_syms or not os.path.exists(path):
            dropped.append(sym)
            continue
        df = pd.read_pickle(path)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"  [warn] no volume for {sym}, skipping", flush=True)
            dropped.append(sym)
            continue
        df = pb.add_pine_indicators(df)
        closes[sym] = df["Close"]
        tr, sg = pb.gen_pine_trades(sym, df)
        all_trades.extend(tr)
        skipped += sg
        used.append(sym)
        print(f"  {sym}: {len(tr)} trades", flush=True)
    all_trades.sort(key=lambda t: t["entry_time"])

    rows = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
        rows.append(pb.summarize("PINE_V36_hybrid:UX51:1h", all_trades, port,
                                 skipped, cost_name))

    # approx hold in clock hours from timestamps (stocks ~6.5 bars/day,
    # crypto 24/day, so bars alone are misleading)
    holds_h = [ (t["exit_time"] - t["entry_time"]).total_seconds() / 3600
                for t in all_trades ]
    hold_stats = {"median_hours": round(float(np.median(holds_h)), 1),
                  "mean_hours": round(float(np.mean(holds_h)), 1)} if holds_h else {}

    starts = [fetch_log[s]["start"] for s in used]
    ends = [fetch_log[s]["end"] for s in used]
    results = {
        "timeframe": "1h",
        "notes": [
            "1H transfer test of Pine V3.6 (Hybrid), logic imported unmodified "
            "from pine_backtest.py.",
            "Indicator lookbacks kept in BARS (EMA 9/21/55/200, ATR 14, vol SMA20, "
            "breakout 10) — ~4x less clock time than 4H. Parameters were tuned "
            "for 4H; this tests unmodified transfer, not a re-tuned 1H system.",
            "yfinance 1h bars, regular session only for stocks (~6.5 bars/day), "
            "24h for crypto. yfinance 1h max lookback 730d.",
            "Same portfolio conventions as 4H: 4/25bps, $10k, 1%/trade, max 5 "
            "concurrent positions, 5% portfolio risk, next-bar-open entries, "
            "stop-first ties, gap-below-stop skips.",
            f"Data window: {min(starts)} -> {max(ends)} "
            f"({len(used)}/{len(pb.UNIVERSE_X)} symbols).",
            f"Dropped symbols (no usable 1H data): {dropped or 'none'}.",
        ],
        "symbols_used": used,
        "symbols_dropped": dropped,
        "data_window": {"start": min(starts), "end": max(ends)},
        "avg_hold_hours": hold_stats,
        "runs": rows,
    }
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT}")
    for r in rows:
        print(f"{r['config']} [{r['cost']}]: n={r['trades']} win={r['win_rate_pct']}% "
              f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
              f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}% "
              f"hold={r['avg_hold_bars']}bars tp1={r['tp1_hit_rate_pct']}% "
              f"reasons={r['exit_reasons']}", flush=True)
    print("hold hours:", hold_stats, flush=True)


if __name__ == "__main__":
    main()
