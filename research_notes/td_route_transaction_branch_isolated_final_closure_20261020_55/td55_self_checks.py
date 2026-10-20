#!/usr/bin/env python3
"""-55 pre-execution self-checks (in the clear; NOT part of the
attempt). Exercises driver v7's new branch-isolation adjudication
against the immutable accepted matrix and the immutable -54
candidate matrix, its provenance pin expectations against the
committed sources, and the inherited corrected extractor."""
import copy, hashlib, importlib.util, json, sys
from pathlib import Path
sys.argv = ["td55_self_checks", "/tmp"]
HERE = Path(__file__).parent
NOTES = HERE.parent
spec = importlib.util.spec_from_file_location(
    "qf55_driver", HERE / "proof_driver_v7.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
HF = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks = []
def check(name, ok, detail=""):
    checks.append({"check": name, "pass": bool(ok),
                   "detail": str(detail)[:200]})

ACC = json.loads((NOTES / "td_live_dryrun_clock_adapter_binding_20261017_19"
                  / "clock_adapter_matrix_run2.json").read_bytes())
C54 = json.loads((NOTES / "td_route_transaction_dual_path_clock_closure_20261020_54"
                  / "clock_matrix.json").read_bytes())

def adjud(acc, orig, cand):
    try:
        ev = D.adjudicate_clock_branches(acc, orig, cand)
        return ("PASS", ev)
    except D.Fail as e:
        return (e.key, e.detail)

# 1: positive - accepted as both branches
k, ev = adjud(ACC, ACC, ACC)
check("partition_positive_accepted", k == "PASS"
      and ev["combined_rollup"]["matches_accepted"], k)
# 2: positive-real - accepted original + the immutable -54 candidate
# matrix (whose 19 candidate trials matched; repro_old excluded)
k, ev = adjud(ACC, ACC, C54)
check("partition_positive_real_54_candidate", k == "PASS"
      and ev["candidate_19"]["all_identical"]
      and ev["candidate_19"]
          ["candidate_branch_repro_old_recorded_not_adjudicated"]
          ["gates"][5] == "FAIL", k)
# 3: negative - candidate trial tampered
bad = copy.deepcopy(C54)
bad["trials"]["binding_ok"]["ok"] = False
k, _ = adjud(ACC, ACC, bad)
check("partition_negative_candidate_trial", k == "P1_CLOCK_ADAPTER_REGRESSION", k)
# 4: negative - original repro tampered (gate 6 flipped to the
# -54 contaminated FAIL value: the historical vector must
# reproduce exactly, contaminated values included)
bad = copy.deepcopy(ACC)
bad["trials"]["repro_old"]["gates"][5] = "FAIL"
k, _ = adjud(ACC, bad, C54)
check("partition_negative_original_repro", k == "P1_CLOCK_ORIGINAL_REPRO", k)
# 5: negative - a trial missing from a branch matrix
bad = copy.deepcopy(C54)
del bad["trials"]["scope"]
k, _ = adjud(ACC, ACC, bad)
check("partition_negative_missing_trial", k == "P1_CLOCK_BRANCH_PARTITION", k)
# 6: negative - rollup tampered via a candidate check flip
bad = copy.deepcopy(C54)
t = bad["trials"]["new_12of12"]
key = next(iter(t["checks"]))
t["checks"][key] = not t["checks"][key]
t["gates"] = t["gates"]  # gates untouched: divergence must still fire
k, _ = adjud(ACC, ACC, bad)
check("partition_negative_rollup_or_regression",
      k in ("P1_CLOCK_ADAPTER_REGRESSION", "P1_CLOCK_ROLLUP"), k)
# 7-11: provenance pin expectations on committed sources
check("orig_gate_pin", HF(NOTES / "td_policy_a_live_readiness_packet_20261017_11"
      / "dispatch_gate_r4.py") == D.PIN_R4_GATE_LEGACY)
check("orig_driver_prefix", HF(NOTES / "td_fresh_live_driver_integration_evidence_20261016"
      / "live_driver.py").startswith("5fed4524"))
_s = json.loads((NOTES / "td_fresh_full_manifest_preflight_evidence_20261016"
                 / "fresh_supplement.json").read_bytes())
check("orig_supplement_prefix", HF(NOTES / "td_fresh_full_manifest_preflight_evidence_20261016"
      / "fresh_supplement.json").startswith("3cbdbf63"))
check("orig_mechanism_prefix", HF(NOTES / "pilot_harness" / "validate_input.py").startswith("1b83cdcd"))
check("orig_proof_prefix", next(iter(_s["calendar_proofs"])).startswith("36bc3a89"))
# 12-13: inherited extractor positive/negative (continuity with -54)
m = json.loads((NOTES / "td_route_transaction_workspace_stage_continuation_20261020_52"
                / "gate_matrix.json").read_bytes())
ev = D.extract_gate567(m)
check("extractor_positive", ev is not None and ev["gate5"] == ev["gate6"] == ev["gate7"] == "PASS")
m2 = copy.deepcopy(m)
for tr in m2["trials"]:
    if tr["trial"] == "G01_green_dry_run":
        tr["facts"]["gates_passed"] = 11
check("extractor_negative_gates11", D.extract_gate567(m2) is None)
# 14: v7 base pin sanity
check("driver_v6_pin", HF(NOTES / "td_route_transaction_dual_path_clock_closure_20261020_54"
      / "proof_driver_v6.py") == D.PIN_DRIVER_V6)
out = {"n": len(checks), "n_pass": sum(1 for c in checks if c["pass"]),
       "checks": checks}
(HERE / "td55_self_check_results.json").write_text(
    json.dumps(out, indent=1, sort_keys=True))
print(json.dumps({"n": out["n"], "n_pass": out["n_pass"],
                  "failed": [c["check"] for c in checks if not c["pass"]]}))
