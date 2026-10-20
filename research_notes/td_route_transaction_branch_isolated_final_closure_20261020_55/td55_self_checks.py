#!/usr/bin/env python3
"""QF-TD-...-20261020-55 r1 self-checks for proof driver v7.
Static/synthetic only: no suite execution, no staging, no network.
Checks: (1) v6 pin; (2) v6->v7 function confinement; (3) pin
constants vs files + spec prefixes; (4) scoped comparator behavior
on synthetic mutations of the real accepted run-2 matrix."""
import ast, copy, hashlib, importlib.util, json, sys
from pathlib import Path

NOTES = Path("/home/hatch/workspace/qf-td55/research_notes")
PKG54 = NOTES / "td_route_transaction_dual_path_clock_closure_20261020_54"
PKG55 = NOTES / "td_route_transaction_branch_isolated_final_closure_20261020_55"
H = lambda b: hashlib.sha256(b).hexdigest()
checks = []
def ck(name, ok, detail=""):
    checks.append({"check": name, "pass": bool(ok), "detail": str(detail)[:300]})

v6_src = (PKG54 / "proof_driver_v6.py").read_text()
v7_src = (PKG55 / "proof_driver_v7.py").read_text()
ck("v6_hash_is_frozen_pin",
   H(v6_src.encode()) == "3d02de026938c2a8f05a8ad7fee35f96b6d2bfd5eb7a6dadf9dd86090bb3bcf6",
   H(v6_src.encode()))

def funcs(src):
    out = {}
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = ast.get_source_segment(src, node)
    return out
f6, f7 = funcs(v6_src), funcs(v7_src)
ALLOWED_CHANGED = {"hash_gates", "cleanup_shadow", "p1", "main",
                   "build_shadow_gitaware", "p3"}  # p3: pilot-rename only, proven separately below
NEW_FUNCS = {"build_original_worktree", "branch_provenance",
             "_trial_contrib", "compare_clock_scoped"}
bad = []
for name, seg in f6.items():
    if name in ALLOWED_CHANGED:
        continue
    if name not in f7 or f7[name] != seg:
        bad.append(name)
ck("unchanged_functions_byte_identical", not bad, bad)
ck("new_functions_exact_set", NEW_FUNCS <= set(f7) and not (set(f7) - set(f6) - NEW_FUNCS),
   sorted(set(f7) - set(f6)))
# build_shadow_gitaware may differ ONLY by the pilot-stage dir rename
norm = f7["build_shadow_gitaware"].replace("td55_pilot_stage", "td54_pilot_stage")
ck("build_shadow_gitaware_only_pilot_rename", norm == f6["build_shadow_gitaware"])
for fn in ["stage_transition_clock", "p2", "extract_gate567",
           "compare_matrix", "canonicalize", "token_map"]:
    ck(f"frozen_{fn}", f7.get(fn) == f6.get(fn))
# p3 differs ONLY by the pilot-stage dir identity string (td54->td55),
# the same authorized staging rename proven for build_shadow_gitaware
ck("frozen_p3_modulo_pilot_rename",
   f7["p3"].replace("td55_pilot_stage", "td54_pilot_stage") == f6["p3"])

# load v7 as a module (OUT = argv[1])
sys.argv = ["self_checks", "/tmp"]
spec = importlib.util.spec_from_file_location("qf55_v7", PKG55 / "proof_driver_v7.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ck("pin_driver_v6_constant", mod.PIN_DRIVER_V6 == H(v6_src.encode()))
ck("pin_orig_driver", mod.PIN_ORIG_DRIVER.startswith("5fed4524")
   and mod.PIN_ORIG_DRIVER == H((mod.PKG04 / "live_driver.py").read_bytes()))
ck("pin_orig_supplement", mod.PIN_ORIG_SUPPLEMENT.startswith("3cbdbf63")
   and mod.PIN_ORIG_SUPPLEMENT == H((mod.R1PKG / "fresh_supplement.json").read_bytes()))
ck("pin_orig_mechanism", mod.PIN_ORIG_MECHANISM.startswith("1b83cdcd")
   and mod.PIN_ORIG_MECHANISM == H((mod.PILOT / "validate_input.py").read_bytes()))
supp_o = json.loads((mod.R1PKG / "fresh_supplement.json").read_bytes())
ck("pin_orig_proof", mod.PIN_ORIG_PROOF.startswith("36bc3a89")
   and mod.PIN_ORIG_PROOF == next(iter(supp_o["calendar_proofs"])))
supp_c = json.loads((mod.PKG48 / "fresh_supplement_v2_candidate.json").read_bytes())
ck("candidate_proof_constant", next(iter(supp_c["calendar_proofs"]))
   == "6b030c62fdaf3cd738001a438b6f6a562b381b93b29dd8b299753de6aebe4fa5")
for label, fn, pref in [("gate", "dispatch_gate_r5_candidate.py", "94ef967c"),
                        ("driver", "live_driver_r5_candidate.py", "d11c6b58"),
                        ("supplement", "fresh_supplement_v2_candidate.json", "55ad6f40"),
                        ("adapter", "live_dry_run_adapter_r5_candidate.py", "6980b5b3"),
                        ("executor", "live_readiness_executor_r5_candidate.py", "bbc23616")]:
    ck(f"candidate_pin_{label}", H((mod.PKG48 / fn).read_bytes()).startswith(pref))
ck("candidate_mechanism_pin", mod.PIN_VALIDATOR_CAND.startswith("ca3bafd8")
   and mod.PIN_VALIDATOR_CAND == H(mod.F_VALIDATOR.read_bytes()))

# scoped comparator synthetic tests against the real accepted matrix
acc = json.loads((mod.PKG19 / "clock_adapter_matrix_run2.json").read_bytes())
def run_case(orig, cand):
    mod.results = {"task": "selfcheck"}
    try:
        mod.compare_clock_scoped(copy.deepcopy(orig), copy.deepcopy(cand))
        return None
    except mod.Fail as e:
        return e.key
ck("scoped_pass_exact_both", run_case(acc, acc) is None)
c2 = copy.deepcopy(acc); c2["trials"]["repro_old"]["checks"]["gates_11_of_12"] = False
ck("scoped_candidate_repro_mutation_ignored", run_case(acc, c2) is None)
c3 = copy.deepcopy(acc); c3["trials"]["binding_ok"]["checks"]["adapter_pin_matches_file"] = False
ck("scoped_candidate_other_mutation_fails", run_case(acc, c3) == "P1_CLOCK_ADAPTER_REGRESSION")
o4 = copy.deepcopy(acc); o4["trials"]["repro_old"]["ok"] = False
ck("scoped_original_repro_mutation_fails", run_case(o4, acc) == "P1_CLOCK_ADAPTER_REGRESSION")
c5 = copy.deepcopy(acc); del c5["trials"]["scope"]
ck("scoped_partition_missing_trial_fails", run_case(acc, c5) == "P1_CLOCK_TRIAL_PARTITION")

n_pass = sum(1 for c in checks if c["pass"])
out = {"task": "QF-TD-ROUTE-TRANSACTION-BRANCH-ISOLATED-FINAL-CLOSURE-20261020-55",
       "driver_v7_sha256": H(v7_src.encode()), "n_pass": n_pass,
       "n_checks": len(checks), "checks": checks}
(PKG55 / "td55_self_check_results.json").write_text(json.dumps(out, indent=1))
print(f"self-checks: {n_pass}/{len(checks)} PASS")
for c in checks:
    if not c["pass"]:
        print("FAIL:", c["check"], c["detail"])
sys.exit(0 if n_pass == len(checks) else 1)
