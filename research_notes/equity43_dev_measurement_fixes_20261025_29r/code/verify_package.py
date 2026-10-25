"""Independent verifier for the 29r session-time repair package.

Recomputes everything checkable from the package's own artifacts
plus committed repo artifacts (no stage assets, no simulator re-run):
  * SHA256_MANIFEST integrity;
  * the pinned session table artifact in the repo still hashes to
    the pin the repaired code enforces;
  * mtm_dev.json internal consistency: all-bar >= event-sampled,
    event values == the committed -13 results.json rows, all-bar DD
    recomputed from the committed regenerated series == reported,
    DD delta vs the -29 held figures == 0, final series value ==
    final equity;
  * regenerated series hygiene: no bar_close stamp at 17:30, census
    412 @13:30 + 412 @16:00 + 3 @13:00 per view, 1,304 points;
  * parity_repair.json: every harness check passed and the ledger
    sha under the repaired fork is the committed 267e794c…;
  * the three test batteries exit 0.

Run from the package dir: python3 code/verify_package.py
"""
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(PKG, "..", ".."))
ART = os.path.join(PKG, "artifacts")
FAILS = []
LEDGER_SHA = ("267e794c284a409d7d9b6d8e1056c452976b59746062e9e6e18"
              "c5664b74c003b")
TABLE_SHA = ("00c5555c26d391444509e54de322841fa3269b64f3161a50aa5"
             "07bf1d2bd416f")


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILS.append(name)


def load(p):
    return json.load(open(os.path.join(ART, p)))


def main():
    man = os.path.join(PKG, "SHA256_MANIFEST.txt")
    n_ok = 0
    for line in open(man):
        line = line.rstrip("\n")
        if not line:
            continue
        h, rel = line.split("  ", 1)
        actual = hashlib.sha256(
            open(os.path.join(PKG, rel), "rb").read()).hexdigest()
        if actual == h:
            n_ok += 1
        else:
            check(f"manifest hash {rel}", False)
    check(f"manifest: {n_ok} files verified", n_ok >= 12, f"n={n_ok}")

    tab_path = os.path.join(
        REPO, "research_notes", "equity43_feed_source_review_20261024_22",
        "bundle", "calendar", "session_table_751_qualified.json")
    check("pinned session table artifact hashes to the enforced pin",
          hashlib.sha256(open(tab_path, "rb").read()).hexdigest()
          == TABLE_SHA)

    mtm = load("mtm_dev.json")
    series = load("equity_series_allbar.json")
    parity = load("parity_repair.json")
    committed = json.load(open(os.path.join(
        REPO, "research_notes",
        "equity43_dev_order_censor_20261023_13", "results.json")))
    check("session_table_sha256 recorded in mtm_dev == pin",
          mtm["session_table_sha256"] == TABLE_SHA)
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
        check(f"{name}: DD delta vs -29 held == 0",
              v["dd_delta_pp"] == 0.0
              and abs(v["allbar_max_drawdown_pct_full"]
                      - v["held_29_allbar_max_drawdown_pct_full"])
              < 1e-9,
              f"delta {v['dd_delta_pp']}")
        check(f"{name}: series final == final equity",
              abs(series[name][-1][1] - v["final_equity"]) < 1e-6)
        bc = [t for t, _e, k in series[name] if k == "bar_close"]
        census = Counter(t[11:19] for t in bc)
        check(f"{name}: bar_close census 412/412/3, no 17:30",
              census == {"13:30:00": 412, "16:00:00": 412,
                         "13:00:00": 3}
              and all("17:30" not in t for t in bc),
              f"{dict(census)}")
        check(f"{name}: series points == 1304",
              len(series[name]) == 1304, f"{len(series[name])}")

    check("parity_repair: all harness checks passed",
          all(c["pass"] for c in parity["checks"])
          and len(parity["checks"]) >= 29,
          f"n={len(parity['checks'])}")
    check("parity_repair: ledger byte-identical under repaired fork",
          parity["ledger_sha256_under_repaired_fork"] == LEDGER_SHA)

    for t in ("test_session_bins.py", "test_mtm_allbar.py",
              "test_telemetry.py"):
        p = subprocess.run([sys.executable, os.path.join(PKG, "tests", t)],
                           capture_output=True, text=True)
        check(f"battery {t} exit 0", p.returncode == 0,
              p.stdout.strip().splitlines()[-1] if p.stdout
              else p.stderr[-200:])

    print("VERIFY_PACKAGE", "FAIL" if FAILS else "PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
