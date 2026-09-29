#!/usr/bin/env python3
"""Shared data builders for the research audit (placebo / multiple-testing).
Regenerates canonical baseline trades via pine_backtest (import only, unmodified)
and the study classifications (lone-wolf RS flags, crowded-bar trade mapping).
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402 — canonical, imported unmodified

CACHE4H = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
CACHED = os.path.join(BASE, "pine_sector_rs_backtest", "cache")
OUTDIR = os.path.join(BASE, "research_audit", "stats")

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB", "ONDS", "DRAM",
             "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
SECTOR = {"QQQ": "XLK", "SMCI": "SOXX", "PLTR": "XLK", "ANET": "XLK",
          "SOFI": "XLF", "RKLB": "XLI", "ONDS": "XLK", "DRAM": "SOXX",
          "SPCX": "XLI", "ASTX": "XLK", "BBAI": "XLK", "NIO": "XLY",
          "HOOD": "XLF", "AMD": "SOXX"}
COST = 0.0025  # 25 bps, mandate benchmark
LOOKBACK = 20  # trading days

_D = None  # lazy cache


def daily_closes_4h(df4h):
    s = df4h["Close"].copy()
    s.index = s.index.tz_convert("America/New_York").tz_localize(None)
    return s.resample("1D").last().dropna()


def ret20(series, date):
    idx = series.index
    pos = idx.searchsorted(date, side="right") - 1
    if pos < LOOKBACK:
        return np.nan
    return series.iloc[pos] / series.iloc[pos - LOOKBACK] - 1.0


def get_data():
    """Returns dict: trades (list with net_r), per-trade RS flags, crowded bars."""
    global _D
    if _D is not None:
        return _D

    stock_d, closes = {}, {}
    trades = []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        stock_d[sym] = daily_closes_4h(df)
        df = pb.add_pine_indicators(df)
        closes[sym] = df["Close"]
        ts, _ = pb.gen_pine_trades(sym, df)
        trades.extend(ts)
    trades.sort(key=lambda t: t["entry_time"])
    assert len(trades) == 237, f"expected 237 canonical trades, got {len(trades)}"

    etf_d = {}
    for sym in ["SPY", "XLK", "SOXX", "XLF", "XLI", "XLY"]:
        df = pd.read_pickle(os.path.join(CACHED, f"d_{sym}.pkl"))
        s = df["Close"].copy()
        s.index = pd.to_datetime(
            s.index.tz_localize(None) if s.index.tz is not None else s.index
        ).normalize()
        etf_d[sym] = s.asfreq("1D").ffill().dropna()

    enriched = []
    for tr in trades:
        sym = tr["symbol"]
        net_r = pb._outcome(tr["entry"], tr["stop"], tr["exit"], COST)[2]
        sig_date = (pd.Timestamp(tr["signal_time"])
                    .tz_convert("America/New_York").tz_localize(None).normalize())
        sec = SECTOR[sym]
        srs = ret20(stock_d[sym], sig_date) - ret20(etf_d["SPY"], sig_date)
        secrs = ret20(etf_d[sec], sig_date) - ret20(etf_d["SPY"], sig_date)
        if pd.isna(srs) or pd.isna(secrs):
            lone_wolf, srs, secrs = False, np.nan, np.nan
        else:
            lone_wolf = bool(srs > 0 and secrs <= 0)
        enriched.append({
            "symbol": sym, "net_r": float(net_r),
            "stock_rs": None if pd.isna(srs) else float(srs),
            "sector_rs": None if pd.isna(secrs) else float(secrs),
            "lone_wolf": lone_wolf,
            "signal_time": tr["signal_time"],
            "entry_time": str(tr["entry_time"]),
        })

    _D = {"trades": enriched, "stock_d": stock_d, "etf_d": etf_d}
    return _D


def save_json(name, obj):
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, name)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)
    print("wrote", path)
    return path


if __name__ == "__main__":
    d = get_data()
    tr = d["trades"]
    rs = np.array([t["net_r"] for t in tr])
    blocked = [t for t in tr if t["lone_wolf"]]
    kept = [t for t in tr if not t["lone_wolf"]]
    b = np.array([t["net_r"] for t in blocked])
    k = np.array([t["net_r"] for t in kept])
    print(f"baseline n={len(tr)} exp={rs.mean():.4f} win={100*(rs>0).mean():.1f}%")
    print(f"lone-wolf blocked n={len(blocked)} exp={b.mean():.4f} "
          f"(study: n=83 exp=-0.0183)")
    print(f"retained n={len(kept)} exp={k.mean():.4f} (study: n=154 exp=0.3773)")
    print(f"delta={k.mean()-rs.mean():.4f} (study: 0.1386)")
