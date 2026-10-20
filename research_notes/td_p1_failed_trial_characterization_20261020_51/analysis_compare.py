#!/usr/bin/env python3
"""-51 static per-cell comparison: accepted -11 run-2 matrix vs -50 candidate
gate_matrix.json, replicating the -50 driver's canonicalize() exactly
(proof_driver_v2.py token_map/canonicalize, read as text). Pure JSON/file
analysis: imports NO chain code; executes nothing from the chain."""
import ast, hashlib, json
from pathlib import Path

NOTES = Path("/tmp/td51_wt/research_notes")
PKG44 = NOTES / "td_validator_dst_repair_requalification_20261019_44"
PKG48 = NOTES / "td_route_adoption_transaction_prep_20261020_48"
PKG11 = NOTES / "td_policy_a_live_readiness_packet_20261017_11"
PKG19 = NOTES / "td_live_dryrun_clock_adapter_binding_20261017_19"
PKG04 = NOTES / "td_fresh_live_driver_integration_evidence_20261016"
R1PKG = NOTES / "td_fresh_full_manifest_preflight_evidence_20261016"
PILOT = NOTES / "pilot_harness"
CAND = NOTES / "td_route_transaction_proof_checker_correction_rerun_20261020_50" / "gate_matrix.json"
ACC = PKG11 / "dispatch_matrix_run2.json"

