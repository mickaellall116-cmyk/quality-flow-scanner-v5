"""3H + FVG-as-entry backtest: the two winners combined.

- 3H bars: 1H cache (pine_2h3h_backtest/cache/h1_{SYM}.pkl) resampled WITHIN
  each trading day, bins anchored at 09:30 ET (09:30/12:30/15:30 + 15:30-16:00
  stub kept) — identical convention to pine_2h3h_backtest/run_2h3h_watchlist.py.
- FVG entry: Hybrid buySignal OR the ported fvgBuy sub-signal (from
  pine_entry_timing_backtest/run_entry_timing.py, imported unmodified).
  Pullback and sweep toggles OFF.
- pine_backtest.py imported UNMODIFIED; only pb.pine_buy_signal monkey-patched
  per combo (same pattern as the entry-timing study).
- Indicator lookbacks kept in BARS (unmodified transfer, no tuning) — same
  approach as the 2H/3H study.
- Combos run: BASE (all-off, rerun in THIS study) and FVG-only.

Local-only research. No frozen files modified.
"""
import json
import os
import sys

import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_3h_fvg_backtest")
H1CACHE = os.path.join(BASE, "pine_2h3h_backtest", "cache")
OUT = os.path.join(OUTDIR, "pine_3h_fvg_results.json")
os.makedirs(OUTDIR, exist_ok=True)

sys.path.insert(0, BASE)
import pine_backtest as pb
sys.path.insert(0, os.path.join(BASE, "pine_entry_timing_backtest"))
from run_entry_timing import (add_entry_timing_columns, sub_signals,
                              make_combo_signal, _orig_signal)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
MIN_BARS = 200
AGG = {"Open": "first", "High": "max", "Low": "min",
       "Close": "last", "Volume": "sum"}


def resample_within_day(df, rule):
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
    out = {"symbol": sym, "trades": len(trades)}
    if not trades:
        return out
    t = pd.DataFrame(trades)
    for cost_name, cost in pb.COSTS.items():
        net_rs = [pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]
                  for tr in trades]
        s = pd.Series(net_rs)
        wins, losses = s[s > 0], s[s <= 0]
        gw, gl = float(wins.sum()), float(-losses.sum())
        out[cost_name] = {
            "trades": len(trades),
            "win_rate_pct": round(float((s > 0).mean()) * 100, 1),
            "expectancy_net_r": round(float(s.mean()), 3),
            "profit_factor": round(gw / gl, 2) if gl > 0 else None,
        }
    return out


def main():
    data, closes, dropped = {}, {}, []
    for sym in WATCHLIST:
        path = os.path.join(H1CACHE, f"h1_{sym}.pkl")
        if not os.path.exists(path):
            dropped.append(sym)
            continue
        df = resample_within_day(pd.read_pickle(path), "3h")
        if len(df) < MIN_BARS:
            dropped.append(sym)
            continue
        if "Volume" not in df.columns or df["Volume"].isna().all():
            dropped.append(sym)
            continue
        df = pb.add_pine_indicators(df)
        df = add_entry_timing_columns(df)
        data[sym] = df
        closes[sym] = df["Close"]
    used = [s for s in WATCHLIST if s in data]
    print(f"loaded {len(used)} tickers; dropped: {dropped}", flush=True)

    # signal-bar sets for FVG attribution (3H)
    sig_sets = {}
    for sym in used:
        df = data[sym]
        canon, fvg = set(), set()
        for i in range(pb.WARMUP, len(df) - 1):
            if _orig_signal(df, i):
                canon.add(df.index[i])
            if sub_signals(df, i)["fvg"]:
                fvg.add(df.index[i])
        sig_sets[sym] = {"canonical": canon, "fvg": fvg}
    marg_bars = sum(len(sig_sets[s]["fvg"] - sig_sets[s]["canonical"]) for s in used)
    tot_fvg = sum(len(sig_sets[s]["fvg"]) for s in used)

    results = {"fvg_marginal_bars_not_canonical": marg_bars,
               "fvg_sub_signal_bars_total": tot_fvg,
               "combos": []}
    combos = [("BASE(all-off)", make_combo_signal(False, False, False)),
              ("FVG-only", make_combo_signal(False, True, False))]
    for name, sigfn in combos:
        pb.pine_buy_signal = sigfn
        all_trades, skipped, per_sym = [], 0, {}
        for sym in used:
            tr, sg = pb.gen_pine_trades(sym, data[sym])
            per_sym[sym] = tr
            all_trades.extend(tr)
            skipped += sg
        all_trades.sort(key=lambda t: t["entry_time"])

        added = 0
        for tr in all_trades:
            st = pd.Timestamp(tr["signal_time"])
            if st.tzinfo is None:
                st = st.tz_localize("America/New_York")
            if st not in sig_sets[tr["symbol"]]["canonical"]:
                added += 1

        pooled = []
        for cost_name, cost in pb.COSTS.items():
            port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
            pooled.append(pb.summarize(f"3H_FVG:{name}", all_trades, port,
                                       skipped, cost_name))
        per_ticker = [per_ticker_stats(s, per_sym.get(s, [])) for s in used]
        results["combos"].append({"name": name, "trades": len(all_trades),
                                  "trades_added_by_fvg": added,
                                  "skipped_gap": skipped,
                                  "pooled": pooled,
                                  "per_ticker": per_ticker})
        for p in pooled:
            print(f"{name} [{p['cost']}]: n={p['trades']} (+{added} by FVG) "
                  f"win={p['win_rate_pct']}% exp={p['expectancy_net_r']}R "
                  f"PF={p['profit_factor']} maxDD={p['max_drawdown_pct']}%",
                  flush=True)

    pb.pine_buy_signal = _orig_signal
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
