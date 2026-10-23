#!/usr/bin/env python3
"""Synthetic signal-contract checks, offline only."""
from staged_signal_parity_probe import verify
BASE = {"symbol": "TEST", "signal_bar_start_at": "2026-10-22T09:30:00-04:00",
        "signal_bar_close_at": "2026-10-22T13:30:00-04:00",
        "v54_rule_version": "2026-09-15-v54"}
def row(**kw):
    x = dict(BASE, **kw)
    x["signal_id"] = f'v54:{x["symbol"]}:4h:{x["signal_bar_close_at"]}:{x["v54_rule_version"]}'
    return x
def case(name, x, verdict, failure=None):
    z = verify([x])
    assert z["verdict"] == verdict, (name, z)
    if failure:
        assert failure in z["failures"], (name, z)
    print("PASS", name)
def main():
    case("clean canonical", row(), "PASS")
    case("off-grid historical", row(signal_bar_start_at="2026-10-22T10:30:00-04:00",
          signal_bar_close_at="2026-10-22T14:30:00-04:00"), "HOLD", "off_frozen_0930_1330_grid")
    case("short final bin", row(signal_bar_start_at="2026-10-22T14:30:00-04:00",
          signal_bar_close_at="2026-10-22T16:00:00-04:00"), "HOLD", "not_exact_four_hours")
    case("naive timestamp", row(signal_bar_start_at="2026-10-22T09:30:00"), "HOLD", "missing_or_naive_stamps")
    forged = row()
    forged["signal_id"] = "arbitrary"
    case("forged ID", forged, "HOLD", "noncanonical_signal_id")
    assert verify([row(), row()])["failures"]["duplicate_signal_id"] == 1
    print("PASS duplicate ID")
    z = verify({"assessments": [{"features": row()}]})
    assert z["verdict"] == "PASS" and z["container"] == "assessment_features"
    print("PASS assessment export schema")
    print("7/7 checks PASS")
if __name__ == "__main__":
    main()
