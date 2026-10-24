#!/usr/bin/env python3
"""
reproduce.py — task item 1: mechanically reproduce the VBASIS lane on
the pinned pilot inputs and prove the reported control facts against
the -02 committed checker_report.json (counts re-derived here from the
store bytes; the committed report is the comparison target, never an
input to the computation). SMCI/HO is NOT read (governing bound: no
SMCI body reads); its -02 classification stands as prior record only.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (PKG, chk, load_sessions, window_sessions, load_frame,
                    admit, verify_checker_pin, DECLARED_SPLITS_PILOT)

PILOT_STORE = Path("/home/hatch/workspace/qf_td_pilot_20261023/store")
TABLE = (Path("/home/hatch/workspace/qf_td20_stage/wt/research_notes")
         / "shadow_closeout_20261022" / "session_table.json")
COMMITTED_REPORT = (Path("/home/hatch/workspace/qf_td20_stage/wt/research_notes")
                    / "td_pilot_adjudication_20261023_02" / "checker_report.json")
LEGS = [("NVDA", "HO"), ("NVDA", "DEV"), ("TSLA", "HO"), ("TSLA", "DEV"),
        ("AAPL", "HO"), ("AAPL", "DEV"), ("SPY", "HO"), ("SPY", "DEV")]


def lane_summary(res):
    return {
        "overall": res["overall"],
        "completeness_verdict": res["completeness_verdict"],
        "convention_verdict": res["convention_verdict"],
        "count_verdict": res["count"]["verdict"],
        "anomaly_count": len(res["anomaly"]["price_moving_zero_volume"])
        + len(res["anomaly"]["defect_bars"]),
        "step": res["step"]["results"],
        "volume_notes": res["volume_notes"],
        "step_all_suspects": res["step_all"]["results"],
        "vbasis_suspects": res["vbasis"]["results"],
        "vbasis_count": len(res["vbasis"]["results"]),
    }


def main():
    checker_sha = verify_checker_pin()
    sessions, table_sha, cal_ver = load_sessions(TABLE)
    committed = {leg["leg"]: leg for leg in
                 json.loads(COMMITTED_REPORT.read_bytes())["legs"]}
    out = {"checker_sha256": checker_sha, "checker_version": chk.CHECKER_VERSION,
           "session_table_sha256": table_sha, "calendar_version": cal_ver,
           "legs": []}
    all_match = True
    for sym, win in LEGS:
        sw = window_sessions(sessions, win)
        path = PILOT_STORE / "raw" / f"{sym}__{win}.json"
        frame = load_frame(path)
        admitted, excluded = admit(frame, sw)
        splits = DECLARED_SPLITS_PILOT.get((sym, win), [])
        res = chk.run_check(admitted, sw, splits, instrument="equity")
        ls = lane_summary(res)
        c = committed[f"{sym}/{win}"]["admitted_check"]
        match = {
            "rows_admitted": len(admitted) == committed[f"{sym}/{win}"]["rows_admitted"],
            "vbasis_count": ls["vbasis_count"] == c["vbasis_suspects"],
            "step_all_count": len(ls["step_all_suspects"]) == c["step_all_suspects"],
            "overall": ls["overall"] == c["overall"],
            "completeness": ls["completeness_verdict"] == c["completeness_verdict"],
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()
            == committed[f"{sym}/{win}"]["source_sha256"],
        }
        if not all(match.values()):
            all_match = False
        out["legs"].append({
            "leg": f"{sym}/{win}",
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rows_raw": len(frame), "rows_admitted": len(admitted),
            "rows_excluded": len(excluded), "lanes": ls,
            "matches_committed_02_report": match})
        print(f"{sym}/{win}: admitted={len(admitted)} excluded={len(excluded)} "
              f"vbasis={ls['vbasis_count']} step_all={len(ls['step_all_suspects'])} "
              f"overall={ls['overall']} match={all(match.values())}")
    out["reproduction_exact_vs_02_committed"] = all_match
    (PKG / "evidence" / "reproduction.json").write_text(
        json.dumps(out, indent=1, default=str))
    print("REPRODUCTION_EXACT:", all_match)
    if not all_match:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
