#!/usr/bin/env python3
"""
event_table_tests.py — r2 fail-before/after + rejection tests
(governing: Issue #1 comment 6384407724, item 3).

  ET-1  FAIL-BEFORE: under r1's false table, the AVGO/DEV leg carries
        a declared-boundary STEP record at 2024-10-11 classified
        CONTINUOUS_ADJUSTED with an UNSCALED volume note and
        basis_mismatch False — i.e. the false row manufactured a
        handled positive control — and the boundary is suppressed
        from the ordinary lanes (no VBASIS judgment at 2024-10-11 is
        possible, because the checker skips declared dates).
  ET-2  FAIL-AFTER: under the corrected attested table, AVGO/DEV has
        no STEP record and no volume note at all; 2024-10-11 is an
        ordinary boundary judged by the ordinary lanes.
  ET-3  The R-B-relevant classification changes: the set of positive
        controls drops AVGO/DEV (denominator 3 -> 2), and AVGO's
        R-B disposition becomes that of an ordinary no-event leg
        (every VBASIS flag a note unless STEP-ALL corroborates).
  ET-4  The false row itself is rejected by the corrected machinery:
        validate_declared("AVGO","DEV",[("2024-10-11",10)]) exits.
  ET-5  An attested but out-of-window event is rejected rather than
        silently used: validate_declared("AVGO","DEV",
        [("2024-07-15",10)]) exits.
  ET-6  An unattested symbol/event is rejected:
        validate_declared("MSFT","DEV",[("2025-01-01",2)]) exits.
  ET-7  The corrected controls validate: NVDA/HO (2024-06-10 x10) and
        NFLX/DEV (2025-11-17 x10) pass validation, and
        leg_declared("AVGO","DEV") is empty.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (PKG, load_sessions, validate_declared, leg_declared,
                    DECLARED_SPLITS_DEV, R1_DECLARED_SPLITS_DEV)
from impact_eval import eval_leg
from rules_eval import CAPTURE_STORE, TABLE


def rejected(sym, win, splits):
    try:
        validate_declared(sym, win, splits)
    except SystemExit:
        return True
    return False


def main():
    sessions, _, _ = load_sessions(TABLE)
    avgo_false = eval_leg("AVGO", "DEV", CAPTURE_STORE, sessions,
                          R1_DECLARED_SPLITS_DEV)
    avgo_fixed = eval_leg("AVGO", "DEV", CAPTURE_STORE, sessions,
                          DECLARED_SPLITS_DEV)

    step_f = avgo_false["step"]
    checks = {
        "ET1_false_row_manufactures_control":
            len(step_f) == 1
            and step_f[0]["effective"] == "2024-10-11"
            and step_f[0]["classification"] == "CONTINUOUS_ADJUSTED"
            and step_f[0]["basis_mismatch"] is False
            and avgo_false["volume_notes"][0]["note"] == "UNSCALED"
            and "2024-10-11" not in avgo_false["vbasis_boundaries"],
        "ET2_corrected_table_no_declared_record":
            avgo_fixed["step"] == [] and avgo_fixed["volume_notes"] == [],
        "ET3_positive_denominator_3_to_2":
            len(R1_DECLARED_SPLITS_DEV) == 3
            and all(k != ("AVGO", "DEV") for k in DECLARED_SPLITS_DEV)
            and len([1 for k in DECLARED_SPLITS_DEV]) == 2,
        "ET4_false_row_rejected":
            rejected("AVGO", "DEV", [("2024-10-11", 10)]),
        "ET5_out_of_window_attested_rejected":
            rejected("AVGO", "DEV", [("2024-07-15", 10)]),
        "ET6_unattested_rejected":
            rejected("MSFT", "DEV", [("2025-01-01", 2)]),
        "ET7_corrected_controls_validate":
            validate_declared("NVDA", "HO", [("2024-06-10", 10)])
            == [("2024-06-10", 10)]
            and validate_declared("NFLX", "DEV", [("2025-11-17", 10)])
            == [("2025-11-17", 10)]
            and leg_declared("AVGO", "DEV") == [],
    }
    out = {"checks": checks, "all_checks_pass": all(checks.values()),
           "avgo_false_step": step_f,
           "avgo_false_notes": avgo_false["volume_notes"],
           "avgo_fixed_step": avgo_fixed["step"],
           "avgo_fixed_notes": avgo_fixed["volume_notes"],
           "avgo_RA_false": avgo_false["RA_vbasis_flags"],
           "avgo_RA_fixed": avgo_fixed["RA_vbasis_flags"],
           "avgo_RC_false": len(avgo_false["RC_breaks"]),
           "avgo_RC_fixed": len(avgo_fixed["RC_breaks"])}
    print(json.dumps(out, indent=1, default=str))
    (PKG / "evidence" / "event_table_tests.json").write_text(
        json.dumps(out, indent=1, default=str))
    if not out["all_checks_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
