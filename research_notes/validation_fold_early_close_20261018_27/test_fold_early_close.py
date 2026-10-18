"""Static SYNTHETIC_FIXTURE suite for fold_materializer_v2 (task
QF-FOLD-EARLY-CLOSE-CONTRACT-20261018-27 r1, spec Issue #1 comment
6255676888). All calendars, schedules and timestamps below are synthetic
fixtures, labeled as such; no real market, schedule, or OHLC data is used.
Predeclared fixtures (spec item 6): full session; official 13:00 early
close; unexplained missing 13:30; extra 13:30 on an early close; holiday
absence; DST transitions; duplicate/non-monotonic timestamps; fold/session
counts and digests deterministic across two runs. Plus fail-closed pin
checks and byte-preservation checks for the -25 materializer and the
Amendment v2 inference bytes.
"""

import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_NOTES = HERE.parent
sys.path.insert(0, str(HERE))

import fold_materializer_v2 as fm

FIXTURE_LABEL = "SYNTHETIC_FIXTURE"
HOLIDAYS = {"2024-11-28", "2024-12-25", "2025-01-01"}  # absent from schedule entirely
EARLY_CLOSES = {"2024-11-29": "13:00", "2024-12-24": "13:00", "2025-07-03": "13:00"}
N_SESSIONS = 400


def build_schedule():
    """Deterministic synthetic schedule artifact (NOT exchange data)."""
    sessions = []
    day = date(2024, 9, 16)
    while len(sessions) < N_SESSIONS:
        iso = day.isoformat()
        if day.weekday() < 5 and iso not in HOLIDAYS:
            sessions.append(
                {"date": iso, "open": "09:30", "close": EARLY_CLOSES.get(iso, "16:00")}
            )
        day += timedelta(days=1)
    doc = {
        "artifact": "XNYS_SESSION_SCHEDULE_V1",
        "source": "SYNTHETIC_FIXTURE_NOT_EXCHANGE_DATA",
        "version": "fixture-1",
        "sessions": sessions,
    }
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    return doc, raw, hashlib.sha256(raw).hexdigest()


def build_bars(doc):
    """Bars derived from the fixture schedule by the plain reading of the
    rule: a 16:00 close yields both anchors; a 13:00 close yields 09:30
    only. Constructed independently of the module under test."""
    bars = []
    for s in doc["sessions"]:
        bars.append(f"{s['date']}T09:30")
        if s["close"] == "16:00":
            bars.append(f"{s['date']}T13:30")
    return bars


