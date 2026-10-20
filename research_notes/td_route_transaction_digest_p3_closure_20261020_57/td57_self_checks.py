#!/usr/bin/env python3
"""-57 pre-execution self-checks (static; executes no proof step).
Verifies: the v9 derivation from EXECUTED v8 is confined to the
spec-6302105446 sanctioned changes (identity/lease + corrected
digest check + main sequence); the corrected digest checker passes
its positive and rejects its negatives on the pinned supplement
bytes; the inherited comparator still proves the -56 candidate
matrix identical to the accepted matrix and detects a mutation;
the retired substring check's schema-invalidity is factual."""
import ast, copy, hashlib, importlib.util, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES = HERE.parent
PKG56 = NOTES / "td_route_transaction_collision_safe_remainder_20261020_56"
PKG48 = NOTES / "td_route_adoption_transaction_prep_20261020_48"
PKG04 = NOTES / "td_fresh_live_driver_integration_evidence_20261016"

V8_PIN = "aad2e97c39b5ef9d59d249a0d5ca6431d27c7c257a3e5542604ce3c4f84d67ad"
SUPP_PIN = "55ad6f40509ac77f0634b8ab4208bf39017219ae065e240af852ac581c1acca5"
EXPECTED = "6b030c62fdaf3cd738001a438b6f6a562b381b93b29dd8b299753de6aebe4fa5"
ORIG_PROOF = "36bc3a89bd266b9d7478d7f6082addd7b764a824bac45afdcbe534eb1d37f21a"

def H(b): return hashlib.sha256(b).hexdigest()
def HF(p): return H(Path(p).read_bytes())

checks = []
def ck(name, cond, detail=""):
    checks.append({"check": name, "pass": bool(cond), "detail": str(detail)})

v8p = PKG56 / "proof_driver_v8.py"
v9p = HERE / "proof_driver_v9.py"
ck("v8_base_pin", HF(v8p) == V8_PIN, HF(v8p))
v8, v9 = v8p.read_text(), v9p.read_text()

def fn_sources(src):
    tree = ast.parse(src)
    return {n.name: ast.get_source_segment(src, n)
            for n in tree.body if isinstance(n, ast.FunctionDef)}
f8, f9 = fn_sources(v8), fn_sources(v9)
ck("v9_new_functions_exact", set(f9) - set(f8) == {"proof_digest_check"},
   str(sorted(set(f9) - set(f8))))
ck("v9_no_functions_removed", set(f8) - set(f9) == set(),
   str(sorted(set(f8) - set(f9))))
SANCTIONED = {"verify_lease", "hash_gates", "build_shadow_gitaware",
              "p2", "p3", "main"}
ident = [n for n in f8 if n not in SANCTIONED and f8[n] == f9.get(n)]
ck("unsanctioned_functions_byte_identical",
   len(ident) == len(f8) - len(SANCTIONED & set(f8)),
   f"{len(ident)}/{len(f8) - len(SANCTIONED & set(f8))} identical")
CRITICAL = ["token_map", "canonicalize", "first_divergence",
            "compare_matrix", "extract_gate567", "serialize",
            "stage_transition_clock", "compare_clock_scoped",
            "branch_provenance", "checker_self_checks", "p0_receipt",
            "p1", "gate7_spot", "run_suite", "cleanup_shadow",
            "build_original_worktree", "p0"]
ck("critical_functions_identical",
   all(f8[n] == f9[n] for n in CRITICAL),
   ",".join(n for n in CRITICAL if f8[n] != f9[n]))
ck("p3_identity_token_only",
   f9["p3"].replace("td57_pilot_stage", "td56_pilot_stage") == f8["p3"])
ck("build_shadow_identity_token_only",
   f9["build_shadow_gitaware"].replace("td57_pilot_stage",
                                        "td56_pilot_stage")
   == f8["build_shadow_gitaware"])
m9 = f9["main"]
ck("main_sequence_exact",
   all(s in m9 for s in ("verify_lease()", "hash_gates()",
                         "build_shadow_gitaware()", "p2()",
                         "p3(expected_f1)"))
   and m9.index("verify_lease()") < m9.index("build_shadow_gitaware()")
   < m9.index("p2()") < m9.index("p3(expected_f1)"))
ck("main_no_closed_family_calls",
   all(s not in m9 for s in ("p0_receipt()", "p1()",
                             "build_original_worktree()",
                             "stage_transition_clock()")))
p2src = f9["p2"]
ck("p2_no_suite_rerun",
   "run_suite" not in p2src and "run_integration_trials" not in p2src)
