"""Mean-reversion entry backtest: "buy the dip to the long-term mean".

Idea (Mike-approved, from the Overkill Trading reel): buy when price taps its
long-term average. Adapted to the 4H system as a pre-defined, no-tuning study:

- Long-term mean = 200-bar SMA on 4H (point-in-time, no lookahead).
  (On 4H, 200 bars ~= 100 trading days ~= 5 months -- NOT 4 years; the reel's
  4-year line is not reproducible on available 4H history. Stated as-is.)
- MR_GUARD: signal = bar's low touches/crosses below the 200SMA AND the bar
  closes back above it (the bounce), WHILE EMA21 > EMA55 (uptrend intact --
  the value-trap guard). No other entry conditions.
- MR_RAW:   signal = low <= sma200 and close > sma200 (no guard).
- BASE:     standard Hybrid pine_buy_signal, rerun in-study (never reuse
  numbers across studies).

pine_backtest.py is imported UNMODIFIED; only pb.pine_buy_signal is
monkey-patched per variant. Exits (Mode B), costs, portfolio sim untouched.
Local-only research. No frozen files modified.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_meanrev_backtest")
sys.path.insert(0, BASE)
import pine_backtest as pb

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "meanrev_results.json")

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

SMA_LB = 200  # long-term mean lookback (bars), adapted from the reel's 4y line

_orig_signal = pb.pine_buy_signal


def add_meanrev_columns(df):
    out = df.copy()
    out["sma200"] = out["Close"].rolling(SMA_LB).mean()  # point-in-time
    return out


def meanrev_signal(df, i, guard):
    r = df.iloc[i]
    if pd.isna(r["sma200"]) or pd.isna(r["e21"]) or pd.isna(r["e55"]):
        return False
    touched = r["Low"] <= r["sma200"] and r["Close"] > r["sma200"]
    if not touched:
        return False
    if guard and not (r["e21"] > r["e55"]):
        return False
    return True


def make_meanrev_signal(guard):
    def sig(df, i):
        return bool(meanrev_signal(df, i, guard))
    return sig


def per_ticker_stats(sym, trades):
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
        gw, gl = float(wins.sum()), float(-losses.sum())
        out[cost_name] = {
            "trades": len(trades),
            "win_rate_pct": round(float((s > 0).mean()) * 100, 1),
            "expectancy_net_r": round(float(s.mean()), 3),
            "profit_factor": round(gw / gl, 2) if gl > 0 else None,
        }
    return out


def main():
    data, closes = {}, {}
    dropped = []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        if "Volume" not in df.columns or df["Volume"].isna().all():
            dropped.append(sym)
            continue
        df = pb.add_pine_indicators(df)
        df = add_meanrev_columns(df)
        data[sym] = df
        closes[sym] = df["Close"]
    used = [s for s in WATCHLIST if s in data]
    print(f"loaded {len(used)} tickers; dropped: {dropped}", flush=True)
    for s in used:
        d = data[s]
        print(f"  {s}: {d.index.min()} -> {d.index.max()} ({len(d)} bars)",
              flush=True)

    # signal-bar sets for attribution (WARMUP..n-1, same range gen scans)
    sig_sets = {}
    for sym in used:
        df = data[sym]
        canon, mr = set(), set()
        for i in range(pb.WARMUP, len(df) - 1):
            if _orig_signal(df, i):
                canon.add(df.index[i])
            if meanrev_signal(df, i, guard=True):
                mr.add(df.index[i])
        sig_sets[sym] = {"canonical": canon, "meanrev_guarded": mr}

    variants = [
        ("BASE", None),
        ("MR_GUARD", True),
        ("MR_RAW", False),
    ]
    results = {"variants": [], "signal_marginals": {
        "meanrev_guarded_bars": sum(len(sig_sets[s]["meanrev_guarded"]) for s in used),
        "meanrev_guarded_not_canonical":
            sum(len(sig_sets[s]["meanrev_guarded"] - sig_sets[s]["canonical"]) for s in used),
        "canonical_bars":
            sum(len(sig_sets[s]["canonical"]) for s in used),
    }}

    for name, guard in variants:
        pb.pine_buy_signal = _orig_signal if guard is None else make_meanrev_signal(guard)
        all_trades, skipped = [], 0
        per_sym_trades = {}
        for sym in used:
            tr, sg = pb.gen_pine_trades(sym, data[sym])
            per_sym_trades[sym] = tr
            all_trades.extend(tr)
            skipped += sg
        all_trades.sort(key=lambda t: t["entry_time"])

        pooled = []
        for cost_name, cost in pb.COSTS.items():
            port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
            pooled.append(pb.summarize(f"MEANREV:{name}:4h",
                                       all_trades, port, skipped, cost_name))
        per_ticker = [per_ticker_stats(s, per_sym_trades.get(s, [])) for s in used]
        results["variants"].append({
            "name": name,
            "trades": len(all_trades),
            "skipped_gap": skipped,
            "pooled": pooled,
            "per_ticker": per_ticker,
        })
        for p in pooled:
            print(f"{name} [{p['cost']}]: n={p['trades']} "
                  f"win={p['win_rate_pct']}% exp={p['expectancy_net_r']}R "
                  f"PF={p['profit_factor']} maxDD={p.get('max_drawdown_pct', '?')}%",
                  flush=True)

    pb.pine_buy_signal = _orig_signal
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
