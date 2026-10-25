"""Independent verifier for the -30 P8 repair + semantic-pins package.

Recomputes everything checkable from the package's own artifacts
plus committed repo artifacts (no stage assets, no simulator re-run):
  * SHA256_MANIFEST integrity;
  * the base session table in the repo still hashes to the adopted
    pin (byte-untouched by this lane), and the extension artifact
    hashes to the pin the successor code enforces;
  * the extension builder's cross-checks are recorded and clean
    (X1 base reproduction is re-run here from the historical lists
    against the committed base table bytes);
  * exposure_dev.json and p9_parity.json agree with fresh
    recomputation from the committed artifacts;
  * all five test batteries exit 0.

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
CODE = os.path.join(PKG, "code")
FAILS = []
TABLE_SHA = ("00c5555c26d391444509e54de322841fa3269b64f3161a50aa5"
             "07bf1d2bd416f")
EXT_SHA = ("d2fa788d70f2c8677ca49b9e0201940586c051b9227f815b8d2"
           "da55b1e5d3a2f")
sys.path.insert(0, CODE)


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILS.append(name)


def main():
    man = os.path.join(PKG, "SHA256_MANIFEST.txt")
    n_ok = 0
    n_tot = 0
    for line in open(man):
        line = line.rstrip("\n")
        if not line:
            continue
        n_tot += 1
        h, rel = line.split("  ", 1)
        actual = hashlib.sha256(
            open(os.path.join(PKG, rel), "rb").read()).hexdigest()
        if actual == h:
            n_ok += 1
        else:
            check(f"manifest hash {rel}", False)
    check(f"manifest: all {n_tot} files verified", n_ok == n_tot,
          f"{n_ok}/{n_tot}")

    tab_path = os.path.join(
        REPO, "research_notes", "equity43_feed_source_review_20261024_22",
        "bundle", "calendar", "session_table_751_qualified.json")
    check("base session table hashes to the adopted pin (untouched)",
          hashlib.sha256(open(tab_path, "rb").read()).hexdigest()
          == TABLE_SHA)
    ext_path = os.path.join(ART, "session_table_extension_2027.json")
    check("extension artifact hashes to the enforced pin",
          hashlib.sha256(open(ext_path, "rb").read()).hexdigest()
          == EXT_SHA)

    import build_session_extension as bse
    base = json.load(open(tab_path))["sessions"]
    from datetime import date
    repro = bse.build_sessions(date(2023, 10, 19), date(2026, 10, 16),
                                bse.HIST_HOLIDAYS,
                                bse.HIST_EARLY_CLOSES)
    check("X1 re-run: the builder's construction reproduces the "
          "adopted 751 table exactly", repro == base)
    ext_doc = json.load(open(ext_path))
    rebuilt = bse.build_sessions(bse.HORIZON_FIRST, bse.HORIZON_LAST,
                                  bse.HOLIDAYS, bse.EARLY_CLOSES)
    check("extension sessions == fresh rebuild from the encoded "
          "NYSE lists", rebuilt == ext_doc["sessions"])
    x2 = ext_doc["cross_checks"]["X2_exchange_calendars"]
    check("X2 recorded clean (exchange_calendars overlap agreement)",
          x2["date_mismatches"] == [] and x2["close_mismatches"] == []
          and x2["sessions_compared"] == 256)

    import exposure_report as xr
    import parity_check as pc
    dev = xr.dev_application()
    art_x = json.load(open(os.path.join(ART, "exposure_dev.json")))
    check("exposure_dev.json agrees with fresh recomputation",
          art_x["basis"]["A_last_mark_le_entry"]["peak_gross"]
          == dev["basis"]["A_last_mark_le_entry"]["peak_gross"]
          and art_x["flat_equity_crosscheck"]["peak_gross"]
          == dev["flat_equity_crosscheck"]["peak_gross"])
    rep9 = pc.parity_report()
    art9 = json.load(open(os.path.join(ART, "p9_parity.json")))
    check("p9_parity.json verdict PASS and agrees with recomputation",
          rep9["verdict"] == "PASS" and art9["verdict"] == "PASS"
          and art9["views"]["25bps"]["recomputed"]["mean_r"]
          == rep9["views"]["25bps"]["recomputed"]["mean_r"])

    for t in ("test_session_bins.py", "test_session_bins_ext.py",
              "test_telemetry.py", "test_telemetry_txn.py",
              "test_semantic_pins.py"):
        p = subprocess.run([sys.executable, os.path.join(PKG, "tests", t)],
                           capture_output=True, text=True)
        check(f"battery {t} exit 0", p.returncode == 0,
              (p.stdout.strip().splitlines() or [""])[-1]
              if p.returncode == 0 else p.stderr[-300:])

    print("VERIFY_PACKAGE", "FAIL" if FAILS else "PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
