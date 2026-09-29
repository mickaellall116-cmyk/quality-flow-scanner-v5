"""Counterfactual: what if scanner-EXIT exits were ignored (hold to stop/target/time)?"""
import os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_cache")
trades = pd.read_csv(os.path.join(CACHE, "trades_structural_open_entry.csv"))
se = trades[trades["reason"] == "scanner-exit"].copy()
print(f"scanner-exit trades: {len(se)}", flush=True)

dfs = {}
sigs = {}
rows = []
for _, t in se.iterrows():
    sym = t["symbol"]
    if sym not in dfs:
        dfs[sym] = bt.cached(f"h4_{sym}", lambda: None)
        sigs[sym], _, _ = pd.read_pickle(os.path.join(CACHE, f"signals_{sym}.pkl"))
    df, sig = dfs[sym], sigs[sym]
    # find entry bar: first bar whose close time matches entry_date
    entry_ts = pd.Timestamp(t["entry_date"])
    cands = df.index[df.index.get_loc(entry_ts)] if False else None
    i = int(df.index.searchsorted(entry_ts, side="right") - 1)
    # entry was next-bar open
    entry = float(df["Open"].iloc[i + 1])
    stop, tp1 = float(t["stop"]), float(t["tp1"])
    n = len(df)
    end = min(i + bt.MAX_HOLD_BARS, n - 1)
    outcome = ("time", float(df["Close"].iloc[end]), end)
    for j in range(i + 1, end + 1):
        lo, hi = float(df["Low"].iloc[j]), float(df["High"].iloc[j])
        if lo <= stop:
            outcome = ("stop", stop, j); break
        if hi >= tp1:
            outcome = ("target", tp1, j); break
    reason2, exit2, j2 = outcome
    ret2 = (exit2 - entry) / entry - bt.ROUNDTRIP_COST
    rows.append({"symbol": sym, "entry_date": t["entry_date"],
                 "actual_ret_pct": t["ret_pct"], "actual_reason": "scanner-exit",
                 "no_exit_ret_pct": round(ret2 * 100, 3), "no_exit_reason": reason2,
                 "delta_pct": round(ret2 * 100 - t["ret_pct"], 3)})
out = pd.DataFrame(rows)
print(out.to_string(), flush=True)
print(f"\nActual total: {out['actual_ret_pct'].sum():.2f}% | "
      f"Ignoring EXIT: {out['no_exit_ret_pct'].sum():.2f}% | "
      f"Delta: {out['delta_pct'].sum():.2f}%", flush=True)
out.to_csv(os.path.join(CACHE, "scanner_exit_counterfactual.csv"), index=False)
