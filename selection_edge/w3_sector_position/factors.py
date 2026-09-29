"""W3 shared library: F5 (sector leadership) + F6 (60-day-high proximity).

Strict-PIT factor computation for the selection-edge study, worker W3.

HARD BLINDING: the 14 names (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM,
SPCX, ASTX, BBAI, NIO, HOOD, AMD) are masked from the working universe for
ALL construction and evaluation. Only the 8 present in the 131-universe need
removal; the other 6 are not in the universe at all. The 14 are never
referenced anywhere else in this worker's code.
"""

import json
import os
import pickle

import pandas as pd

CB = os.path.expanduser(
    "~/workspace/quality-flow-scanner-v5/canonical_baseline")

# The 14 masked names. Only 8 are present in the 131-universe; all 14 are
# excluded from the working set regardless.
MASKED14 = {"QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB", "ONDS", "DRAM",
            "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"}

# GICS-style sector -> sector ETF (current-pull mapping, canonical baseline)
SECTOR_ETF = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Energy": "XLE",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Consumer Defensive": "XLP",
    "Consumer Cyclical": "XLY",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB",
    "Communication Services": "XLC",
}
ETF11 = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLY", "XLU",
         "XLRE", "XLB", "XLC"]

_etf_cache = {}
_stock_cache = {}


def load_universe():
    with open(os.path.join(CB, "universe.json")) as fh:
        u = json.load(fh)
    return u


def working_set():
    """131-name PIT universe minus the masked 14. Returns (symbols, sector_map)."""
    u = load_universe()
    syms = [x["symbol"] for x in u if x["symbol"] not in MASKED14]
    sec = {x["symbol"]: x["sector"] for x in u if x["symbol"] not in MASKED14}
    return syms, sec


def load_daily(sym):
    """Daily bars (adjusted), tz-aware ET index. None if missing."""
    if sym in _stock_cache:
        return _stock_cache[sym]
    p = os.path.join(CB, "data", f"d1_{sym}.pkl")
    df = None
    if os.path.exists(p):
        df = pickle.load(open(p, "rb"))
    _stock_cache[sym] = df
    return df


def load_etf(sym):
    if sym in _etf_cache:
        return _etf_cache[sym]
    df = pickle.load(open(os.path.join(CB, "data", f"d1_{sym}.pkl"), "rb"))
    _etf_cache[sym] = df
    return df


def pit_endpoint(idx, sig_ts):
    """Index of the last COMPLETED daily bar as of signal time.

    Signal closes are 13:30 (first 4H bar, session not done) or 16:00
    (second bar, daily session complete). A 13:30 signal may not read
    today's daily bar; a 16:00 signal may. This mirrors the live overlay
    convention (v54_lonewolf_overlay.py) and the PIT contract rule 2-3.
    """
    if sig_ts.hour < 16:
        cutoff = sig_ts.floor("D") - pd.Timedelta("1ns")
    else:
        cutoff = sig_ts
    return idx.searchsorted(cutoff, side="right") - 1


def f5_sector_rank(sym, sector, sig_ts, window=20, top_k=3):
    """F5: rank 11 sector ETFs by window-day return vs SPY at strict PIT.

    Returns (selected, detail). Unmapped sectors (ETF/None) -> (False, 'no_sector').
    """
    etf = SECTOR_ETF.get(sector)
    if etf is None:
        return False, {"reason": "no_sector_mapping"}
    spy = load_etf("SPY")
    es = pit_endpoint(spy.index, sig_ts)
    if es < window:
        return False, {"reason": "insufficient_history"}
    spy_ret = float(spy["Close"].iloc[es] / spy["Close"].iloc[es - window] - 1)
    scores = {}
    for e in ETF11:
        df = load_etf(e)
        ei = pit_endpoint(df.index, sig_ts)
        if ei < window:
            return False, {"reason": "insufficient_history"}
        r = float(df["Close"].iloc[ei] / df["Close"].iloc[ei - window] - 1)
        scores[e] = r - spy_ret
    ranked = sorted(scores, key=lambda e: -scores[e])
    rank = ranked.index(etf) + 1
    return (rank <= top_k), {"etf": etf, "rank": rank,
                            "ranked": ranked, "sector_score": scores[etf]}


def f6_position(sym, sig_ts, window=60):
    """F6: (close - Wd low)/(Wd high - Wd low) on daily closes, strict PIT.

    Returns (value, selected, detail). Flat range -> value 0.0 (unselected).
    """
    df = load_daily(sym)
    if df is None:
        return None, False, {"reason": "no_data"}
    e = pit_endpoint(df.index, sig_ts)
    if e < window - 1:
        return None, False, {"reason": "insufficient_history"}
    closes = df["Close"].iloc[e - window + 1: e + 1]
    c = float(closes.iloc[-1])
    lo, hi = float(closes.min()), float(closes.max())
    if hi == lo:
        return 0.0, False, {"reason": "flat_range"}
    return (c - lo) / (hi - lo), None, {}


def factor_row(sym, sector, sig_ts, f5_kwargs=None, f6_kwargs=None):
    """Compute pre-registered F5/F6 selections for one (symbol, signal time)."""
    f5_kwargs = f5_kwargs or {}
    f6_kwargs = f6_kwargs or {}
    sel5, d5 = f5_sector_rank(sym, sector, sig_ts, **f5_kwargs)
    pos, _, d6 = f6_position(sym, sig_ts, **f6_kwargs)
    thr = f6_kwargs.get("threshold", 0.8)
    sel6 = bool(pos is not None and pos > thr)
    return {
        "f5_selected": bool(sel5), "f5_detail": d5,
        "f6_position": None if pos is None else float(pos),
        "f6_selected": sel6,
    }


if __name__ == "__main__":
    syms, sec = working_set()
    print("working set:", len(syms))
    assert not (set(syms) & MASKED14)
    # spot check
    import numpy as np
    ts = pd.Timestamp("2024-03-26T13:30:00-04:00")
    r = factor_row("MSFT", sec["MSFT"], ts)
    print(r["f5_selected"], r["f5_detail"]["rank"], round(r["f6_position"], 3), r["f6_selected"])
    ts2 = pd.Timestamp("2024-04-11T16:00:00-04:00")
    r2 = factor_row("SPY", sec["SPY"], ts2)
    print("SPY:", r2["f5_selected"], r2["f5_detail"], round(r2["f6_position"], 3), r2["f6_selected"])
