#!/usr/bin/env python3
"""P14 — Time effects study (2026-09-24).

Question: do structural timing effects (day of week, month, earnings
proximity, quarter-end, opex week) affect baseline trade expectancy?

Measurement study on CANONICAL 4H Hybrid baseline trades only (entries and
exits untouched). Null hypothesis: time effects are noise. With ~20 buckets,
one will look good by chance — a bucket is only interesting if the effect is
strong, persistent across years, AND explainable by a mechanism.

Buckets (pre-declared):
  dow       : entry weekday Mon..Fri
  month     : entry month 1..12 (thin months flagged, no claims)
  earnings  : entry within 5 calendar days BEFORE an earnings date
              ("pre"), within 5 calendar days AFTER ("post"), else "none".
              Earnings dates from yfinance (actual reported dates only,
              filtered to <= study end; cached to earnings_dates.json).
  qend      : entry in the last 5 business days of a calendar quarter vs rest
  opex      : entry in the Mon-Fri week containing the month's 3rd Friday
              vs rest
"""
import calendar
import datetime as dt
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_timefx_backtest")
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402  (canonical engine, unmodified)

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
COST = 0.0025  # 25 bps
STUDY_END = dt.date(2026, 9, 24)
EARN_CACHE = os.path.join(OUTDIR, "earnings_dates.json")


def load_earnings():
    """Actual earnings dates per symbol from yfinance; cached to disk."""
    if os.path.exists(EARN_CACHE):
        with open(EARN_CACHE) as f:
            return {k: [dt.date.fromisoformat(d) for d in v]
                    for k, v in json.load(f).items()}
    import yfinance as yf
    out = {}
    for sym in WATCHLIST:
        try:
            ed = yf.Ticker(sym).get_earnings_dates(limit=20)
            dates = sorted({pd.Timestamp(x).date() for x in ed.index
                            if pd.Timestamp(x).date() <= STUDY_END})
            out[sym] = [d.isoformat() for d in dates]
            print(f"  {sym}: {len(dates)} earnings dates", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  {sym}: earnings fetch failed ({e}); using []", flush=True)
            out[sym] = []
    with open(EARN_CACHE, "w") as f:
        json.dump(out, f)
    return {k: [dt.date.fromisoformat(d) for d in v]
            for k, v in out.items()}


def earnings_bucket(entry_date, dates):
    """pre = within 5 cal days before earnings; post = within 5 after."""
    for e in dates:
        delta = (entry_date - e).days
        if -5 <= delta < 0:
            return "pre"
        if 0 < delta <= 5:
            return "post"
        if delta == 0:
            return "earnings_day"
    return "none"


def quarter_end_business_days(year):
    """Set of dates: last 5 business days of each calendar quarter."""
    out = set()
    for qm in (3, 6, 9, 12):
        last = dt.date(year, qm, calendar.monthrange(year, qm)[1])
        bdays = pd.bdate_range(end=last, periods=5)
        out.update(d.date() for d in bdays)
    return out


def opex_weeks(year):
    """Set of dates: Mon-Fri of the week containing the 3rd Friday."""
    out = set()
    for m in range(1, 13):
        c = calendar.monthcalendar(year, m)
        fridays = [w[calendar.FRIDAY] for w in c if w[calendar.FRIDAY] != 0]
        third = dt.date(year, m, fridays[2])
        monday = third - dt.timedelta(days=4)
        out.update(monday + dt.timedelta(days=i) for i in range(5))
    return out


def net_r(tr):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], COST)[2]


def stats(rs):
    rs = np.asarray(rs, dtype=float)
    n = len(rs)
    if n == 0:
        return {"n": 0}
    return {"n": n, "exp_r": round(float(rs.mean()), 4),
            "win_rate": round(float((rs > 0).mean() * 100), 1)}


def main():
    earnings = load_earnings()
    qend_days = set()
    opex_days = set()
    for y in (2023, 2024, 2025, 2026):
        qend_days |= quarter_end_business_days(y)
        opex_days |= opex_weeks(y)

    all_trades = []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        tr, _ = pb.gen_pine_trades(sym, df)
        all_trades.extend(tr)
        print(f"  {sym}: {len(tr)} trades", flush=True)

    base_rs = [net_r(t) for t in all_trades]
    print(f"BASELINE CHECK: n={len(all_trades)} exp={np.mean(base_rs):.4f}R")

    rows = []
    for t in all_trades:
        ts = pd.Timestamp(t["signal_time"])
        d = ts.date()
        rows.append({
            "symbol": t["symbol"], "r": net_r(t), "year": ts.year,
            "dow": ts.strftime("%a"),
            "month": ts.month,
            "earn": earnings_bucket(d, earnings[t["symbol"]]),
            "qend": "qend" if d in qend_days else "rest",
            "opex": "opex_wk" if d in opex_days else "rest",
        })

    out = {"baseline_check": {"n": len(all_trades),
                              "exp_r_25bps": round(float(np.mean(base_rs)), 4),
                              "earnings_coverage": {
                                  s: len(v) for s, v in earnings.items()}},
           "buckets": {}, "persistence": {}}

    def bucketize(key, order):
        b = {}
        for name in order:
            b[name] = stats([x["r"] for x in rows if x[key] == name])
        return b

    out["buckets"]["dow"] = bucketize(
        "dow", ["Mon", "Tue", "Wed", "Thu", "Fri"])
    out["buckets"]["month"] = bucketize("month", list(range(1, 13)))
    out["buckets"]["earnings"] = bucketize(
        "earn", ["pre", "earnings_day", "post", "none"])
    out["buckets"]["qend"] = bucketize("qend", ["qend", "rest"])
    out["buckets"]["opex"] = bucketize("opex", ["opex_wk", "rest"])

    # persistence: cross-tab the headline-extreme buckets by year
    for dim, key, interesting in [
            ("dow", "dow", None), ("earnings", "earn", ["pre", "post"]),
            ("qend", "qend", ["qend"]), ("opex", "opex", ["opex_wk"])]:
        vals = interesting or sorted({x[key] for x in rows})
        tab = {}
        for v in vals:
            by_year = {}
            for y in (2023, 2024, 2025, 2026):
                by_year[str(y)] = stats(
                    [x["r"] for x in rows if x[key] == v and x["year"] == y])
            tab[str(v)] = by_year
        out["persistence"][dim] = tab

    # month persistence too (flag thin months)
    mtab = {}
    for m in range(1, 13):
        by_year = {}
        for y in (2023, 2024, 2025, 2026):
            by_year[str(y)] = stats(
                [x["r"] for x in rows if x["month"] == m and x["year"] == y])
        mtab[str(m)] = by_year
    out["persistence"]["month"] = mtab

    with open(os.path.join(OUTDIR, "timefx_results.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("wrote timefx_results.json")


if __name__ == "__main__":
    main()
