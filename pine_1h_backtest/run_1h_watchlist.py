"""1H backtest of the Quality Flow signal logic on Mike's 12-ticker watchlist.

Method (mirrors the corrected 4H baseline in pine_sensitivity/run_corrected_v2.py):
- Imports the FIXED canonical pine_backtest.py UNMODIFIED (entries + exits +
  portfolio sim imported, never copied): add_pine_indicators, pine_buy_signal
  (Hybrid), gen_pine_trades, simulate_portfolio, summarize, COSTS, RISK_PCT,
  WARMUP, _outcome.
- Indicator lookbacks kept in BARS (EMA 9/21/55/200, ATR 14, vol SMA20,
  breakout 10) = ~4x less clock time than 4H. Parameters tuned for 4H; this is
  an unmodified-transfer test, NOT a re-tuned 1H system. No parameter tuned.
- yfinance 1H, regular session only for stocks (prepost=False), 730d window.
- Same portfolio conventions as the 4H baseline: 4/25bps costs, $10k,
  1%/trade, max 5 concurrent positions, 5% portfolio risk, next-bar-open
  entries, stop-first ties, gap-below-stop skips.
- Reports pooled stats (via pb.summarize, identical to the 4H baseline) plus
  per-ticker stats derived the same way (net R via pb._outcome).

Local-only research. No frozen files modified.
"""
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pine_backtest as pb

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache")
OUT = os.path.join(BASE, "pine_1h_watchlist_results.json")

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO"]


def per_ticker_stats(sym, trades):
    """Replicate pb.summarize's net-R derivation per ticker, both costs."""
    out = {"symbol": sym, "trades": len(trades)}
    if not trades:
        return out
    t = pd.DataFrame(trades)
    for cost_name, cost in pb.COSTS.items():
        net_rs = [pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]
                  for tr in trades]
        s = pd.Series(net_rs)
        wins = s[s > 0]
        losses = s[s <= 0]
        gw = float(wins.sum())
        gl = float(-losses.sum())
        out[cost_name] = {
            "trades": len(trades),
            "win_rate_pct": round(float((s > 0).mean()) * 100, 1),
            "expectancy_net_r": round(float(s.mean()), 3),
            "profit_factor": round(gw / gl, 2) if gl > 0 else None,
            "avg_hold_bars": round(float(t["hold_bars"].mean()), 1),
            "tp1_hit_rate_pct": round(float(t["tp1_hit"].mean()) * 100, 1),
            "exit_reasons": t["reason"].value_counts().to_dict(),
        }
    return out


def main():
    with open(os.path.join(BASE, "fetch_watchlist_1h_log.json")) as f:
        fetch_log = json.load(f)

    all_trades, closes, skipped = [], {}, 0
    used, dropped = [], []
    per_sym_trades = {}
    for sym in WATCHLIST:
        v = fetch_log.get(sym, {})
        path = os.path.join(CACHE, f"h1_{sym}.pkl")
        if not v.get("ok") or not os.path.exists(path):
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
        per_sym_trades[sym] = tr
        all_trades.extend(tr)
        skipped += sg
        used.append(sym)
        print(f"  {sym}: {len(tr)} trades", flush=True)
    all_trades.sort(key=lambda t: t["entry_time"])

    pooled = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
        pooled.append(pb.summarize(f"PINE_V36_hybrid:WATCH12:1h",
                                   all_trades, port, skipped, cost_name))

    per_ticker = [per_ticker_stats(s, per_sym_trades.get(s, [])) for s in WATCHLIST]

    starts = [fetch_log[s]["start"] for s in used]
    ends = [fetch_log[s]["end"] for s in used]
    results = {
        "timeframe": "1h",
        "universe": "WATCH12 (Mike's watchlist)",
        "code": "canonical pine_backtest.py WITH 2026-09-20 score fix (a141ca9); "
                "Hybrid pine_buy_signal, parameters unmodified from 4H",
        "notes": [
            "Unmodified-transfer test: indicator lookbacks in BARS identical to "
            "4H (EMA 9/21/55/200, ATR 14, vol SMA20, breakout 10) — ~4x less "
            "clock time per lookback than 4H. No parameter tuned for 1H.",
            "yfinance 1H, regular session only (prepost=False), 730d max window.",
            "Same portfolio conventions as corrected 4H baseline: 4/25bps, $10k, "
            "1%/trade, max 5 concurrent, 5% portfolio risk, next-bar-open "
            "entries, stop-first ties, gap-below-stop skips.",
            "Pooled stats via pb.summarize (identical accounting to the 4H "
            "baseline); per-ticker net R via pb._outcome, same derivation.",
        ],
        "data_window": {"start": min(starts), "end": max(ends)},
        "symbols_used": used,
        "symbols_dropped": dropped,
        "pooled": pooled,
        "per_ticker": per_ticker,
    }
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)
    print(f"wrote {OUT}")
    for r in pooled:
        print(f"pooled [{r['cost']}]: n={r['trades']} win={r['win_rate_pct']}% "
              f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
              f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}%")


if __name__ == "__main__":
    main()
