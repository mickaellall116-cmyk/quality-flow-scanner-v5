"""Independent verifier for the -31 P6 full-grid repair package.

Recomputes everything checkable from committed artifacts (no stage
assets, no simulator re-run):
  * SHA256_MANIFEST integrity;
  * the -30 package is byte-untouched by this lane (its code and
    artifact hashes still match the -30 manifest pins);
  * the regenerated exposure_dev.json agrees exactly with a fresh
    recomputation from the committed -13 ledger and -29r series;
  * the superseded block in the artifact equals the committed -30
    artifact (reproduced by the pinned -30 module);
  * the P6 grid battery exits 0.

Run from the package dir: python3 code/verify_package.py
"""
import hashlib
import json
import os
import subprocess
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(PKG, "..", ".."))
CODE = os.path.join(PKG, "code")
FAILS = []
PRED_CODE_SHA = ("f219f34248112048c4d4c5af4908fc4a6a33f2c8f9bcee"
                 "44f7ce87fb262cf248")
PRED_ART_SHA = ("d2da4b45bb264f6e7ffa8d6a6f330d9fd57586d161c5e"
                "5052f258fafee54101c")
sys.path.insert(0, CODE)


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILS.append(name)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    man = os.path.join(PKG, "SHA256_MANIFEST.txt")
    n_ok = n_tot = 0
    for line in open(man):
        line = line.rstrip("\n")
        if not line:
            continue
        n_tot += 1
        h, rel = line.split("  ", 1)
        if sha(os.path.join(PKG, rel)) == h:
            n_ok += 1
        else:
            check(f"manifest hash {rel}", False)
    check(f"manifest: all {n_tot} files verified", n_ok == n_tot,
          f"{n_ok}/{n_tot}")

    pred_dir = os.path.join(
        REPO, "research_notes",
        "equity43_dev_measurement_fixes_20261025_30")
    check("-30 code byte-untouched (pin)",
          sha(os.path.join(pred_dir, "code",
                           "exposure_report.py")) == PRED_CODE_SHA)
    check("-30 artifact byte-untouched (pin)",
          sha(os.path.join(pred_dir, "artifacts",
                           "exposure_dev.json")) == PRED_ART_SHA)

    import exposure_report as er
    fresh = er.dev_application()
    committed = json.load(open(os.path.join(
        PKG, "artifacts", "exposure_dev.json")))
    check("artifact == fresh recomputation (deep, JSON-normalized)",
          json.loads(json.dumps(fresh)) == committed)
    sup = committed["superseded_entry_only"]
    committed30 = json.load(open(os.path.join(
        pred_dir, "artifacts", "exposure_dev.json")))
    check("superseded block == committed -30 artifact",
          sup["basis"] == committed30["basis"]
          and sup["flat_equity_crosscheck"]
          == committed30["flat_equity_crosscheck"])
    corr = committed["corrected_full_grid"]["basis"][
        "A_last_mark_le_entry"]
    check("corrected basis A: 964 samples, peak at the 2025-09-08 "
          "entry timestamp",
          corr["samples"] == 964
          and corr["peak_gross_at"] == "2025-09-08T09:30:00-04:00")

    bat = subprocess.run(
        [sys.executable, os.path.join(PKG, "tests",
                                      "test_p6_grid.py")],
        capture_output=True, text=True)
    print(bat.stdout.strip().splitlines()[-1] if bat.stdout else "")
    check("battery test_p6_grid.py exit 0", bat.returncode == 0)

    print("VERIFY", "FAIL" if FAILS else "PASS",
          f"({len(FAILS)} fails)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
