"""Timestamp-only walk-forward fold-calendar materializer v2.

Supersedes ONLY the schedule/grid clauses of fold_materializer r1
(SHA-256 b58194b40b8871581af5aa1135243630b557037917ec76d300579871707c1a4e,
preserved unedited) per PREREGISTRATION AMENDMENT V3 (task
QF-FOLD-EARLY-CLOSE-CONTRACT-20261018-27 r1, Issue #1 comment 6255676888).
Failure key closed: FOLD_EARLY_CLOSE_GRID_CONFLICT.

Contract change versus r1: r1 required every session to carry exactly the
two grid bars 09:30 and 13:30, so a legitimate XNYS 13:00 early close --
whose canonical resampler correctly yields only the 09:30 partial 4H bar --
was falsely rejected as BAD_GRID. v2 instead derives the expected bar
anchors MECHANICALLY from a separate PINNED exchange-schedule artifact:

  - include anchor 09:30 when the session's regular close is after 09:30;
  - include anchor 13:30 only when the regular close is after 13:30;
  - therefore an official 13:00 close expects exactly one 09:30 bar and
    still counts as exactly one fold session.

Rules that may never be violated:
  - a second bar is NEVER fabricated;
  - an early close is NEVER inferred from missing data -- it exists only
    because the pinned schedule declares that session's regular close;
  - an early-close session is NEVER treated as a holiday;
  - a missing or extra bar versus the pinned schedule fails closed;
  - an absent or unpinned (SHA-256 mismatched) schedule fails closed.

The pinned schedule artifact is the SOLE calendar authority in v2: a
weekday absent from it is definitionally a non-session (holiday/closure),
subsuming r1's declared-holiday input and its UNRESOLVED_GAP check, while
any bar on an unscheduled date fails closed (SESSION_NOT_IN_SCHEDULE).

Input remains timestamp-only plus the schedule artifact bytes and their
expected SHA-256 pin. No parameter or code path accepts a price, quantity,
outcome, or performance value. Pure standard library; no
pandas_market_calendars dependency. Runtime generation of a real schedule
artifact is a later qualified-data input step; this module is only the
frozen artifact contract and its deterministic consumer.

Fail-closed: any violation raises MaterializerError with a named code and
no output is produced.
"""

import hashlib
import json
from datetime import date

HOLDOUT_START = date(2023, 10, 19)
HOLDOUT_END = date(2024, 9, 15)
DEV_START = date(2024, 9, 16)
ANCHOR_TIMES = ("09:30", "13:30")
MIN_TRAIN_SESSIONS = 252
OOS_BLOCK_SESSIONS = 63
SCHEDULE_ARTIFACT_KIND = "XNYS_SESSION_SCHEDULE_V1"


class MaterializerError(Exception):
    def __init__(self, code, detail):
        super().__init__(f"{code}: {detail}")
        self.code = code


def expected_anchors(regular_close):
    """Mechanically derive a session's expected bar anchors from its
    regular close time ("HH:MM"): 09:30 iff close is after 09:30; 13:30
    iff close is after 13:30. String comparison is exact for zero-padded
    HH:MM values."""
    anchors = []
    if regular_close > "09:30":
        anchors.append("09:30")
    if regular_close > "13:30":
        anchors.append("13:30")
    return anchors


def _valid_hhmm(s):
    if not isinstance(s, str) or len(s) != 5 or s[2] != ":":
        return False
    try:
        h, m = int(s[:2]), int(s[3:])
    except Exception:
        return False
    return 0 <= h <= 23 and 0 <= m <= 59


