#!/usr/bin/env python3
"""
negative_tests.py — task item 2: lane-separation negative tests on
synthetic fixtures built on the pinned session table (60 consecutive
DEV sessions from 2024-09-16; 7 hourly bars per session, flat price
100.00 unless the fixture says otherwise).

  NT-1  completeness failure cannot become a convention failure:
        one session's bars removed + three zero-volume price-moving
        bars; volumes otherwise continuous. Expect completeness FAIL,
        convention PASS, and no R-B/R-C break.
  NT-2  a standalone gradual volume-regime move cannot be labeled a
        discrete split/basis break without corroboration: volume
        ramps +10%/session for the whole span (a smooth regime drift,
        no discrete step, flat prices, complete grid). The CURRENT
        R-A lane is expected to flag it (documented failure mode,
        fail-before). Under R-B it must remain a NOTE (no price/event
        corroboration exists); under R-C the stability conditions
        must reject it (no stable pre/post plateaus).
  NT-3  lane independence, other direction: an undeclared
        factor-shaped PRICE step (synthetic 2:1 split signature at
        one boundary, volumes continuous). Expect completeness PASS
        and a STEP-ALL convention suspect from the price lane alone.
  NT-4  sensitivity probe (not a negative test; the honesty anchor):
        a discrete x3 volume step at one boundary, flat prices, no
        declared event. R-A flags it; R-B leaves it a NOTE (this is
        R-B's disclosed sensitivity limit — a price-silent vendor
        volume-basis change is indistinguishable from a market regime
        shift on volume alone); R-C flags it (step shape present).
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PKG, chk, load_sessions, session_totals
from rules_eval import rc_breaks, in_band

TABLE = (Path("/home/hatch/workspace/qf_td20_stage/wt/research_notes")
         / "shadow_closeout_20261022" / "session_table.json")
N_SESSIONS = 60


def build(sessions_w, volume_fn, price_fn=None, drop_session=None,
          zero_vol_moving=()):
    dates = sorted(sessions_w)[:N_SESSIONS]
    rows, idx = [], []
    for si, d in enumerate(dates):
        if drop_session is not None and si == drop_session:
            continue
        day = pd.Timestamp(d).tz_localize("America/New_York")
        starts = chk._expected_starts(day, sessions_w[d])
        total = volume_fn(si)
        per_bar = total / len(starts)
        for bi, ts in enumerate(starts):
            o = price_fn(si, bi) if price_fn else 100.0
            v = per_bar
            if (si, bi) in zero_vol_moving:
                # zero volume but close != open: price-moving defect bar
                rows.append({"Open": 100.0, "High": 101.0, "Low": 100.0,
                             "Close": 101.0, "Volume": 0.0})
                idx.append(ts)
                continue
            rows.append({"Open": o, "High": o, "Low": o, "Close": o,
                         "Volume": v})
            idx.append(ts)
    return pd.DataFrame(rows, index=pd.DatetimeIndex(idx)), dates


def lanes(res):
    return {"completeness": res["completeness_verdict"],
            "convention": res["convention_verdict"],
            "vbasis_flags": len(res["vbasis"]["results"]),
            "step_all": len(res["step_all"]["results"])}


def main():
    sessions, _, _ = load_sessions(TABLE)
    lo = sorted(d for d in sessions if d.isoformat() >= "2024-09-16")
    sw = {d: sessions[d] for d in lo[:N_SESSIONS]}
    out = {}

    # NT-1: completeness defects, continuous volumes/prices
    frame, _ = build(sw, lambda si: 700_000.0, drop_session=30,
                     zero_vol_moving={(10, 0), (10, 1), (10, 2)})
    res = chk.run_check(frame, sw, [], instrument="equity")
    totals = session_totals(frame)
    brk, _u = rc_breaks(totals, set())
    out["NT1"] = {**lanes(res), "RC_breaks": len(brk),
                  "expect": "completeness FAIL, convention PASS, RC 0"}
    print("NT1:", json.dumps(out["NT1"]))

    # NT-2: gradual ramp +10%/session
    frame, _ = build(sw, lambda si: 700_000.0 * (1.10 ** si))
    res = chk.run_check(frame, sw, [], instrument="equity")
    totals = session_totals(frame)
    brk, _u = rc_breaks(totals, set())
    sa = len(res["step_all"]["results"])
    out["NT2"] = {**lanes(res), "RC_breaks": len(brk),
                  "RB_disposition": "NOTE_ONLY" if sa == 0 else "CORROBORATED",
                  "expect": "RA flags (failure mode); RB NOTE_ONLY; RC 0"}
    print("NT2:", json.dumps(out["NT2"]))

    # NT-3: undeclared 2:1 price step at session 30, volumes continuous
    def split_price(si, bi):
        return 100.0 if si < 30 else 50.0
    frame, _ = build(sw, lambda si: 700_000.0, price_fn=split_price)
    res = chk.run_check(frame, sw, [], instrument="equity")
    out["NT3"] = {**lanes(res),
                  "expect": "completeness PASS, STEP-ALL suspect >= 1"}
    print("NT3:", json.dumps(out["NT3"]))

    # NT-4: discrete x3 volume step at session 30, flat prices
    frame, _ = build(sw, lambda si: 700_000.0 if si < 30 else 2_100_000.0)
    res = chk.run_check(frame, sw, [], instrument="equity")
    totals = session_totals(frame)
    brk, _u = rc_breaks(totals, set())
    out["NT4"] = {**lanes(res), "RC_breaks": len(brk),
                  "expect": "RA flags; RC flags (step shape); RB NOTE_ONLY"}
    print("NT4:", json.dumps(out["NT4"]))

    checks = {
        "NT1_lane_separation": out["NT1"]["completeness"] == "FAIL"
        and out["NT1"]["convention"] == "PASS" and out["NT1"]["RC_breaks"] == 0,
        "NT2_RA_failure_mode_documented": out["NT2"]["vbasis_flags"] >= 1,
        "NT2_RB_note_only": out["NT2"]["RB_disposition"] == "NOTE_ONLY",
        "NT2_RC_rejects_ramp": out["NT2"]["RC_breaks"] == 0,
        "NT3_price_lane_independent": out["NT3"]["completeness"] == "PASS"
        and out["NT3"]["step_all"] >= 1,
        "NT4_RC_sensitive_to_step": out["NT4"]["RC_breaks"] >= 1
        and out["NT4"]["vbasis_flags"] >= 1,
    }
    out["checks"] = checks
    out["all_checks_pass"] = all(checks.values())
    print("CHECKS:", json.dumps(checks), "ALL:", out["all_checks_pass"])
    (PKG / "evidence" / "negative_tests.json").write_text(
        json.dumps(out, indent=1, default=str))
    if not out["all_checks_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
