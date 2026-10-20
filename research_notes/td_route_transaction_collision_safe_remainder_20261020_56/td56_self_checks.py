#!/usr/bin/env python3
"""-56 pre-execution self-checks (static; executes no proof step).
Verifies: the v8 derivation is confined to the spec-6300344562
sanctioned changes; the P2 adapter differs from the frozen runner
by exactly the I01 validator-path line; all pins resolve."""
import ast, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES = HERE.parent
WT = NOTES.parent.parent

def H(b): return hashlib.sha256(b).hexdigest()
def HF(p): return H(Path(p).read_bytes())

checks = []
def ck(name, cond, detail=""):
    checks.append({"check": name, "pass": bool(cond), "detail": detail})

v7p = NOTES / "td_route_transaction_branch_isolated_final_closure_20261020_55" / "proof_driver_v7.py"
v8p = HERE / "proof_driver_v8.py"
v7, v8 = v7p.read_text(), v8p.read_text()
ck("v7_base_pin", HF(v7p) == "bb375b76ddd49af88ebc085ec2c09cef806e67c83a3e21f0596d793d4b26d656", HF(v7p))

def fn_sources(src):
    tree = ast.parse(src)
    out = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            out[node.name] = ast.get_source_segment(src, node)
    return out
f7, f8 = fn_sources(v7), fn_sources(v8)
ck("v8_new_functions_exact", set(f8) - set(f7) == {"verify_lease", "gate7_spot"},
   str(sorted(set(f8) - set(f7))))
ck("v8_no_functions_removed", set(f7) - set(f8) == set(), str(sorted(set(f7) - set(f8))))
SANCTIONED = {"hash_gates", "build_shadow_gitaware", "p1", "p3", "main"}
ident = [n for n in f7 if n not in SANCTIONED and f7[n] == f8.get(n)]
ck("unsanctioned_functions_byte_identical",
   len(ident) == len(f7) - len(SANCTIONED & set(f7)),
   f"{len(ident)}/{len(f7) - len(SANCTIONED & set(f7))} identical")
CRITICAL = ["token_map", "canonicalize", "first_divergence", "compare_matrix",
            "extract_gate567", "p2", "serialize", "stage_transition_clock",
            "compare_clock_scoped", "branch_provenance", "checker_self_checks",
            "p0_receipt", "run_suite", "cleanup_shadow"]
ck("critical_functions_identical", all(f7[n] == f8[n] for n in CRITICAL),
   ",".join(n for n in CRITICAL if f7[n] != f8[n]))
# p3 differs only by the pilot-stage identity token
ck("p3_identity_token_only",
   f8["p3"].replace("td56_pilot_stage", "td55_pilot_stage") == f7["p3"])
# p1: receipt head identical; remainder is gate7_spot only
h7 = f7["p1"].index("    # -54: post-receipt stage transition")
ck("p1_receipt_head_identical", f8["p1"][:h7] == f7["p1"][:h7])
ck("p1_no_clock_execution",
   all(s not in f8["p1"] for s in ("run_clock_adapter_trials",
                                   "stage_transition_clock()",
                                   "branch_provenance()",
                                   "compare_clock_scoped")),
   "no clock-suite/transition/provenance calls in v8 p1")
ck("main_no_original_worktree", "build_original_worktree()" not in f8["main"])
ck("main_lease_first",
   f8["main"].index("verify_lease()") < f8["main"].index("build_shadow_gitaware()"))
ck("gate7_absolute_mechanism", "REPO / mod.P_MECHANISM" in f8["gate7_spot"]
   and "P1_GATE7_SPOT_CHECK" in f8["gate7_spot"])

# adapter: exactly one line differs from the frozen runner
fz = (NOTES / "td_fresh_live_driver_integration_evidence_20261016"
      / "run_integration_trials.py").read_text().splitlines()
adp = (HERE / "run_integration_trials_candidate_aware.py").read_text()
adl = adp.splitlines()
diff_lines = [i for i, (a, b) in enumerate(zip(fz, adl)) if a != b]
ck("adapter_same_length", len(fz) == len(adl), f"{len(fz)} vs {len(adl)}")
ck("adapter_exactly_one_line", len(diff_lines) == 1, str(diff_lines))
if len(diff_lines) == 1:
    i = diff_lines[0]
    ck("adapter_line_is_I01_validate_input",
       '"pilot_harness/validate_input.py"' in fz[i]
       and '"td_validator_dst_repair_requalification_20261019_44/validate_input_v3_dstfix.py"' in adl[i]
       and "NL_MECHANISM_MODULE_SHA256" in adl[i],
       f"line {i + 1}")
ck("adapter_digest_key_count1",
   adp.count("36bc3a89bd266b9d7478d7f6082addd7b764a824bac45afdcbe534eb1d37f21a") == 1)
ck("adapter_pin_in_driver",
   HF(HERE / "run_integration_trials_candidate_aware.py") in v8)

# mechanism + gate pins
ck("candidate_validator_pin",
   HF(NOTES / "td_validator_dst_repair_requalification_20261019_44" / "validate_input_v3_dstfix.py")
   == "ca3bafd87e7cb439d538ddf924aa08a029dd2c9bb32b485f61acbeea91429cc6")
ck("original_mechanism_pin",
   HF(NOTES / "pilot_harness" / "validate_input.py")
   == "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58")
g_o = (NOTES / "td_policy_a_live_readiness_packet_20261017_11" / "dispatch_gate_r4.py").read_text()
g_c = (NOTES / "td_route_adoption_transaction_prep_20261020_48" / "dispatch_gate_r5_candidate.py").read_text()
ck("gate_mechanism_paths",
   'P_MECHANISM = "research_notes/pilot_harness/validate_input.py"' in g_o
   and 'P_MECHANISM = "research_notes/td_validator_dst_repair_requalification_20261019_44/validate_input_v3_dstfix.py"' in g_c)
ck("identity_paths_td56", 'td56_wt' in v8 and 'qf_td56_stage' in v8
   and 'td55_wt' not in v8 and 'qf_td55_stage' not in v8)
lease = Path("/home/hatch/workspace/qf_td56_owner_lease.json")
ck("lease_present_matching",
   lease.exists() and json.loads(lease.read_text())["task"]
   == "QF-TD-ROUTE-TRANSACTION-COLLISION-SAFE-REMAINDER-20261020-56")

out = {"task": "QF-TD-ROUTE-TRANSACTION-COLLISION-SAFE-REMAINDER-20261020-56",
       "checks": checks,
       "passed": sum(1 for c in checks if c["pass"]), "total": len(checks)}
(HERE / "td56_self_check_results.json").write_text(json.dumps(out, indent=1))
print(json.dumps({"passed": out["passed"], "total": out["total"],
                  "failed": [c["check"] for c in checks if not c["pass"]]}))
sys.exit(0 if out["passed"] == out["total"] else 1)
