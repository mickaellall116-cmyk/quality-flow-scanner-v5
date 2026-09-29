"""Download 5y daily bars for the Pine daily-timeframe backtest."""
import os
import sys
import time

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pine_backtest import UNIVERSE_X

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "backtest_cache", "v3")

for sym in UNIVERSE_X:
    path = os.path.join(CACHE, f"d1_5y_{sym}.pkl")
    if os.path.exists(path):
        print(f"  {sym}: cached", flush=True)
        continue
    try:
        df = yf.download(sym, period="5y", interval="1d", auto_adjust=False,
                         progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns={"Open": "Open", "High": "High", "Low": "Low",
                                "Close": "Close", "Volume": "Volume"})
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        df.to_pickle(path)
        print(f"  {sym}: {len(df)} bars", flush=True)
    except Exception as e:
        print(f"  {sym}: FAILED {e}", flush=True)
    time.sleep(0.3)
print("done")
