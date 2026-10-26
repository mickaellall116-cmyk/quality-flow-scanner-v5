#!/usr/bin/env python3
"""Verify the EXP-14 Decision B amendment package (no returns).

Checks:
  1. SHA256_MANIFEST.txt entries match the bytes on disk.
  2. The frozen artifacts are carried BYTE-IDENTICAL from the v2
     successor package (commit 32dfdb3): feasibility / cohort / draws
     file SHA-256s equal the successor pins; internal coherence as
     the successor verifier checked it (census 2,892; de-clustered
     320; cohort 311 = 320 - 9 h20 drops; ladder 4 steps; frozen step
     first with drop <= 15% or last; retained 240 + dropped 71 ==
     311; step-(c) rate recomputes; review-named events absent; h20
     ceiling respected; B-A draws cover exactly the retained events
     at min(20, pool) without replacement; B-T cardinality).
  3. AMENDMENT.md carries the Decision B record: the decision, the
     preserved STOP, the four conditions, and the not-execution
     boundary.
  4. The execution-only price input descriptor (item (a)): 44,849
     bars over 43 symbols x 1,043; alignment vs the pinned P7b
     inventory recorded exact (44,849 compared, 0 ts / 0 close
     mismatches); the P7b inventory pin itself unchanged
     (a6bbd19a...); an archive placement + commit recorded. NO price
     rows anywhere in this public package (no .jsonl files).
  5. The output schema (item (c)): DEV EXPLORATORY label const; the
     mandatory disclosure block with all count fields; the
     cost-sensitivity block pinned at 25 bps; percent views declared
     at every horizon.
  6. The v3 script: seeds pinned; RETURNS_ENABLED is False and
     compute_forward_returns raises ExecutionGoRequired (item (b)
     gate); build_disclosure on the REAL pinned cohort recomputes
     311 / 240 / 71 at the feasibility step-(c) rate.
  7. The synthetic suite passes (it carries the CLI wiring gate test
     and the fixture end-to-end test for item (b), the price-
     separation proofs for item (a), and the disclosure / percent /
     cost-line proofs for item (c)).
Exit 0 = PASS; exit 2 = FAIL (fail-closed).
"""
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
BARS_PER_SYMBOL = 1043
H20_CEILING = BARS_PER_SYMBOL - 1 - 20
REVIEW_NAMED_EVENTS = {"AMAT:1024", "AMZN:1031", "GOOGL:1027",
                       "SHOP:1029", "SMH:1025"}
