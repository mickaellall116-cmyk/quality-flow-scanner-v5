"""Study 3: Daily + Weekly transfer of unmodified Pine V3.6.
Daily: backtest_cache/v3/d1_5y_*.pkl (UX51, 2021-09-15 -> 2026-09-15).
Weekly: yfinance 1wk download -> pine_expansion/cache_w1/.
Logic imported unmodified from pine_backtest; lookbacks kept in bars; WARMUP=215 kept.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import yfinance as yf
import pine_backtest as pb

BASE = os.path.dirname(os.path.abspath(__file__))
W1 = os.path.join(BASE, "cache_w1")
os.makedirs(W1, exist_ok=True)
OUT = os.path.join(BASE, "study3_results.json")


def fetch_weekly():
    log = {}
    for sym in pb.UNIVERSE_X:
        path = os.path.join(W1, f"w1_{sym}.pkl")
        if os.path.exists(path):
            continue
        try:
            df = yf.download(sym, interval="1wk", period="6y", progress=False,
                             auto_adjust=True, threads=False)
            time.sleep(0.3)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            df = df.dropna()
            if df.empty or len(df) < 50:
                log[sym] = {"ok": False, "bars": 0 if df is None else len(df)}
                continue
            df.to_pickle(path)
            log[sym] = {"ok": True, "bars": len(df),
                        "start": str(df.index[0]), "end": str(df.index[-1])}
        except Exception as e:
            log[sym] = {"ok": False, "reason": type(e).__name__}
    with open(os.path.join(BASE, "fetch_w1_log.json"), "w") as f:
        json.dump(log, f, indent=1, default=str)
    return log


def run_weekly():
    all_trades, closes, skipped = [], {}, 0
    syms = []
    for sym in pb.UNIVERSE_X:
        path = os.path.join(W1, f"w1_{sym}.pkl")
        if not os.path.exists(path):
            print(f"  [warn] no weekly cache for {sym}", flush=True)
            continue
        df = pd.read_pickle(path)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"  [warn] no volume {sym}", flush=True)
            continue
        df = pb.add_pine_indicators(df)
        closes[sym] = df["Close"]
        tr, sg = pb.gen_pine_trades(sym, df)
        all_trades.extend(tr)
        skipped += sg
        syms.append(sym)
        print(f"  {sym}: {len(tr)} trades ({len(df)} bars)", flush=True)
    all_trades.sort(key=lambda t: t["entry_time"])
    rows = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
        rows.append(pb.summarize("PINE_V36_hybrid:UX51:1wk", all_trades, port,
                                 skipped, cost_name))
    return rows, all_trades, syms


def main():
    results = {"notes": [
        "Study 3: unmodified Pine V3.6 on Daily and Weekly. Lookbacks kept in bars.",
        "Daily uses backtest_cache/v3/d1_5y_*.pkl (2021-09-15->2026-09-15).",
        "Weekly uses yfinance 1wk downloads (cache_w1/). WARMUP=215 kept.",
    ]}
    print("== DAILY (cached d1_5y) ==", flush=True)
    daily_rows, _ = pb.run_universe(pb.UNIVERSE_X, "UX51", tf="1d")
    results["daily"] = daily_rows
    for r in daily_rows:
        print(f"  [{r['cost']}] n={r['trades']} exp={r['expectancy_net_r']}R "
              f"PF={r['profit_factor']} ret={r['total_return_pct']}% "
              f"dd={r['max_drawdown_pct']}%", flush=True)

    print("== WEEKLY: fetching ==", flush=True)
    wlog = fetch_weekly()
    nok = sum(1 for v in wlog.values() if v.get("ok"))
    print(f"  weekly fetched: {nok} new this run", flush=True)
    print("== WEEKLY: running ==", flush=True)
    wrows, wtrades, wsyms = run_weekly()
    results["weekly"] = wrows
    results["weekly_symbols"] = wsyms
    results["weekly_trade_count_check"] = len(wtrades)
    for r in wrows:
        print(f"  [{r['cost']}] n={r['trades']} exp={r['expectancy_net_r']}R "
              f"PF={r['profit_factor']} ret={r['total_return_pct']}% "
              f"dd={r['max_drawdown_pct']}%", flush=True)
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
