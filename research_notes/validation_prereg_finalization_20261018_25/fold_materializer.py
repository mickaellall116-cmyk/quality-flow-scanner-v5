"""Timestamp-only walk-forward fold-calendar materializer.

Frozen by PREREGISTRATION_20261018_25 section 1 (task
QF-VALIDATION-PREREG-FINALIZATION-20261018-25 r1). Pure standard library;
no market-data calendar package is used.

The materializer accepts ONLY bar timestamps (plus an optional set of
declared-holiday dates). It has no parameter or code path that accepts a
price, quantity, outcome, or performance value. Its canonical JSON output
must be produced and committed before any such field is supplied to any
downstream computation.

Fail-closed: any validation violation raises MaterializerError with a
named code and no output is produced.
"""

import hashlib
import json
from datetime import date, timedelta

HOLDOUT_START = date(2023, 10, 19)
HOLDOUT_END = date(2024, 9, 15)
DEV_START = date(2024, 9, 16)
GRID_TIMES = ("09:30", "13:30")
MIN_TRAIN_SESSIONS = 252
OOS_BLOCK_SESSIONS = 63


class MaterializerError(Exception):
    def __init__(self, code, detail):
        super().__init__(f"{code}: {detail}")
        self.code = code


def _parse(ts):
    if not isinstance(ts, str):
        raise MaterializerError("MALFORMED_TIMESTAMP", f"not a string: {type(ts).__name__}")
    try:
        day_s, time_s = ts.split("T")
        y, m, d = (int(p) for p in day_s.split("-"))
        day = date(y, m, d)
    except Exception:
        raise MaterializerError("MALFORMED_TIMESTAMP", f"unparseable: {ts!r}")
    if time_s not in GRID_TIMES:
        raise MaterializerError("BAD_GRID", f"bar time {time_s!r} not in grid {GRID_TIMES} ({ts!r})")
    return day, time_s


def materialize(timestamps, declared_holidays=frozenset()):
    """Materialize fold boundaries from bar timestamps only.

    timestamps: list of "YYYY-MM-DDTHH:MM" strings (America/New_York local).
    declared_holidays: set of "YYYY-MM-DD" strings for exchange holidays
    that legitimately explain missing Mon-Fri session dates.
    Returns a dict; serialization via canonical_json() is deterministic.
    """
    holidays = set()
    for h in declared_holidays:
        try:
            y, m, d = (int(p) for p in str(h).split("-"))
            holidays.add(date(y, m, d))
        except Exception:
            raise MaterializerError("MALFORMED_TIMESTAMP", f"unparseable holiday: {h!r}")

    parsed = [_parse(ts) for ts in timestamps]

    seen = set()
    for ts in timestamps:
        if ts in seen:
            raise MaterializerError("DUPLICATE_TIMESTAMP", ts)
        seen.add(ts)
    for prev, cur in zip(timestamps, timestamps[1:]):
        if not prev < cur:
            raise MaterializerError("NON_MONOTONIC", f"{prev!r} !< {cur!r}")

    sessions = {}
    for day, time_s in parsed:
        sessions.setdefault(day, []).append(time_s)
    days = sorted(sessions)

    for day in days:
        if HOLDOUT_START <= day <= HOLDOUT_END:
            raise MaterializerError("HOLDOUT_TOUCH", f"session inside sealed holdout window: {day}")
        if day < DEV_START:
            raise MaterializerError("PRE_DEV_DATE", f"session before DEV_START {DEV_START}: {day}")
        if day.weekday() >= 5:
            raise MaterializerError("BAD_GRID", f"weekend session date: {day}")
        if sorted(sessions[day]) != sorted(GRID_TIMES):
            raise MaterializerError("BAD_GRID", f"session {day} bars {sessions[day]} != grid {list(GRID_TIMES)}")

    for prev, cur in zip(days, days[1:]):
        probe = prev + timedelta(days=1)
        while probe < cur:
            if probe.weekday() < 5 and probe not in holidays:
                raise MaterializerError(
                    "UNRESOLVED_GAP", f"missing weekday session {probe} between {prev} and {cur}"
                )
            probe += timedelta(days=1)

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

    return {
        "materializer": "fold_materializer r1 (PREREGISTRATION_20261018_25 s1)",
        "input_timestamp_digest": hashlib.sha256("\n".join(timestamps).encode()).hexdigest(),
        "calendar_digest": hashlib.sha256("\n".join(d.isoformat() for d in days).encode()).hexdigest(),
        "session_count": n,
        "holdout_window_excluded": f"{HOLDOUT_START.isoformat()}..{HOLDOUT_END.isoformat()}",
        "dev_start": DEV_START.isoformat(),
        "min_train_sessions": MIN_TRAIN_SESSIONS,
        "oos_block_sessions": OOS_BLOCK_SESSIONS,
        "dropped_tail_sessions": n - (MIN_TRAIN_SESSIONS + OOS_BLOCK_SESSIONS * len(folds)),
        "folds": folds,
    }


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