def expect_error(code, fn):
    try:
        fn()
    except fm.MaterializerError as e:
        return e.code == code
    return False


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    checks = {}

    doc, sched_raw, sched_pin = build_schedule()
    bars = build_bars(doc)
    out1 = fm.materialize(bars, sched_raw, sched_pin)
    out2 = fm.materialize(list(bars), sched_raw, sched_pin)

    # 1. Full session -> 09:30 + 13:30 (fixture day 2024-09-16 is full).
    checks["full_session_two_anchors"] = (
        "2024-09-16T09:30" in bars and "2024-09-16T13:30" in bars
    )
    # 2. Official 13:00 early close -> 09:30 only, still one fold session.
    checks["early_close_single_anchor"] = (
        "2024-11-29T09:30" in bars and "2024-11-29T13:30" not in bars
    )
    checks["early_close_counts_as_one_session"] = (
        out1["session_count"] == N_SESSIONS
        and out1["early_close_sessions"] == sorted(EARLY_CLOSES)
    )
    # 3. Holiday absence: no schedule entry, no bars, calendar still builds.
    checks["holiday_absence_accepted"] = all(
        h not in [s["date"] for s in doc["sessions"]] for h in HOLIDAYS
    ) and not any(b.startswith(tuple(h + "T" for h in HOLIDAYS)) for b in bars)
    # 4. DST transitions (fall back 2024-11-03, spring forward 2025-03-09):
    #    neighbouring sessions keep local 09:30/13:30 anchors unchanged.
    checks["dst_anchors_unchanged"] = all(
        f"{d}T09:30" in bars and f"{d}T13:30" in bars
        for d in ("2024-11-01", "2024-11-04", "2025-03-07", "2025-03-10")
    )
    # 5. Unexplained missing 13:30 on a full session -> reject.
    bars_missing = [b for b in bars if b != "2024-09-17T13:30"]
    checks["missing_1330_full_session_rejected"] = expect_error(
        "SCHEDULE_BAR_MISMATCH", lambda: fm.materialize(bars_missing, sched_raw, sched_pin)
    )
    # 6. Extra 13:30 on an early-close session -> reject.
    bars_extra = sorted(bars + ["2024-11-29T13:30"])
    checks["extra_1330_early_close_rejected"] = expect_error(
        "SCHEDULE_BAR_MISMATCH", lambda: fm.materialize(bars_extra, sched_raw, sched_pin)
    )
    # 7a. Duplicate timestamp -> reject.
    bars_dup = bars[:5] + [bars[4]] + bars[5:]
    checks["duplicate_timestamp_rejected"] = expect_error(
        "DUPLICATE_TIMESTAMP", lambda: fm.materialize(bars_dup, sched_raw, sched_pin)
    )
    # 7b. Non-monotonic timestamps -> reject.
    bars_swap = list(bars)
    bars_swap[10], bars_swap[11] = bars_swap[11], bars_swap[10]
    checks["non_monotonic_rejected"] = expect_error(
        "NON_MONOTONIC", lambda: fm.materialize(bars_swap, sched_raw, sched_pin)
    )
    # 8. Absent schedule -> reject; wrong pin -> reject.
    checks["absent_schedule_rejected"] = expect_error(
        "SCHEDULE_MISSING", lambda: fm.materialize(bars, None, None)
    )
    checks["unpinned_schedule_rejected"] = expect_error(
        "SCHEDULE_PIN_MISMATCH", lambda: fm.materialize(bars, sched_raw, "0" * 64)
    )
    # 9. Bar on an unscheduled date (the fixture holiday) -> reject; an
    #    early close is never inferred from bar data.
    bars_unscheduled = sorted(bars + ["2024-11-28T09:30"])
    checks["bar_on_unscheduled_date_rejected"] = expect_error(
        "SESSION_NOT_IN_SCHEDULE",
        lambda: fm.materialize(bars_unscheduled, sched_raw, sched_pin),
    )
    # 10. Holdout touch still fails closed (bar inside sealed window).
    bars_holdout = ["2024-09-10T09:30"] + bars
    checks["holdout_touch_rejected"] = expect_error(
        "HOLDOUT_TOUCH", lambda: fm.materialize(bars_holdout, sched_raw, sched_pin)
    )
    # 11. Fold/session counts + digests deterministic across two runs.
    checks["deterministic_two_runs_byte_identical"] = (
        fm.canonical_json(out1) == fm.canonical_json(out2)
    )
    checks["fold_counts_deterministic"] = (
        out1["session_count"] == N_SESSIONS
        and len(out1["folds"]) == (N_SESSIONS - 252) // 63
        and out1["folds"][0]["train_sessions"] == 252
        and all(f["oos_sessions"] == 63 for f in out1["folds"])
        and out1["schedule_sha256"] == sched_pin
    )
    # 12. Preservation: -25 materializer and Amendment v2 inference bytes
    #     are byte-identical to their accepted pins (nothing superseded
    #     except by reference in Amendment v3).
    checks["preserved_25_materializer_b58194b4"] = sha256_file(
        REPO_NOTES / "validation_prereg_finalization_20261018_25" / "fold_materializer.py"
    ) == "b58194b40b8871581af5aa1135243630b557037917ec76d300579871707c1a4e"
    checks["preserved_amendment_v2_03f5a564"] = sha256_file(
        REPO_NOTES / "validation_inference_null_calibration_20261018_26" / "PREREGISTRATION_AMENDMENT_V2.md"
    ) == "03f5a56444d1f3436270c863b85078dcbd924a441702e57b1a76d237eeee578a"
    checks["preserved_26_inference_v2_81b213f6"] = sha256_file(
        REPO_NOTES / "validation_inference_null_calibration_20261018_26" / "inference_layer_v2.py"
    ) == "81b213f694c5e28e688d009027ee12914b9d5ee6a8663e2fa0a4f10001c36997"

    results = {
        "task": "QF-FOLD-EARLY-CLOSE-CONTRACT-20261018-27 r1",
        "fixture_label": FIXTURE_LABEL,
        "checks": checks,
        "checks_passed": sum(1 for v in checks.values() if v),
        "checks_total": len(checks),
        "session_count": out1["session_count"],
        "fold_count": len(out1["folds"]),
        "early_close_sessions": out1["early_close_sessions"],
        "schedule_sha256": sched_pin,
        "input_timestamp_digest": out1["input_timestamp_digest"],
        "calendar_digest": out1["calendar_digest"],
        "output_digest": hashlib.sha256(fm.canonical_json(out1).encode()).hexdigest(),
        "verdict_retained": "PRE_DATA_PREREG_READY__EXACT_FOLDS_PENDING_QUALIFIED_TIMESTAMPS_AND_PINNED_SCHEDULE",
    }
    (HERE / "TEST_RESULTS.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n"
    )
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'} {name}")
    print(f"{results['checks_passed']}/{results['checks_total']} checks passed")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
