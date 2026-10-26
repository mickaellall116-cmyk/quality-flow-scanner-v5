#!/usr/bin/env python3
"""Verify the M1/M2 preparatory package (outcome-blind, no returns).

Checks:
  1. SHA256_MANIFEST.txt entries match the bytes on disk.
  2. P7b coverage artifact: reconciliation to the 2,892-fire census is
     recorded as exact (symmetric difference 0) and totals are coherent
     (43 symbols x 1,043 bars = 44,849 rows; generator-domain missing
     fields are zero for atr/atr_pct/ema21/ema55/ema200).
  3. EXP-14 feasibility artifact: census reconciled, ladder has 4 steps,
     frozen step is the first with drop rate <= 15% or the last step,
     retained + dropped == cohort.
  4. Frozen cohort / draws artifacts agree with the feasibility counts;
     every draw is 20 bars or the whole pool, without replacement.
  5. The synthetic-fixture test suite passes.
Exit 0 = PASS; exit 2 = FAIL (fail-closed).
"""
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    failures = []

    manifest = HERE / "SHA256_MANIFEST.txt"
    listed = {}
    for line in manifest.read_text().splitlines():
        line = line.strip()
        if line:
            digest, name = line.split(None, 1)
            listed[name.strip()] = digest.strip()
    for name, digest in listed.items():
        p = HERE / name
        if not p.exists():
            failures.append(f"missing file: {name}")
        elif sha256(p) != digest:
            failures.append(f"hash mismatch: {name}")

    cov = json.loads((HERE / "artifacts/p7b_coverage.json").read_text())
    recon = cov["reconciliation_vs_committed_p7_journal"]
    if not recon["reconciled"] or recon["symmetric_difference"] != 0:
        failures.append("P7b reconciliation not exact")
    if recon["journal_fires"] != 2892 or recon["inventory_domain_fires"] != 2892:
        failures.append("P7b fire counts != 2,892")
    if cov["total_bars"] != 43 * 1043:
        failures.append(f"P7b total bars {cov['total_bars']} != 44,849")
    for sym, ps in cov["per_symbol"].items():
        if ps["bars"] != 1043:
            failures.append(f"{sym}: bars {ps['bars']} != 1,043")
        md = ps["missing_fields_generator_domain"]
        if any(md[k] != 0 for k in ("atr", "atr_pct", "ema21", "ema55", "ema200")):
            failures.append(f"{sym}: generator-domain missing fields {md}")

    feas = json.loads((HERE / "artifacts/exp14_feasibility_counts.json").read_text())
    if feas["census_fires_reconciled"] != 2892:
        failures.append("EXP-14 census != 2,892")
    if len(feas["ladder"]) != 4:
        failures.append("EXP-14 ladder != 4 steps")
    want_frozen = next((r["step"] for r in feas["ladder"]
                        if r["drop_rate"] <= 0.15), "c")
    if feas["frozen_step"] != want_frozen:
        failures.append("EXP-14 frozen step inconsistent with ladder")
    if feas["retained_events"] + feas["dropped_events_at_frozen_step"] \
            != feas["cohort_events_primary_h10"]:
        failures.append("EXP-14 retained + dropped != cohort")

    cohort = json.loads((HERE / "artifacts/exp14_frozen_cohort.json").read_text())
    draws = json.loads((HERE / "artifacts/exp14_frozen_draws.json").read_text())
    if len(cohort["cohort"]) != feas["cohort_events_primary_h10"]:
        failures.append("cohort artifact size != feasibility cohort")
    if len(cohort["retained"]) != feas["retained_events"]:
        failures.append("cohort retained != feasibility retained")
    if set(draws["draws"]["B-A"]) != set(cohort["retained"]):
        failures.append("B-A draws do not cover exactly the retained events")
    for key, d in draws["draws"]["B-A"].items():
        pool_n = feas["pool_sizes_ba_at_frozen_step"][key]
        if len(d) != min(20, pool_n) or len(set(d)) != len(d):
            failures.append(f"draw {key}: size/replacement violation")
            break

    r = subprocess.run([sys.executable, str(HERE / "tests/test_exp14_synthetic.py")],
                       capture_output=True, text=True)
    if r.returncode != 0 or "0 failures" not in r.stdout:
        failures.append("synthetic test suite did not pass cleanly")

    if failures:
        print("VERIFY: FAIL")
        for f in failures:
            print(f"  - {f}")
        return 2
    print("VERIFY: PASS (manifest, P7b reconciliation 2,892 exact, "
          "cohort/ladder/draws coherent, synthetic suite PASS)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
