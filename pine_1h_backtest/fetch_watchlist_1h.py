"""Fetch 1H bars for the V3.7 watchlist (Mike's 12 tickers) via yfinance.

Same download convention as pine_1h/fetch_1h.py (the 2026-09-18 1H run):
yfinance interval=1h, period=730d, auto_adjust=False, prepost=False
(regular session only for stocks), deduped/sorted, Close-dropna.
Writes to pine_1h_backtest/cache/h1_{sym}.pkl + fetch log.

Local-only research. Modifies nothing frozen.
"""
import json
import os
import sys
import time

import pandas as pd
import yfinance as yf

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache")
os.makedirs(CACHE, exist_ok=True)
LOG = os.path.join(BASE, "fetch_watchlist_1h_log.json")

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO"]


def fetch(sym):
    df = yf.download(sym, interval="1h", period="730d", auto_adjust=False,
                     progress=False, prepost=False)
    if df is None or df.empty:
        return None, "empty"
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep].copy()
    df = df.dropna(subset=["Close"])
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if df.empty:
        return None, "no-valid-rows"
    return df, None


def main():
    log = {}
    for i, sym in enumerate(WATCHLIST):
        try:
            df, err = fetch(sym)
        except Exception as e:  # noqa: BLE001
            df, err = None, f"exception: {type(e).__name__}: {e}"
        if err:
            log[sym] = {"ok": False, "error": err}
            print(f"  [{i+1}/{len(WATCHLIST)}] {sym}: FAIL {err}", flush=True)
        else:
            path = os.path.join(CACHE, f"h1_{sym}.pkl")
            df.to_pickle(path)
            log[sym] = {"ok": True, "bars": len(df),
                        "start": df.index[0].isoformat(),
                        "end": df.index[-1].isoformat()}
            print(f"  [{i+1}/{len(WATCHLIST)}] {sym}: {len(df)} bars "
                  f"{df.index[0].date()} -> {df.index[-1].date()}", flush=True)
        time.sleep(1.0)
    ok = sum(1 for v in log.values() if v["ok"])
    print(f"DONE: {ok}/{len(log)} symbols cached")
    with open(LOG, "w") as f:
        json.dump(log, f, indent=1)


if __name__ == "__main__":
    main()
