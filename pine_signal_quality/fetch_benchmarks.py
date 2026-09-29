"""Fetch DAILY benchmark bars (SPY, QQQ + sector ETFs) for the H1 relative-strength
filter. Daily used because Yahoo restricts 1h bars to the last 730 days, which
cannot cover the 2024-09 research window start or 2022 validation (documented in
SIGNAL_QUALITY_SPEC.md Amendment A). Sector mapping was frozen by the earlier run
(sector_map.json); this script only downloads price data."""
import json
import os
import sys
import time
import traceback

import pandas as pd
import yfinance as yf

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache")

SECTOR_TO_ETF = {
    "Technology": "XLK", "Financial Services": "XLF", "Financial": "XLF",
    "Healthcare": "XLV", "Energy": "XLE", "Industrials": "XLI",
    "Consumer Defensive": "XLP", "Utilities": "XLU", "Consumer Cyclical": "XLY",
    "Communication Services": "XLC", "Communication": "XLC",
    "Real Estate": "XLRE", "Basic Materials": "XLB",
}


def download_daily(sym, tries=4):
    for a in range(tries):
        try:
            df = yf.download(sym, start="2021-06-01", end="2026-09-19", interval="1d",
                             auto_adjust=False, progress=False)
            if df is not None and len(df) > 100:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df
        except Exception as e:
            print(f"  {sym} attempt {a+1}: {type(e).__name__}", flush=True)
        time.sleep(3 + a * 4)
    return None


def main():
    secmap = json.load(open(os.path.join(BASE, "sector_map.json")))
    needed = {"SPY", "QQQ"}
    for sym, sec in secmap.items():
        etf = SECTOR_TO_ETF.get(sec) if sec else None
        if etf:
            needed.add(etf)
    print("benchmark ETFs needed:", sorted(needed), flush=True)

    manifest = {}
    for etf in sorted(needed):
        path = os.path.join(CACHE, f"bench_1d_{etf}.pkl")
        if os.path.exists(path):
            print(f"{etf}: cached", flush=True)
            manifest[etf] = {"file": path, "freq": "1d"}
            continue
        df = download_daily(etf)
        if df is not None:
            if df.index.tz is None:
                df.index = df.index.tz_localize("America/New_York")
            df.index = df.index.tz_convert("UTC")
            df.to_pickle(path)
            manifest[etf] = {"file": path, "freq": "1d"}
            print(f"{etf}: saved daily ({len(df)} bars, "
                  f"{df.index[0].date()} -> {df.index[-1].date()})", flush=True)
        else:
            manifest[etf] = {"file": None, "freq": None}
            print(f"{etf}: NO DATA", flush=True)
        time.sleep(2)
    json.dump(manifest, open(os.path.join(BASE, "benchmark_manifest.json"), "w"), indent=1)
    missing = [k for k, v in manifest.items() if not v["file"]]
    print("missing:", missing, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
