"""Build session-aligned 4H bars for the entry-timing study.

Resamples the pine_2h3h_backtest 1H cache (all 14 watchlist tickers) to 4H
within each trading day, bins anchored at the 09:30 session open — the same
convention as the canonical backtest_cache/v3 h4_*.pkl (bars at 09:30, 13:30
ET, no bar spans the overnight gap).

Local-only research. Modifies nothing frozen.
"""
import os

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache")
H1 = "/home/hatch/workspace/quality-flow-scanner-v5/pine_2h3h_backtest/cache"
os.makedirs(CACHE, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

AGG = {"Open": "first", "High": "max", "Low": "min",
       "Close": "last", "Volume": "sum"}


def resample_4h(df):
    tz = df.index.tz
    out_days = []
    for day, g in df.groupby(df.index.date, sort=True):
        g = g.sort_index()
        origin = pd.Timestamp(day).tz_localize(tz) + pd.Timedelta(hours=9, minutes=30)
        r = g.resample("4h", origin=origin).agg(AGG)
        r = r.dropna(subset=["Close"])
        if not r.empty:
            out_days.append(r)
    if not out_days:
        return df.iloc[0:0]
    out = pd.concat(out_days).sort_index()
    return out[~out.index.duplicated(keep="last")]


def main():
    for sym in WATCHLIST:
        src = os.path.join(H1, f"h1_{sym}.pkl")
        df = pd.read_pickle(src)
        h4 = resample_4h(df)
        dst = os.path.join(CACHE, f"h4_{sym}.pkl")
        h4.to_pickle(dst)
        print(f"{sym}: {len(df)} 1H bars -> {len(h4)} 4H bars "
              f"({h4.index[0]} .. {h4.index[-1]})", flush=True)


if __name__ == "__main__":
    main()
