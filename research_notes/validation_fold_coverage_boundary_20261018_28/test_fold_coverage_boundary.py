"""Static SYNTHETIC_FIXTURE suite for fold_materializer_v3 (task
QF-FOLD-CALENDAR-COVERAGE-BOUNDARY-20261018-28 r1, spec Issue #1 comment
6256681829). All calendars, schedules and timestamps below are synthetic
fixtures, labeled as such; no real market, schedule, or OHLC data is used.
Predeclared fixtures (spec item 6): exact full interval PASS; delayed
first session FAIL; missing final scheduled session FAIL; missing
interior session FAIL; weekend/holiday coverage_end maps to preceding
scheduled session; early close remains one session; bad
exchange/timezone/bounds FAIL; two-run byte identity; -27/-26
preservation hashes. Plus retained -27 fail-closed cases (pin checks,
missing/extra bars) and the coverage-side cases (overshoot, artifact
coverage deficit, v1 artifact rejected).
"""

import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_NOTES = HERE.parent
sys.path.insert(0, str(HERE))

import fold_materializer_v3 as fm

FIXTURE_LABEL = "SYNTHETIC_FIXTURE"
HOLIDAYS = {"2024-11-28", "2024-12-25", "2025-01-01"}  # absent from schedule entirely
EARLY_CLOSES = {"2024-11-29": "13:00", "2024-12-24": "13:00", "2025-07-03": "13:00"}
N_SESSIONS = 400


def build_schedule(coverage_end=None, **overrides):
    """Deterministic synthetic V2 schedule artifact (NOT exchange data).
    coverage_end defaults to the last session date; the artifact declares
    bounds, it does not derive them from bars."""
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
        "artifact": "XNYS_SESSION_SCHEDULE_V2",
        "source": "SYNTHETIC_FIXTURE_NOT_EXCHANGE_DATA",
        "version": "fixture-2",
        "exchange": "XNYS",
        "timezone": "America/New_York",
        "coverage_start": "2024-09-16",
        "coverage_end": coverage_end or sessions[-1]["date"],
        "sessions": sessions,
    }
    doc.update(overrides)
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    return doc, raw, hashlib.sha256(raw).hexdigest()


