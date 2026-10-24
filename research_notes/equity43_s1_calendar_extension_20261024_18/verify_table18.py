#!/usr/bin/env python3
"""QF-EQUITY43-S1-CALENDAR-EXTENSION-20261024-18 — consumer verifier.

Fail-closed verification of the candidate extended session table
against its pin record. ANY mismatch returns STOP (nonzero exit):
  * table file SHA-256 != pinned table SHA;
  * pin-record field mismatch: timezone, artifact, calendar_version,
    superseded (prefix) table SHA, generator SHA, session counts;
  * structural violation: duplicate date, missing session (count or
    continuity break vs the pinned prefix), out-of-order dates,
    weekend session, open != 09:30, close not in {13:00, 16:00},
    first-751 rows not exactly the pinned prefix rows.
Used by the -18 tamper battery: every mutation class must STOP.
"""
import hashlib
import json
import sys
from datetime import date

EXPECTED_TZ = "America/New_York"


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def verify(table_path, pin_path, prefix_table_path, generator_path):
    """Returns (ok: bool, detail: dict). Never raises on bad input."""
    try:
        raw = open(table_path, "rb").read()
        pin = json.load(open(pin_path))
    except Exception as e:
        return False, {"reason": f"unreadable: {e}"}
    if _sha(raw) != pin["table_sha256"]:
        return False, {"reason": "table SHA mismatch"}
    if pin["timezone"] != EXPECTED_TZ:
        return False, {"reason": "timezone pin mismatch"}
    try:
        table = json.loads(raw)
    except Exception as e:
        return False, {"reason": f"table JSON invalid: {e}"}
    if table["artifact"] != pin["artifact"]:
        return False, {"reason": "artifact pin mismatch"}
    if table["calendar_version"] != pin["calendar_version"]:
        return False, {"reason": "calendar_version pin mismatch"}
    if table["session_count"] != pin["session_count"]:
        return False, {"reason": "session_count pin mismatch"}
    if pin["generator_sha256"] != _sha(open(generator_path, "rb").read()):
        return False, {"reason": "generator pin mismatch"}
    if pin["supersedes_table_sha256"] != _sha(
            open(prefix_table_path, "rb").read()):
        return False, {"reason": "source (prefix) pin mismatch"}
    rows = table["sessions"]
    if len(rows) != table["session_count"]:
        return False, {"reason": "row count != session_count"}
    dates = [r["date"] for r in rows]
    if dates != sorted(dates):
        return False, {"reason": "out-of-order session dates"}
    if len(set(dates)) != len(dates):
        return False, {"reason": "duplicate session date"}
    for r in rows:
        d = date.fromisoformat(r["date"])
        if d.weekday() >= 5:
            return False, {"reason": f"weekend session {r['date']}"}
        if r["open"] != "09:30" or r["close"] not in ("13:00", "16:00"):
            return False, {"reason": f"bad open/close on {r['date']}"}
    prefix = json.load(open(prefix_table_path))["sessions"]
    if rows[:len(prefix)] != prefix:
        return False, {"reason": "prefix rows not preserved"}
    return True, {"sessions": len(rows), "first": dates[0],
                  "last": dates[-1]}


def main():
    ok, detail = verify(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    print(("PASS " if ok else "STOP ") + json.dumps(detail, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
