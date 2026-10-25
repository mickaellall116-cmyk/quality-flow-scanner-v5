"""Workpaper (as executed): baseline reproduction harness for -29.
Requires the -13 stage assets (archive_clone, engine dirs, session
table) and pandas_market_calendars on PYTHONPATH (read from
qf_td17_stage/pylibs, read-only). See MEMO.md."""
"""QF -29 baseline harness: reproduce the -13 pipeline (phases 2/4/build/
fidelity/5) from the pinned stage assets and compare the produced ledger +
P5_run views against the committed -13 artifacts. Measurement/parity only.
"""
import hashlib
import json
import os
import pickle
import sys

HOME = os.path.expanduser("~/workspace/qf_fix29_stage/home")
OUT = os.path.expanduser("~/workspace/qf_fix29_stage/out_base")
os.environ["QF_OUT"] = OUT
os.chdir(HOME)
sys.path.insert(0, HOME)

import run_study13 as drv  # noqa: E402


def check(tag):
    if drv.failures:
        print(f"STOP after {tag}: {drv.failures}")
        sys.exit(2)


def main():
    child_manifest = json.load(open(os.path.join(HOME, "child_manifest.json")))
    symbols43 = drv.PILOT + [l["symbol"] for l in child_manifest["legs"]
                             if l["window"] == "W_DEV"]
    assert len(symbols43) == 43
    table, dev_sessions = drv.load_session_table()
    admitted = drv.phase2(table, dev_sessions, symbols43)
    check("phase2")
    bars = drv.phase4(admitted, dev_sessions, symbols43)
    check("phase4")
    import pandas as pd
    cutoff = max(bars[s].index[-1] for s in symbols43) + pd.Timedelta(hours=4)
    data, closes, canonical, closed_all, censored_all, skipped_gap, feats = \
        drv.build_inputs(bars, admitted, symbols43)
    check("build_inputs")
    drv.phase4_fidelity(canonical, closes, censored_all, cutoff)
    check("phase4_fidelity")
    with open(os.path.expanduser("~/workspace/qf_fix29_stage/work/pipeline.pkl"),
              "wb") as f:
        pickle.dump({"data": data, "closes": closes, "canonical": canonical,
                     "feats": feats, "skipped_gap": skipped_gap,
                     "cutoff": cutoff, "symbols43": symbols43,
                     "censored_all": censored_all}, f)
    drv.phase5(canonical, closes, feats, skipped_gap, censored_all,
               symbols43, cutoff)
    check("phase5")
    led = os.path.join(OUT, "trade_ledger.json")
    h = hashlib.sha256(open(led, "rb").read()).hexdigest()
    print("LEDGER_SHA256", h)
    committed = json.load(open(os.path.expanduser(
        "~/workspace/qf_fix29_stage/work/committed_results.json")))
    mine = drv.report["phases"]["P5_run"]
    theirs = committed["phases"]["P5_run"]
    print("VIEWS_EQUAL", json.dumps(mine, sort_keys=True, default=str)
          == json.dumps(theirs, sort_keys=True, default=str))
    for cn in ("gross", "4bps", "25bps"):
        for k in sorted(set(mine[cn]) | set(theirs[cn])):
            if json.dumps(mine[cn].get(k), sort_keys=True, default=str) != \
               json.dumps(theirs[cn].get(k), sort_keys=True, default=str):
                print("VIEW_DIFF", cn, k, "mine=", mine[cn].get(k),
                      "theirs=", theirs[cn].get(k))
    print("P4_CANDIDATES", json.dumps(drv.report["phases"]["P4_candidates"],
                                      sort_keys=True, default=str)[:400])
    print("BASELINE_DONE")


if __name__ == "__main__":
    main()