def _parse_schedule(schedule_bytes, schedule_sha256):
    """Validate the pinned schedule artifact. Returns (sessions, meta)
    where sessions maps date -> {"open": str, "close": str}."""
    if schedule_bytes is None or schedule_sha256 is None:
        raise MaterializerError(
            "SCHEDULE_MISSING", "a pinned exchange-schedule artifact is required"
        )
    if not isinstance(schedule_bytes, (bytes, bytearray)):
        raise MaterializerError("SCHEDULE_MALFORMED", "schedule artifact must be bytes")
    actual = hashlib.sha256(bytes(schedule_bytes)).hexdigest()
    if actual != schedule_sha256:
        raise MaterializerError(
            "SCHEDULE_PIN_MISMATCH", f"artifact sha256 {actual} != pin {schedule_sha256}"
        )
    try:
        doc = json.loads(bytes(schedule_bytes).decode("utf-8"))
    except Exception:
        raise MaterializerError("SCHEDULE_MALFORMED", "artifact is not valid UTF-8 JSON")
    if not isinstance(doc, dict) or doc.get("artifact") != SCHEDULE_ARTIFACT_KIND:
        raise MaterializerError(
            "SCHEDULE_MALFORMED", f"artifact kind must be {SCHEDULE_ARTIFACT_KIND}"
        )
    source, version = doc.get("source"), doc.get("version")
    if not isinstance(source, str) or not source or not isinstance(version, str) or not version:
        raise MaterializerError("SCHEDULE_MALFORMED", "source/version must be non-empty strings")
    raw_sessions = doc.get("sessions")
    if not isinstance(raw_sessions, list) or not raw_sessions:
        raise MaterializerError("SCHEDULE_MALFORMED", "sessions must be a non-empty list")
    sessions = {}
    for entry in raw_sessions:
        if not isinstance(entry, dict):
            raise MaterializerError("SCHEDULE_MALFORMED", f"session entry not an object: {entry!r}")
        try:
            y, m, d = (int(p) for p in str(entry["date"]).split("-"))
            day = date(y, m, d)
        except Exception:
            raise MaterializerError("SCHEDULE_MALFORMED", f"unparseable session date: {entry!r}")
        open_s, close_s = entry.get("open"), entry.get("close")
        if not _valid_hhmm(open_s) or not _valid_hhmm(close_s) or not close_s > open_s:
            raise MaterializerError(
                "SCHEDULE_MALFORMED", f"bad open/close for {day}: {open_s!r}/{close_s!r}"
            )
        if not expected_anchors(close_s):
            raise MaterializerError(
                "SCHEDULE_MALFORMED", f"session {day} closes at/before first anchor 09:30"
            )
        if day in sessions:
            raise MaterializerError("SCHEDULE_MALFORMED", f"duplicate schedule session: {day}")
        sessions[day] = {"open": open_s, "close": close_s}
    return sessions, {"source": source, "version": version}


def _parse_ts(ts):
    if not isinstance(ts, str):
        raise MaterializerError("MALFORMED_TIMESTAMP", f"not a string: {type(ts).__name__}")
    try:
        day_s, time_s = ts.split("T")
        y, m, d = (int(p) for p in day_s.split("-"))
        day = date(y, m, d)
    except Exception:
        raise MaterializerError("MALFORMED_TIMESTAMP", f"unparseable: {ts!r}")
    if time_s not in ANCHOR_TIMES:
        raise MaterializerError("BAD_GRID", f"bar time {time_s!r} not an anchor {ANCHOR_TIMES} ({ts!r})")
    return day, time_s


