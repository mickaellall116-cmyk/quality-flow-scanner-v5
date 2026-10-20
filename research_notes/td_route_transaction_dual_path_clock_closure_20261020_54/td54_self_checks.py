#!/usr/bin/env python3
"""-54 pre-execution self-checks (in the clear; NOT part of the
attempt). Exercises driver v6's new static-resolution helpers and
the inherited corrected extractor against the immutable sources."""
import copy, hashlib, importlib.util, json, sys
from pathlib import Path
sys.argv = ["td54_self_checks", "/tmp"]
HERE = Path(__file__).parent
NOTES = HERE.parent
spec = importlib.util.spec_from_file_location(
    "qf54_driver", HERE / "proof_driver_v6.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
HF = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks = []
def check(name, ok, detail=""):
    checks.append({"check": name, "pass": bool(ok), "detail": str(detail)[:200]})

old_src = (NOTES / "td_status_query_placement_20261017_17"
           / "r4_dry_run_adapter.py").read_text()
check("old_adapter_pin_gate", D._const_str(old_src, "PIN_R4_GATE") == D.PIN_R4_GATE_LEGACY)
check("old_adapter_pin_runner", D._const_str(old_src, "PIN_R4_RUNNER") == D.PIN_R4_RUNNER)
check("legacy_gate_source_hash",
      HF(NOTES / "td_policy_a_live_readiness_packet_20261017_11" / "dispatch_gate_r4.py") == D.PIN_R4_GATE_LEGACY)
ca = NOTES / "td_route_adoption_transaction_prep_20261020_48" / "live_dry_run_adapter_r5_candidate.py"
parts = D._join_parts(ca.read_text(), "GATE_PATH")
gate = NOTES.joinpath(*parts)
check("candidate_adapter_gate_path", parts == ["td_route_adoption_transaction_prep_20261020_48", "dispatch_gate_r5_candidate.py"], parts)
check("candidate_adapter_gate_pin", D._const_str(ca.read_text(), "PIN_R4_GATE") == HF(gate) == "94ef967ca832faea4a4a21c666e1a310395961b6df342e098963728ce622555b")
ce = NOTES / "td_route_adoption_transaction_prep_20261020_48" / "live_readiness_executor_r5_candidate.py"
parts = D._join_parts(ce.read_text(), "ADAPTER_PATH")
ad = NOTES.joinpath(*parts)
check("candidate_executor_adapter_path", parts == ["td_route_adoption_transaction_prep_20261020_48", "live_dry_run_adapter_r5_candidate.py"], parts)
check("candidate_executor_adapter_pin", D._const_str(ce.read_text(), "ADAPTER_SHA256") == HF(ad) == HF(ca))
runner = (NOTES / "td_live_dryrun_clock_adapter_binding_20261017_19"
          / "run_clock_adapter_trials.py").read_text()
for label, pat in [("branch_repro", 'load(os.path.join(PKG17, "r4_dry_run_adapter.py")'),
                   ("branch_new", 'load(os.path.join(HERE, "live_dry_run_adapter.py")'),
                   ("branch_binding", 'load(os.path.join(HERE, "live_readiness_executor_r4.py")')]:
    check(label, pat in runner)
m = json.loads((NOTES / "td_route_transaction_workspace_stage_continuation_20261020_52" / "gate_matrix.json").read_bytes())
ev = D.extract_gate567(m)
check("extractor_positive", ev is not None and ev["gate5"] == ev["gate6"] == ev["gate7"] == "PASS")
m2 = copy.deepcopy(m); m2["trials"][0]["facts"]["gates_passed"] = 11
# mutate the G01 green trial specifically
for tr in m2["trials"]:
    if tr["trial"] == "G01_green_dry_run":
        tr["facts"]["gates_passed"] = 11
check("extractor_negative_gates11", D.extract_gate567(m2) is None)
out = {"n": len(checks), "n_pass": sum(1 for c in checks if c["pass"]), "checks": checks}
(HERE / "td54_self_check_results.json").write_text(json.dumps(out, indent=1, sort_keys=True))
print(json.dumps({"n": out["n"], "n_pass": out["n_pass"],
                  "failed": [c["check"] for c in checks if not c["pass"]]}))
