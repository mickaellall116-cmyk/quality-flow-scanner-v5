#!/usr/bin/env python3
"""Quantify the same-day-close lookahead in the RS studies (P10 sector-RS,
lone-wolf confirmatory, lone-wolf protocol).

Study method: 20-day returns use the SIGNAL DATE's daily close as endpoint.
For a signal fired on the first 4H bar of the day (09:30-13:30), the
signal-date daily close includes the 13:30-16:00 bar -- up to 6.5h of data
not yet known at signal time.

Strict point-in-time alternative:
  - second-bar signal (13:30 bar): signal-date daily close IS known
    (bar closes at 16:00 = market close) -> study method is correct.
  - first-bar signal (09:30 bar): endpoint not yet known -> stock leg uses
    the signal bar's own close; ETF legs use the previous trading day's
    daily close (exactly what the live overlay does for today's signals).

Impact: count classification flips for the lone-wolf filter and the P10
buckets; recompute blocked/allowed expectancy under strict PIT.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "research_audit", "data_leakage")
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402 - unmodified

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
SECTOR = {"QQQ": "XLK", "SMCI": "SOXX", "PLTR": "XLK", "ANET": "XLK",
          "SOFI": "XLF", "RKLB": "XLI", "ONDS": "XLK", "DRAM": "SOXX",
          "SPCX": "XLI", "ASTX": "XLK", "BBAI": "XLK", "NIO": "XLY",
          "HOOD": "XLF", "AMD": "SOXX"}
CACHE4H = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
CACHED = os.path.join(BASE, "pine_sector_rs_backtest", "cache")
COST = 0.0025
LOOKBACK = 20


def net_r(tr):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], COST)[2]


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


# ---- data ----
h4 = {}
for sym in WATCHLIST:
    df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
    h4[sym] = df
stock_d = {sym: daily_closes_4h(df) for sym, df in h4.items()}
etf_d = {}
for sym in ["SPY", "XLK", "SOXX", "XLF", "XLI", "XLY"]:
    df = pd.read_pickle(os.path.join(CACHED, f"d_{sym}.pkl"))
    s = df["Close"].copy()
    s.index = pd.to_datetime(s.index.tz_localize(None)
                             if s.index.tz is not None else s.index).normalize()
    etf_d[sym] = s.asfreq("1D").ffill().dropna()

# ---- canonical trades (unmodified engine) ----
trades = []
for sym in WATCHLIST:
    df = pb.add_pine_indicators(h4[sym])
    ts, _ = pb.gen_pine_trades(sym, df)
    trades.extend(ts)
trades.sort(key=lambda t: t["entry_time"])
print(f"trades: {len(trades)}")

n_first = n_second = 0
flips = []
study_blocked_r, strict_blocked_r = [], []
study_allowed_r, strict_allowed_r = [], []
p10_flips = 0
for tr in trades:
    sym = tr["symbol"]
    sig_ts = pd.Timestamp(tr["signal_time"]).tz_convert("America/New_York")
    sig_date = sig_ts.tz_localize(None).normalize()
    sec = SECTOR[sym]
    first_bar = (sig_ts.hour * 60 + sig_ts.minute) == 570
    n_first += first_bar
    n_second += (not first_bar)

    # study method
    srs = ret20(stock_d[sym], sig_date) - ret20(etf_d["SPY"], sig_date)
    secrs = ret20(etf_d[sec], sig_date) - ret20(etf_d["SPY"], sig_date)
    study_block = bool(srs > 0 and secrs <= 0)

    # strict PIT: for first-bar signals, shift the endpoint back
    if first_bar:
        # stock: replace endpoint close with the signal bar's close
        sd = stock_d[sym]
        pos = sd.index.searchsorted(sig_date, side="right") - 1
        sig_bar_close = float(h4[sym].loc[pd.Timestamp(tr["signal_time"])]["Close"])
        srs_s = (sig_bar_close / sd.iloc[pos - LOOKBACK] - 1.0) \
            - (etf_d["SPY"].iloc[etf_d["SPY"].index.searchsorted(sig_date, side="right") - 2]
               / etf_d["SPY"].iloc[etf_d["SPY"].index.searchsorted(sig_date, side="right") - 2 - LOOKBACK] - 1.0)
        # sector ETF & SPY: previous trading day's close as endpoint
        p = etf_d["SPY"].index.searchsorted(sig_date, side="right") - 1  # signal date pos
        def ret20_prev(series):
            pp = series.index.searchsorted(sig_date, side="right") - 2  # prev trading day
            if pp < LOOKBACK:
                return np.nan
            return series.iloc[pp] / series.iloc[pp - LOOKBACK] - 1.0
        secrs_s = ret20_prev(etf_d[sec]) - ret20_prev(etf_d["SPY"])
        # stock leg vs SPY at previous-day endpoint for the subtraction leg:
        # stock uses signal-bar endpoint, SPY leg must match endpoint for RS math;
        # strict RS = stock_ret20(signal-bar endpoint) - SPY_ret20(prev-day endpoint).
        # (mixed endpoints; documented; the defensible conservative variant.)
    else:
        srs_s, secrs_s = srs, secrs
    strict_block = bool(srs_s > 0 and secrs_s <= 0) \
        if not (pd.isna(srs_s) or pd.isna(secrs_s)) else False

    if study_block != strict_block:
        flips.append({"symbol": sym, "signal_time": tr["signal_time"],
                      "study_block": study_block, "strict_block": strict_block,
                      "stock_rs_study": round(float(srs), 4) if not pd.isna(srs) else None,
                      "sector_rs_study": round(float(secrs), 4) if not pd.isna(secrs) else None,
                      "stock_rs_strict": round(float(srs_s), 4) if not pd.isna(srs_s) else None,
                      "sector_rs_strict": round(float(secrs_s), 4) if not pd.isna(secrs_s) else None,
                      "net_r": round(net_r(tr), 4)})

    # P10 bucket flip (needs both legs; use study vs strict on both legs)
    def bucket(a, b):
        if pd.isna(a) or pd.isna(b):
            return None
        if a > 0 and b > 0:
            return "both_pos"
        if a > 0 and b <= 0:
            return "stock_lead"
        if a <= 0 and b > 0:
            return "sector_lead"
        return "both_neg"
    if bucket(srs, secrs) != bucket(srs_s, secrs_s):
        p10_flips += 1

    r = net_r(tr)
    (study_blocked_r if study_block else study_allowed_r).append(r)
    (strict_blocked_r if strict_block else strict_allowed_r).append(r)

n_study_block = len(study_blocked_r)
n_strict_block = len(strict_blocked_r)
res = {
    "n_trades": len(trades),
    "signals_on_first_4h_bar_pct": round(n_first / len(trades) * 100, 1),
    "signals_on_second_4h_bar_pct": round(n_second / len(trades) * 100, 1),
    "lonewolf_classification_flips": len(flips),
    "flip_details": flips,
    "p10_bucket_flips": p10_flips,
    "study_method": {
        "blocked_n": n_study_block,
        "blocked_expectancy_net_r": round(float(np.mean(study_blocked_r)), 4) if study_blocked_r else None,
        "allowed_n": len(study_allowed_r),
        "allowed_expectancy_net_r": round(float(np.mean(study_allowed_r)), 4),
    },
    "strict_pit": {
        "blocked_n": n_strict_block,
        "blocked_expectancy_net_r": round(float(np.mean(strict_blocked_r)), 4) if strict_blocked_r else None,
        "allowed_n": len(strict_allowed_r),
        "allowed_expectancy_net_r": round(float(np.mean(strict_allowed_r)), 4),
    },
}
print(json.dumps({k: v for k, v in res.items() if k != "flip_details"}, indent=1))
print(f"\nflips ({len(flips)}):")
for f in flips:
    print(f"  {f['symbol']} {f['signal_time'][:16]} study_block={f['study_block']} "
          f"strict_block={f['strict_block']} rs_study=({f['stock_rs_study']},{f['sector_rs_study']}) "
          f"rs_strict=({f['stock_rs_strict']},{f['sector_rs_strict']}) net_r={f['net_r']}")
with open(os.path.join(OUTDIR, "rs_leakage_quant.json"), "w") as fh:
    json.dump(res, fh, indent=1, default=str)
print(f"\nwrote {OUTDIR}/rs_leakage_quant.json")
