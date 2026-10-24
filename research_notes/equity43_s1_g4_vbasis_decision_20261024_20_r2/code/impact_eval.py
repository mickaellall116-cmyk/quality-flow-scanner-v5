#!/usr/bin/env python3
"""
impact_eval.py — r2 item: prove exactly what the false AVGO row did.

Runs the r1 evaluation logic (copied unchanged from r1 rules_eval.py's
eval_leg) on the SAME pinned bytes under BOTH event tables:

  FALSE  = r1's committed table (AVGO/DEV declared 2024-10-11 x10)
  FIXED  = r2's corrected source-attested table (AVGO: no DEV event)

and diffs: the AVGO/DEV leg record field by field, the positive-
control set, and the full DEV43 census totals. The FALSE run is first
checked against r1's committed evidence (evidence/rules_eval.json of
the r1 package, commit b1d3661) — if it does not reproduce r1 exactly,
the comparison is not apples-to-apples and this script exits nonzero.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (PKG, chk, load_sessions, window_sessions, load_frame,
                    admit, session_totals, DECLARED_SPLITS_DEV,
                    R1_DECLARED_SPLITS_DEV)
from rules_eval import rc_breaks, PILOT_STORE, CAPTURE_STORE, TABLE

R1_EVIDENCE = (Path("/home/hatch/workspace/qf_td20r2_stage/research_notes")
               / "equity43_s1_g4_vbasis_decision_20261024_20"
               / "evidence" / "rules_eval.json")


def eval_leg(sym, win, store, sessions, table):
    sw = window_sessions(sessions, win)
    path = (store / "raw" / f"{sym}__{win}.json") if store == PILOT_STORE \
        else (store / f"{sym}__{win}.json")
    frame = load_frame(path)
    admitted, _ = admit(frame, sw)
    splits = table.get((sym, win), [])
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
        "vbasis_boundaries": sorted(f["boundary"] for f in vb),
        "RB_corroborated_breaks": corroborated,
        "RB_notes": len(vb) - len(corroborated),
        "RC_breaks": breaks_c, "RC_untestable_boundaries": untestable_c,
    }


def census(sessions, table):
    census_syms = sorted(p.stem.replace("__DEV", "") for p in
                         CAPTURE_STORE.glob("*__DEV.json"))
    legs = [eval_leg(s, "DEV", CAPTURE_STORE, sessions, table)
            for s in census_syms]
    legs += [eval_leg(s, "DEV", PILOT_STORE, sessions, table)
             for s in ["NVDA", "TSLA", "AAPL", "SPY"]]
    totals = {
        "legs": len(legs),
        "RA_flag_total": sum(r["RA_vbasis_flags"] for r in legs),
        "RA_legs_flagged": sum(1 for r in legs if r["RA_vbasis_flags"]),
        "RB_break_total": sum(len(r["RB_corroborated_breaks"]) for r in legs),
        "RB_legs_with_break": sum(1 for r in legs
                                  if r["RB_corroborated_breaks"]),
        "RC_break_total": sum(len(r["RC_breaks"]) for r in legs),
        "RC_legs_with_break": sum(1 for r in legs if r["RC_breaks"]),
        "step_all_legs": sum(1 for r in legs if r["step_all_count"]),
        "step_all_total": sum(r["step_all_count"] for r in legs)}
    return legs, totals


def slim(r):
    return {k: r[k] for k in ("leg", "rows_admitted", "completeness",
                              "step", "volume_notes", "step_all_count",
                              "RA_vbasis_flags", "RB_notes",
                              "RC_untestable_boundaries")}


def main():
    sessions, _, _ = load_sessions(TABLE)
    r1 = json.loads(R1_EVIDENCE.read_bytes())

    # 1) FALSE-table AVGO/DEV must reproduce r1's committed record.
    avgo_false = eval_leg("AVGO", "DEV", CAPTURE_STORE, sessions,
                          R1_DECLARED_SPLITS_DEV)
    r1_avgo = [r for r in r1["controls"]["positive"]
               if r["leg"] == "AVGO/DEV"][0]
    repro_fields = {}
    for k in ("rows_admitted", "completeness", "step", "volume_notes",
              "step_all_count", "RA_vbasis_flags", "RB_notes"):
        repro_fields[k] = (avgo_false[k] == r1_avgo[k])
    rb_false_n = len(avgo_false["RB_corroborated_breaks"])
    repro_fields["RB_breaks"] = (
        rb_false_n == len(r1_avgo["RB_corroborated_breaks"]))
    repro_fields["RC_breaks"] = (
        avgo_false["RC_breaks"] == r1_avgo["RC_breaks"])
    repro_ok = all(repro_fields.values())
    print("FALSE-table AVGO/DEV reproduces r1 committed record:",
          repro_ok, json.dumps(repro_fields))

    # 2) FIXED-table AVGO/DEV on the same bytes.
    avgo_fixed = eval_leg("AVGO", "DEV", CAPTURE_STORE, sessions,
                          DECLARED_SPLITS_DEV)

    # 3) Census under both tables.
    legs_false, tot_false = census(sessions, R1_DECLARED_SPLITS_DEV)
    legs_fixed, tot_fixed = census(sessions, DECLARED_SPLITS_DEV)
    repro_census = (tot_false == r1["census_totals"])
    print("FALSE-table census reproduces r1 census totals:", repro_census)

    changed_legs = []
    fixed_by_leg = {r["leg"]: r for r in legs_fixed}
    for rf in legs_false:
        rx = fixed_by_leg[rf["leg"]]
        diff = {}
        for k in ("step", "volume_notes", "step_all_count",
                  "RA_vbasis_flags", "RB_notes", "RC_untestable_boundaries"):
            if rf[k] != rx[k]:
                diff[k] = {"false": rf[k], "fixed": rx[k]}
        if len(rf["RB_corroborated_breaks"]) != len(rx["RB_corroborated_breaks"]):
            diff["RB_breaks"] = {"false": len(rf["RB_corroborated_breaks"]),
                                 "fixed": len(rx["RB_corroborated_breaks"])}
        if rf["RC_breaks"] != rx["RC_breaks"]:
            diff["RC_breaks"] = {"false": rf["RC_breaks"],
                                 "fixed": rx["RC_breaks"]}
        if diff:
            changed_legs.append({"leg": rf["leg"], "diff": diff})

    out = {
        "apples_to_apples": {"avgo_record_reproduced": repro_ok,
                             "avgo_fields": repro_fields,
                             "census_totals_reproduced": repro_census},
        "avgo_dev_false_table": {**slim(avgo_false),
                                 "RB_breaks": rb_false_n,
                                 "RC_breaks": avgo_false["RC_breaks"],
                                 "vbasis_at_2024-10-11":
                                     "2024-10-11" in
                                     avgo_false["vbasis_boundaries"]},
        "avgo_dev_fixed_table": {**slim(avgo_fixed),
                                 "RB_breaks":
                                     len(avgo_fixed["RB_corroborated_breaks"]),
                                 "RC_breaks": avgo_fixed["RC_breaks"],
                                 "vbasis_at_2024-10-11":
                                     "2024-10-11" in
                                     avgo_fixed["vbasis_boundaries"]},
        "census_false_table": tot_false,
        "census_fixed_table": tot_fixed,
        "census_legs_changed": changed_legs,
        "positive_controls": {
            "r1_denominator": 3,
            "r1_set": ["NVDA/HO", "AVGO/DEV", "NFLX/DEV"],
            "r2_denominator": 2,
            "r2_set": ["NVDA/HO", "NFLX/DEV"],
            "avgo_excluded_reason": ("attested first split-adjusted "
                                     "trading date 2024-07-15 precedes "
                                     "the DEV window (starts 2024-09-16)")},
    }
    print("AVGO false:", json.dumps(out["avgo_dev_false_table"])[:400])
    print("AVGO fixed:", json.dumps(out["avgo_dev_fixed_table"])[:400])
    print("CENSUS false:", json.dumps(tot_false))
    print("CENSUS fixed:", json.dumps(tot_fixed))
    print("LEGS CHANGED:", json.dumps([c["leg"] for c in changed_legs]))
    (PKG / "evidence" / "impact.json").write_text(
        json.dumps(out, indent=1, default=str))
    if not (repro_ok and repro_census):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
