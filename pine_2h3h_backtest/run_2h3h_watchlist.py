"""2H + 3H backtest of the Quality Flow signal logic on Mike's CURRENT 14-ticker watchlist.

Method (mirrors pine_1h_backtest/run_1h_watchlist.py and the corrected 4H
baseline in pine_sensitivity/run_corrected_v2.py):
- Imports the FIXED canonical pine_backtest.py UNMODIFIED (entries + exits +
  portfolio sim imported, never copied): add_pine_indicators, pine_buy_signal
  (Hybrid), gen_pine_trades, simulate_portfolio, summarize, COSTS, RISK_PCT,
  WARMUP, _outcome.
- yfinance serves no 2h/3h interval, so 1H bars (regular session only,
  prepost=False, 730d) are resampled to 2H/3H with pandas, resampled WITHIN
  each trading day so no bar spans the overnight gap. Bins are anchored at
  the 09:30 session open per day: 2H -> 09:30/11:30/13:30/15:30 (+30-min stub
  15:30-16:00 kept); 3H -> 09:30/12:30/15:30 (+30-min stub kept). OHLCV:
  first Open, max High, min Low, last Close, sum Volume.
- Indicator lookbacks kept in BARS (EMA 9/21/55/200, ATR 14, vol SMA20,
  breakout 10) = ~2x / ~1.33x less clock time than 4H. Parameters tuned for
  4H; this is an unmodified-transfer test, NOT a re-tuned system.
- Same portfolio conventions as the 4H baseline: 4/25bps costs, $10k,
  1%/trade, max 5 concurrent positions, 5% portfolio risk, next-bar-open
  entries, stop-first ties, gap-below-stop skips.
- Symbols with <200 resampled bars are fail-closed (excluded), same rule as
  the live SPCX handling.
- Reports pooled stats (via pb.summarize, identical to the 4H baseline) plus
  per-ticker stats derived the same way (net R via pb._outcome), per
  timeframe.

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
OUT = os.path.join(BASE, "pine_2h3h_watchlist_results.json")

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO",
             "HOOD", "AMD"]

TIMEFRAMES = {"2h": "2h", "3h": "3h"}
MIN_BARS = 200

AGG = {"Open": "first", "High": "max", "Low": "min",
       "Close": "last", "Volume": "sum"}


def resample_within_day(df, rule):
    """Resample 1H bars to 2H/3H within each trading day (no bar spans the
    overnight gap). Bins anchored at the 09:30 session open per day."""
    tz = df.index.tz
    out_days = []
    for day, g in df.groupby(df.index.date, sort=True):
        g = g.sort_index()
        origin = pd.Timestamp(day).tz_localize(tz) + pd.Timedelta(hours=9, minutes=30)
        r = g.resample(rule, origin=origin).agg(AGG)
        r = r.dropna(subset=["Close"])
        if not r.empty:
            out_days.append(r)
    if not out_days:
        return df.iloc[0:0]
    out = pd.concat(out_days).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out


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


def run_timeframe(tf, rule, fetch_log):
    all_trades, closes, skipped = [], {}, 0
    used, dropped, dropped_vol, dropped_short = [], [], [], []
    per_sym_trades = {}
    bar_counts = {}
    for sym in WATCHLIST:
        v = fetch_log.get(sym, {})
        path = os.path.join(CACHE, f"h1_{sym}.pkl")
        if not v.get("ok") or not os.path.exists(path):
            dropped.append(sym)
            continue
        df1h = pd.read_pickle(path)
        if "Volume" not in df1h.columns or df1h["Volume"].isna().all():
            print(f"  [warn] no volume for {sym}, skipping", flush=True)
            dropped_vol.append(sym)
            continue
        df = resample_within_day(df1h, rule)
        bar_counts[sym] = len(df)
        if len(df) < MIN_BARS:
            print(f"  [warn] {sym}: only {len(df)} {tf} bars (<{MIN_BARS}), "
                  f"fail-closed", flush=True)
            dropped_short.append(sym)
            continue
        df = pb.add_pine_indicators(df)
        closes[sym] = df["Close"]
        tr, sg = pb.gen_pine_trades(sym, df)
        per_sym_trades[sym] = tr
        all_trades.extend(tr)
        skipped += sg
        used.append(sym)
        print(f"  {tf} {sym}: {len(df)} bars, {len(tr)} trades", flush=True)
    all_trades.sort(key=lambda t: t["entry_time"])

    pooled = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
        pooled.append(pb.summarize(f"PINE_V36_hybrid:WATCH14:{tf}",
                                   all_trades, port, skipped, cost_name))

    per_ticker = [per_ticker_stats(s, per_sym_trades.get(s, [])) for s in WATCHLIST]
    return {
        "timeframe": tf,
        "symbols_used": used,
        "symbols_dropped": dropped,
        "symbols_dropped_no_volume": dropped_vol,
        "symbols_fail_closed_short_history": dropped_short,
        "bar_counts": bar_counts,
        "trades_total": len(all_trades),
        "skipped_gap": skipped,
        "pooled": pooled,
        "per_ticker": per_ticker,
    }


def main():
    with open(os.path.join(BASE, "fetch_watchlist_1h_log.json")) as f:
        fetch_log = json.load(f)

    results = {
        "universe": "WATCH14 (Mike's current watchlist)",
        "code": "canonical pine_backtest.py WITH 2026-09-20 score fix (a141ca9); "
                "Hybrid pine_buy_signal, parameters unmodified from 4H",
        "notes": [
            "Unmodified-transfer test: indicator lookbacks in BARS identical to "
            "4H (EMA 9/21/55/200, ATR 14, vol SMA20, breakout 10). No parameter "
            "tuned for 2H/3H.",
            "yfinance serves no 2h/3h interval: 1H bars (regular session only, "
            "prepost=False, 730d) resampled within each trading day; no bar "
            "spans the overnight gap. Bins anchored at 09:30/day; the final "
            "15:30-16:00 stub bar of each day is kept. OHLCV: first/max/min/"
            "last/sum.",
            "Same portfolio conventions as corrected 4H baseline: 4/25bps, $10k, "
            "1%/trade, max 5 concurrent, 5% portfolio risk, next-bar-open "
            "entries, stop-first ties, gap-below-stop skips.",
            "Symbols with <200 resampled bars fail closed (excluded).",
            "Pooled stats via pb.summarize (identical accounting to the 4H "
            "baseline); per-ticker net R via pb._outcome, same derivation.",
        ],
        "data_window": {
            "start": min(v["start"] for v in fetch_log.values() if v.get("ok")),
            "end": max(v["end"] for v in fetch_log.values() if v.get("ok")),
        },
        "timeframes": {},
    }
    for tf, rule in TIMEFRAMES.items():
        print(f"=== {tf} ===", flush=True)
        results["timeframes"][tf] = run_timeframe(tf, rule, fetch_log)

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)
    print(f"wrote {OUT}")
    for tf, r in results["timeframes"].items():
        for p in r["pooled"]:
            print(f"pooled [{tf}][{p['cost']}]: n={p['trades']} "
                  f"win={p['win_rate_pct']}% exp={p['expectancy_net_r']}R "
                  f"PF={p['profit_factor']} ret={p['total_return_pct']}% "
                  f"dd={p['max_drawdown_pct']}%")


if __name__ == "__main__":
    main()
