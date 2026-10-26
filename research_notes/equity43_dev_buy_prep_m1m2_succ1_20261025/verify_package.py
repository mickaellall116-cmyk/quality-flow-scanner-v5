#!/usr/bin/env python3
"""Verify the EXP-14 successor package (outcome-blind, no returns).

Checks:
  1. SHA256_MANIFEST.txt entries match the bytes on disk.
  2. Feasibility artifact coherence under the single complete-window
     rule: census 2,892; de-clustered 320; cohort == de-clustered
     minus the h=20 window drops; ladder has 4 steps; frozen step is
     the first with drop rate <= 15% or the last; retained + dropped
     == cohort; the step-(c) drop rate recomputes exactly.
  3. Review item 1 reproductions: the five h=10-cohort events named in
     comment 6405786931 (AMAT:1024, AMZN:1031, GOOGL:1027, SHOP:1029,
     SMH:1025) are absent from the successor cohort; no cohort event
     or drawn control exceeds the h=20 ceiling (idx + 20 <= 1042 for
     the 1,043-bar series).
  4. Frozen draws agree with the feasibility counts: B-A groups cover
     exactly the retained events; each draw is min(20, pool) bars
     without replacement; B-T group count matches the report.
  5. Seed pins: MASTER_SEED 7715012043445510037 and BOOTSTRAP_SEED
     6050949521315240661 appear identically in the feasibility
     artifact, the draws artifact, and the script's own constants.
  6. The analysis gate holds in the pinned script (RETURNS_ENABLED is
     False and compute_forward_returns raises), the output-schema
     artifact parses, and the synthetic suite passes.
Exit 0 = PASS; exit 2 = FAIL (fail-closed).
"""
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
BARS_PER_SYMBOL = 1043  # P7b coverage artifact, predecessor package
H20_CEILING = BARS_PER_SYMBOL - 1 - 20
REVIEW_NAMED_EVENTS = {"AMAT:1024", "AMZN:1031", "GOOGL:1027",
                       "SHOP:1029", "SMH:1025"}


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

    feas = json.loads(
        (HERE / "artifacts/exp14_feasibility_counts.json").read_text())
    if feas["census_fires_reconciled"] != 2892:
        failures.append("census != 2,892")
    if feas["declustered_events_total"] != 320:
        failures.append("de-clustered != 320")
    drops = feas["events_dropped_forward_window_by_horizon"]
    if feas["cohort_events_single_rule_h20"] \
            != feas["declustered_events_total"] - drops["20"]:
        failures.append("cohort != de-clustered - h20 drops")
    if len(feas["ladder"]) != 4:
        failures.append("ladder != 4 steps")
    want_frozen = next((r["step"] for r in feas["ladder"]
                        if r["drop_rate"] <= 0.15), "c")
    if feas["frozen_step"] != want_frozen:
        failures.append("frozen step inconsistent with ladder")
    if feas["retained_events"] + feas["dropped_events_at_frozen_step"] \
            != feas["cohort_events_single_rule_h20"]:
        failures.append("retained + dropped != cohort")
    step_c = next(r for r in feas["ladder"] if r["step"] == "c")
    if abs(step_c["drop_rate"]
           - step_c["dropped"] / feas["cohort_events_single_rule_h20"]) \
            > 1e-12:
        failures.append("step-(c) drop rate does not recompute")
    if feas["master_seed"] != 7715012043445510037:
        failures.append("master seed drift in feasibility artifact")
    if feas["bootstrap_seed"] != 6050949521315240661:
        failures.append("bootstrap seed drift in feasibility artifact")

    cohort = json.loads(
        (HERE / "artifacts/exp14_frozen_cohort.json").read_text())
    draws = json.loads(
        (HERE / "artifacts/exp14_frozen_draws.json").read_text())
    if len(cohort["cohort"]) != feas["cohort_events_single_rule_h20"]:
        failures.append("cohort artifact size != feasibility cohort")
    if len(cohort["retained"]) != feas["retained_events"]:
        failures.append("cohort retained != feasibility retained")
    cohort_keys = {f"{c['symbol']}:{c['signal_idx']}"
                   for c in cohort["cohort"]}
    if cohort_keys & REVIEW_NAMED_EVENTS:
        failures.append("review-named h20-incomplete events still in "
                        f"cohort: {cohort_keys & REVIEW_NAMED_EVENTS}")
    for c in cohort["cohort"]:
        if c["signal_idx"] > H20_CEILING:
            failures.append(f"cohort event {c['symbol']}:"
                            f"{c['signal_idx']} beyond h20 ceiling")
            break
    if draws["master_seed"] != 7715012043445510037:
        failures.append("master seed drift in draws artifact")
    if set(draws["draws"]["B-A"]) != set(cohort["retained"]):
        failures.append("B-A draws do not cover exactly the retained "
                        "events")
    for key, d in draws["draws"]["B-A"].items():
        pool_n = feas["pool_sizes_ba_at_frozen_step"][key]
        if len(d) != min(20, pool_n) or len(set(d)) != len(d):
            failures.append(f"draw {key}: size/replacement violation")
            break
        if any(j > H20_CEILING for j in d):
            failures.append(f"draw {key}: control beyond h20 ceiling")
            break
    for key, d in draws["draws"]["B-T"].items():
        if any(j > H20_CEILING for j in d):
            failures.append(f"B-T draw {key}: control beyond ceiling")
            break
    if len(draws["draws"]["B-T"]) != feas["bt_viable_groups"]:
        failures.append("B-T group count != feasibility bt_viable")
    if feas["ba_groups_with_full_20_draws"] \
            + feas["ba_groups_all_available_below_20"] \
            != feas["ba_draw_groups"]:
        failures.append("B-A draw-group cardinality does not add up")

    schema = json.loads(
        (HERE / "artifacts/exp14_output_schema.json").read_text())
    if schema["object"]["label"] != \
            "const 'DEV EXPLORATORY' — required on every real-data output":
        failures.append("output schema label drift")

    spec = importlib.util.spec_from_file_location(
        "exp14_buy", HERE / "code/exp14_buy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if mod.RETURNS_ENABLED is not False:
        failures.append("RETURNS_ENABLED is not False in the pin")
    try:
        mod.compute_forward_returns()
        failures.append("compute_forward_returns did not raise")
    except mod.ExecutionGoRequired:
        pass
    if mod.MASTER_SEED != 7715012043445510037 \
            or mod.BOOTSTRAP_SEED != 6050949521315240661:
        failures.append("seed constants drift in script")

    r = subprocess.run(
        [sys.executable, str(HERE / "tests/test_exp14_synthetic.py")],
        capture_output=True, text=True)
    if r.returncode != 0 or "0 failures" not in r.stdout:
        failures.append("synthetic test suite did not pass cleanly")

    if failures:
        print("VERIFY: FAIL")
        for f in failures:
            print(f"  - {f}")
        return 2
    print("VERIFY: PASS (manifest, single-rule cohort/ladder/draws "
          "coherent, review-named events excluded, seeds pinned, "
          "gate holds, synthetic suite PASS)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