def HF(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def token_map():
    supp_o = json.loads((R1PKG / "fresh_supplement.json").read_bytes())
    supp_n = json.loads((PKG48 / "fresh_supplement_v2_candidate.json").read_bytes())
    pairs = [
        (HF(PILOT / "validate_input.py"), HF(PKG44 / "validate_input_v3_dstfix.py"), "MECH"),
        (HF(R1PKG / "fresh_supplement.json"), HF(PKG48 / "fresh_supplement_v2_candidate.json"), "SUPP"),
        (next(iter(supp_o["calendar_proofs"])), next(iter(supp_n["calendar_proofs"])), "PROOF"),
        (HF(PKG04 / "live_driver.py"), HF(PKG48 / "live_driver_r5_candidate.py"), "DRIVER"),
        (HF(PKG11 / "dispatch_gate_r4.py"), HF(PKG48 / "dispatch_gate_r5_candidate.py"), "GATE"),
        (HF(PKG19 / "live_dry_run_adapter.py"), HF(PKG48 / "live_dry_run_adapter_r5_candidate.py"), "ADAPTER"),
        (HF(PKG19 / "live_readiness_executor_r4.py"), HF(PKG48 / "live_readiness_executor_r5_candidate.py"), "EXEC"),
    ]
    names = [
        ("live_driver_r5_candidate.py", "live_driver.py", "DRVFILE"),
        ("fresh_supplement_v2_candidate.json", "fresh_supplement.json", "SUPPFILE"),
        ("dispatch_gate_r5_candidate.py", "dispatch_gate_r4.py", "GATEFILE"),
        ("live_dry_run_adapter_r5_candidate.py", "live_dry_run_adapter.py", "ADPFILE"),
        ("live_readiness_executor_r5_candidate.py", "live_readiness_executor_r4.py", "EXECFILE"),
        ("validate_input_v3_dstfix.py", "validate_input.py", "MECHFILE"),
        ("pilot_build_v6_dstfix.py", "pilot_build.py", "ENTRYFILE"),
    ]
    revs = []
    for pth in [PKG11 / "dispatch_gate_r4.py", PKG48 / "dispatch_gate_r5_candidate.py"]:
        for node in ast.parse(pth.read_text()).body:
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "REVISION" \
               and isinstance(node.value, ast.Constant):
                revs.append(node.value.value)
    return pairs, names, revs

def canonicalize(obj, pairs, names, revs):
    s = json.dumps(obj, sort_keys=True)
    for new, old, tok in names:
        s = s.replace(new, f"<{tok}>").replace(old, f"<{tok}>")
    for o, n, tok in pairs:
        s = s.replace(o, f"<{tok}>").replace(n, f"<{tok}>")
    for o, n, tok in pairs:
        s = s.replace(o[:12], f"<{tok}>").replace(n[:12], f"<{tok}>")
        s = s.replace(o[:8], f"<{tok}>").replace(n[:8], f"<{tok}>")
    for r in revs:
        s = s.replace(r, "<REV>")
    s = s.replace("td_route_adoption_transaction_prep_20261020_48", "<PKG48>")
    return json.loads(s)

def count_leaves(o):
    if isinstance(o, dict):
        return sum(count_leaves(v) for v in o.values())
    if isinstance(o, list):
        return sum(count_leaves(v) for v in o)
    return 1

def flatten(o, path="$", out=None):
    if out is None:
        out = {}
    if isinstance(o, dict):
        for k in sorted(o):
            flatten(o[k], f"{path}.{k}", out)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            flatten(v, f"{path}[{i}]", out)
    else:
        out[path] = o
    return out

pairs, names, revs = token_map()
acc_raw = json.loads(ACC.read_bytes())
cand_raw = json.loads(CAND.read_bytes())
acc = canonicalize(acc_raw, pairs, names, revs)
cand = canonicalize(cand_raw, pairs, names, revs)
print("leaf counts: accepted", count_leaves(acc), "candidate", count_leaves(cand),
      "(driver recorded 751 / 659)")
fa, fc = flatten(acc), flatten(cand)
keys = sorted(set(fa) | set(fc))
divergent, only_acc, only_cand = [], [], []
for k in keys:
    if k in fa and k in fc:
        if fa[k] != fc[k] or type(fa[k]) is not type(fc[k]):
            divergent.append({"path": k, "accepted": fa[k], "candidate": fc[k]})
    elif k in fa:
        only_acc.append({"path": k, "accepted": fa[k]})
    else:
        only_cand.append({"path": k, "candidate": fc[k]})
print("divergent:", len(divergent), "only_accepted:", len(only_acc), "only_candidate:", len(only_cand))

# trial name map: index -> name (from raw accepted, order preserved in both)
acc_trials = {t["trial"]: t for t in acc_raw["trials"]}
cand_trials = {t["trial"]: t for t in cand_raw["trials"]}
print("accepted statuses:", {t["trial"]: t["status"] for t in acc_raw["trials"] if t["status"] != "PASS"})
print("candidate FAIL trials:", [t["trial"] for t in cand_raw["trials"] if t["status"] != "PASS"])

json.dump({"divergent": divergent, "only_accepted": only_acc,
           "only_candidate": only_cand,
           "leaf_counts": {"accepted": count_leaves(acc), "candidate": count_leaves(cand)}},
          open("/tmp/td51_diff.json", "w"), indent=1)
# also dump raw per-trial facts side by side for the failing 24
failing = ["G01_green_dry_run","G02_green_dispatch_and_replay","G03_default_factory_spy_wiring",
 "F19_token_mismatch","F20_evidence_tamper_token","G04_lease_lifecycle","H01_helper_import_fail_seam",
 "H02_helper_wrong_module","H03_helper_wrong_callable","H04_helper_wrong_binding",
 "H05_helper_real_sanctioned_path","C01_contention_two_process","P01_helper_absent_path",
 "P02_shadow_on_default_path","P03_wrong_origin_no_pin","P04_signature_mismatch","P05_post_gate_swap",
 "P06_tampered_bytes","P08_handoff_shadow_installed","A01_policy_digest_drift","A03_go_record_absent",
 "A04_go_record_malformed","A05_gate3_remaining_exactly_52","A06_gate3_remaining_51"]
side = {}
for name in failing:
    side[name] = {"accepted": acc_trials[name], "candidate": cand_trials[name]}
json.dump(side, open("/tmp/td51_failing24.json", "w"), indent=1)
passing = [t["trial"] for t in cand_raw["trials"] if t["status"] == "PASS"]
json.dump({"passing22": passing,
           "facts": {n: {"accepted": acc_trials[n]["facts"], "candidate": cand_trials[n]["facts"]} for n in passing}},
          open("/tmp/td51_passing22.json", "w"), indent=1)
print("wrote /tmp/td51_diff.json, td51_failing24.json, td51_passing22.json")
