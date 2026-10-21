#!/usr/bin/env python3
"""
tsla_completeness_check.py — INDEPENDENT single-series completeness +
convention-continuity check (task -82, item 4).

Design constraint (the whole point): this check NEVER compares two
series against each other. The -75 C2 check paired the adjust=splits
series against its adjust=none twin bar-by-bar; a 0/0 volume pair fit
neither convention and produced the misleading label "INCONSISTENT
convention". This check instead examines ONE series on its own terms:

  COUNT   — row/session reconciliation against a session table (the
            qualified-calendar stand-in): every session inside the
            series span must carry exactly the expected hourly bar
            starts (09:30 + k*1h while start < session close). Missing
            or extra bars are completeness failures.
  ANOMALY — enumeration of zero-volume PRICE-MOVING bars
            (volume == 0 AND (high > low OR close != open)). A bar
            that moved but reports no volume is a completeness
            defect. Zero-volume FLAT bars (O=H=L=C) are classified
            separately as NO_TRADE_FLAT and are NOT anomalies: a
            no-trade hour is a market fact, not a data defect.
  STEP    — single-series continuity at DECLARED split effective
            dates: for a uniformly back-adjusted (adjust=splits)
            series, price level is continuous across the split
            boundary, so |log(open(first bar of D) / close(last bar
            of prev session))| must be small. A step near the declared
            factor (or its reciprocal) is the signature of a
            MIXED-BASIS series — a true convention break — detected
            from inside the one series, with no twin.

Verdicts are kept in separate lanes on purpose:
  completeness_verdict: PASS | FAIL   (COUNT or ANOMALY failed)
  convention_verdict:   PASS | CONVENTION_BREAK_SUSPECT  (STEP failed)
A completeness failure can never print as a convention failure again.
"""
import math

import pandas as pd

STEP_LOG_TOLERANCE = math.log(1.5)  # >50% overnight step at a declared
# split boundary is not explainable as ordinary price movement in
# these fixtures; the threshold is a fixture parameter, recorded here.


def _expected_starts(day: pd.Timestamp, close_min: int) -> list:
    open_min = 9 * 60 + 30
    starts = []
    m = open_min
    while m < close_min:
        starts.append(day + pd.Timedelta(minutes=m))
        m += 60
    return starts


def run_check(bars: pd.DataFrame, sessions: dict, declared_splits: list) -> dict:
    """bars: tz-aware (America/New_York) 1H OHLCV frame.
    sessions: {date: close_minutes_after_midnight} for every session in
    the span. declared_splits: [(effective_date, factor)]."""
    idx = bars.index
    days = sorted({ts.normalize() for ts in idx})

    # COUNT — per-session bar-start reconciliation.
    missing, extra = [], []
    for day in days:
        d = day.date()
        if d not in sessions:
            extra.append((str(d), "session_not_in_calendar"))
            continue
        expected = set(_expected_starts(day, sessions[d]))
        actual = set(idx[idx.normalize() == day])
        for ts in sorted(expected - actual):
            missing.append(str(ts))
        for ts in sorted(actual - expected):
            extra.append(str(ts))
    count_pass = not missing and not extra

    # ANOMALY — zero-volume classification.
    anomalies, flat_no_trade = [], []
    for ts, row in bars.iterrows():
        if row["Volume"] == 0:
            if row["High"] > row["Low"] or row["Close"] != row["Open"]:
                anomalies.append(str(ts))
            else:
                flat_no_trade.append(str(ts))
    anomaly_pass = not anomalies

    # STEP — continuity at declared split boundaries (single series).
    step_results = []
    step_pass = True
    for eff_date, factor in declared_splits:
        eff = pd.Timestamp(eff_date).tz_localize(idx.tz)
        prior = [d for d in days if d < eff]
        if eff not in days or not prior:
            step_results.append({"effective": str(eff_date),
                                 "status": "UNTESTABLE_BOUNDARY"})
            continue
        prev_day = prior[-1]
        last_close = bars[idx.normalize() == prev_day].iloc[-1]["Close"]
        first_open = bars[idx.normalize() == eff].iloc[0]["Open"]
        step = first_open / last_close
        ok = abs(math.log(step)) <= STEP_LOG_TOLERANCE
        step_pass = step_pass and ok
        step_results.append({"effective": str(eff_date), "factor": factor,
                             "observed_step": round(float(step), 6),
                             "status": "PASS" if ok else "CONVENTION_BREAK_SUSPECT"})

    completeness = "PASS" if (count_pass and anomaly_pass) else "FAIL"
    convention = "PASS" if step_pass else "CONVENTION_BREAK_SUSPECT"
    if completeness == "FAIL" and convention != "PASS":
        overall = "COMPLETENESS_FAIL_AND_CONVENTION_BREAK_SUSPECT"
    elif completeness == "FAIL":
        overall = "COMPLETENESS_FAIL"
    elif convention != "PASS":
        overall = "CONVENTION_BREAK_SUSPECT"
    else:
        overall = "QUALIFIED_CLEAN"
    return {
        "count": {"verdict": "PASS" if count_pass else "FAIL",
                  "missing_bars": missing, "extra_bars": extra},
        "anomaly": {"verdict": "PASS" if anomaly_pass else "FAIL",
                    "price_moving_zero_volume": anomalies,
                    "no_trade_flat_zero_volume": flat_no_trade},
        "step": {"verdict": convention, "results": step_results},
        "completeness_verdict": completeness,
        "convention_verdict": convention,
        "overall": overall,
    }
