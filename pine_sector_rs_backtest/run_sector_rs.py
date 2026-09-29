#!/usr/bin/env python3
"""Priority 10 — Sector-relative strength (2026-09-24).

Question (pre-registered): is a setup stronger when BOTH stock-level and
sector-level relative strength agree (vs SPY)?

METHOD (declared before looking at results):
- Baseline: canonical 4H Hybrid trades, 14-stock watchlist, 4H bars,
  Oct 2023-Sep 2026, frozen Mode B exits, 25bps costs. Engine imported
  unmodified; MEASUREMENT study — no filter built or proposed.
- At each trade's signal date (point-in-time), compute 20-trading-day
  returns on DAILY bars (4H ETF history only reaches ~Oct 2024, so daily
  is used for everything to keep the window whole):
    stockRS  = stock_ret20  - SPY_ret20
    sectorRS = sectorETF_ret20 - SPY_ret20
- Sector ETF mapping (pre-declared, documented in README):
    QQQ->XLK  SMCI->SOXX  PLTR->XLK  ANET->XLK  SOFI->XLF  RKLB->XLI
    ONDS->XLK DRAM->SOXX SPCX->XLI  ASTX->XLK  BBAI->XLK  NIO->XLY
    HOOD->XLF AMD->SOXX
- Buckets (pre-declared):
    both_pos    : stockRS > 0 and sectorRS > 0   (agreement, both strong)
    stock_lead  : stockRS > 0 and sectorRS <= 0  (stock leading its sector)
    sector_lead : stockRS <= 0 and sectorRS > 0  (sector strong, stock lagging)
    both_neg    : stockRS <= 0 and sectorRS <= 0 (agreement, both weak)
- Per bucket: n, expectancy @25bps, win rate, PF.
- Incremental test (the real question): does sector agreement add anything
  BEYOND stock-level RS?  Within stockRS>0, compare sectorRS>0 vs <=0;
  within stockRS<=0, same split.
- Persistence: cross-tab the most interesting split by year.
- Verdict: agreement bucket clearly better across years -> MAYBE with a
  future filter direction; flat -> NO.

NOTE: independent of the failed Pine/scanner agreement study — that was
about indicator agreement, this is about price relative strength.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_sector_rs_backtest")
CACHE4H = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
CACHED = os.path.join(OUTDIR, "cache")
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

# pre-declared sector ETF mapping
SECTOR = {
    "QQQ": "XLK",   # Nasdaq-100; XLK is the tech-sector proxy
    "SMCI": "SOXX", "PLTR": "XLK", "ANET": "XLK", "SOFI": "XLF",
    "RKLB": "XLI",  # aerospace -> industrials
    "ONDS": "XLK", "DRAM": "SOXX",
    "SPCX": "XLI",  # space thematic ETF -> industrials
    "ASTX": "XLK",  # 2x ASTS; closest broad sector is tech
    "BBAI": "XLK", "NIO": "XLY",  # EV -> consumer discretionary
    "HOOD": "XLF", "AMD": "SOXX",
}

COST = 0.0025
LOOKBACK = 20  # trading days


def net_r(tr, cost=COST):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]


def bucket_stats(trades):
    if not trades:
        return {"n": 0}
    rs = np.array([net_r(t) for t in trades])
    wins = rs[rs > 0]
    losses = rs[rs <= 0]
    gw, gl = wins.sum(), -losses.sum()
    return {
        "n": len(trades),
        "expectancy_net_r": round(float(rs.mean()), 4),
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1),
        "profit_factor": round(float(gw / gl), 2) if gl > 0 else None,
    }


def daily_closes_4h(df4h):
    """Resample 4H bars to daily closes (tz-naive date index)."""
    s = df4h["Close"].copy()
    s.index = s.index.tz_convert("America/New_York").tz_localize(None)
    return s.resample("1D").last().dropna()


def ret20(series, date):
    """20-trading-day return ending at `date` (point-in-time)."""
    idx = series.index
    pos = idx.searchsorted(date, side="right") - 1
    if pos < LOOKBACK:
        return np.nan
    return series.iloc[pos] / series.iloc[pos - LOOKBACK] - 1.0


def main():
    os.makedirs(OUTDIR, exist_ok=True)

    # stock daily closes from 4H cache
    stock_d = {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        stock_d[sym] = daily_closes_4h(df)

    # ETF daily closes (downloaded)
    etf_d = {}
    for sym in ["SPY", "XLK", "SOXX", "XLF", "XLI", "XLY"]:
        df = pd.read_pickle(os.path.join(CACHED, f"d_{sym}.pkl"))
        s = df["Close"].copy()
        s.index = pd.to_datetime(s.index.tz_localize(None)
                                 if s.index.tz is not None else s.index).normalize()
        etf_d[sym] = s.asfreq("1D").ffill().dropna()

    # baseline trades (canonical engine, unmodified)
    trades = []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        tr, _ = pb.gen_pine_trades(sym, df)
        trades.extend(tr)
    trades.sort(key=lambda t: t["entry_time"])
    print(f"baseline trades: {len(trades)}", flush=True)

    rows = []
    for t in trades:
        sym = t["symbol"]
        sig_date = pd.Timestamp(t["signal_time"]).tz_convert(
            "America/New_York").tz_localize(None).normalize()
        sec = SECTOR[sym]
        srs = ret20(stock_d[sym], sig_date) - ret20(etf_d["SPY"], sig_date)
        secrs = ret20(etf_d[sec], sig_date) - ret20(etf_d["SPY"], sig_date)
        rows.append({
            "symbol": sym, "sector_etf": sec,
            "signal_time": t["signal_time"],
            "year": str(pd.Timestamp(t["signal_time"]).year),
            "r": net_r(t),
            "stock_rs": float(srs), "sector_rs": float(secrs),
        })
    m = pd.DataFrame(rows)
    bad = m[["stock_rs", "sector_rs"]].isna().any(axis=1).sum()
    print(f"rows with NaN RS (dropped from buckets): {bad}", flush=True)
    m = m.dropna(subset=["stock_rs", "sector_rs"]).reset_index(drop=True)
    tr2 = [trades[i] for i in m.index]

    def lab(r):
        sp, sr = r["stock_rs"] > 0, r["sector_rs"] > 0
        if sp and sr:
            return "both_pos (agree strong)"
        if sp and not sr:
            return "stock_lead (stock strong, sector weak)"
        if not sp and sr:
            return "sector_lead (sector strong, stock weak)"
        return "both_neg (agree weak)"

    m["bucket"] = m.apply(lab, axis=1)
    labels = ["both_pos (agree strong)", "stock_lead (stock strong, sector weak)",
              "sector_lead (sector strong, stock weak)", "both_neg (agree weak)"]

    results = {
        "n_trades": len(tr2),
        "baseline": bucket_stats(tr2),
        "sector_mapping": SECTOR,
        "lookback_trading_days": LOOKBACK,
        "buckets": {},
    }
    print("\n== agreement buckets ==", flush=True)
    for l in labels:
        idx = m[m["bucket"] == l].index.tolist()
        b = bucket_stats([tr2[i] for i in idx])
        b["mean_stock_rs_pct"] = round(float(m.loc[idx, "stock_rs"].mean()) * 100, 2)
        b["mean_sector_rs_pct"] = round(float(m.loc[idx, "sector_rs"].mean()) * 100, 2)
        results["buckets"][l] = b
        print(f"  {l}: n={b['n']} exp={b['expectancy_net_r']}R "
              f"win={b['win_rate_pct']}% pf={b['profit_factor']}", flush=True)

    # incremental test: sector agreement conditional on stock RS sign
    print("\n== incremental: sector agreement beyond stock RS ==", flush=True)
    inc = {}
    for cond, name in [(m["stock_rs"] > 0, "given stockRS>0"),
                       (m["stock_rs"] <= 0, "given stockRS<=0")]:
        sub = m[cond]
        for agree, aname in [(sub["sector_rs"] > 0, "sector agrees>0"),
                             (sub["sector_rs"] <= 0, "sector disagrees<=0")]:
            idx = agree[agree].index.tolist()
            b = bucket_stats([tr2[i] for i in idx])
            inc[f"{name} | {aname}"] = b
            print(f"  {name} | {aname}: n={b['n']} exp={b['expectancy_net_r']}R "
                  f"win={b['win_rate_pct']}% pf={b['profit_factor']}", flush=True)
    results["incremental_sector_agreement"] = inc

    # persistence: most interesting split = both_pos vs stock_lead by year
    print("\n== persistence: both_pos vs stock_lead, by year ==", flush=True)
    yr = {}
    for y, grp in m.groupby("year"):
        out = {}
        for l, k in [("both_pos (agree strong)", "both_pos"),
                     ("stock_lead (stock strong, sector weak)", "stock_lead")]:
            g = grp[grp["bucket"] == l]["r"]
            out[k] = {"n": int(len(g)),
                      "exp_r": round(float(g.mean()), 4) if len(g) else None}
        yr[y] = out
        print(f"  {y}: both_pos n={out['both_pos']['n']} {out['both_pos']['exp_r']}R | "
              f"stock_lead n={out['stock_lead']['n']} {out['stock_lead']['exp_r']}R",
              flush=True)
    results["persistence_bothpos_vs_stocklead_by_year"] = yr

    # sector-ETF-level summary (which sectors drove what)
    print("\n== by sector ETF ==", flush=True)
    sec_sum = {}
    for sec, grp in m.groupby("sector_etf"):
        b = bucket_stats([tr2[i] for i in grp.index])
        sec_sum[sec] = b
        print(f"  {sec}: n={b['n']} exp={b['expectancy_net_r']}R "
              f"win={b['win_rate_pct']}% pf={b['profit_factor']}", flush=True)
    results["by_sector_etf"] = sec_sum

    out = os.path.join(OUTDIR, "sector_rs_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
