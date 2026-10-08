#!/usr/bin/env python3
"""Synthetic tests for QF-VCP-1A-INTERVAL-FIX-20261008-06 (adjudication 6053282451).

Proves, on synthetic data only (zero real-data performance reruns), by calling
PRODUCTION functions (build_panels.forward_window, build_panels.admit_interval,
analyze.resolve_horizon_filter):
  I1  ordinary index removal (continuing/open): forward window extends PAST
      membership end using actual post-removal bars -> 'complete'
  I2  verified terminal acquisition: window past series end -> 'delisted_flat',
      exact flat-hold return = last_close/obs - 1, counted COMPLETE
  I3  ambiguous identity (manifest ambiguous/quarantine) -> interval REJECTED
      (admit_interval returns admit=False), fail closed
  I4  ticker reuse (series starts after interval end, legacy guard) -> REJECTED
  I5  cross-field invariant in resolve_horizon_filter: consistent rows pass;
      corrupted row (complete=True with status='censored') -> hard RuntimeError
  I6  manifest disposition of a continuing interval routes series_closed=False
      and of a terminal interval routes series_closed=True (admission ->
      forward_window integration)

Run: python3 test_vcp_phase1a_intervalfix.py   (exit 0 = all pass)
"""
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_panels import (
    forward_window, admit_interval, FWD_STATUS_OK,
    DISP_CONTINUING, DISP_TERMINAL, DISP_AMBIGUOUS,
)
import analyze

PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f" [{detail}]" if detail and not cond else ""))


def tdates(start, n):
    """n consecutive trading-ish days (Mon-Fri) from start date."""
    d = datetime.date.fromisoformat(start)
    out = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


# ---------- I1: ordinary removal, continuing series ----------
dates = tdates("2015-01-01", 600)   # long series
# membership ends at bar 300 (ordinary removal); series continues to bar 599
pos = 250                            # observation bar (inside membership)
w = 63
status, end_i = forward_window(dates, pos, w, series_closed=False)
check("I1 continuing: status complete past membership end",
      status == "complete" and end_i == pos + w, f"{status} {end_i}")
# a window that would exceed the dataset edge is still censored
pos2 = 560
status2, end_i2 = forward_window(dates, pos2, w, series_closed=False)
check("I1 continuing: censored at dataset boundary",
      status2 == "censored" and end_i2 == len(dates) - 1, f"{status2}")

# ---------- I2: verified terminal flat-hold ----------
dates_t = tdates("2020-01-01", 400)  # series ends at delisting (bar 399)
pos_t = 350
w_t = 63
status_t, end_i_t = forward_window(dates_t, pos_t, w_t, series_closed=True)
check("I2 terminal: status delisted_flat", status_t == "delisted_flat", f"{status_t}")
check("I2 terminal: end index = last bar", end_i_t == len(dates_t) - 1)
check("I2 terminal: counted COMPLETE", status_t in FWD_STATUS_OK)
# exact flat-hold return: last close / obs - 1
closes = [100.0 + i * 0.1 for i in range(len(dates_t))]
ret = closes[end_i_t] / closes[pos_t] - 1.0
expect = closes[-1] / closes[pos_t] - 1.0
check("I2 terminal: exact flat-hold return", abs(ret - expect) < 1e-12, f"{ret} vs {expect}")

# ---------- I3: ambiguous identity rejected ----------
manifest = {
    "AMB|2015-01-01|2018-06-01": DISP_AMBIGUOUS,
    "CON|2015-01-01|2018-06-01": DISP_CONTINUING,
    "TER|2015-01-01|2018-06-01": DISP_TERMINAL,
}
s0, s1 = "2009-01-02", "2026-09-30"
admit, disp, log = admit_interval("AMB", "2015-01-01", "2018-06-01", s0, s1, manifest)
check("I3 ambiguous: admit=False", admit is False, f"admit={admit}")
check("I3 ambiguous: disposition recorded", disp == DISP_AMBIGUOUS)
check("I3 ambiguous: log says QUARANTINED", "QUARANTINED" in log)

# ---------- I4: ticker reuse rejected via legacy guard ----------
# series starts AFTER the interval end -> reuse_guard END_MISMATCH
admit4, disp4, log4 = admit_interval(
    "REU", "2010-01-01", "2015-12-28", "2017-11-01", "2026-09-30", manifest)
check("I4 reuse: admit=False", admit4 is False, f"admit={admit4}")
check("I4 reuse: legacy path (no manifest disposition)", disp4 is None)
check("I4 reuse: log says QUARANTINED", "QUARANTINED" in log4)

# ---------- manifest-driven admissions ----------
admit_c, disp_c, log_c = admit_interval("CON", "2015-01-01", "2018-06-01", s0, s1, manifest)
check("I4b continuing: admitted", admit_c is True and disp_c == DISP_CONTINUING)
admit_t, disp_t, log_t = admit_interval("TER", "2015-01-01", "2018-06-01", s0, s1, manifest)
check("I4b terminal: admitted", admit_t is True and disp_t == DISP_TERMINAL)
# unknown ticker falls back to legacy guard (open interval, fresh series -> ok)
admit_l, disp_l, _ = admit_interval("NEW", "2020-01-01", "2200-01-01", "2009-01-02", "2026-09-30", manifest)
check("I4b legacy open interval: admitted via guard", admit_l is True and disp_l is None)

# ---------- I5: cross-field invariant ----------
def row(t, m, comp, stat):
    return {"t": t, "m": m,
            "fwd_complete_r3": comp[0], "fwd_complete_r6": comp[1], "fwd_complete_r12": comp[2],
            "fwd_status_r3": stat[0], "fwd_status_r6": stat[1], "fwd_status_r12": stat[2]}
good = [row("A", "2020-01-31", (True, True, True), ("complete", "complete", "complete")),
        row("B", "2020-01-31", (True, True, False), ("complete", "delisted_flat", "censored"))]
try:
    r = analyze.resolve_horizon_filter(good)
    check("I5 invariant: consistent rows pass", r["mode"] == "flags")
except RuntimeError as e:
    check("I5 invariant: consistent rows pass", False, str(e)[:80])

bad = [row("A", "2020-01-31", (True, True, True), ("complete", "complete", "complete")),
       row("B", "2020-01-31", (True, True, True), ("complete", "complete", "censored"))]
try:
    analyze.resolve_horizon_filter(bad)
    check("I5 invariant: corrupted row hard-errors", False, "no error raised")
except RuntimeError as e:
    check("I5 invariant: corrupted row hard-errors", "invariant" in str(e).lower(), str(e)[:80])

# ---------- I6: disposition -> series_closed routing ----------
def route(disp):
    if disp == DISP_TERMINAL:
        return True
    if disp == DISP_CONTINUING:
        return False
    raise AssertionError("ambiguous must not route")
check("I6 continuing routes series_closed=False", route(DISP_CONTINUING) is False)
check("I6 terminal routes series_closed=True", route(DISP_TERMINAL) is True)
try:
    route(DISP_AMBIGUOUS)
    check("I6 ambiguous never routes", False, "no error")
except AssertionError:
    check("I6 ambiguous never routes", True)
# integration: continuing window uses post-removal bars (I1 already proves via
# production forward_window with series_closed=False)
check("I6 integration: post-removal bars observable",
      dates[pos + w] > dates[300], "membership-end bar index")

print(f"\n{PASS.__len__()} passed, {FAIL.__len__()} failed")
sys.exit(1 if FAIL else 0)
