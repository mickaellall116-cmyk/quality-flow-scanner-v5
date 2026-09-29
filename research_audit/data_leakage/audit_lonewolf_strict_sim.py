#!/usr/bin/env python3
"""Strict point-in-time lone-wolf variant through the REAL portfolio sim.

Mirrors pine_lonewolf_backtest/run_lonewolf.py::simulate_with_admission,
but the admission flag uses strict point-in-time RS (endpoint = last
completed daily bar at signal time, same convention as the live overlay).
Compares CONTROL / NO_LONE_WOLF(study method) / NO_LONE_WOLF(strict PIT).
"""
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "research_audit", "data_leakage")
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402 - unmodified

spec = importlib.util.spec_from_file_location(
    "rl", os.path.join(BASE, "pine_lonewolf_backtest", "run_lonewolf.py"))
rl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rl)

WATCHLIST = rl.WATCHLIST
SECTOR = rl.SECTOR
LOOKBACK = 20
COST = 0.0025


def net_r(tr):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], COST)[2]


# ---- data (same caches as run_lonewolf) ----
stock_d, h4 = {}, {}
for sym in WATCHLIST:
    df = pd.read_pickle(os.path.join(rl.CACHE4H, f"h4_{sym}.pkl"))
    h4[sym] = df
    stock_d[sym] = rl.daily_closes_4h(df)
etf_d = {}
for sym in ["SPY", "XLK", "SOXX", "XLF", "XLI", "XLY"]:
    df = pd.read_pickle(os.path.join(rl.CACHED, f"d_{sym}.pkl"))
    s = df["Close"].copy()
    s.index = pd.to_datetime(s.index.tz_localize(None)
                             if s.index.tz is not None else s.index).normalize()
    etf_d[sym] = s.asfreq("1D").ffill().dropna()

# ---- canonical trades (same as run_lonewolf) ----
data, closes, trades = {}, {}, []
for sym in WATCHLIST:
    df = pb.add_pine_indicators(h4[sym])
    data[sym] = df
    closes[sym] = df["Close"]
    ts, _ = pb.gen_pine_trades(sym, df)
    trades.extend(ts)
trades.sort(key=lambda t: t["entry_time"])

flags = {}
for tr in trades:
    sym = tr["symbol"]
    sig_ts = pd.Timestamp(tr["signal_time"]).tz_convert("America/New_York")
    sig_date = sig_ts.tz_localize(None).normalize()
    sec = SECTOR[sym]
    first_bar = (sig_ts.hour * 60 + sig_ts.minute) == 570
    # study method
    srs = rl.ret20(stock_d[sym], sig_date) - rl.ret20(etf_d["SPY"], sig_date)
    secrs = rl.ret20(etf_d[sec], sig_date) - rl.ret20(etf_d["SPY"], sig_date)
    study_lw = bool(srs > 0 and secrs <= 0)
    # strict PIT
    if first_bar:
        sd = stock_d[sym]
        pos = sd.index.searchsorted(sig_date, side="right") - 1
        sig_bar_close = float(h4[sym].loc[pd.Timestamp(tr["signal_time"])]["Close"])
        if pos < LOOKBACK:
            strict_lw = False
        else:
            sp = etf_d["SPY"].index.searchsorted(sig_date, side="right") - 2
            srs_s = (sig_bar_close / sd.iloc[pos - LOOKBACK] - 1.0) - \
                    (etf_d["SPY"].iloc[sp] / etf_d["SPY"].iloc[sp - LOOKBACK] - 1.0)
            secrs_s = rl.ret20(etf_d[sec], sig_date - pd.Timedelta(days=1)) - \
                      rl.ret20(etf_d["SPY"], sig_date - pd.Timedelta(days=1))
            strict_lw = bool(srs_s > 0 and secrs_s <= 0)
    else:
        strict_lw = study_lw
    flags[id(tr)] = {"study": study_lw, "strict": strict_lw}

variants = {
    "CONTROL": lambda tr: True,
    "NO_LONE_WOLF_study": lambda tr: not flags[id(tr)]["study"],
    "NO_LONE_WOLF_strict": lambda tr: not flags[id(tr)]["strict"],
}
out = {}
for name, ok in variants.items():
    def admit(tr, ok=ok):
        return (ok(tr), "")
    port = rl.simulate_with_admission(trades, closes, COST, pb.RISK_PCT, admit)
    taken = [tr for tr in trades if id(tr) in port["opened_ids"]]
    rs = np.array([net_r(t) for t in taken])
    blocked = [tr for tr, r_ in port["blocked"]]
    brs = np.array([net_r(t) for t in blocked]) if blocked else np.array([])
    out[name] = {
        "trades_taken": len(taken),
        "expectancy_net_r": round(float(rs.mean()), 4) if len(rs) else None,
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1) if len(rs) else None,
        "blocked_n": len(blocked),
        "blocked_expectancy_net_r": round(float(brs.mean()), 4) if len(brs) else None,
        "total_return_pct": round((port["final_equity"] / pb.START_EQUITY - 1) * 100, 2),
        "max_drawdown_pct": round(port["max_drawdown"] * 100, 2),
    }
    print(f"{name}: taken={out[name]['trades_taken']} exp={out[name]['expectancy_net_r']}R "
          f"blocked={out[name]['blocked_n']} blocked_exp={out[name]['blocked_expectancy_net_r']}")
with open(os.path.join(OUTDIR, "lonewolf_strict_sim.json"), "w") as f:
    json.dump(out, f, indent=1, default=str)
print(f"\nwrote {OUTDIR}/lonewolf_strict_sim.json")
