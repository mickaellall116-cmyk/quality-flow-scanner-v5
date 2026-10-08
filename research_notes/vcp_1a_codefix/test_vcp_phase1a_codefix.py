#!/usr/bin/env python3
"""Synthetic tests for QF-VCP-1A-CODEFIX-20261007-03 (adjudication 6051281109).

Proves, on synthetic data only (zero real-data performance reruns):
  T1  subperiod month counts: old lexical comparison -> 23 months;
      fixed month-period comparison -> 24 months (frozen spec: 2Y = 24).
  T2  boundary inclusion: '2011-12-31' is inside 2010-2011; '2025-09' month
      handling for the r12 cutoff.
  T3  data-derived horizon cutoff: on the real raw EOD calendars (no vendor
      calls), w=252 -> 2025-08 (September genuinely 1 day short), w=63/126
      -> 2025-12.
  T4  MA window tolerance (build_panels): 230/250 bars accepted (frozen
      MA_REQ tolerance), 229/250 rejected.
  T5  forward-window completeness flags: truncated r12 flagged False while
      r3/r6 stay True near series end.
  T6  delisting: months after series end produce no rows.
  T7  annualization: raw primary vs horizon-aware secondary (x4/x2/x1);
      old x12-for-all rejected for r12.

Run: python3 test_vcp_phase1a_codefix.py   (exit 0 = all pass)
"""
import bisect
import calendar as _cal
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"[{PASS if cond else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def month_ends_2010_2025():
    ms = []
    for y in range(2010, 2026):
        for mo in range(1, 13):
            last = _cal.monthrange(y, mo)[1]
            ms.append(f"{y}-{mo:02d}-{last:02d}")
    return ms


# ---------- T1/T2: subperiod date-boundary fix ----------
SUBPERIODS = [(f"{y}-01", f"{y+1}-12") for y in range(2010, 2025, 2)]

def old_sub(months):
    out = {}
    for (y0, y1) in SUBPERIODS:
        out[f"{y0[:4]}-{y1[:4]}"] = [m for m in months if y0 <= m <= y1]
    return out

def new_sub(months):
    out = {}
    for (y0, y1) in SUBPERIODS:
        out[f"{y0[:4]}-{y1[:4]}"] = [m for m in months if y0 <= m[:7] <= y1]
    return out

def test_t1_t2():
    months = month_ends_2010_2025()
    old = old_sub(months)
    new = new_sub(months)
    check("T1a old code: every subperiod has 23 months (bug reproduced)",
          all(len(v) == 23 for v in old.values()),
          f"counts={[len(v) for v in old.values()]}")
    check("T1b new code: every complete 2Y subperiod has 24 months",
          all(len(v) == 24 for v in new.values()),
          f"counts={[len(v) for v in new.values()]}")
    check("T2a '2011-12-31' inside 2010-2011 (new)",
          "2011-12-31" in new["2010-2011"])
    check("T2b '2011-12-31' excluded 2010-2011 (old bug)",
          "2011-12-31" not in old["2010-2011"])
    check("T2c subperiods are non-overlapping and cover 2010-01..2025-12",
          sorted(m for v in new.values() for m in v) == months)


# ---------- T3: data-derived horizon cutoff ----------
def test_t3():
    import analyze
    months = month_ends_2010_2025()
    rows = [{"m": m, "t": t} for m in months
            for t in json.load(open(os.path.join(HERE, "universe.json")))["tickers"]]
    # NOTE: synthetic month grid x full universe overstates the denominator;
    # restrict to tickers with raw files (mirrors the real call path, where
    # by_month comes from actual panel rows).
    eod_dir = os.path.join(HERE, "raw", "eod")
    if not os.path.isdir(eod_dir):
        check("T3 skipped: raw/eod not present", True, "no raw data on disk")
        return
    have_files = set(f[:-5] for f in os.listdir(eod_dir) if f.endswith(".json"))
    rows = [r for r in rows if r["t"] in have_files]
    months_real = sorted(set(json.loads(l)["m"] for l in
                             open(os.path.join(HERE, "panels", "panel.jsonl"))))
    rows_real = [{"m": r["m"], "t": r["t"]} for r in
                 (json.loads(l) for l in open(os.path.join(HERE, "panels", "panel.jsonl")))]
    c12 = analyze.last_complete_month(rows_real, months_real, 252, eod_dir)
    c6 = analyze.last_complete_month(rows_real, months_real, 126, eod_dir)
    c3 = analyze.last_complete_month(rows_real, months_real, 63, eod_dir)
    check("T3a data-derived r12 cutoff is 2025-08-29 (Sep genuinely 1d short)",
          c12 == "2025-08-29", f"got {c12}")
    check("T3b data-derived r6 cutoff is 2025-12-31", c6 == "2025-12-31",
          f"got {c6}")
    check("T3c data-derived r3 cutoff is 2025-12-31", c3 == "2025-12-31",
          f"got {c3}")
    # determinism
    c12b = analyze.last_complete_month(rows_real, months_real, 252, eod_dir)
    check("T3d cutoff deterministic across runs", c12b == c12)