def materialize(timestamps, schedule_bytes, schedule_sha256):
    """Materialize fold boundaries from bar timestamps + pinned schedule.

    timestamps: list of "YYYY-MM-DDTHH:MM" strings (America/New_York local).
    schedule_bytes: canonical bytes of the pinned schedule artifact.
    schedule_sha256: expected SHA-256 hex digest of schedule_bytes (the pin).
    Returns a dict; serialization via canonical_json() is deterministic.
    """
    sessions, meta = _parse_schedule(schedule_bytes, schedule_sha256)

    parsed = [_parse_ts(ts) for ts in timestamps]

    seen = set()
    for ts in timestamps:
        if ts in seen:
            raise MaterializerError("DUPLICATE_TIMESTAMP", ts)
        seen.add(ts)
    for prev, cur in zip(timestamps, timestamps[1:]):
        if not prev < cur:
            raise MaterializerError("NON_MONOTONIC", f"{prev!r} !< {cur!r}")

    bars = {}
    for day, time_s in parsed:
        bars.setdefault(day, []).append(time_s)
    days = sorted(bars)

    for day in days:
        if HOLDOUT_START <= day <= HOLDOUT_END:
            raise MaterializerError("HOLDOUT_TOUCH", f"session inside sealed holdout window: {day}")
        if day < DEV_START:
            raise MaterializerError("PRE_DEV_DATE", f"session before DEV_START {DEV_START}: {day}")
        if day.weekday() >= 5:
            raise MaterializerError("BAD_GRID", f"weekend session date: {day}")
        if day not in sessions:
            raise MaterializerError(
                "SESSION_NOT_IN_SCHEDULE",
                f"bar date {day} absent from pinned schedule; never infer a session, "
                "early close, or holiday from bar data",
            )
        expected = expected_anchors(sessions[day]["close"])
        actual = sorted(bars[day])
        if actual != expected:
            missing = [a for a in expected if a not in actual]
            extra = [a for a in actual if a not in expected]
            raise MaterializerError(
                "SCHEDULE_BAR_MISMATCH",
                f"session {day} (regular close {sessions[day]['close']}): "
                f"missing bars {missing}, extra bars {extra}; never fabricate or infer",
            )

    # Every pinned schedule session inside the supplied calendar span must
    # be fully present; a scheduled session with no bars at all fails
    # closed rather than being silently dropped from the fold calendar.
    if days:
        for day in sorted(sessions):
            if days[0] <= day <= days[-1] and day not in bars:
                raise MaterializerError(
                    "SCHEDULE_BAR_MISMATCH",
                    f"scheduled session {day} (regular close {sessions[day]['close']}) "
                    "has no bars; missing bars [] vs expected "
                    f"{expected_anchors(sessions[day]['close'])}",
                )

    n = len(days)
    if n < MIN_TRAIN_SESSIONS + OOS_BLOCK_SESSIONS:
        raise MaterializerError(
            "INSUFFICIENT_SESSIONS", f"{n} sessions < {MIN_TRAIN_SESSIONS + OOS_BLOCK_SESSIONS}"
        )

    folds = []
    k = 1
    while True:
        train_end_idx = MIN_TRAIN_SESSIONS + OOS_BLOCK_SESSIONS * (k - 1)
        oos_end_idx = train_end_idx + OOS_BLOCK_SESSIONS
        if oos_end_idx > n:
            break
        folds.append(
            {
                "fold": k,
                "train_start": days[0].isoformat(),
                "train_end": days[train_end_idx - 1].isoformat(),
                "train_sessions": train_end_idx,
                "oos_start": days[train_end_idx].isoformat(),
                "oos_end": days[oos_end_idx - 1].isoformat(),
                "oos_sessions": OOS_BLOCK_SESSIONS,
            }
        )
        k += 1

    early_close_sessions = [
        d.isoformat()
        for d in days
        if expected_anchors(sessions[d]["close"]) == ["09:30"]
    ]

    return {
        "materializer": "fold_materializer v2 (PREREGISTRATION_20261018_25 s1 as superseded by AMENDMENT_V3_20261018_27)",
        "input_timestamp_digest": hashlib.sha256("\n".join(timestamps).encode()).hexdigest(),
        "calendar_digest": hashlib.sha256("\n".join(d.isoformat() for d in days).encode()).hexdigest(),
        "schedule_sha256": schedule_sha256,
        "schedule_source": meta["source"],
        "schedule_version": meta["version"],
        "session_count": n,
        "early_close_sessions": early_close_sessions,
        "holdout_window_excluded": f"{HOLDOUT_START.isoformat()}..{HOLDOUT_END.isoformat()}",
        "dev_start": DEV_START.isoformat(),
        "min_train_sessions": MIN_TRAIN_SESSIONS,
        "oos_block_sessions": OOS_BLOCK_SESSIONS,
        "dropped_tail_sessions": n - (MIN_TRAIN_SESSIONS + OOS_BLOCK_SESSIONS * len(folds)),
        "folds": folds,
    }


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
