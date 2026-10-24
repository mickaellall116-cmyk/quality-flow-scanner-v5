#!/usr/bin/env python3
"""
rules_eval.py — r2 recompute (governing: Issue #1 comment
6384407724): the SAME preregistered non-return decision rules as r1,
on the corrected source-attested event table, and each rule's
disposition of the already captured EQUITY43 DEV bytes. No new rule,
no threshold change. The only differences from r1's script are the
event table (imported from r2 common.py), the positive-control set
(AVGO removed — see below), and the session-table path (same pinned
bytes).

Rules (fully specified in PACKET.md BEFORE this script was executed):
  R-A  current fixed band — the checker's VBASIS lane as-is
       (band 1.5, 5-session medians, undeclared boundaries):
       any flag -> CONVENTION_BREAK_SUSPECT.
  R-B  declared-action / STEP corroboration — a VBASIS flag stands as
       a convention break ONLY if the same boundary carries price-side
       corroboration (a STEP-ALL factor-shaped suspect at the same
       boundary date, a declared event at that boundary, or the
       declared-boundary note-mismatch rule). Uncorroborated flags are
       VOLUME_REGIME_NOTE (information, never a failure). Declared
       boundaries keep the existing STEP + NOTES lanes unchanged.
  R-C  event-free step-shape rule — an undeclared boundary is a break
       iff (i) the VBASIS 5-session ratio is outside [1/1.5, 1.5],
       (ii) the pre-window is stable (median of the 5 pre sessions vs
       median of the 20 sessions before them inside the band), and
       (iii) the post-window is stable (median of sessions +5..+25 vs
       median of the first 5 post sessions inside the band).
       Boundaries without 25 sessions on both sides are UNTESTABLE,
       never breaks. No events, no prices, no returns are consulted.

Controls (predeclared):
  NEGATIVE (no declared split/basis event in window): NVDA/DEV,
  TSLA/HO, TSLA/DEV, AAPL/HO, AAPL/DEV, SPY/HO, SPY/DEV.
  POSITIVE (declared split, source-attested, in-window): NVDA/HO
  (pilot), NFLX/DEV (capture store) — denominator 2. AVGO is NOT a
  positive control in r2: its attested split-adjusted date
  (2024-07-15) precedes the DEV window, and r1's in-window AVGO row
  was false. AVGO/DEV is still evaluated in the census as an ordinary
  leg with no declared event. SMCI is not a control: its DEV leg was
  never captured (separate line in -11) and its HO body is not read
  under this task's bounds.
Census: all 43 EQUITY43 DEV legs (39 capture + 4 pilot).
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (PKG, chk, load_sessions, window_sessions, load_frame,
                    admit, session_totals, DECLARED_SPLITS_DEV)

PILOT_STORE = Path("/home/hatch/workspace/qf_td_pilot_20261023/store")
CAPTURE_STORE = Path("/home/hatch/workspace/qf_td11_stage/store/raw")
TABLE = (Path("/home/hatch/workspace/qf_td20r2_stage/wt/research_notes")
         / "shadow_closeout_20261022" / "session_table.json")
BAND = 1.5
NEGATIVE = [("NVDA", "DEV"), ("TSLA", "HO"), ("TSLA", "DEV"),
            ("AAPL", "HO"), ("AAPL", "DEV"), ("SPY", "HO"), ("SPY", "DEV")]
POSITIVE = [("NVDA", "HO", PILOT_STORE),
            ("NFLX", "DEV", CAPTURE_STORE)]


def in_band(r):
    return (1.0 / BAND) <= r <= BAND


def rc_breaks(totals, declared_dates):
    """R-C step-shape breaks + untestable count over session totals."""
    dates = [d for d, _ in totals]
    vals = [v for _, v in totals]
    breaks, untestable = [], 0
    for i in range(1, len(vals)):
        if str(dates[i]) in declared_dates:
            continue
        if i < 25 or i + 25 > len(vals):
            # still counts as scanned-by-VBASIS if VBASIS could flag it;
            # R-C simply cannot judge it
            if 1 <= i and len(vals[i:i + 5]) >= 5:
                untestable += 1
            continue
        pre5 = statistics.median(vals[i - 5:i])
        post5 = statistics.median(vals[i:i + 5])
        if pre5 == 0:
            continue
        ratio5 = post5 / pre5
        if in_band(ratio5):
            continue
        pre_stab = statistics.median(vals[i - 25:i - 5])
        post_stab = statistics.median(vals[i + 5:i + 25])
        if pre_stab == 0 or post5 == 0:
            continue
        if in_band(pre5 / pre_stab) and in_band(post_stab / post5):
            breaks.append({"boundary": str(dates[i]),
                           "observed_ratio": round(ratio5, 6)})
    return breaks, untestable


def eval_leg(sym, win, store, sessions):
    sw = window_sessions(sessions, win)
    path = (store / "raw" / f"{sym}__{win}.json") if store == PILOT_STORE \
        else (store / f"{sym}__{win}.json")
    frame = load_frame(path)
    admitted, _ = admit(frame, sw)
    splits = DECLARED_SPLITS_DEV.get((sym, win), [])
    res = chk.run_check(admitted, sw, splits, instrument="equity")
    totals = session_totals(admitted)
    declared_dates = {d for d, _ in splits}
    vb = res["vbasis"]["results"]
    sa_dates = set()
    for s in res["step_all"]["results"]:
        for k in ("boundary", "date", "session", "effective"):
            if k in s:
                sa_dates.add(str(s[k])[:10])
    corroborated = [f for f in vb if f["boundary"] in sa_dates
                    or f["boundary"] in declared_dates]
    breaks_c, untestable_c = rc_breaks(totals, declared_dates)
    return {
        "leg": f"{sym}/{win}", "rows_admitted": len(admitted),
        "completeness": res["completeness_verdict"],
        "step": res["step"]["results"], "volume_notes": res["volume_notes"],
        "step_all_count": len(res["step_all"]["results"]),
        "step_all": res["step_all"]["results"],
        "RA_vbasis_flags": len(vb),
        "RB_corroborated_breaks": corroborated,
        "RB_notes": len(vb) - len(corroborated),
        "RC_breaks": breaks_c, "RC_untestable_boundaries": untestable_c,
    }


def main():
    sessions, _, _ = load_sessions(TABLE)
    out = {"controls": {"negative": [], "positive": []}, "census_DEV43": []}
    for sym, win in NEGATIVE:
        r = eval_leg(sym, win, PILOT_STORE, sessions)
        out["controls"]["negative"].append(r)
        print(f"NEG {r['leg']}: RA={r['RA_vbasis_flags']} "
              f"RB_breaks={len(r['RB_corroborated_breaks'])} "
              f"RC={len(r['RC_breaks'])} step_all={r['step_all_count']}")
    for sym, win, store in POSITIVE:
        r = eval_leg(sym, win, store, sessions)
        out["controls"]["positive"].append(r)
        print(f"POS {r['leg']}: step={json.dumps(r['step'])[:160]} "
              f"notes={json.dumps(r['volume_notes'])[:120]} "
              f"RA={r['RA_vbasis_flags']} RC={len(r['RC_breaks'])}")
    census_syms = sorted(p.stem.replace("__DEV", "") for p in
                         CAPTURE_STORE.glob("*__DEV.json"))
    pilot_dev = ["NVDA", "TSLA", "AAPL", "SPY"]
    for sym in census_syms:
        r = eval_leg(sym, "DEV", CAPTURE_STORE, sessions)
        out["census_DEV43"].append(r)
    for sym in pilot_dev:
        r = eval_leg(sym, "DEV", PILOT_STORE, sessions)
        out["census_DEV43"].append(r)
    tot_ra = sum(r["RA_vbasis_flags"] for r in out["census_DEV43"])
    tot_rb = sum(len(r["RB_corroborated_breaks"]) for r in out["census_DEV43"])
    tot_rc = sum(len(r["RC_breaks"]) for r in out["census_DEV43"])
    legs_ra = sum(1 for r in out["census_DEV43"] if r["RA_vbasis_flags"])
    legs_rb = sum(1 for r in out["census_DEV43"] if r["RB_corroborated_breaks"])
    legs_rc = sum(1 for r in out["census_DEV43"] if r["RC_breaks"])
    legs_sa = sum(1 for r in out["census_DEV43"] if r["step_all_count"])
    out["census_totals"] = {
        "legs": len(out["census_DEV43"]),
        "RA_flag_total": tot_ra, "RA_legs_flagged": legs_ra,
        "RB_break_total": tot_rb, "RB_legs_with_break": legs_rb,
        "RC_break_total": tot_rc, "RC_legs_with_break": legs_rc,
        "step_all_legs": legs_sa,
        "step_all_total": sum(r["step_all_count"] for r in out["census_DEV43"])}
    print("CENSUS:", json.dumps(out["census_totals"]))
    (PKG / "evidence" / "rules_eval.json").write_text(
        json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