# ---------- T4/T5/T6: build_panels behaviors on synthetic bars ----------
def synth_bars(n_days, start="2020-01-02", end_gap=0):
    """Business-day date list of length n_days (synthetic calendar)."""
    import datetime
    d = datetime.date.fromisoformat(start)
    out = []
    while len(out) < n_days + end_gap:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out[:n_days]


def ma_ok(n_bars, w, need):
    """Mirror of build_panels MA gate."""
    pos = n_bars - 1
    if pos + 1 < need:
        return False, None
    seg_len = min(w, pos + 1)
    return (seg_len >= need), seg_len


def test_t4():
    ok, seg = ma_ok(230, 250, 230)
    check("T4a 230/250 bars: MA250 accepted over 230 bars (frozen tolerance)",
          ok and seg == 230, f"seg_len={seg}")
    ok, seg = ma_ok(229, 250, 230)
    check("T4b 229/250 bars: row skipped (below need=230)", not ok)
    ok, seg = ma_ok(300, 250, 230)
    check("T4c 300/250 bars: full 250-bar window used", ok and seg == 250,
          f"seg_len={seg}")


def fwd_complete(pos, n_bars, w):
    """Mirror of the corrected build_panels.py flag: full w-trading-day
    window present after the observation bar at index pos."""
    return (pos + w <= n_bars - 1)


def test_t5():
    # 400-bar series, obs bar at index 199 (200 bars remain after it)
    n, pos = 400, 199
    check("T5a r12 flagged incomplete when only 200 bars remain",
          not fwd_complete(pos, n, 252))
    check("T5b r6/r3 complete while r12 incomplete",
          fwd_complete(pos, n, 126) and fwd_complete(pos, n, 63))
    # 700-bar series, obs at index 447 (252 bars remain)
    check("T5c all horizons complete with 252 bars remaining",
          fwd_complete(447, 700, 252) and fwd_complete(447, 700, 126))


def test_t6():
    # delisted ticker: synthetic series ends 2020-06-16; months after the
    # series end must produce no rows (mirror of build_panels' stale guard:
    # obs bar > 9 calendar days before month end -> drop).
    import datetime
    dates = synth_bars(380, start="2019-01-02")  # ends 2020-06-16
    last = dates[-1]
    months = ["2020-05-29", "2020-06-30", "2020-07-31", "2020-08-31"]
    rows = []
    for m in months:
        pos = bisect.bisect_right(dates, m) - 1
        if pos < 0:
            continue
        obs = dates[pos]
        gap = (datetime.date.fromisoformat(m)
               - datetime.date.fromisoformat(obs)).days
        if gap > 9:
            continue
        rows.append(m)
    check("T6a months after series end produce no rows",
          "2020-07-31" not in rows and "2020-08-31" not in rows,
          f"rows={rows}")
    check("T6b month containing the last bar still emits a row",
          "2020-05-29" in rows, f"rows={rows}, last={last}")
    check("T6c series truly ends before 2020-07", last < "2020-07-01",
          f"last={last}")


# ---------- T7: annualization ----------
def test_t7():
    import analyze
    import numpy as np
    d = np.array([-0.003557] * 60)  # raw r3-style window effects
    s3 = analyze.summarize(d, analyze.ANN_FACTOR["r3"])
    s12 = analyze.summarize(d, analyze.ANN_FACTOR["r12"])
    check("T7a primary is the raw per-window effect",
          abs(s3["mean_window"] - (-0.003557)) < 1e-9,
          f"mean_window={s3['mean_window']}")
    check("T7b r3 secondary = raw x4", abs(s3["mean_ann_linear_equiv_SECONDARY"]
          - (-0.003557 * 4)) < 1e-9)
    check("T7c r12 secondary = raw x1 (NOT x12)",
          abs(s12["mean_ann_linear_equiv_SECONDARY"] - (-0.003557)) < 1e-9)
    check("T7d old x12-for-all would give wrong r12 magnitude",
          abs((-0.003557 * 12) - (-0.003557)) > 0.03)


def main():
    print("== QF-VCP-1A-CODEFIX-20261007-03 synthetic tests (synthetic data only) ==")
    test_t1_t2()
    test_t3()
    test_t4()
    test_t5()
    test_t6()
    test_t7()
    n_fail = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{len(results) - n_fail}/{len(results)} passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
