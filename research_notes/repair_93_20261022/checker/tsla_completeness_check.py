#!/usr/bin/env python3
"""
tsla_completeness_check.py — v3 CANDIDATE: independent single-series
completeness + convention-continuity check (task -93; extends the
-89 v2 / repair -91 candidate; design -86 F4, extending the -82
checker).

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

V3 ADDITIONS (task -93, from Claude's -92 review HOLD on checker
v2/-91 — Issue #1 comment 6343957169). All v1/v2 lane semantics are
preserved on inputs the new lanes do not touch; every semantic
tightening is named here, not silent:

  STRUCTURAL — v3 NEW lane, runs before COUNT: the series as a
             sequence must be well-formed before any lane reads it.
               + duplicate timestamps -> DUPLICATE_TIMESTAMP
                 (v2's set-based COUNT collapsed duplicates
                 silently — a doubled bar was invisible)
               + tz-naive index -> TZ_NAIVE; equity mode with a
                 zone != America/New_York -> TZ_NOT_SESSION_ZONE
                 (v2 reconciled a UTC frame against NY expected
                 starts and reported chaos, not a named defect)
               + any backward step in the index -> ORDER_VIOLATION
                 (v2's set logic hid order; first/last-bar reads
                 in STEP silently used file order)
             Structural defects fail completeness.
  OHLC validity — v3 NEW defect classes in the ANOMALY lane:
               + any of O/H/L/C <= 0 -> ZERO_OR_NEGATIVE_PRICE
                 (SEMANTIC TIGHTENING vs v2, disclosed: an
                 all-zero flat bar was NO_TRADE_FLAT in v2; a 0.00
                 print is not a trade price and is a defect in v3)
               + High < Low -> HIGH_LT_LOW
               + Open or Close outside [Low, High] ->
                 PRICE_OUT_OF_RANGE
  Boundary NaN — v3: a NaN first-open or last-close AT a declared
             split boundary (or feeding a STEP-ALL boundary step)
             classifies that boundary UNTESTABLE instead of v2's
             silent fall-through to PRICE_ACTION / skip. Any
             untestable boundary is enumerated in the top-level
             `untestable` list; if nothing else fails, the overall
             verdict is UNTESTABLE (v3 verdict value, disclosed).
  CRYPTO   — v3 NEW instrument mode, run_check(..., instrument=
             "crypto"): the S-C1…S-C6 continuous calendar. A
             session is one America/New_York calendar date; every
             date in the table is a session; expected bars are the
             24 hourly starts 00:00…23:00 ET. Bars are attributed
             to ET dates regardless of the frame's stamp zone (any
             tz-aware stamp accepted; naive refuses structurally).
             Declared splits are a caller error in this mode
             (fail-closed ValueError) — a 24/7 pair has no split
             events. STEP-ALL / VBASIS still scan date boundaries:
             a factor-shaped step in a crypto series is the same
             data-defect signature as in equities.
"""
import math
import statistics

import pandas as pd

CHECKER_VERSION = "checker-v3-candidate-1"

SESSION_ZONE = "America/New_York"

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


def _expected_starts_crypto(day: pd.Timestamp) -> list:
    """S-C1: a crypto session is one ET calendar date; expected bars
    are the 24 hourly starts 00:00…23:00 ET of that date. (On the
    fall-back date the repeated wall hour surfaces as a duplicate
    stamp — STRUCTURAL — rather than being silently absorbed.
    Disclosed in ../SPEC_93.md as an open convention point for
    adjudication; the spring-forward date yields 23 stamps and its
    missing wall hour is a COUNT finding, also disclosed.)"""
    return [day + pd.Timedelta(hours=h) for h in range(24)]


def _tz_name(tz):
    if tz is None:
        return None
    key = getattr(tz, "key", None)
    if key:
        return str(key)
    zone = getattr(tz, "zone", None)
    if zone:
        return str(zone)
    return str(tz)


def _near(log_value, anchor_log):
    return abs(log_value - anchor_log) <= STEP_LOG_TOLERANCE


