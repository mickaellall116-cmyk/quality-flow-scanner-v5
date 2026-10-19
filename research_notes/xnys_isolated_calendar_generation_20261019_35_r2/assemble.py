#!/usr/bin/env python3
"""Assembler for QF-XNYS-ISOLATED-CALENDAR-GENERATION-20261019-35 r1.

Compares emission A and emission C session-for-session (correlated
consistency check ONLY, per -30). If they differ in any element: writes
the disagreement log and exits 3 (HOLD). Else assembles the §4
XNYS_SESSION_SCHEDULE_V2 artifact, canonical-serializes it, writes it,
and prints its SHA-256.
"""
import hashlib
import json
import sys

SOURCE = ("QF-XNYS-ISOLATED-CALENDAR-GENERATION-20261019-35 r1"
          " + primary record packages -31/-32/-33")


def load(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def main():
    a_path, c_path, out_path, log_path = sys.argv[1:5]
    A = {(s["date"], s["open"], s["close"]) for s in load(a_path)}
    C = {(s["date"], s["open"], s["close"]) for s in load(c_path)}
    diff = sorted(A.symmetric_difference(C))
    if diff:
        with open(log_path, "w") as f:
            json.dump({"agreement": "DISAGREE",
                       "differences": [list(x) for x in diff]}, f, indent=1)
        print(f"DISAGREE: {len(diff)} differing elements -> HOLD")
        return 3
    sessions = [{"close": c, "date": d, "open": o} for (d, o, c) in sorted(A)]
    artifact = {
        "artifact": "XNYS_SESSION_SCHEDULE_V2",
        "coverage_end": "2026-10-16",
        "coverage_start": "2024-09-16",
        "exchange": "XNYS",
        "sessions": sessions,
        "source": SOURCE,
        "timezone": "America/New_York",
        "version": "1",
    }
    blob = (json.dumps(artifact, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True) + "\n").encode("utf-8")
    with open(out_path, "wb") as f:
        f.write(blob)
    with open(log_path, "w") as f:
        json.dump({"agreement": "AGREE", "differences": [],
                   "sessions": len(sessions)}, f, indent=1)
    print(f"AGREE sessions={len(sessions)} "
          f"artifact_sha256={hashlib.sha256(blob).hexdigest()} bytes={len(blob)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
