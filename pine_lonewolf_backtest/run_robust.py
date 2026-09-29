#!/usr/bin/env python3
"""Lone-wolf robustness: cost stress (50/100 bps) + RS-lookback perturbation
(10/40 trading days). Same engine, same P10 sector mapping, admission rule
unchanged. Pre-declared robustness points only -- not optimization."""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
sys.path.insert(0, os.path.join(BASE, "pine_lonewolf_backtest"))
sys.path.insert(0, BASE)
import run_lonewolf as lw  # noqa: E402

CACHE4H = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
CACHED = os.path.join(BASE, "pine_sector_rs_backtest", "cache")


def load_all():
    stock_d = {}
    for sym in lw.WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        stock_d[sym] = lw.daily_closes_4h(df)
    etf_d = {}
    for sym in ["SPY", "XLK", "SOXX", "XLF", "XLI", "XLY"]:
        df = pd.read_pickle(os.path.join(CACHED, f"d_{sym}.pkl"))
        s = df["Close"].copy()
        s.index = pd.to_datetime(s.index.tz_localize(None)
                                 if s.index.tz is not None else s.index).normalize()
        etf_d[sym] = s.asfreq("1D").ffill().dropna()
    data, closes, trades = {}, {}, []
    for sym in lw.WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        df = lw.pb.add_pine_indicators(df)
        data[sym] = df
        closes[sym] = df["Close"]
        ts, _ = lw.pb.gen_pine_trades(sym, df)
        trades.extend(ts)
    trades.sort(key=lambda t: t["entry_time"])
    return stock_d, etf_d, closes, trades


def main():
    stock_d, etf_d, closes, trades = load_all()

    def rs_flags():
        flags = {}
        for tr in trades:
            sym = tr["symbol"]
            sig_date = pd.Timestamp(tr["signal_time"]).tz_convert(
                "America/New_York").tz_localize(None).normalize()
            sec = lw.SECTOR[sym]
            srs = lw.ret20(stock_d[sym], sig_date) - lw.ret20(etf_d["SPY"], sig_date)
            secrs = lw.ret20(etf_d[sec], sig_date) - lw.ret20(etf_d["SPY"], sig_date)
            if pd.isna(srs) or pd.isna(secrs):
                flags[id(tr)] = False
            else:
                flags[id(tr)] = bool(srs > 0 and secrs <= 0)
        return flags

    combos = [
        ("lookback20_cost50", 20, 0.0050),
        ("lookback20_cost100", 20, 0.0100),
        ("lookback10_cost25", 10, 0.0025),
        ("lookback40_cost25", 40, 0.0025),
    ]
    out = {}
    for label, lb, cost in combos:
        lw.LOOKBACK = lb
        lw.COST = cost
        flags = rs_flags()
        n_lw = sum(flags.values())

        def admit_all(tr):
            return True, ""

        def admit_no_lw(tr):
            return (False, "lone_wolf") if flags[id(tr)] else (True, "")

        row = {"lone_wolf_flagged": n_lw}
        for name, admit in [("CONTROL", admit_all), ("NO_LONE_WOLF", admit_no_lw)]:
            port = lw.simulate_with_admission(trades, closes, cost, lw.pb.RISK_PCT, admit)
            taken = [tr for tr in trades if id(tr) in port["opened_ids"]]
            stats = lw.dist_stats(taken, cost)
            stats["trades_taken"] = len(taken)
            stats["total_return_pct"] = round(
                (port["final_equity"] / lw.pb.START_EQUITY - 1) * 100, 2)
            stats["max_drawdown_pct"] = round(port["max_drawdown"] * 100, 2)
            row[name] = stats
        row["delta_exp_r"] = round(
            row["NO_LONE_WOLF"]["expectancy_net_r"] - row["CONTROL"]["expectancy_net_r"], 4)
        out[label] = row
        print(f"{label}: CONTROL exp={row['CONTROL']['expectancy_net_r']}R "
              f"n={row['CONTROL']['n']} | NO_LONE_WOLF exp={row['NO_LONE_WOLF']['expectancy_net_r']}R "
              f"n={row['NO_LONE_WOLF']['n']} | delta={row['delta_exp_r']}R "
              f"dd_ctrl={row['CONTROL']['max_drawdown_pct']}% "
              f"dd_nlw={row['NO_LONE_WOLF']['max_drawdown_pct']}%", flush=True)

    with open(os.path.join(lw.OUTDIR, "lonewolf_robustness.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print("wrote lonewolf_robustness.json", flush=True)


if __name__ == "__main__":
    main()
