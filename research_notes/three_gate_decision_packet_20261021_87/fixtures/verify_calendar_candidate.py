#!/usr/bin/env python3
"""
verify_calendar_candidate.py — Gate 1 fixture for task -87.

INDEPENDENT verification of the -81 XNYS candidate extension artifact
against (a) its pinned sha256, (b) a from-first-principles regeneration
of the session list (weekday enumeration minus the closure sets stated
in the two official ICE releases), and (c) the pinned -35 r2 qualified
calendar (pin + abutment + union arithmetic).

Inputs are byte copies of the committed artifacts, carried in
fixtures/inputs/ with provenance:
  - XNYS_SESSION_SCHEDULE_CANDIDATE_EXTENSION_20261021_81.json
    origin/main research_notes/nyse_calendar_2023_evidence_20261021_81/
    (package commit 9c59ea1), sha256 8d659dde9ccb51b9d86d6c45759abceb...
  - XNYS_SESSION_SCHEDULE_V2.json
    origin/main research_notes/xnys_isolated_calendar_generation_20261019_35_r2/
    sha256 3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88

Closure / early-close sets used for regeneration are transcribed from
the instruments themselves (quoted in the -81 CAPTURE_MEMO):
  - ICE release Dec 21, 2022 (2023 column): closures 2023-01-02, 01-16,
    02-20, 04-07, 05-29, 06-19, 07-04, 09-04, 11-23, 12-25; early closes
    2023-07-03, 2023-11-24 (footnotes *, **). Footnote *** enumerates
    December early closes for 2024/2025 ONLY -> no Dec-2023 early close.
  - Pinned ICE release Nov 10, 2023 (2024 column, per -79/-81): closures
    in window 2024-01-01, 01-15, 02-19, 03-29, 05-27, 06-19, 07-04,
    09-02; early close 2024-07-03.
Window: 2023-10-19..2024-09-15 (-25 preregistration pin).

Offline, stdlib only. Prints PASS/FAIL per check; exit 1 on any FAIL.
"""
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
CAND_PATH = HERE / "inputs" / "XNYS_SESSION_SCHEDULE_CANDIDATE_EXTENSION_20261021_81.json"
V2_PATH = HERE / "inputs" / "XNYS_SESSION_SCHEDULE_V2.json"
CAND_SHA = "8d659dde9ccb51b9d86d6c45759abceb6ccd90ad7fa49e7478b13c2dc153a0a2"
V2_SHA = "3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88"

RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def main():
    # V1/V2 — pins.
    case("V1_candidate_pin", sha256(CAND_PATH) == CAND_SHA, sha256(CAND_PATH)[:16])
    case("V2_v2_pin", sha256(V2_PATH) == V2_SHA, sha256(V2_PATH)[:16])

    cand = json.loads(CAND_PATH.read_text())
    v2 = json.loads(V2_PATH.read_text())
    cs = cand["sessions"]
    vs = v2["sessions"]
    cdates = [s["date"] for s in cs]
    vdates = [s["date"] for s in vs]

    case("V2b_status_flag", cand.get("status") == "CANDIDATE_NOT_ADOPTED",
         f"status={cand.get('status')}")
    case("V2c_counts", len(cs) == 227 and len(vs) == 524,
         f"candidate={len(cs)} v2={len(vs)}")

    # V3 — independent regeneration of the extension session set.
    closures = {
        # 2023 in-window (ICE Dec-21-2022 release, 2023 column)
        "2023-11-23", "2023-12-25",
        # 2024 in-window (pinned Nov-10-2023 release, 2024 column)
        "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29",
        "2024-05-27", "2024-06-19", "2024-07-04", "2024-09-02",
    }
    regen = [d.isoformat() for d in daterange(date(2023, 10, 19), date(2024, 9, 15))
             if d.weekday() < 5 and d.isoformat() not in closures]
    case("V3_regen_set_equality", regen == cdates,
         f"regen={len(regen)} candidate={len(cdates)} "
         f"symdiff={sorted(set(regen) ^ set(cdates))[:5]}")

    # V4 — session shape: opens all 09:30; closes 16:00 except exactly
    # the two 13:00 early closes stated in the instruments.
    early = {s["date"]: s["close"] for s in cs if s["close"] != "16:00"}
    case("V4_early_closes_exact",
         early == {"2023-11-24": "13:00", "2024-07-03": "13:00"}, str(early))
    case("V4b_opens", all(s["open"] == "09:30" for s in cs), "all opens 09:30")

    # V5 — ordering / uniqueness / weekday-only.
    case("V5_sorted_unique_weekday",
         cdates == sorted(set(cdates))
         and all(date.fromisoformat(x).weekday() < 5 for x in cdates),
         f"first={cdates[0]} last={cdates[-1]}")

    # V6 — no December-2023 early close (footnote *** covers 2024/2025
    # only): Dec 22 and Dec 26, 2023 are regular 16:00 sessions.
    by_date = {s["date"]: s for s in cs}
    case("V6_no_dec2023_early_close",
         by_date["2023-12-22"]["close"] == "16:00"
         and by_date["2023-12-26"]["close"] == "16:00"
         and "2023-12-25" not in by_date and "2023-12-24" not in by_date,
         "12-22/12-26 regular; 12-25 closure absent")

    # V7 — boundary + union arithmetic with the qualified -35 artifact.
    case("V7_boundary_abuts",
         cdates[-1] == "2024-09-13" and vdates[0] == "2024-09-16"
         and date(2024, 9, 16).weekday() == 0,
         "candidate last Fri 2024-09-13; v2 first Mon 2024-09-16 (09-14/15 = weekend)")
    union = sorted(set(cdates) | set(vdates))
    case("V7b_union_751_disjoint",
         len(union) == 751 and not (set(cdates) & set(vdates)),
         f"union={len(union)} overlap={len(set(cdates) & set(vdates))}")
    case("V7c_v2_shape",
         vdates == sorted(set(vdates)) and vs[0]["open"] == "09:30"
         and vs[-1]["date"] == "2026-10-16",
         f"v2 span {vdates[0]}..{vdates[-1]}")

    # V8 — segment counts match the -81 REAUDIT (A: 50, B: 177).
    seg_a = [x for x in cdates if x <= "2023-12-31"]
    seg_b = [x for x in cdates if x >= "2024-01-01"]
    case("V8_segment_counts", len(seg_a) == 50 and len(seg_b) == 177,
         f"A={len(seg_a)} B={len(seg_b)}")

    n_fail = sum(1 for _, ok in RESULTS if not ok)
    print(f"\n{len(RESULTS) - n_fail}/{len(RESULTS)} PASS")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
