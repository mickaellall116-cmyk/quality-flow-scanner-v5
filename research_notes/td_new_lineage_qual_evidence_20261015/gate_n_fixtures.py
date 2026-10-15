"""Gate N fixture runner — QF-TD-NEW-LINEAGE-QUAL-20261015-01 r1.

Uses the pinned mechanism (validate_input.py @ f64d12f tree, sha256
1b83cdcd...) against the frozen expectations from the f95dc0e lineage
package. Exact equality only; any mismatch FAILs closed. Output is a
deterministic machine-readable JSON (no timestamps) so two runs can be
compared byte-for-byte.
"""
import copy
import json
import pathlib
import sys

TREE = pathlib.Path("/tmp/tdqual/tree_f64d12f")
sys.path.insert(0, str(TREE / "research_notes" / "pilot_harness"))

import pandas as pd  # noqa: E402
from validate_input import xnys_schedule, expected_1h_starts  # noqa: E402

EXPECTATIONS_PATH = pathlib.Path(
    "/home/hatch/workspace/quality-flow-scanner-v5/research_notes/"
    "td_calendar_lineage_evidence_20261014/fixture_expectations.json")


def compute(date_str):
    sched = xnys_schedule(pd.Timestamp(date_str, tz="America/New_York"))
    if sched is None:
        return {"session_open": False, "xnys_schedule": None,
                "open_utc": None, "close_utc": None,
                "bar_starts_et": [], "bar_starts_utc": [], "n_bars": 0}
    open_ts, close_ts = sched
    starts = expected_1h_starts(open_ts, close_ts)
    return {
        "session_open": True,
        "open_utc": open_ts.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "close_utc": close_ts.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bar_starts_et": [t.strftime("%H:%M") for t in starts],
        "bar_starts_utc": [t.tz_convert("UTC").strftime("%H:%M") for t in starts],
        "n_bars": len(starts),
    }


def check_date(exp):
    """Return (passed, computed) for one expected date entry."""
    got = compute(exp["date"])
    if exp["session"] in ("CLOSED", "NON_SESSION_WEEKEND"):
        ok = (got["xnys_schedule"] is None if "xnys_schedule" in got else True)
        ok = ok and got["session_open"] is False and got["n_bars"] == 0
        ok = ok and exp.get("expected_1h_bars") == 0
        return ok, got
    ok = got["session_open"] is True
    ok = ok and got["open_utc"] == exp["open_utc"]
    ok = ok and got["close_utc"] == exp["close_utc"]
    ok = ok and got["bar_starts_et"] == exp["bar_starts_et"]
    ok = ok and got["bar_starts_utc"] == exp["bar_starts_utc"]
    ok = ok and got["n_bars"] == exp["expected_1h_bars"]
    return ok, got


def evaluate(expectations):
    """Full FX-01..FX-04 evaluation; returns (all_pass, per-date results)."""
    results = {}
    all_pass = True
    for group, entries in expectations.items():
        results[group] = []
        for exp in entries:
            ok, got = check_date(exp)
            all_pass = all_pass and ok
            results[group].append(
                {"date": exp["date"], "expected_session": exp["session"],
                 "pass": ok, "computed": got})
    # FX-04 multi-day all-None conjunct: every date 2026-07-03..2026-07-05
    conjunct = all(
        xnys_schedule(pd.Timestamp(d, tz="America/New_York")) is None
        for d in ("2026-07-03", "2026-07-04", "2026-07-05"))
    results["FX-04_all_none_conjunct_2026-07-03_to_2026-07-05"] = conjunct
    all_pass = all_pass and conjunct
    return all_pass, results


def fx05_negative_controls(expectations):
    """FX-05: the comparator must FAIL on wrong expectations; a calendar
    that cannot be resolved must FAIL closed, never substitute."""
    controls = {}

    mutated = copy.deepcopy(expectations)  # +1h on one open instant
    mutated["FX-01_spring_dst"][0]["open_utc"] = "2025-03-07T15:30:00Z"
    ok, _ = evaluate(mutated)
    controls["NC1_shifted_open_instant_detected"] = (ok is False)

    mutated = copy.deepcopy(expectations)  # closed day claimed open
    mutated["FX-03_mixed_thanksgiving_window_SPT05_06"][1] = {
        "date": "2025-11-27", "session": "FULL",
        "open_utc": "2025-11-27T14:30:00Z", "close_utc": "2025-11-27T21:00:00Z",
        "bar_starts_et": ["09:30", "10:30", "11:30", "12:30", "13:30",
                          "14:30", "15:30"],
        "bar_starts_utc": ["14:30", "15:30", "16:30", "17:30", "18:30",
                           "19:30", "20:30"],
        "expected_1h_bars": 7}
    ok, _ = evaluate(mutated)
    controls["NC2_closed_day_claimed_open_detected"] = (ok is False)

    mutated = copy.deepcopy(expectations)  # one bar start off by a minute
    mutated["FX-03_mixed_thanksgiving_window_SPT05_06"][2][
        "bar_starts_utc"][3] = "17:31"
    ok, _ = evaluate(mutated)
    controls["NC3_bar_start_off_by_one_minute_detected"] = (ok is False)

    import pandas_market_calendars as mcal
    try:
        mcal.get_calendar("XNYS_DOES_NOT_EXIST")
        controls["NC4_unresolvable_calendar_fails_closed"] = False
    except Exception:
        controls["NC4_unresolvable_calendar_fails_closed"] = True

    return controls


def main():
    out_path = pathlib.Path(sys.argv[1])
    expectations = json.loads(EXPECTATIONS_PATH.read_text())
    all_pass, results = evaluate(expectations)
    controls = fx05_negative_controls(expectations)
    fx05_pass = all(controls.values())
    doc = {
        "suite": "Gate N fixtures FX-01..FX-05 (f95dc0e expectations)",
        "fx01_fx04_all_pass": all_pass,
        "per_date": results,
        "fx05_negative_controls": controls,
        "fx05_pass": fx05_pass,
        "verdict_inputs_pass": bool(all_pass and fx05_pass),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"out": str(out_path), "fx01_fx04_all_pass": all_pass,
                      "fx05_pass": fx05_pass}))
    return 0 if (all_pass and fx05_pass) else 1


if __name__ == "__main__":
    raise SystemExit(main())