ck("retired_substring_check_absent",
   "candidate_proof_digest_present_in_candidate_matrix" not in v9
   and "new_proof in raw" not in v9)
ck("identity_paths_td57",
   "td57_wt" in v9 and "qf_td57_stage" in v9
   and "qf_td56_stage" not in v9 and "td56_wt" not in v9)

# import v9 module (top level is side-effect free) for unit tests
sys.argv = ["proof_driver_v9.py", "/tmp"]
spec = importlib.util.spec_from_file_location("proof_driver_v9", v9p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ck("v9_constants_exact",
   mod.PIN_DRIVER_V8 == V8_PIN
   and mod.PIN_CANDIDATE_SUPPLEMENT_FULL == SUPP_PIN
   and mod.EXPECTED_PROOF_DIGEST == EXPECTED)

supp_path = PKG48 / "fresh_supplement_v2_candidate.json"
ck("supplement_source_pin", HF(supp_path) == SUPP_PIN, HF(supp_path))
supp = json.loads(supp_path.read_bytes())
pos = mod.proof_digest_check(supp)
ck("digest_check_positive_on_pinned_supplement", pos["ok"], pos)
neg1 = copy.deepcopy(supp)
neg1["calendar_proofs"] = {ORIG_PROOF: next(iter(
    neg1["calendar_proofs"].values()))}
for v in neg1["entries"].values():
    v["calendar_proof_digest"] = ORIG_PROOF
ck("digest_check_negative_orig_digest_rejected",
   not mod.proof_digest_check(neg1)["ok"])
neg2 = copy.deepcopy(supp)
del neg2["calendar_proofs"]
ck("digest_check_negative_missing_field_rejected",
   not mod.proof_digest_check(neg2)["ok"])
neg3 = copy.deepcopy(supp)
neg3["calendar_proofs"]["0" * 64] = {}
ck("digest_check_negative_two_keys_rejected",
   not mod.proof_digest_check(neg3)["ok"])
neg4 = copy.deepcopy(supp)
neg4["entries"]["REQ-SPT-07"]["calendar_proof_digest"] = ORIG_PROOF
ck("digest_check_negative_entry_mismatch_rejected",
   not mod.proof_digest_check(neg4)["ok"])

# comparator demonstration on committed artifacts (not a suite run)
pairs, names, revs = mod.token_map()
acc = mod.canonicalize(json.loads(
    (PKG04 / "integration_matrix_run2.json").read_bytes()),
    pairs, names, revs)
cand = mod.canonicalize(json.loads(
    (PKG56 / "run_artifacts" / "driver_matrix.json").read_bytes()),
    pairs, names, revs)
ck("comparator_receipt_demo_identical",
   mod.first_divergence(acc, cand) is None
   and mod.count_leaves(acc) == 205,
   f"cells={mod.count_leaves(acc)}")
# mutate deterministically: flip the first PASS leaf to FAIL
cand2 = copy.deepcopy(cand)
def mutate(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if v == "PASS":
                o[k] = "FAIL"
                return True
            if mutate(v):
                return True
    elif isinstance(o, list):
        for v in o:
            if mutate(v):
                return True
    return False
assert mutate(cand2)
ck("comparator_negative_control_detects_mutation",
   mod.first_divergence(acc, cand2) is not None)
hexre = re.compile(r"[0-9a-f]{64}")
ck("matrix_schema_no_64hex_candidate",
   not hexre.search((PKG56 / "run_artifacts" / "driver_matrix.json")
                    .read_text()))
ck("matrix_schema_no_64hex_accepted",
   not hexre.search((PKG04 / "integration_matrix_run2.json")
                    .read_text()))

lease = Path("/home/hatch/workspace/qf_td57_owner_lease.json")
ck("lease_present_matching",
   lease.exists()
   and json.loads(lease.read_text())["task_id"]
   == "QF-TD-ROUTE-TRANSACTION-DIGEST-P3-CLOSURE-20261020-57"
   and json.loads(lease.read_text())["stage_root_planned"]
   == "/home/hatch/workspace/qf_td57_stage")

out = {"task": "QF-TD-ROUTE-TRANSACTION-DIGEST-P3-CLOSURE-20261020-57",
       "checks": checks,
       "passed": sum(1 for c in checks if c["pass"]),
       "total": len(checks)}
(HERE / "td57_self_check_results.json").write_text(json.dumps(out, indent=1))
print(json.dumps({"passed": out["passed"], "total": out["total"],
                  "failed": [c["check"] for c in checks
                             if not c["pass"]]}))
sys.exit(0 if out["passed"] == out["total"] else 1)
