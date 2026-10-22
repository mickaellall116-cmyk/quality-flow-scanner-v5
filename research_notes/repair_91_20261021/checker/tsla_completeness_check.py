#!/usr/bin/env python3
"""
tsla_completeness_check.py — v2 CANDIDATE: independent single-series
completeness + convention-continuity check (task -89; design -86 F4,
extending the -82 checker).

STATUS: isolated candidate module. NOT adopted; the -82 v1 checker
(this file's predecessor, sha256 0a7712be…) remains the cited
instrument until adoption under GO G4. Adoption (G4) is also the GO
that authorizes re-analyzing the -75 Day-1 snapshots under v2 — that
re-analysis is NOT part of this package and no snapshot is touched
here. All fixtures are synthetic.

DESIGN CONSTRAINT (inherited, the whole point): this check NEVER
compares two series against each other. It examines ONE series on
its own terms, and completeness verdicts can never print as
convention verdicts (the -75 C2 conflation this instrument exists
to prevent).

LANES (v1 lanes preserved; v2 additions marked):
  COUNT    — row/session reconciliation against a session table.
             REPAIR -91 (2026-10-21, ChatGPT review blocker 1): the
             session table is a REQUIRED input and the lane iterates
             EXPECTED sessions, not only days present in the bars.
             A session in the table with ZERO rows in the series is
             a first-class finding (missing_sessions) and fails
             COUNT -> COMPLETENESS_FAIL: a fully-absent session in a
             qualified window can no longer pass silently.
  ANOMALY  — completeness defects, enumerated per bar:
             v1: zero-volume PRICE-MOVING bars (zero-volume FLAT bars
             are NO_TRADE_FLAT market facts, not defects).
             v2: + NaN in Volume or any OHLC field -> NAN_VALUE
                 + negative volume -> NEGATIVE_VOLUME
                 + sub-plausible price-moving volume
                   (0 < v < MIN_PLAUSIBLE_VOLUME with high > low or
                   close != open) -> SUB_PLAUSIBLE_VOLUME_PRICE_MOVING
                   (a 1-share FLAT bar stays NO_TRADE_FLAT.)
  STEP     — DECLARED split boundaries only. v2 replaces v1's
             blanket |log step| tolerance with an explicit
             CLASSIFICATION (the false-flag guard):
               step ~ 1            -> CONTINUOUS_ADJUSTED (PASS)
               step ~ factor or
                 ~ 1/factor        -> MIXED_BASIS_SUSPECT
               anything else       -> PRICE_ACTION (NO flag — a
                                      genuine +60% gap at a declared
                                      boundary is a market fact)
             SEMANTIC CHANGE vs v1, disclosed: v1 flagged ANY
             |log step| > log(1.5) at a declared boundary as
             suspect; v2 flags only factor-shaped steps. Readouts
             produced under v1 STEP semantics are not silently
             comparable to v2 readouts (see ../ADOPTION_NOTES.md).
  STEP-ALL — v2 NEW: scans ALL undeclared session boundaries for
             factor-shaped price steps (step ~ a plausible split
             factor or its reciprocal) -> CONVENTION_BREAK_SUSPECT
             (undeclared split signature).
  VBASIS   — v2 NEW: a persistent step in volume scale (median of
             the 5 sessions after a boundary vs the median of the
             sessions before, outside [1/1.5, 1.5]) at a NON-declared
             boundary -> CONVENTION_BREAK_SUSPECT (volume-basis
             step). Declared boundaries are excluded: their volume
             step is measured by the note lane instead.
  NOTES    — v2 NEW: at each declared boundary, the volume scale
             step (pre-session total / boundary-session total) vs
             the declared factor: ~ factor -> SCALED_BY_FACTOR;
             ~ 1 -> UNSCALED; anything else -> OTHER_VOLUME_STEP.
             Notes are information, not failures — EXCEPT the
             mismatch rule: prices classified CONTINUOUS_ADJUSTED
             while the volume step is neither ~1 nor ~factor means
             the two bases disagree in an unclassifiable way ->
             CONVENTION_BREAK_SUSPECT. An unmeasurable step (NaN
             volume in either session) records UNTESTABLE and feeds
             no verdict.

Verdict lanes stay separate:
  completeness_verdict: PASS | FAIL   (COUNT or ANOMALY)
  convention_verdict:   PASS | CONVENTION_BREAK_SUSPECT
                        (STEP classification, STEP-ALL, VBASIS, or
                        the note mismatch rule)
"""
import math
import statistics

import pandas as pd

CHECKER_VERSION = "checker-v2-candidate-1"

STEP_LOG_TOLERANCE = math.log(1.5)  # inherited from v1: the anchor
# radius (log space) for "step ~ anchor" in every classification.

MIN_PLAUSIBLE_VOLUME = 2  # governed checker constant (-86 F4): a
# price-moving bar with 0 < volume < 2 (i.e. exactly 1 share) is a
# completeness defect. Amendable only by governed amendment.

PLAUSIBLE_SPLIT_FACTORS = (2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 20.0)
# STEP-ALL anchors are these factors and their reciprocals. 1.5 is
# deliberately absent: log(1.5/1.001) < STEP_LOG_TOLERANCE, so a 1.5
# anchor would flag ordinary +0.1% overnight drift as factor-shaped.

