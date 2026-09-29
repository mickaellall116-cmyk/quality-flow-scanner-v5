#!/usr/bin/env python3
"""Lone-wolf CONFIRMATORY study (2026-09-25): structural effect or 20-day accident?

PREDECLARED FAMILY (no optimization, no extra variants):
  L15   : block when stockRS(15d)>0 and sectorRS(15d)<=0
  L20   : block when stockRS(20d)>0 and sectorRS(20d)<=0   (original, predeclared)
  L25   : block when stockRS(25d)>0 and sectorRS(25d)<=0
  CONT_REL: block when stockRS(20d)>0 and sectorRS(20d) < trailing-1y median of
            sectorRS(20d) at the signal date (point-in-time). One predeclared
            relative/continuous formulation of "sector not participating".

MAIN QUESTION: is "stock strength without sector participation" genuinely lower
quality? PASS requires the directional effect to hold across the family,
not just at 20d.

METHOD: canonical 4H Hybrid entries, 14-stock watchlist, Oct 2023-Sep 2026,
frozen Mode B exits, portfolio sim with admission hook (faithful copy of
pb.simulate_portfolio, same pattern as pine_lonewolf_backtest). pine_backtest
imported unmodified. New folder only. Research only.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_lonewolf_confirm")
CACHE4H = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
CACHED = os.path.join(BASE, "pine_sector_rs_backtest", "cache")
OUT = os.path.join(OUTDIR, "confirm_results.json")
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

SECTOR = {
    "QQQ": "XLK", "SMCI": "SOXX", "PLTR": "XLK", "ANET": "XLK", "SOFI": "XLF",
    "RKLB": "XLI", "ONDS": "XLK", "DRAM": "SOXX", "SPCX": "XLI", "ASTX": "XLK",
    "BBAI": "XLK", "NIO": "XLY", "HOOD": "XLF", "AMD": "SOXX",
}

COSTS = [0.0025, 0.005, 0.01]  # 25 / 50 / 100 bps


def net_r(tr, cost):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]


def daily_closes_4h(df4h):
    s = df4h["Close"].copy()
    s.index = s.index.tz_convert("America/New_York").tz_localize(None)
    return s.resample("1D").last().dropna()


def ret_n(series, date, n):
    """n-trading-day return ending at `date` (point-in-time)."""
    idx = series.index
    pos = idx.searchsorted(date, side="right") - 1
    if pos < n:
        return np.nan
    return series.iloc[pos] / series.iloc[pos - n] - 1.0


def simulate_with_admission(trades, closes, cost, risk_pct, admit):
    """Faithful copy of pb.simulate_portfolio with an admission hook."""
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


def dist_stats(trades, cost):
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


def variant_stats(name, admit, trades, closes, cost, flags, split_ts):
    port = simulate_with_admission(trades, closes, cost, pb.RISK_PCT, admit)
    taken = [tr for tr in trades if id(tr) in port["opened_ids"]]
    stats = dist_stats(taken, cost)
    stats["trades_taken"] = len(taken)
    stats["trades_generated"] = len(trades)
    stats["total_return_pct"] = round((port["final_equity"] / pb.START_EQUITY - 1) * 100, 2)
    stats["max_drawdown_pct"] = round(port["max_drawdown"] * 100, 2)
    stats["blocked_n"] = len(port["blocked"])

    btrs = [tr for tr, _ in port["blocked"]]
    brs = np.array([net_r(tr, cost) for tr in btrs]) if btrs else np.array([])
    stats["blocked_expectancy_net_r"] = round(float(brs.mean()), 4) if len(brs) else None
    stats["blocked_win_rate_pct"] = round(float((brs > 0).mean()) * 100, 1) if len(brs) else None

    by_sym = {}
    for tr in btrs:
        d = by_sym.setdefault(tr["symbol"], {"n": 0, "rs": []})
        d["n"] += 1
        d["rs"].append(net_r(tr, cost))
    stats["blocked_by_symbol"] = {
        s: {"n": v["n"], "expectancy_net_r": round(float(np.mean(v["rs"])), 4)}
        for s, v in sorted(by_sym.items())}

    yearly = {}
    for yr in sorted({t["entry_time"].year for t in trades}):
        yt = [t for t in taken if t["entry_time"].year == yr]
        if yt:
            yrs_ = np.array([net_r(t, cost) for t in yt])
            yearly[str(yr)] = {"n": len(yt),
                               "expectancy_net_r": round(float(yrs_.mean()), 4)}
    stats["yearly"] = yearly

    wf = {}
    for per, flt in (("train_le2024", lambda t: t["entry_time"] < split_ts),
                     ("test_ge2025", lambda t: t["entry_time"] >= split_ts)):
        pt = [t for t in taken if flt(t)]
        if pt:
            prs = np.array([net_r(t, cost) for t in pt])
            wf[per] = {"n": len(pt), "expectancy_net_r": round(float(prs.mean()), 4)}
    stats["walkforward"] = wf
    return stats


def main():
    # --- data ---
    stock_d, etf_d = {}, {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        stock_d[sym] = daily_closes_4h(df)
    for sym in ["SPY", "XLK", "SOXX", "XLF", "XLI", "XLY"]:
        df = pd.read_pickle(os.path.join(CACHED, f"d_{sym}.pkl"))
        s = df["Close"].copy()
        s.index = pd.to_datetime(s.index.tz_localize(None)
                                if s.index.tz is not None else s.index).normalize()
        etf_d[sym] = s.asfreq("1D").ffill().dropna()

    # canonical Hybrid trades (engine unmodified)
    closes, trades = {}, []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        closes[sym] = df["Close"]
        ts, _ = pb.gen_pine_trades(sym, df)
        trades.extend(ts)
    trades.sort(key=lambda t: t["entry_time"])
    print(f"canonical trades: {len(trades)}", flush=True)
    split_ts = pd.Timestamp("2025-01-01").tz_localize(trades[0]["entry_time"].tz)

    # --- predeclare the family: precompute flags per formulation ---
    def sig_date(tr):
        return pd.Timestamp(tr["signal_time"]).tz_convert(
            "America/New_York").tz_localize(None).normalize()

    flags = {}  # formulation -> {id(tr): block_bool}
    flag_detail = {}

    for L in (15, 20, 25):
        fl, detail = {}, {}
        for tr in trades:
            sym = tr["symbol"]
            d = sig_date(tr)
            srs = ret_n(stock_d[sym], d, L) - ret_n(etf_d["SPY"], d, L)
            secrs = ret_n(etf_d[SECTOR[sym]], d, L) - ret_n(etf_d["SPY"], d, L)
            if pd.isna(srs) or pd.isna(secrs):
                fl[id(tr)], detail[id(tr)] = False, (None, None)
            else:
                fl[id(tr)] = bool(srs > 0 and secrs <= 0)
                detail[id(tr)] = (round(float(srs), 4), round(float(secrs), 4))
        flags[f"L{L}"] = fl
        flag_detail[f"L{L}"] = detail
        print(f"L{L}: flagged={sum(fl.values())}", flush=True)

    # CONT_REL: stockRS(20)>0 AND sectorRS(20) < trailing-1y median of sectorRS(20)
    # Precompute the trailing-median series per sector ETF (point-in-time).
    sec_rs_series = {}
    for etf in ["XLK", "SOXX", "XLF", "XLI", "XLY"]:
        s = etf_d[etf]
        rs = s / s.shift(20) - 1.0 - (etf_d["SPY"] / etf_d["SPY"].shift(20) - 1.0)
        sec_rs_series[etf] = rs.rolling(252, min_periods=126).median().shift(1)

    fl, detail = {}, {}
    for tr in trades:
        sym = tr["symbol"]
        etf = SECTOR[sym]
        d = sig_date(tr)
        srs = ret_n(stock_d[sym], d, 20) - ret_n(etf_d["SPY"], d, 20)
        secrs = ret_n(etf_d[etf], d, 20) - ret_n(etf_d["SPY"], d, 20)
        med = sec_rs_series[etf].get(d, np.nan) if d in sec_rs_series[etf].index else np.nan
        if pd.isna(srs) or pd.isna(secrs) or pd.isna(med):
            fl[id(tr)], detail[id(tr)] = False, (None, None)
        else:
            fl[id(tr)] = bool(srs > 0 and secrs < med)
            detail[id(tr)] = (round(float(srs), 4), round(float(secrs), 4))
    flags["CONT_REL"] = fl
    flag_detail["CONT_REL"] = detail
    print(f"CONT_REL: flagged={sum(fl.values())}", flush=True)

    # --- run: control + 4 formulations x 3 costs ---
    results = {
        "hypothesis": "stock strength without sector participation is lower quality",
        "family": ["L15", "L20", "L25", "CONT_REL"],
        "sector_mapping": SECTOR,
        "variants": {},
    }

    def admit_all(tr):
        return True, ""

    for cost in COSTS:
        bps = int(cost * 10000)
        results["variants"][f"CONTROL@{bps}bps"] = variant_stats(
            "CONTROL", admit_all, trades, closes, cost, None, split_ts)
        print(f"CONTROL@{bps}bps done", flush=True)

    for fam in ("L15", "L20", "L25", "CONT_REL"):
        fl = flags[fam]

        def admit(tr, _fl=fl):
            return (False, "lone_wolf") if _fl[id(tr)] else (True, "")

        for cost in COSTS:
            bps = int(cost * 10000)
            key = f"{fam}@{bps}bps"
            results["variants"][key] = variant_stats(
                fam, admit, trades, closes, cost, None, split_ts)
            print(f"{key} done", flush=True)

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
