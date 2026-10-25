"""Independent verifier for the -29 measurement-fix package.

Recomputes everything checkable from the package's own artifacts plus
the committed -13 artifacts (no stage assets, no simulator re-run):
  * SHA256_MANIFEST integrity;
  * all-fire journal census == allfire_summary.json; matched == 590;
  * per-view ledger artifacts == per_view_summary.json; 25 bps headline;
  * mtm_dev.json internal consistency: all-bar >= event-sampled, event
    values == the committed results.json rows, and the all-bar DD
    recomputed from the committed equity series equals the reported
    figure; final series value == final equity;
  * the four test batteries exit 0; the P4 bytecode evidence says PASS.

Run from the package dir: python3 code/verify_package.py
"""
import hashlib
import json
import os
import subprocess
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(PKG, "..", ".."))
ART = os.path.join(PKG, "artifacts")
FAILS = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILS.append(name)


def load(p):
    return json.load(open(os.path.join(ART, p)))


def main():
    # Manifest
    man = os.path.join(PKG, "SHA256_MANIFEST.txt")
    n_ok = 0
    for line in open(man):
        line = line.rstrip("\n")
        if not line:
            continue
        h, rel = line.split("  ", 1)
        p = os.path.join(PKG, rel)
        actual = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if actual == h:
            n_ok += 1
        else:
            check(f"manifest hash {rel}", False)
    check(f"manifest: {n_ok} files verified", n_ok >= 15, f"n={n_ok}")

    # All-fire census
    journal = load("allfire_journal.json")
    summ = load("allfire_summary.json")
    by = {}
    for r in journal:
        by[r["classification"]] = by.get(r["classification"], 0) + 1
    check("journal census == summary", by == summ["by_class"],
          f"{by} vs {summ['by_class']}")
    check("journal total == summary total",
          len(journal) == summ["total_fires"])
    matched = {(r["symbol"], r["signal_idx"]) for r in journal
               if r["classification"] == "MATCHED_CANDIDATE"}
    check("matched == 590", len(matched) == 590)
    check("UNCLASSIFIED == 0", by.get("UNCLASSIFIED", 0) == 0)
    check("GAP_INELIGIBLE == 1", by.get("GAP_INELIGIBLE_ENTRY", 0) == 1)

    # Per-view ledgers
    pvs = load("per_view_summary.json")
    for name in ("gross", "4bps", "25bps"):
        lv = load(f"ledger_{name}.json")
        check(f"{name}: artifact records == summary taken",
              len(lv["records"]) == pvs[name]["taken"],
              f"{len(lv['records'])} vs {pvs[name]['taken']}")
    check("25bps headline reproduced (185 closed, +0.10751R)",
          pvs["25bps"]["closed"] == 185
          and pvs["25bps"]["mean_r"] == 0.10751)
    check("cost-convention identity: 0 violations",
          pvs["cost_convention_check"]["violations"] == 0)

    # MTM
    mtm = load("mtm_dev.json")
    series = load("equity_series_allbar.json")
    committed = json.load(open(os.path.join(
        REPO, "research_notes",
        "equity43_dev_order_censor_20261023_13", "results.json")))
    for name in ("gross", "4bps", "25bps"):
        v = mtm["views"][name]
        rep = committed["phases"]["P5_run"][name]["max_drawdown_pct"]
        check(f"{name}: event DD == committed results row",
              abs(v["event_sampled_max_drawdown_pct"] - rep) < 0.005,
              f"{v['event_sampled_max_drawdown_pct']} vs {rep}")
        check(f"{name}: all-bar DD >= event DD",
              v["allbar_max_drawdown_pct"]
              >= v["event_sampled_max_drawdown_pct"])
        peak, dd = -1.0, 0.0
        for _t, e, _k in series[name]:
            peak = max(peak, e)
            dd = max(dd, (peak - e) / peak if peak > 0 else 0.0)
        check(f"{name}: series-recomputed all-bar DD == reported",
              abs(round(100 * dd, 4) - v["allbar_max_drawdown_pct"])
              < 0.001, f"{round(100 * dd, 4)} vs "
              f"{v['allbar_max_drawdown_pct']}")
        check(f"{name}: series final == final equity",
              abs(series[name][-1][1] - v["final_equity"]) < 1e-6)

    # P4 evidence
    p4 = open(os.path.join(ART, "p4_bytecode_check.txt")).read()
    check("P4 bytecode evidence PASS", "P4_BYTECODE PASS" in p4)

    # Test batteries
    for t in ("test_mtm_allbar.py", "test_allfire.py",
              "test_telemetry.py", "test_reconcile.py"):
        p = subprocess.run([sys.executable, os.path.join(PKG, "tests", t)],
                           capture_output=True, text=True)
        check(f"battery {t} exit 0", p.returncode == 0,
              p.stdout.strip().splitlines()[-1] if p.stdout else p.stderr[-200:])

    print("VERIFY_PACKAGE", "FAIL" if FAILS else "PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