VBASIS_BAND = 1.5            # ratio outside [1/1.5, 1.5] is a step
VBASIS_POST_SESSIONS = 5     # the step must be sustained >= 5 sessions


def _expected_starts(day: pd.Timestamp, close_min: int) -> list:
    open_min = 9 * 60 + 30
    starts = []
    m = open_min
    while m < close_min:
        starts.append(day + pd.Timedelta(minutes=m))
        m += 60
    return starts


def _near(log_value, anchor_log):
    return abs(log_value - anchor_log) <= STEP_LOG_TOLERANCE


def run_check(bars: pd.DataFrame, sessions: dict, declared_splits: list) -> dict:
    """bars: tz-aware (America/New_York) 1H OHLCV frame.
    sessions: {date: close_minutes_after_midnight} for every session in
    the span. declared_splits: [(effective_date, factor)]."""
    if not sessions:
        raise ValueError(
            "SESSION_TABLE_REQUIRED: run_check requires the adopted "
            "session table (calendar artifact) as its `sessions` "
            "input; without it a fully-missing session is invisible "
            "(repair -91).")
    idx = bars.index
    days = sorted({ts.normalize() for ts in idx})
    declared_dates = {pd.Timestamp(d).date() for d, _ in declared_splits}

    # COUNT — per-session bar-start reconciliation. (v1, unchanged)
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
    # REPAIR -91: expected-session iteration. Every session in the
    # table must have rows; a zero-row session is a finding here,
    # not an absence the lane steps over.
    present_dates = {day.date() for day in days}
    missing_sessions = []
    for sess_date in sorted(sessions):
        d = sess_date.date() if hasattr(sess_date, "date") else sess_date
        if d not in present_dates:
            day_ts = pd.Timestamp(d, tz=idx.tz)
            missing_sessions.append({
                "session": str(d),
                "expected_bar_starts": [
                    str(t) for t in _expected_starts(day_ts, sessions[sess_date])],
            })
    count_pass = not missing and not extra and not missing_sessions

    # ANOMALY — per-bar completeness defects. (v1 zero-volume classes
    # preserved verbatim; v2 adds NaN / negative / sub-plausible.)
    anomalies, flat_no_trade, defect_bars = [], [], []
    for ts, row in bars.iterrows():
        o, h, l, c, v = (row["Open"], row["High"], row["Low"],
                         row["Close"], row["Volume"])
        if any(pd.isna(x) for x in (o, h, l, c, v)):
            defect_bars.append({"ts": str(ts), "defect": "NAN_VALUE"})
            continue
        moving = (h > l) or (c != o)
        if v < 0:
            defect_bars.append({"ts": str(ts), "defect": "NEGATIVE_VOLUME"})
        elif v == 0:
            if moving:
                anomalies.append(str(ts))
            else:
                flat_no_trade.append(str(ts))
        elif v < MIN_PLAUSIBLE_VOLUME:
            if moving:
                defect_bars.append(
                    {"ts": str(ts),
                     "defect": "SUB_PLAUSIBLE_VOLUME_PRICE_MOVING"})
            else:
                flat_no_trade.append(str(ts))
    anomaly_pass = not anomalies and not defect_bars

    # Per-session volume totals (+ NaN presence) for NOTES / VBASIS.
    session_totals = []   # [(date, total, has_nan)]
    for day in days:
        vols = bars[idx.normalize() == day]["Volume"]
        session_totals.append((day.date(), float(vols.sum(skipna=True)),
                               bool(vols.isna().any())))
    totals_by_date = {d: (t, nan) for d, t, nan in session_totals}

    def first_open(day):
        return bars[idx.normalize() == day].iloc[0]["Open"]

    def last_close(day):
        return bars[idx.normalize() == day].iloc[-1]["Close"]

    # STEP — declared boundaries: classification + volume note.
    step_results, volume_notes = [], []
    convention_suspect = False
    for eff_date, factor in declared_splits:
        eff = pd.Timestamp(eff_date).tz_localize(idx.tz)
        prior = [d for d in days if d < eff]
        if eff not in days or not prior:
            step_results.append({"effective": str(eff_date),
                                 "status": "UNTESTABLE_BOUNDARY"})
            volume_notes.append({"effective": str(eff_date),
                                 "note": "UNTESTABLE"})
            continue
        prev_day = prior[-1]
        step = first_open(eff) / last_close(prev_day)
        log_step = math.log(step)
        if _near(log_step, 0.0):
            classification, status = "CONTINUOUS_ADJUSTED", "PASS"
        elif _near(log_step, math.log(factor)) or \
                _near(log_step, -math.log(factor)):
            classification, status = ("MIXED_BASIS_SUSPECT",
                                      "CONVENTION_BREAK_SUSPECT")
            convention_suspect = True
        else:
            classification, status = "PRICE_ACTION", "PRICE_ACTION_NO_FLAG"

        # Volume scale-step note at the same boundary.
        pre_total, pre_nan = totals_by_date[prev_day.date()]
        post_total, post_nan = totals_by_date[eff.date()]
        if pre_nan or post_nan or post_total == 0:
            note, ratio = "UNTESTABLE", None
        else:
            ratio = pre_total / post_total
            log_ratio = math.log(ratio)
            if _near(log_ratio, math.log(factor)):
                note = "SCALED_BY_FACTOR"
            elif _near(log_ratio, 0.0):
                note = "UNSCALED"
            else:
                note = "OTHER_VOLUME_STEP"
        # Mismatch rule: adjusted prices + an unclassifiable volume
        # step = the two bases disagree -> suspect.
        mismatch = (classification == "CONTINUOUS_ADJUSTED"
                    and note == "OTHER_VOLUME_STEP")
        if mismatch:
            convention_suspect = True
        step_results.append({"effective": str(eff_date), "factor": factor,
                             "observed_step": round(float(step), 6),
                             "classification": classification,
                             "status": status, "basis_mismatch": mismatch})
        volume_notes.append({"effective": str(eff_date), "note": note,
                             "observed_pre_post_ratio":
                                 None if ratio is None else round(float(ratio), 6)})
    step_pass = not convention_suspect

    # STEP-ALL — undeclared boundaries, factor-shaped price steps.
    step_all_results = []
    anchors = sorted({a for f in PLAUSIBLE_SPLIT_FACTORS for a in (f, 1.0 / f)})
    for prev_day, day in zip(days, days[1:]):
        if day.date() in declared_dates:
            continue
        step = first_open(day) / last_close(prev_day)
        if step <= 0:
            continue
        log_step = math.log(step)
        in_tol = [a for a in anchors if _near(log_step, math.log(a))]
        matched = (min(in_tol, key=lambda a: abs(log_step - math.log(a)))
                   if in_tol else None)
        if matched is not None:
            step_all_results.append(
                {"boundary": str(day.date()),
                 "observed_step": round(float(step), 6),
                 "matched_anchor": matched,
                 "status": "CONVENTION_BREAK_SUSPECT"})
    step_all_suspect = bool(step_all_results)
    convention_suspect = convention_suspect or step_all_suspect

    # VBASIS — persistent volume-scale steps at non-declared boundaries.
    vbasis_results = []
    vbasis_note = None
    if any(nan for _, _, nan in session_totals):
        vbasis_note = "NOT_EVALUATED_NAN_VOLUME"
    else:
        totals = [t for _, t, _ in session_totals]
        for i in range(1, len(session_totals)):
            if session_totals[i][0] in declared_dates:
                continue
            post = totals[i:i + VBASIS_POST_SESSIONS]
            if len(post) < VBASIS_POST_SESSIONS:
                continue
            pre = totals[max(0, i - VBASIS_POST_SESSIONS):i]
            if not pre:
                continue
            pre_med = statistics.median(pre)
            if pre_med == 0:
                continue
            ratio = statistics.median(post) / pre_med
            if ratio > VBASIS_BAND or ratio < 1.0 / VBASIS_BAND:
                vbasis_results.append(
                    {"boundary": str(session_totals[i][0]),
                     "observed_ratio": round(float(ratio), 6),
                     "status": "CONVENTION_BREAK_SUSPECT"})
    vbasis_suspect = bool(vbasis_results)
    convention_suspect = convention_suspect or vbasis_suspect

    completeness = "PASS" if (count_pass and anomaly_pass) else "FAIL"
    convention = "PASS" if not convention_suspect else "CONVENTION_BREAK_SUSPECT"
    if completeness == "FAIL" and convention != "PASS":
        overall = "COMPLETENESS_FAIL_AND_CONVENTION_BREAK_SUSPECT"
    elif completeness == "FAIL":
        overall = "COMPLETENESS_FAIL"
    elif convention != "PASS":
        overall = "CONVENTION_BREAK_SUSPECT"
    else:
        overall = "QUALIFIED_CLEAN"
    return {
        "checker_version": CHECKER_VERSION,
        "count": {"verdict": "PASS" if count_pass else "FAIL",
                  "missing_bars": missing, "extra_bars": extra,
                  "missing_sessions": missing_sessions,
                  "expected_sessions": len(sessions),
                  "present_sessions": len(present_dates & {
                      (k.date() if hasattr(k, "date") else k)
                      for k in sessions})},
        "anomaly": {"verdict": "PASS" if anomaly_pass else "FAIL",
                    "price_moving_zero_volume": anomalies,
                    "no_trade_flat_zero_volume": flat_no_trade,
                    "defect_bars": defect_bars},
        "step": {"verdict": "PASS" if step_pass else "CONVENTION_BREAK_SUSPECT",
                 "results": step_results},
        "volume_notes": volume_notes,
        "step_all": {"verdict": "CONVENTION_BREAK_SUSPECT" if step_all_suspect
                     else "PASS",
                     "results": step_all_results},
        "vbasis": {"verdict": "CONVENTION_BREAK_SUSPECT" if vbasis_suspect
                   else "PASS",
                   "results": vbasis_results, "note": vbasis_note},
        "completeness_verdict": completeness,
        "convention_verdict": convention,
        "overall": overall,
    }