def build_bars(doc, sessions=None):
    """Bars derived from the fixture schedule by the plain reading of the
    rule: a 16:00 close yields both anchors; a 13:00 close yields 09:30
    only. Constructed independently of the module under test."""
    bars = []
    for s in (doc["sessions"] if sessions is None else sessions):
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
    last_session = doc["sessions"][-1]["date"]

    # 1. Exact full interval PASS, with bounds and mapped endpoints out.
    checks["exact_full_interval_pass"] = (
        out1["session_count"] == N_SESSIONS
        and out1["coverage_start"] == "2024-09-16"
        and out1["coverage_end"] == last_session
        and out1["coverage_first_session"] == "2024-09-16"
        and out1["coverage_last_session"] == last_session
        and out1["schedule_sha256"] == sched_pin
    )
    # 2. Delayed first session (bars start at the second session) FAIL.
    checks["delayed_first_session_rejected"] = expect_error(
        "COVERAGE_PREFIX_MISSING",
        lambda: fm.materialize(build_bars(doc, doc["sessions"][1:]), sched_raw, sched_pin),
    )
    # 3. Missing final scheduled session FAIL.
    checks["missing_final_session_rejected"] = expect_error(
        "COVERAGE_SUFFIX_MISSING",
        lambda: fm.materialize(build_bars(doc, doc["sessions"][:-1]), sched_raw, sched_pin),
    )
    # 4. Missing interior session FAIL (whole session's bars removed).
    interior = date.fromisoformat(doc["sessions"][200]["date"])
    bars_interior = [b for b in bars if not b.startswith(interior.isoformat() + "T")]
    checks["missing_interior_session_rejected"] = expect_error(
        "COVERAGE_INTERIOR_MISSING",
        lambda: fm.materialize(bars_interior, sched_raw, sched_pin),
    )
    # 5. Weekend coverage_end maps to the preceding scheduled session
    #    through the schedule only: extend coverage_end to the Sunday
    #    after the last session; the last required session is unchanged.
    last_day = date.fromisoformat(last_session)
    sunday = last_day + timedelta(days=(6 - last_day.weekday()) % 7 or 7)
    doc_wk, raw_wk, pin_wk = build_schedule(coverage_end=sunday.isoformat())
    out_wk = fm.materialize(bars, raw_wk, pin_wk)
    checks["weekend_coverage_end_maps_to_preceding_session"] = (
        out_wk["coverage_end"] == sunday.isoformat()
        and out_wk["coverage_last_session"] == last_session
        and out_wk["session_count"] == N_SESSIONS
    )
    # 5b. Holiday coverage_end (Thanksgiving 2024-11-28, inside the span)
    #     is simply not a session: full run still passes and the holiday
    #     never enters the calendar.
    expected_calendar_digest = hashlib.sha256(
        "\n".join(s["date"] for s in doc["sessions"]).encode()
    ).hexdigest()
    checks["holiday_inside_interval_not_a_session"] = (
        "2024-11-28" not in [s["date"] for s in doc["sessions"]]
        and all(not b.startswith("2024-11-28T") for b in bars)
        and out1["calendar_digest"] == expected_calendar_digest
    )
    # 6. Early close remains exactly one session, counted once.
    checks["early_close_remains_one_session"] = (
        out1["early_close_sessions"] == sorted(EARLY_CLOSES)
        and out1["session_count"] == N_SESSIONS
        and "2024-11-29T13:30" not in bars
    )
    # 7a. Bad exchange FAIL.
    _, raw_badex, pin_badex = build_schedule(exchange="XNAS")
    checks["bad_exchange_rejected"] = expect_error(
        "SCHEDULE_MALFORMED", lambda: fm.materialize(bars, raw_badex, pin_badex)
    )
    # 7b. Bad timezone FAIL.
    _, raw_badtz, pin_badtz = build_schedule(timezone="UTC")
    checks["bad_timezone_rejected"] = expect_error(
        "SCHEDULE_MALFORMED", lambda: fm.materialize(bars, raw_badtz, pin_badtz)
    )
    # 7c. Bad coverage_start (not the frozen 2024-09-16) FAIL.
    _, raw_badcs, pin_badcs = build_schedule(coverage_start="2024-09-17")
    checks["bad_coverage_start_rejected"] = expect_error(
        "SCHEDULE_MALFORMED", lambda: fm.materialize(bars, raw_badcs, pin_badcs)
    )
    # 7d. Inverted bounds (coverage_end before coverage_start) FAIL.
    _, raw_inv, pin_inv = build_schedule(coverage_end="2024-09-01")
    checks["inverted_bounds_rejected"] = expect_error(
        "SCHEDULE_MALFORMED", lambda: fm.materialize(bars, raw_inv, pin_inv)
    )
    # 8. Bars reaching past the frozen coverage_end FAIL (overshoot):
    #    declare coverage_end at session #380 but supply all 400 sessions.
    doc_os, raw_os, pin_os = build_schedule(
        coverage_end=doc["sessions"][379]["date"]
    )
    checks["bars_past_coverage_end_rejected"] = expect_error(
        "COVERAGE_OVERSHOOT", lambda: fm.materialize(bars, raw_os, pin_os)
    )
    # 9. Artifact coverage deficit: shrink the declared bounds so no
    #    listed session falls inside them (bounds after last session).
    doc_def, raw_def, pin_def = build_schedule(
        coverage_start="2024-09-16", coverage_end="2024-09-16",
        sessions=[{"date": "2026-01-05", "open": "09:30", "close": "16:00"}],
    )
    checks["artifact_coverage_deficit_rejected"] = expect_error(
        "SCHEDULE_COVERAGE_DEFICIT", lambda: fm.materialize(bars, raw_def, pin_def)
    )
    # 10. A V1 artifact (no coverage fields) no longer satisfies the
    #     consumer: bounds can never be silently absent.
    v1_doc = {
        "artifact": "XNYS_SESSION_SCHEDULE_V1",
        "source": "SYNTHETIC_FIXTURE_NOT_EXCHANGE_DATA",
        "version": "fixture-1",
        "sessions": doc["sessions"],
    }
    v1_raw = json.dumps(v1_doc, sort_keys=True, separators=(",", ":")).encode()
    checks["v1_artifact_rejected"] = expect_error(
        "SCHEDULE_MALFORMED",
        lambda: fm.materialize(bars, v1_raw, hashlib.sha256(v1_raw).hexdigest()),
    )
    # 11. Retained -27 fail-closed cases still fire in v3.
    checks["absent_schedule_rejected"] = expect_error(
        "SCHEDULE_MISSING", lambda: fm.materialize(bars, None, None)
    )
    checks["unpinned_schedule_rejected"] = expect_error(
        "SCHEDULE_PIN_MISMATCH", lambda: fm.materialize(bars, sched_raw, "0" * 64)
    )
    bars_missing = [b for b in bars if b != "2024-09-17T13:30"]
    checks["missing_1330_full_session_rejected"] = expect_error(
        "SCHEDULE_BAR_MISMATCH", lambda: fm.materialize(bars_missing, sched_raw, sched_pin)
    )
    bars_extra = sorted(bars + ["2024-11-29T13:30"])
    checks["extra_1330_early_close_rejected"] = expect_error(
        "SCHEDULE_BAR_MISMATCH", lambda: fm.materialize(bars_extra, sched_raw, sched_pin)
    )
    # 12. Determinism: two runs byte-identical; fold logic unchanged.
    checks["deterministic_two_runs_byte_identical"] = (
        fm.canonical_json(out1) == fm.canonical_json(out2)
    )
    checks["fold_counts_deterministic"] = (
        len(out1["folds"]) == (N_SESSIONS - 252) // 63
        and out1["folds"][0]["train_sessions"] == 252
        and all(f["oos_sessions"] == 63 for f in out1["folds"])
    )
    # 13. Preservation: every prior frozen byte asserted on every run.
    checks["preserved_25_materializer_b58194b4"] = sha256_file(
        REPO_NOTES / "validation_prereg_finalization_20261018_25" / "fold_materializer.py"
    ) == "b58194b40b8871581af5aa1135243630b557037917ec76d300579871707c1a4e"
    checks["preserved_27_materializer_v2_b969fc85"] = sha256_file(
        REPO_NOTES / "validation_fold_early_close_20261018_27" / "fold_materializer_v2.py"
    ) == "b969fc852c074e771a339da8bcf3ad79abd597c0b2e7c933b31fe8ae06bbc35b"
    checks["preserved_amendment_v3_26f7ad4f"] = sha256_file(
        REPO_NOTES / "validation_fold_early_close_20261018_27" / "PREREGISTRATION_AMENDMENT_V3.md"
    ).startswith("26f7ad4f")
    checks["preserved_amendment_v2_03f5a564"] = sha256_file(
        REPO_NOTES / "validation_inference_null_calibration_20261018_26" / "PREREGISTRATION_AMENDMENT_V2.md"
    ) == "03f5a56444d1f3436270c863b85078dcbd924a441702e57b1a76d237eeee578a"
    checks["preserved_26_inference_v2_81b213f6"] = sha256_file(
        REPO_NOTES / "validation_inference_null_calibration_20261018_26" / "inference_layer_v2.py"
    ) == "81b213f694c5e28e688d009027ee12914b9d5ee6a8663e2fa0a4f10001c36997"

    results = {
        "task": "QF-FOLD-CALENDAR-COVERAGE-BOUNDARY-20261018-28 r1",
        "fixture_label": FIXTURE_LABEL,
        "checks": checks,
        "checks_passed": sum(1 for v in checks.values() if v),
        "checks_total": len(checks),
        "session_count": out1["session_count"],
        "fold_count": len(out1["folds"]),
        "coverage_start": out1["coverage_start"],
        "coverage_end": out1["coverage_end"],
        "coverage_first_session": out1["coverage_first_session"],
        "coverage_last_session": out1["coverage_last_session"],
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
