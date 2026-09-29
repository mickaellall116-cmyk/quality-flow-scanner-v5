#!/usr/bin/env python3
"""Lone-wolf confirmatory test (pre-registered follow-up of P10 sector-RS, 2026-09-24).

HYPOTHESIS (pre-registered): skipping entries where stock 20-day RS vs SPY > 0
AND sector ETF 20-day RS vs SPY <= 0 (lone-wolf breakouts) improves expectancy,
because breakouts need sector tailwinds -- a stock fighting its sector is
swimming upstream.

P10 EVIDENCE: both_pos (agree strong) +0.464R (n=124) vs stock_lead -0.018R
(n=83); persistent all 3 years; 13/14 names.

METHOD: canonical 4H Hybrid entries, 14-stock watchlist, 4H, Oct 2023-Sep 2026,
frozen Mode B exits, 25bps costs, full portfolio sim. P10's exact sector-ETF
mapping and RS definitions reused verbatim (daily bars, 20-trading-day
returns, point-in-time at the signal bar). No re-tuning.

Variants (admission rule only; entries/exits identical):
  CONTROL      take all signals (baseline)
  NO_LONE_WOLF skip entries where stockRS > 0 and sectorRS <= 0

Research only. V5.4, Mode B, alerts, grades, market gate, AI Observer untouched.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_lonewolf_backtest")
CACHE4H = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
CACHED = os.path.join(BASE, "pine_sector_rs_backtest", "cache")
OUT = os.path.join(OUTDIR, "lonewolf_results.json")
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

# P10's exact sector mapping (pre-declared there; reused verbatim, no tuning)
SECTOR = {
    "QQQ": "XLK", "SMCI": "SOXX", "PLTR": "XLK", "ANET": "XLK", "SOFI": "XLF",
    "RKLB": "XLI", "ONDS": "XLK", "DRAM": "SOXX", "SPCX": "XLI", "ASTX": "XLK",
    "BBAI": "XLK", "NIO": "XLY", "HOOD": "XLF", "AMD": "SOXX",
}

COST = 0.0025  # 25 bps, mandate benchmark
LOOKBACK = 20  # trading days


def net_r(tr, cost=COST):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]


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


def simulate_with_admission(trades, closes, cost, risk_pct, admit):
    """Faithful copy of pb.simulate_portfolio with an admission hook.

    admit(tr) -> (ok: bool, reason: str). RS flags are precomputed per-trade
    from the SIGNAL bar (point-in-time, no lookahead).
    """
    events = []
    for t in trades:
        events.append((t["exit_time"], 0, t))
        events.append((t["entry_time"], 1, t))
    events.sort(key=lambda e: (e[0], e[1]))
    realized = pb.START_EQUITY
    open_pos, by_id = [], {}
    skipped_cap_count = skipped_cap_risk = 0
    blocked = []
    opened_ids = set()
    peak, max_dd = realized, 0.0
    curve, prev_t = [], None
    open_time = total_time = pd.Timedelta(0)

    def mark(sym, t):
        s = closes[sym]
        idx = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[idx]) if idx >= 0 else float(s.iloc[0])

    def marked_equity(t):
        unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
                      for p, tr in ((p, p["trade"]) for p in open_pos))
        return realized + unreal

    for t, kind, tr in events:
        if prev_t is not None and t > prev_t:
            dt = t - prev_t
            total_time += dt
            if open_pos:
                open_time += dt
        prev_t = t
        if kind == 1:
            eq = marked_equity(t)
            open_risk = sum(p["risk_dollars"] for p in open_pos) / eq if eq > 0 else 1
            if len(open_pos) >= pb.MAX_CONCURRENT:
                skipped_cap_count += 1
                continue
            if open_risk + risk_pct > pb.MAX_PORTFOLIO_RISK + 1e-9:
                skipped_cap_risk += 1
                continue
            ok, reason = admit(tr)
            if not ok:
                blocked.append((tr, reason))
                continue
            risk_dollars = risk_pct * eq
            risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
            open_pos.append({"trade": tr, "risk_dollars": risk_dollars,
                             "size": risk_dollars / risk_frac,
                             "risk_frac": risk_frac})
            by_id[id(tr)] = open_pos[-1]
            opened_ids.add(id(tr))
        else:
            pos = by_id.pop(id(tr), None)
            if pos is None:
                continue
            _, _, net_r_, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
            realized += pos["risk_dollars"] * net_r_
            open_pos.remove(pos)
        eq = marked_equity(t)
        curve.append((t, eq, realized, len(open_pos)))
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    exposure = float(open_time / total_time) if total_time > pd.Timedelta(0) else 0.0
    return {"final_equity": realized, "max_drawdown": max_dd,
            "skipped_cap_count": skipped_cap_count,
            "skipped_cap_risk": skipped_cap_risk,
            "exposure": exposure, "blocked": blocked, "opened_ids": opened_ids}


def dist_stats(trades, cost=COST):
    if not trades:
        return {"n": 0}
    rs = np.array([net_r(t, cost) for t in trades])
    wins = rs[rs > 0]
    losses = rs[rs <= 0]
    gw, gl = wins.sum(), -losses.sum()
    return {
        "n": len(trades),
        "expectancy_net_r": round(float(rs.mean()), 4),
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1),
        "profit_factor": round(float(gw / gl), 2) if gl > 0 else None,
    }


def main():
    # stock daily closes from 4H cache
    stock_d = {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        stock_d[sym] = daily_closes_4h(df)

    # ETF daily closes (P10's cache, reused)
    etf_d = {}
    for sym in ["SPY", "XLK", "SOXX", "XLF", "XLI", "XLY"]:
        df = pd.read_pickle(os.path.join(CACHED, f"d_{sym}.pkl"))
        s = df["Close"].copy()
        s.index = pd.to_datetime(s.index.tz_localize(None)
                                 if s.index.tz is not None else s.index).normalize()
        etf_d[sym] = s.asfreq("1D").ffill().dropna()

    # canonical Hybrid trades (engine unmodified)
    data, closes = {}, {}
    trades = []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        data[sym] = df
        closes[sym] = df["Close"]
        ts, _ = pb.gen_pine_trades(sym, df)
        trades.extend(ts)
    trades.sort(key=lambda t: t["entry_time"])
    print(f"canonical trades: {len(trades)}", flush=True)

    # precompute per-trade RS flags at the SIGNAL bar (point-in-time, no lookahead)
    flags = {}
    n_nan = 0
    for tr in trades:
        sym = tr["symbol"]
        sig_date = pd.Timestamp(tr["signal_time"]).tz_convert(
            "America/New_York").tz_localize(None).normalize()
        sec = SECTOR[sym]
        srs = ret20(stock_d[sym], sig_date) - ret20(etf_d["SPY"], sig_date)
        secrs = ret20(etf_d[sec], sig_date) - ret20(etf_d["SPY"], sig_date)
        if pd.isna(srs) or pd.isna(secrs):
            n_nan += 1
            flags[id(tr)] = {"lone_wolf": False, "stock_rs": None, "sector_rs": None}
        else:
            flags[id(tr)] = {
                "lone_wolf": bool(srs > 0 and secrs <= 0),
                "stock_rs": round(float(srs), 4),
                "sector_rs": round(float(secrs), 4),
            }
    print(f"trades with NaN RS (treated as non-lone-wolf): {n_nan}", flush=True)

    # sanity: lone-wolf count vs P10's stock_lead bucket
    n_lw = sum(1 for f in flags.values() if f["lone_wolf"])
    print(f"lone-wolf flagged trades: {n_lw} (P10 stock_lead n=83)", flush=True)

    def admit_all(tr):
        return True, ""

    def admit_no_lone_wolf(tr):
        if flags[id(tr)]["lone_wolf"]:
            return False, "lone_wolf"
        return True, ""

    results = {
        "hypothesis": "skipping lone-wolf entries (stockRS>0, sectorRS<=0) improves expectancy",
        "sector_mapping": SECTOR,
        "lookback_trading_days": LOOKBACK,
        "cost_bps": 25,
        "variants": {},
    }

    for name, admit in [("CONTROL", admit_all), ("NO_LONE_WOLF", admit_no_lone_wolf)]:
        port = simulate_with_admission(trades, closes, COST, pb.RISK_PCT, admit)
        taken = [tr for tr in trades if id(tr) in port["opened_ids"]]
        stats = dist_stats(taken)
        stats["trades_taken"] = len(taken)
        stats["trades_generated"] = len(trades)
        stats["total_return_pct"] = round(
            (port["final_equity"] / pb.START_EQUITY - 1) * 100, 2)
        stats["max_drawdown_pct"] = round(port["max_drawdown"] * 100, 2)
        stats["market_exposure_pct"] = round(port["exposure"] * 100, 1)
        stats["skipped_cap_count"] = port["skipped_cap_count"]
        stats["skipped_cap_risk"] = port["skipped_cap_risk"]
        stats["blocked_n"] = len(port["blocked"])

        # opportunity cost: what did the filter block?
        btrs = [tr for tr, _ in port["blocked"]]
        brs = np.array([net_r(tr) for tr in btrs]) if btrs else np.array([])
        stats["blocked_expectancy_net_r"] = (
            round(float(brs.mean()), 4) if len(brs) else None)
        stats["blocked_win_rate_pct"] = (
            round(float((brs > 0).mean()) * 100, 1) if len(brs) else None)
        stats["blocked_total_r"] = (
            round(float(brs.sum()), 2) if len(brs) else None)

        # symbol spread of blocked trades (concentration check)
        by_sym = {}
        for tr in btrs:
            d = by_sym.setdefault(tr["symbol"], {"n": 0, "rs": []})
            d["n"] += 1
            d["rs"].append(net_r(tr))
        stats["blocked_by_symbol"] = {
            s: {"n": v["n"], "expectancy_net_r": round(float(np.mean(v["rs"])), 4)}
            for s, v in sorted(by_sym.items())}

        # yearly split (entry year)
        yearly = {}
        for yr in sorted({t["entry_time"].year for t in trades}):
            yt = [t for t in taken if t["entry_time"].year == yr]
            if yt:
                yrs_ = np.array([net_r(t) for t in yt])
                yearly[str(yr)] = {"n": len(yt),
                                   "expectancy_net_r": round(float(yrs_.mean()), 4)}
        stats["yearly"] = yearly

        # walk-forward: train <=2024 / test >=2025
        wf = {}
        split = pd.Timestamp("2025-01-01").tz_localize(trades[0]["entry_time"].tz)
        for per, flt in (("train_le2024", lambda t: t["entry_time"] < split),
                         ("test_ge2025", lambda t: t["entry_time"] >= split)):
            pt = [t for t in taken if flt(t)]
            if pt:
                prs = np.array([net_r(t) for t in pt])
                wf[per] = {"n": len(pt),
                           "expectancy_net_r": round(float(prs.mean()), 4)}
        stats["walkforward"] = wf

        results["variants"][name] = stats
        print(f"{name}: taken={stats['trades_taken']} exp={stats['expectancy_net_r']}R "
              f"win={stats['win_rate_pct']}% pf={stats['profit_factor']} "
              f"blocked={stats['blocked_n']} blocked_exp={stats['blocked_expectancy_net_r']} "
              f"ret={stats['total_return_pct']}% dd={stats['max_drawdown_pct']}%",
              flush=True)

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