def run_check(bars: pd.DataFrame, sessions: dict, declared_splits: list,
              instrument: str = "equity") -> dict:
    """bars: tz-aware 1H OHLCV frame (America/New_York for equity;
    any tz-aware zone for crypto — bars are attributed to ET dates).
    sessions: {date: close_minutes_after_midnight} for every session
    in the span (equity); for crypto, {date: 1440} — one entry per
    ET calendar date, every date a session (S-C1).
    declared_splits: [(effective_date, factor)] (equity only)."""
    if not sessions:
        raise ValueError(
            "SESSION_TABLE_REQUIRED: run_check requires the adopted "
            "session table (calendar artifact) as its `sessions` "
            "input; without it a fully-missing session is invisible "
            "(repair -91).")
    if instrument not in ("equity", "crypto"):
        raise ValueError(
            f"INSTRUMENT_UNKNOWN: {instrument!r} (expected 'equity' "
            "or 'crypto')")
    if instrument == "crypto" and declared_splits:
        raise ValueError(
            "CRYPTO_DECLARED_SPLITS_NOT_APPLICABLE: a 24/7 pair has "
            "no split events; a declared split in crypto mode is a "
            "caller error (fail-closed).")

    # STRUCTURAL (v3) — the series as a sequence, before any lane
    # reads it. Computed on the caller's original index.
    raw_idx = bars.index
    structural_defects = []
    dup_mask = raw_idx.duplicated(keep=False)
    if bool(dup_mask.any()):
        seen_dup = []
        for ts in raw_idx[dup_mask]:
            if str(ts) not in seen_dup:
                seen_dup.append(str(ts))
        structural_defects.append(
            {"defect": "DUPLICATE_TIMESTAMP", "timestamps": seen_dup,
             "rows": int(dup_mask.sum())})
    tz_name = _tz_name(getattr(raw_idx, "tz", None))
    if tz_name is None:
        structural_defects.append({"defect": "TZ_NAIVE"})
    elif instrument == "equity" and not (
            tz_name == SESSION_ZONE
            or tz_name.endswith("/" + SESSION_ZONE)):
        structural_defects.append(
            {"defect": "TZ_NOT_SESSION_ZONE", "found_tz": tz_name})
    order_violations = [
        {"position": i, "prev": str(raw_idx[i - 1]), "cur": str(raw_idx[i])}
        for i in range(1, len(raw_idx)) if raw_idx[i] < raw_idx[i - 1]]
    if order_violations:
        structural_defects.append(
            {"defect": "ORDER_VIOLATION", "violations": order_violations})
    structural_pass = not structural_defects

    if instrument == "crypto" and tz_name is not None:
        bars = bars.tz_convert(SESSION_ZONE)
    idx = bars.index

    def starts_for(day, sess_key):
        if instrument == "crypto":
            return _expected_starts_crypto(day)
        return _expected_starts(day, sessions[sess_key])
    days = sorted({ts.normalize() for ts in idx})
    declared_dates = {pd.Timestamp(d).date() for d, _ in declared_splits}

    # COUNT — per-session bar-start reconciliation. (v1, unchanged)
    missing, extra = [], []
    for day in days:
        d = day.date()
        if d not in sessions:
            extra.append((str(d), "session_not_in_calendar"))
            continue
        expected = set(starts_for(day, d))
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
                    str(t) for t in starts_for(day_ts, sess_date)],
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
        # OHLC validity (v3): the bar's own geometry must be a
        # possible trade print before volume classes are judged.
        if min(o, h, l, c) <= 0:
            defect_bars.append(
                {"ts": str(ts), "defect": "ZERO_OR_NEGATIVE_PRICE"})
            continue
        if h < l:
            defect_bars.append({"ts": str(ts), "defect": "HIGH_LT_LOW"})
            continue
        if not (l <= o <= h) or not (l <= c <= h):
            defect_bars.append(
                {"ts": str(ts), "defect": "PRICE_OUT_OF_RANGE"})
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
    untestable = []
    convention_suspect = False
    for eff_date, factor in declared_splits:
        eff = pd.Timestamp(eff_date).tz_localize(idx.tz)
        prior = [d for d in days if d < eff]
        if eff not in days or not prior:
            step_results.append({"effective": str(eff_date),
                                 "status": "UNTESTABLE_BOUNDARY"})
            volume_notes.append({"effective": str(eff_date),
                                 "note": "UNTESTABLE"})
            untestable.append({"boundary": str(eff_date),
                               "scope": "declared",
                               "reason": "BOUNDARY_OUTSIDE_SPAN"})
            continue
        prev_day = prior[-1]
        # Boundary NaN (v3): a NaN print at the boundary makes the
        # step unmeasurable — UNTESTABLE, never a silent fall-through
        # to PRICE_ACTION (v2 behavior, closed here).
        if pd.isna(first_open(eff)) or pd.isna(last_close(prev_day)):
            step_results.append({"effective": str(eff_date),
                                 "status": "UNTESTABLE_NAN_BOUNDARY",
                                 "classification": "UNTESTABLE"})
            volume_notes.append({"effective": str(eff_date),
                                 "note": "UNTESTABLE"})
            untestable.append({"boundary": str(eff_date),
                               "scope": "declared",
                               "reason": "NAN_AT_SPLIT_BOUNDARY"})
            continue
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
        if pd.isna(step):
            untestable.append({"boundary": str(day.date()),
                               "scope": "step_all",
                               "reason": "NAN_AT_BOUNDARY"})
            continue
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

    completeness = "PASS" if (count_pass and anomaly_pass
                              and structural_pass) else "FAIL"
    convention = "PASS" if not convention_suspect else "CONVENTION_BREAK_SUSPECT"
    if completeness == "FAIL" and convention != "PASS":
        overall = "COMPLETENESS_FAIL_AND_CONVENTION_BREAK_SUSPECT"
    elif completeness == "FAIL":
        overall = "COMPLETENESS_FAIL"
    elif convention != "PASS":
        overall = "CONVENTION_BREAK_SUSPECT"
    elif untestable:
        overall = "UNTESTABLE"
    else:
        overall = "QUALIFIED_CLEAN"
    return {
        "checker_version": CHECKER_VERSION,
        "structural": {"verdict": "PASS" if structural_pass else "FAIL",
                       "defects": structural_defects},
        "untestable": untestable,
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
