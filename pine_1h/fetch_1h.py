"""Fetch 1H bars for the Pine V3.6 UX51 universe via yfinance.

Local-only research. Writes to pine_1h/cache/h1_{sym}.pkl (new files only).
"""
import json
import os
import sys
import time

import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pine_backtest as pb

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache")
os.makedirs(CACHE, exist_ok=True)

LOG = os.path.join(BASE, "fetch_1h_log.json")


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
    for i, sym in enumerate(pb.UNIVERSE_X):
        try:
            df, err = fetch(sym)
        except Exception as e:  # noqa: BLE001
            df, err = None, f"exception: {type(e).__name__}: {e}"
        if err:
            log[sym] = {"ok": False, "error": err}
            print(f"  [{i+1}/51] {sym}: FAIL {err}", flush=True)
        else:
            path = os.path.join(CACHE, f"h1_{sym}.pkl")
            df.to_pickle(path)
            log[sym] = {"ok": True, "bars": len(df),
                        "start": df.index[0].isoformat(),
                        "end": df.index[-1].isoformat()}
            print(f"  [{i+1}/51] {sym}: {len(df)} bars "
                  f"{df.index[0].date()} -> {df.index[-1].date()}", flush=True)
        time.sleep(1.0)
    ok = sum(1 for v in log.values() if v["ok"])
    print(f"DONE: {ok}/{len(log)} symbols cached")
    with open(LOG, "w") as f:
        json.dump(log, f, indent=1)


if __name__ == "__main__":
    main()