SUCC_PINS = {
    "artifacts/exp14_feasibility_counts.json":
        "80c9f5fe708f67e3dcea5cb84efd83d477511536e152a79589cf6dc041567684",
    "artifacts/exp14_frozen_cohort.json":
        "35690b806e51eefe388fadf35b04baf5ed4c52f8e30ac193a38cf88246332824",
    "artifacts/exp14_frozen_draws.json":
        "fe54808e282515807703692fb08cf3928ee9a4435d04b6939f2b9f47157e4a8a",
}
P7B_INVENTORY_SHA = \
    "a6bbd19a702120cafd48cd01ee4c8ff59b838a8bd6439822415d6c18278ef02f"


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

    # ---- frozen artifacts: byte-identical carry + coherence -------------
    for name, pin in SUCC_PINS.items():
        if sha256(HERE / name) != pin:
            failures.append(f"{name}: not byte-identical to the "
                            "successor pin")
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
    if feas["cohort_events_single_rule_h20"] != 311:
        failures.append("cohort != 311")
    if len(feas["ladder"]) != 4:
        failures.append("ladder != 4 steps")
    want_frozen = next((r["step"] for r in feas["ladder"]
                        if r["drop_rate"] <= 0.15), "c")
    if feas["frozen_step"] != want_frozen:
        failures.append("frozen step inconsistent with ladder")
    if feas["retained_events"] + feas["dropped_events_at_frozen_step"] \
            != feas["cohort_events_single_rule_h20"]:
        failures.append("retained + dropped != cohort")
    if feas["retained_events"] != 240 \
            or feas["dropped_events_at_frozen_step"] != 71:
        failures.append("retained/dropped != 240/71")
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

    # ---- AMENDMENT.md carries the decision --------------------------------
    amend = (HERE / "AMENDMENT.md").read_text()
    for needle in ("DECISION B", "STOP", "71 of 311", "22.8%",
                   "matched subpopulation", "not permission to execute",
                   "No further relaxation",
                   "cannot establish a validated trading edge"):
        if needle not in amend:
            failures.append(f"AMENDMENT.md missing: {needle!r}")

    # ---- exec-prices descriptor (item (a)); no prices in this package -----
    desc = json.loads(
        (HERE / "artifacts/exec_prices_descriptor.json").read_text())
    if desc["total_bars"] != 43 * BARS_PER_SYMBOL:
        failures.append("exec descriptor total_bars != 44,849")
    if len(desc["per_symbol"]) != 43 or any(
            v["bars"] != BARS_PER_SYMBOL
            for v in desc["per_symbol"].values()):
        failures.append("exec descriptor per-symbol counts off")
    al = desc["alignment_vs_pinned_p7b_inventory"]
    if al["bars_compared"] != 43 * BARS_PER_SYMBOL \
            or al["ts_mismatches"] != 0 or al["close_mismatches"] != 0:
        failures.append("exec descriptor alignment not exact")
    if al["inventory_sha256"] != P7B_INVENTORY_SHA:
        failures.append("P7b inventory pin drift in descriptor")
    if len(desc["exec_prices_sha256"]) != 64:
        failures.append("exec prices sha256 malformed in descriptor")
    if "qf-data-archive" not in desc["placement"] \
            or not desc.get("archive_commit"):
        failures.append("exec descriptor placement/commit missing")
    if list(HERE.rglob("*.jsonl")):
        failures.append("price rows present in the public package "
                        "(.jsonl found) — placement violation")

    # ---- output schema (item (c)) -------------------------------------------
    schema = json.loads(
        (HERE / "artifacts/exp14_output_schema.json").read_text())
    obj = schema["object"]
    if obj["label"] != \
            "const 'DEV EXPLORATORY' — required on every real-data output":
        failures.append("output schema label drift")
    disc = obj.get("disclosure", {})
    for k in ("eligible_events", "retained_events_matched",
              "excluded_events_unmatched", "exclusion_rate",
              "exclusion_rate_pct", "matched_subpopulation_only",
              "scope_statement", "decision_basis"):
        if k not in disc:
            failures.append(f"output schema disclosure missing {k}")
    if "25" not in obj.get("cost_sensitivity", {}).get(
            "round_trip_bps", ""):
        failures.append("output schema cost sensitivity not pinned "
                        "at 25 bps")
    hz = obj["horizons"]["5|10|20"]
    for k in ("mean_event_return_pct", "mean_paired_excess_pct"):
        if k not in hz:
            failures.append(f"output schema horizon view missing {k}")

    # ---- the v3 script: gate, seeds, disclosure mechanics -------------------
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
    d = mod.build_disclosure(cohort)
    if d["eligible_events"] != 311 or d["retained_events_matched"] != 240 \
            or d["excluded_events_unmatched"] != 71 \
            or abs(d["exclusion_rate"] - step_c["drop_rate"]) > 1e-12:
        failures.append("build_disclosure on the pinned cohort does "
                        "not recompute 311/240/71 at the step-(c) rate")
    if mod.validate_disclosure(d, cohort) != d:
        failures.append("validate_disclosure does not round-trip the "
                        "pinned cohort disclosure")

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
    print("VERIFY: PASS (manifest; frozen artifacts byte-identical to "
          "successor 32dfdb3 and coherent 311/240/71; Decision B "
          "recorded; exec-prices descriptor exact vs the unchanged "
          "P7b pin, no prices in package; schema disclosure + pct + "
          "25 bps cost line pinned; gate holds; disclosure recomputes; "
          "synthetic suite PASS)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
