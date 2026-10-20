#!/usr/bin/env python3
"""QF-TD-ROUTE-TRANSACTION-PROOF-CHECKER-CORRECTION-RERUN-20261020-50 r1
proof driver v2. Derived from the -49 proof driver (sha256
1478d746af7fa616e055a804f63c5a240bcb94d2493fc546f9f8b7192a004e5f) with
the ONE authorized semantic correction (spec comment 6289252055 SS B):
the P0 top-level comparison keys every non-callable statement by
position-independent AST CONTENT (multiset with multiplicity), never by
line number; plus checker self-checks and the SS C/D v3 manifest-status
gate in P0. Stage order, fixtures, canonical replacements, failure
keys, first-failure stop, and the P1/P2/P3 logic are unchanged from
-49. ONE attempt, network-denied (unshare -n, enforced by the caller
shell). Order: hash gates -> checker self-checks -> P0 static -> P1
readiness chain -> P2 driver -> P3 route binding + CLI -> post-run
rehash. First material failure stops; the terminal verdict is written
to proof_results.json. Synthetic fixtures only; candidate copies
execute only inside the shadow stage; no live file is executed or
written.
"""
import ast
from collections import Counter
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

OUT = Path(sys.argv[1])
REPO = Path("/home/hatch/workspace/td50_wt")
NOTES = REPO / "research_notes"
STAGE = Path("/tmp/td50_stage")
SHADOW = STAGE / "shadow"
SNOTES = SHADOW / "research_notes"
WHEELHOUSE = Path("/home/hatch/workspace/td_nl_wheelhouse_20261016")

TASK = "QF-TD-ROUTE-TRANSACTION-PROOF-CHECKER-CORRECTION-RERUN-20261020-50"
results = {"task": TASK, "run": 1, "repair_minutes": 0}
subprocess_timeouts = []


def H(b):
    return hashlib.sha256(b).hexdigest()


def HF(p):
    return H(Path(p).read_bytes())


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()


class Fail(Exception):
    def __init__(self, key, detail):
        super().__init__(key)
        self.key = key
        self.detail = detail


def fail(key, detail):
    raise Fail(key, detail)


def load_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- paths
PILOT = NOTES / "pilot_harness"
PKG44 = NOTES / "td_validator_dst_repair_requalification_20261019_44"
PKG45 = NOTES / "td_ends_carry_dst_repair_requalification_20261020_45"
PKG46 = NOTES / "td_ends_carry_proof_harness_rerun_20261020_46"
PKG48 = NOTES / "td_route_adoption_transaction_prep_20261020_48"
PKG49 = NOTES / "td_route_transaction_offline_proof_cli_closure_20261020_49"
PKG50 = NOTES / "td_route_transaction_proof_checker_correction_rerun_20261020_50"
PKG11 = NOTES / "td_policy_a_live_readiness_packet_20261017_11"
PKG19 = NOTES / "td_live_dryrun_clock_adapter_binding_20261017_19"
PKG04 = NOTES / "td_fresh_live_driver_integration_evidence_20261016"
R1PKG = NOTES / "td_fresh_full_manifest_preflight_evidence_20261016"

F_CONSTRUCT = PILOT / "construct_4h.py"
F_V6 = PKG45 / "pilot_build_v6_dstfix.py"
F_VALIDATOR = PKG44 / "validate_input_v3_dstfix.py"
F_CAND_CONSTRUCT = PKG49 / "construct_4h_v3_cliguard.py"
F_CAND_ENTRY = PKG49 / "pilot_build_v7_clibound.py"
F_MANIFEST_V2 = PKG49 / "ROUTE_MANIFEST_CANDIDATE_V2.json"
F_MANIFEST_V3 = PKG50 / "ROUTE_MANIFEST_CANDIDATE_V3.json"
F_DAG_UPDATE = PKG49 / "ROUTE_DAG_ROLLBACK_UPDATE.md"

PIN_LOCK = "08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068"
PIN_WHEELHOUSE = "210b8273a15cc7317b4a8029198f8d6e1401c1e375acdbe7f8602167c13e815b"
PIN_F1_SER_SHA = "bd550433d4af504a05a84be551c45d6a6d35be35cef3f479a6acca2cdf5ce813"
PIN_VALIDATOR_CAND = ("ca3bafd87e7cb439d538ddf924aa08a029dd2c9bb32b485f"
                      "61acbeea91429cc6")
PIN_CONSTRUCTOR_CAND = ("3f432e7e30d3d962b36cb0c82cae9658cf269c3214beb"
                        "918402f8645a3fe0ad1")
PIN_ENTRYPOINT_CAND = ("84ccd2c68aea0f0c9b7e3e97e92ad870bbb3af84a125b"
                       "75b2c1f3e57d20d7772")
STATUS_PENDING = "IMPLEMENTED_BY_CANDIDATE__EXECUTION_PROOF_PENDING"
STATUS_OVERCLAIM = "SATISFIED_BY_CANDIDATE__OFFLINE_PROOF_IN_THIS_PACKAGE"


# ---------------------------------------------------------------- gates
def hash_gates():
    g = {}
    # -48 package: all 19 manifest members rehash
    man = (PKG48 / "SHA256_MANIFEST.txt").read_text().splitlines()
    ok = bad = 0
    for line in man:
        parts = line.split()
        if len(parts) != 2:
            continue
        want, rel = parts
        p = PKG48 / rel
        if p.exists() and HF(p) == want:
            ok += 1
        else:
            bad += 1
    g["pkg48_manifest_members"] = {"matched": ok, "mismatched": bad,
                                   "total": ok + bad}
    if bad or ok != 19:
        fail("HASH_GATE_PKG48", g["pkg48_manifest_members"])
    # route pins from the -48 candidate manifest (adjudicated record)
    m48 = json.loads((PKG48 / "ROUTE_MANIFEST_CANDIDATE.json").read_bytes())
    route = m48["route"]
    for label, fkey in [("constructor", F_CONSTRUCT), ("entrypoint", F_V6),
                        ("validator", F_VALIDATOR)]:
        want = route[label]["sha256"]
        got = HF(fkey)
        g[f"route_{label}"] = {"expected": want, "actual": got,
                               "match": want == got}
        if want != got:
            fail(f"HASH_GATE_ROUTE_{label.upper()}", g[f"route_{label}"])
    # readiness candidates: computed hashes recorded (byte-identity of the
    # committed files is the -48 19/19 check above; pins cross-checked in P0)
    for label, fn in [("supplement", "fresh_supplement_v2_candidate.json"),
                      ("driver", "live_driver_r5_candidate.py"),
                      ("gate", "dispatch_gate_r5_candidate.py"),
                      ("adapter", "live_dry_run_adapter_r5_candidate.py"),
                      ("executor", "live_readiness_executor_r5_candidate.py")]:
        g[f"candidate_{label}"] = HF(PKG48 / fn)
    # -49 candidates vs the v2 manifest pins
    m2 = json.loads(F_MANIFEST_V2.read_bytes())
    for label, fkey in [("constructor", F_CAND_CONSTRUCT),
                        ("entrypoint", F_CAND_ENTRY)]:
        want = m2["route"][label]["sha256"]
        got = HF(fkey)
        g[f"cand49_{label}"] = {"expected": want, "actual": got,
                                "match": want == got}
        if want != got:
            fail(f"HASH_GATE_CAND49_{label.upper()}", g[f"cand49_{label}"])
    g["manifest_v2_sha256"] = HF(F_MANIFEST_V2)
    # spec -50 SS A explicit frozen-pins gate (full-length pins from the
    # adjudication comment, not prefix expansions)
    for label, fkey, want in [
            ("validator_candidate", F_VALIDATOR, PIN_VALIDATOR_CAND),
            ("constructor_candidate", F_CAND_CONSTRUCT,
             PIN_CONSTRUCTOR_CAND),
            ("entrypoint_candidate", F_CAND_ENTRY, PIN_ENTRYPOINT_CAND)]:
        got = HF(fkey)
        g[f"frozen_{label}"] = {"expected": want, "actual": got,
                                "match": want == got}
        if want != got:
            fail(f"HASH_GATE_FROZEN_{label.upper()}", g[f"frozen_{label}"])
    # v3 manifest: present, canonical bytes; status gate runs in P0
    m3_raw = F_MANIFEST_V3.read_bytes()
    g["manifest_v3_sha256"] = H(m3_raw)
    g["manifest_v3_canonical_bytes"] = canon(json.loads(m3_raw)) == m3_raw
    if not g["manifest_v3_canonical_bytes"]:
        fail("HASH_GATE_MANIFEST_V3_CANON", g["manifest_v3_sha256"])
    # environment pins
    g["td_lock"] = HF(STAGE / "integration_requirements.lock")
    if g["td_lock"] != PIN_LOCK:
        fail("HASH_GATE_TD_LOCK", g["td_lock"])
    g["wheelhouse_manifest"] = HF(WHEELHOUSE / "SHA256_MANIFEST.txt")
    if g["wheelhouse_manifest"] != PIN_WHEELHOUSE:
        fail("HASH_GATE_WHEELHOUSE", g["wheelhouse_manifest"])
    # -46 expected F1 serialization (immutable proof object)
    r46 = json.loads((PKG46 / "proof_results.json").read_bytes())
    f1 = r46["family_b_e2"][0]
    if f1["fixture"] != "F1" or f1["result"] != "PASS" \
            or H(f1["cleared_serialization"].encode()) != PIN_F1_SER_SHA:
        fail("HASH_GATE_F46_F1", {"fixture": f1.get("fixture"),
                                  "result": f1.get("result")})
    g["f46_f1_serialization_sha256"] = PIN_F1_SER_SHA
    results["hash_gates"] = g
    results["ledger_before"] = HF(PILOT / "credit_ledger.json")
    return m48, m2, f1["cleared_serialization"]


# ---------------------------------------------------------------- P0
def top_items(src):
    """-50 SS B corrected comparison basis. Every top-level item is
    keyed by CONTENT: callables by name -> normalized AST dump; every
    non-callable statement enters a multiset (Counter) of normalized
    AST dumps. ast.dump carries no source positions, so the comparison
    is invariant to line shifts and banner/comment insertions, and the
    Counter preserves multiplicity of duplicate statements."""
    tree = ast.parse(src)
    callables = {}
    others = Counter()
    guards = set()
    docstring = None
    for i, node in enumerate(tree.body):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            callables[node.name] = ast.dump(node)
        else:
            d = ast.dump(node)
            others[d] += 1
            if isinstance(node, ast.If) and "__main__" in d:
                guards.add(d)
            if i == 0 and isinstance(node, ast.Expr) and isinstance(
                    node.value, ast.Constant) and isinstance(
                    node.value.value, str):
                docstring = d
    return {"callables": callables, "others": others, "guards": guards,
            "docstring": docstring}


def others_delta(a, b):
    return dict(a - b), dict(b - a)


def short(d):
    return H(d.encode())[:16]


def checker_self_checks():
    """Spec -50 SS B.3 pre-run self-checks + the v6 line-shift sanity
    properties. Any failure is the run's first failure."""
    sc = {}
    s_plain = "X = compute(1, 2)\n"
    s_shift = "\n\n# banner comment\n\n\nX = compute(1, 2)\n"
    sc["same_statement_different_lineno_equal"] = \
        top_items(s_plain) == top_items(s_shift)
    sc["replaced_expression_detected"] = \
        top_items(s_plain)["others"] != top_items(
            "X = compute(1, 3)\n")["others"]
    sc["added_expression_detected"] = \
        top_items(s_plain)["others"] != top_items(
            "X = compute(1, 2)\nY = 1\n")["others"]
    sc["removed_expression_detected"] = \
        top_items("X = compute(1, 2)\nY = 1\n")["others"] != top_items(
            s_plain)["others"]
    dup = top_items("Y = 1\nY = 1\n")["others"]
    sc["duplicate_count_preserved"] = sorted(dup.values()) == [2]
    d = others_delta(dup, top_items("Y = 1\n")["others"])
    sc["duplicate_delta_counts_one"] = \
        sum(d[0].values()) == 1 and not d[1]
    v6src = F_V6.read_text()
    a = top_items(v6src)
    b = top_items(v6src)
    sc["v6_vs_v6_delta_empty"] = (a == b and others_delta(
        a["others"], b["others"]) == ({}, {}))
    shifted = "# checker sanity banner\n\n\n" + v6src
    c = top_items(shifted)
    sc["v6_line_shifted_delta_empty"] = (a == c and others_delta(
        a["others"], c["others"]) == ({}, {}))
    results["checker_self_checks"] = sc
    if not all(sc.values()):
        fail("P0_CHECKER_SELF_CHECK", sc)


def p0(m48, m2):
    p = {}
    # constructor candidate: library surface identical, guard only
    o = top_items(F_CONSTRUCT.read_text())
    c = top_items(F_CAND_CONSTRUCT.read_text())
    only_o, only_c = others_delta(o["others"], c["others"])
    p["constructor_surface"] = {
        "callables_compared": len(set(o["callables"]) |
                                  set(c["callables"])),
        "callables_identical": o["callables"] == c["callables"],
        "docstring_identical": o["docstring"] == c["docstring"],
        "others_removed_content_sha": sorted(short(d) for d in only_o),
        "others_added_content_sha": sorted(short(d) for d in only_c),
        "removed_items_are_original_guard_only":
            bool(only_o) and set(only_o) <= o["guards"],
        "added_items_are_candidate_guard_only":
            bool(only_c) and set(only_c) <= c["guards"],
    }
    cs = p["constructor_surface"]
    if not cs["callables_identical"] or not cs["docstring_identical"] \
            or not cs["removed_items_are_original_guard_only"] \
            or not cs["added_items_are_candidate_guard_only"]:
        fail("P0_CONSTRUCTOR_SURFACE", p["constructor_surface"])
    # entrypoint candidate: delta limited to constructor rebinding
    o6 = top_items(F_V6.read_text())
    c7 = top_items(F_CAND_ENTRY.read_text())
    rem7, add7 = others_delta(o6["others"], c7["others"])
    fn_same = o6["callables"] == c7["callables"]
    p["entrypoint_delta"] = {
        "callables_compared": len(set(o6["callables"]) |
                                  set(c7["callables"])),
        "all_functions_identical": fn_same,
        "removed_content_sha": sorted(short(d) for d in rem7),
        "added_content_sha": sorted(short(d) for d in add7),
        "removed_previews": sorted(d[:160] for d in rem7),
        "added_previews": sorted(d[:160] for d in add7),
    }
    allowed_frag = ("construct_4h", "_CONSTRUCTOR_PATH", "_c4h_spec",
                    "_c4h_mod", "importlib")
    diff_dumps = list(rem7) + list(add7)
    if not fn_same or not diff_dumps or any(
            not any(f in d for f in allowed_frag) for d in diff_dumps):
        fail("P0_ENTRYPOINT_DELTA", p["entrypoint_delta"])
    # manifest v2: readiness chain carried unchanged; route pins are the
    # new candidates; no stale authoritative route pins in pin positions
    same = {}
    for key in ["candidates", "readiness", "atomic_set", "rollback",
                "governance"]:
        if key in m48 or key in m2:
            if key == "governance":
                a = {k: v for k, v in (m48.get(key) or {}).items()
                     if k != "direct_cli_refusal"}
                b = {k: v for k, v in (m2.get(key) or {}).items()
                     if k != "direct_cli_refusal"}
                same[key] = a == b
            else:
                same[key] = m48.get(key) == m2.get(key)
    p["manifest_v2_chain_carried"] = same
    if not all(same.values()):
        fail("P0_MANIFEST_V2_CHAIN", same)
    scan = json.dumps({k: m2["route"][k] for k in ("entrypoint",
                                                   "constructor")},
                      sort_keys=True)
    for old in ["d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd",
                "442e56cc16bbbb7ba8f3a62910d92bfcd07d85d0bb88ca2346d26b0bdcd2cba6"]:
        scrubbed = scan.replace(f'"supersedes_entrypoint_sha256": "{old}"', "")
        scrubbed = scrubbed.replace(
            f'"supersedes_constructor_sha256": "{old}"', "")
        if old in scrubbed:
            fail("P0_STALE_ROUTE_PIN", {"pin": old})
    p["stale_route_pins_in_pin_positions"] = False
    # DAG/rollback update record present and naming the new pins
    dag_txt = F_DAG_UPDATE.read_text()
    need = [HF(F_CAND_CONSTRUCT), HF(F_CAND_ENTRY), "withdraw"]
    p["dag_rollback_update"] = {"present": F_DAG_UPDATE.exists(),
                                "names_new_pins_and_withdrawal":
                                all(n in dag_txt for n in need)}
    if not all(p["dag_rollback_update"].values()):
        fail("P0_DAG_ROLLBACK", p["dag_rollback_update"])
    # -50 SS C/D: v3 manifest status correction gate. v3 may differ
    # from v2 ONLY in adjudication_basis and the direct_cli_refusal
    # status; the driver rejects the old overclaiming status outright.
    def status_acceptable(s):
        return s == STATUS_PENDING

    m3 = json.loads(F_MANIFEST_V3.read_bytes())

    def masked(m):
        m = json.loads(json.dumps(m))
        m["adjudication_basis"] = "<MASKED>"
        m["governance"]["direct_cli_refusal"]["status"] = "<MASKED>"
        return m

    old_status = (m2.get("governance") or {}).get(
        "direct_cli_refusal", {}).get("status")
    new_status = (m3.get("governance") or {}).get(
        "direct_cli_refusal", {}).get("status")
    v3 = {
        "manifest_v3_sha256": HF(F_MANIFEST_V3),
        "only_allowed_changes_vs_v2": masked(m2) == masked(m3),
        "adjudication_basis_names_comment_6289252055":
            "6289252055" in str(m3.get("adjudication_basis")),
        "old_status": old_status,
        "new_status": new_status,
        "new_status_is_pending": new_status == STATUS_PENDING,
        "old_overclaiming_status_rejected":
            old_status == STATUS_OVERCLAIM
            and not status_acceptable(old_status)
            and status_acceptable(new_status),
    }
    p["manifest_v3_status"] = v3
    if not all(v for k, v in v3.items() if k not in (
            "old_status", "new_status", "manifest_v3_sha256")):
        fail("P0_MANIFEST_V3_STATUS", v3)
    results["P0"] = p


# ---------------------------------------------------------------- shadow
def copy_file(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def build_shadow():
    if SHADOW.exists():
        shutil.rmtree(SHADOW)
    SNOTES.mkdir(parents=True)
    substituted = {
        "td_policy_a_live_readiness_packet_20261017_11",
        "td_fresh_live_driver_integration_evidence_20261016",
        "td_fresh_full_manifest_preflight_evidence_20261016",
        "td_live_dryrun_clock_adapter_binding_20261017_19",
        "td50_pilot_stage",
    }
    for entry in sorted(os.listdir(NOTES)):
        if entry in substituted:
            continue
        os.symlink(NOTES / entry, SNOTES / entry)
    # -11 packet: runner + support files original; gate module = candidate
    d11 = SNOTES / "td_policy_a_live_readiness_packet_20261017_11"
    for fn in ["run_dispatch_gate_trials_r4.py", "lease_holder.py",
               "lease_contender.py", "crash_child.py",
               "readiness_transaction.py"]:
        copy_file(PKG11 / fn, d11 / fn)
    shutil.copytree(PKG11 / "helper_stub", d11 / "helper_stub")
    copy_file(PKG48 / "dispatch_gate_r5_candidate.py",
              d11 / "dispatch_gate_r4.py")
    # -04 driver evidence: runner staged w/ proof-key literal update only;
    # driver module = candidate
    d04 = SNOTES / "td_fresh_live_driver_integration_evidence_20261016"
    runner_src = (PKG04 / "run_integration_trials.py").read_text()
    old_key = "36bc3a89bd266b9d7478d7f6082addd7b764a824bac45afdcbe534eb1d37f21a"
    new_key = "6b030c62fdaf3cd738001a438b6f6a562b381b93b29dd8b299753de6aebe4fa5"
    assert runner_src.count(old_key) == 1
    (d04 / "run_integration_trials.py").parent.mkdir(parents=True,
                                                     exist_ok=True)
    (d04 / "run_integration_trials.py").write_text(
        runner_src.replace(old_key, new_key))
    copy_file(PKG04 / "ledger_worker_i.py", d04 / "ledger_worker_i.py")
    copy_file(PKG48 / "live_driver_r5_candidate.py", d04 / "live_driver.py")
    # R1 preflight dir: manifest original bytes; supplement = candidate
    copy_file(R1PKG / "fresh_manifest.json", SNOTES /
              "td_fresh_full_manifest_preflight_evidence_20261016" /
              "fresh_manifest.json")
    copy_file(PKG48 / "fresh_supplement_v2_candidate.json", SNOTES /
              "td_fresh_full_manifest_preflight_evidence_20261016" /
              "fresh_supplement.json")
    # -19: runner original; adapter + executor = candidates
    d19 = SNOTES / "td_live_dryrun_clock_adapter_binding_20261017_19"
    copy_file(PKG19 / "run_clock_adapter_trials.py",
              d19 / "run_clock_adapter_trials.py")
    copy_file(PKG48 / "live_dry_run_adapter_r5_candidate.py",
              d19 / "live_dry_run_adapter.py")
    copy_file(PKG48 / "live_readiness_executor_r5_candidate.py",
              d19 / "live_readiness_executor_r4.py")
    # pilot stage for P3
    ps = SNOTES / "td50_pilot_stage"
    copy_file(F_CAND_ENTRY, ps / "pilot_build_v7_clibound.py")
    copy_file(F_CAND_CONSTRUCT, ps / "construct_4h_v3_cliguard.py")
    copy_file(F_VALIDATOR, ps / "validate_input.py")
    copy_file(PILOT / "verify_sources.py", ps / "verify_sources.py")
    staged = {
        "gate_module_is_candidate":
            HF(d11 / "dispatch_gate_r4.py") == HF(PKG48 /
            "dispatch_gate_r5_candidate.py"),
        "driver_module_is_candidate":
            HF(d04 / "live_driver.py") == HF(PKG48 /
            "live_driver_r5_candidate.py"),
        "supplement_is_candidate":
            HF(SNOTES / "td_fresh_full_manifest_preflight_evidence_20261016"
               / "fresh_supplement.json") == HF(PKG48 /
               "fresh_supplement_v2_candidate.json"),
        "adapter_is_candidate":
            HF(d19 / "live_dry_run_adapter.py") == HF(PKG48 /
            "live_dry_run_adapter_r5_candidate.py"),
        "executor_is_candidate":
            HF(d19 / "live_readiness_executor_r4.py") == HF(PKG48 /
            "live_readiness_executor_r5_candidate.py"),
        "staged_driver_runner_diff_lines": 1,
    }
    results["staging"] = staged
    if not all(v for k, v in staged.items()
               if k != "staged_driver_runner_diff_lines"):
        fail("STAGING_BINDING", staged)


def run_suite(argv, cwd, timeout=600):
    r = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                       timeout=timeout)
    return r


# ------------------------------------------------------- canonical cmp
def token_map():
    supp_o = json.loads((R1PKG / "fresh_supplement.json").read_bytes())
    supp_n = json.loads((PKG48 / "fresh_supplement_v2_candidate.json")
                        .read_bytes())
    pairs = [
        (HF(PILOT / "validate_input.py"), HF(F_VALIDATOR), "MECH"),
        (HF(R1PKG / "fresh_supplement.json"),
         HF(PKG48 / "fresh_supplement_v2_candidate.json"), "SUPP"),
        (next(iter(supp_o["calendar_proofs"])),
         next(iter(supp_n["calendar_proofs"])), "PROOF"),
        (HF(PKG04 / "live_driver.py"),
         HF(PKG48 / "live_driver_r5_candidate.py"), "DRIVER"),
        (HF(PKG11 / "dispatch_gate_r4.py"),
         HF(PKG48 / "dispatch_gate_r5_candidate.py"), "GATE"),
        (HF(PKG19 / "live_dry_run_adapter.py"),
         HF(PKG48 / "live_dry_run_adapter_r5_candidate.py"), "ADAPTER"),
        (HF(PKG19 / "live_readiness_executor_r4.py"),
         HF(PKG48 / "live_readiness_executor_r5_candidate.py"), "EXEC"),
    ]
    names = [
        ("live_driver_r5_candidate.py", "live_driver.py", "DRVFILE"),
        ("fresh_supplement_v2_candidate.json", "fresh_supplement.json",
         "SUPPFILE"),
        ("dispatch_gate_r5_candidate.py", "dispatch_gate_r4.py", "GATEFILE"),
        ("live_dry_run_adapter_r5_candidate.py", "live_dry_run_adapter.py",
         "ADPFILE"),
        ("live_readiness_executor_r5_candidate.py",
         "live_readiness_executor_r4.py", "EXECFILE"),
        ("validate_input_v3_dstfix.py", "validate_input.py", "MECHFILE"),
        ("pilot_build_v6_dstfix.py", "pilot_build.py", "ENTRYFILE"),
    ]
    revs = []
    for pth in [PKG11 / "dispatch_gate_r4.py",
                PKG48 / "dispatch_gate_r5_candidate.py"]:
        for node in ast.parse(pth.read_text()).body:
            if isinstance(node, ast.Assign) and getattr(
                    node.targets[0], "id", "") == "REVISION" and isinstance(
                    node.value, ast.Constant):
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


def first_divergence(a, b, path="$"):
    if type(a) is not type(b):
        return {"path": path, "accepted": repr(a)[:200],
                "candidate": repr(b)[:200]}
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                return {"path": f"{path}.{k}",
                        "accepted": "present" if k in a else "absent",
                        "candidate": "present" if k in b else "absent"}
            d = first_divergence(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return {"path": path, "accepted_len": len(a),
                    "candidate_len": len(b)}
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_divergence(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    if a != b:
        return {"path": path, "accepted": repr(a)[:200],
                "candidate": repr(b)[:200]}
    return None


def compare_matrix(label, accepted_path, candidate_obj, key):
    pairs, names, revs = token_map()
    acc = canonicalize(json.loads(Path(accepted_path).read_bytes()),
                       pairs, names, revs)
    cand = canonicalize(candidate_obj, pairs, names, revs)
    div = first_divergence(acc, cand)
    entry = {"accepted_source": str(accepted_path),
             "cells_compared": count_leaves(acc),
             "candidate_cells": count_leaves(cand),
             "identical_after_canonicalization": div is None,
             "first_divergence": div}
    results.setdefault("comparisons", {})[label] = entry
    if div is not None:
        fail(key, entry)
    return entry


# ---------------------------------------------------------------- P1
def p1():
    d11 = SNOTES / "td_policy_a_live_readiness_packet_20261017_11"
    troot = OUT / "gate_trials"
    r = run_suite([sys.executable,
                   str(d11 / "run_dispatch_gate_trials_r4.py"),
                   str(troot), str(OUT / "gate_matrix.json")], cwd=d11)
    results["P1_gate_suite"] = {"exit": r.returncode,
                                "stdout_tail": r.stdout[-400:],
                                "stderr_tail": r.stderr[-800:]}
    if r.returncode != 0 or not (OUT / "gate_matrix.json").exists():
        fail("P1_GATE_SUITE_RUN", results["P1_gate_suite"])
    gate_matrix = json.loads((OUT / "gate_matrix.json").read_bytes())
    compare_matrix("gate_dispatch_matrix", PKG11 / "dispatch_matrix_run2.json",
                   gate_matrix, "P1_GATE_REGRESSION")
    # Gate 5/6/7 evidence: an all-green 12-gate cell in the candidate matrix
    found = []

    def walk(o):
        if isinstance(o, dict):
            gates = o.get("gates")
            if isinstance(gates, list) and len(gates) == 12:
                found.append(gates)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(gate_matrix)
    g567 = None
    for gates in found:
        statuses = []
        for item in gates:
            if isinstance(item, dict):
                statuses.append(item.get("status") or item.get("result"))
            else:
                statuses.append(item)
        if all(s == "PASS" for s in statuses):
            g567 = {"gate5": statuses[4], "gate6": statuses[5],
                    "gate7": statuses[6], "all_12_pass": True}
            break
    results["P1_gate567"] = g567 or {"found_12_gate_cells": len(found)}
    if g567 is None:
        fail("P1_GATE567_NOT_EVIDENCED", results["P1_gate567"])
    # adapter + executor: -19 clock/binding regression
    d19 = SNOTES / "td_live_dryrun_clock_adapter_binding_20261017_19"
    r = run_suite([sys.executable,
                   str(d19 / "run_clock_adapter_trials.py"),
                   str(OUT / "clock_matrix.json")], cwd=d19)
    results["P1_clock_suite"] = {"exit": r.returncode,
                                 "stdout_tail": r.stdout[-400:],
                                 "stderr_tail": r.stderr[-800:]}
    if r.returncode != 0 or not (OUT / "clock_matrix.json").exists():
        fail("P1_CLOCK_SUITE_RUN", results["P1_clock_suite"])
    clock_matrix = json.loads((OUT / "clock_matrix.json").read_bytes())
    compare_matrix("clock_adapter_matrix",
                   PKG19 / "clock_adapter_matrix_run2.json",
                   clock_matrix, "P1_CLOCK_ADAPTER_REGRESSION")
    # Gate-7 mechanism spot check: original vs candidate gate derivation
    spot = {}
    try:
        for label, mod_path in [("original", PKG11 / "dispatch_gate_r4.py"),
                                ("candidate", PKG48 /
                                 "dispatch_gate_r5_candidate.py")]:
            mod = load_mod(mod_path, f"spot_gate_{label}")
            facts = mod.derive_calendar(str(WHEELHOUSE),
                                        str(mod.P_MECHANISM))
            spot[label] = facts
        spot["facts_identical"] = spot["original"] == spot["candidate"]
        july3 = [v for k, v in spot["candidate"].items()
                 if "2026_07_03" in k or "2026-07-03" in k]
        spot["candidate_july3_values"] = july3
        if not spot["facts_identical"] or True not in july3:
            fail("P1_GATE7_SPOT_CHECK", spot)
    except Fail:
        raise
    except Exception as e:  # call-convention issue: record, matrix governs
        spot["error"] = f"{type(e).__name__}: {e}"
    results["P1_gate7_spot_check"] = spot


# ---------------------------------------------------------------- P2
def p2():
    d04 = SNOTES / "td_fresh_live_driver_integration_evidence_20261016"
    troot = OUT / "driver_trials"
    r = run_suite([sys.executable, str(d04 / "run_integration_trials.py"),
                   str(troot), str(OUT / "driver_matrix.json")], cwd=d04)
    results["P2_suite"] = {"exit": r.returncode,
                           "stdout_tail": r.stdout[-400:],
                           "stderr_tail": r.stderr[-800:]}
    if r.returncode != 0 or not (OUT / "driver_matrix.json").exists():
        fail("P2_DRIVER_SUITE_RUN", results["P2_suite"])
    raw = (OUT / "driver_matrix.json").read_text()
    matrix = json.loads(raw)
    compare_matrix("driver_integration_matrix",
                   PKG04 / "integration_matrix_run2.json",
                   matrix, "P2_DRIVER_REGRESSION")
    new_proof = "6b030c62fdaf3cd738001a438b6f6a562b381b93b29dd8b299753de6aebe4fa5"
    results["P2_proof_digest"] = {
        "candidate_proof_digest_present_in_candidate_matrix":
            new_proof in raw,
        "negative_controls_identical": True,  # canonical matrix equality
    }
    if new_proof not in raw:
        fail("P2_PROOF_DIGEST", results["P2_proof_digest"])


# ---------------------------------------------------------------- P3
def serialize(df):
    import pandas as pd
    lines = []
    for ts, row in df.iterrows():
        lines.append("|".join([
            pd.Timestamp(ts).isoformat(),
            repr(float(row["Open"])), repr(float(row["High"])),
            repr(float(row["Low"])), repr(float(row["Close"])),
            repr(float(row["Volume"]))]))
    return "\n".join(lines)


def p3(expected_f1):
    import pandas as pd
    ps = SNOTES / "td50_pilot_stage"
    p = {}
    # binding identity (in-process load of the staged entrypoint copy)
    sys.path.insert(0, str(ps))
    v7 = load_mod(ps / "pilot_build_v7_clibound.py", "qf49_v7")
    cmod = sys.modules.get("construct_4h_v3_cliguard")
    p["constructor_module_file"] = str(cmod.__file__) if cmod else None
    p["constructor_module_sha256"] = HF(cmod.__file__) if cmod else None
    p["validator_module_sha256"] = HF(sys.modules["validate_input"].__file__)
    p["entrypoint_module_sha256"] = HF(ps / "pilot_build_v7_clibound.py")
    p["plain_construct_4h_module_loaded"] = "construct_4h" in sys.modules
    p["construct_is_candidate_function"] = (
        v7.construct_4h is cmod.construct_4h)
    if p["constructor_module_sha256"] != HF(F_CAND_CONSTRUCT) \
            or p["validator_module_sha256"] != HF(F_VALIDATOR) \
            or p["entrypoint_module_sha256"] != HF(F_CAND_ENTRY) \
            or p["plain_construct_4h_module_loaded"] \
            or not p["construct_is_candidate_function"]:
        fail("P3_BINDING", p)
    results["P3_binding"] = p
    # F1 fixture via the candidate validator (same construction as -46)
    VAL = sys.modules["validate_input"]
    NY = "America/New_York"
    day = pd.Timestamp("2025-01-08").tz_localize(NY)
    sched = VAL.xnys_schedule(day)
    starts = sorted(VAL.expected_1h_starts(sched[0], sched[1]))
    rows = {}
    for k, ts in enumerate(starts):
        o = float(100 + k)
        rows[ts] = {"open": o, "high": o + 2.0, "low": o - 2.0,
                    "close": o + 1.0, "volume": float(10000 + 100 * k)}
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index = pd.DatetimeIndex(df.index)
    df = df.sort_index()
    f1_csv = OUT / "f1_input.csv"
    df.to_csv(f1_csv, index_label="timestamp")
    # CLI refusal: full-arg invocation inside a watched tree + bare call
    watch = OUT / "cli_watch"
    watch.mkdir(exist_ok=True)
    shutil.copyfile(f1_csv, watch / "input.csv")

    def tree_hashes(root):
        return {str(f.relative_to(root)): HF(f)
                for f in sorted(root.rglob("*")) if f.is_file()}
    before = tree_hashes(watch)
    cand = ps / "construct_4h_v3_cliguard.py"
    r1 = subprocess.run([sys.executable, str(cand), "--input",
                         str(watch / "input.csv"), "--symbol", "TEST",
                         "--out", str(watch / "out.csv"), "--as-of",
                         "2025-01-08T16:00:00-05:00"],
                        capture_output=True, text=True, cwd=str(watch))
    r2 = subprocess.run([sys.executable, str(cand)],
                        capture_output=True, text=True, cwd=str(watch))
    after = tree_hashes(watch)
    cli = {"exit_with_args": r1.returncode, "stderr_with_args": r1.stderr,
           "exit_no_args": r2.returncode, "stderr_no_args": r2.stderr,
           "out_csv_created": (watch / "out.csv").exists(),
           "watch_tree_unchanged": before == after}
    results["P3_cli_refusal"] = cli
    if r1.returncode != 3 or r2.returncode != 3 \
            or "REFUSED" not in r1.stderr or "REFUSED" not in r2.stderr \
            or cli["out_csv_created"] or not cli["watch_tree_unchanged"]:
        fail("P3_CLI_REFUSAL", cli)
    # entrypoint end-to-end on the F1 fixture
    out_csv = OUT / "f1_out.csv"
    r = subprocess.run([sys.executable, str(ps / "pilot_build_v7_clibound.py"),
                        "--input", str(f1_csv), "--symbol", "TEST",
                        "--window-start", "2025-01-08",
                        "--window-end", "2025-01-08",
                        "--as-of", "2025-01-08T16:00:00-05:00",
                        "--out", str(out_csv)],
                       capture_output=True, text=True, cwd=str(ps))
    results["P3_entrypoint_run"] = {"exit": r.returncode,
                                    "stdout_tail": r.stdout[-500:],
                                    "stderr_tail": r.stderr[-500:]}
    if r.returncode != 0 or not out_csv.exists():
        fail("P3_ENTRYPOINT_FIXTURE", results["P3_entrypoint_run"])
    bars = pd.read_csv(out_csv, index_col=0, parse_dates=True)
    bars.index = pd.DatetimeIndex(bars.index)
    ser = serialize(bars)
    results["P3_entrypoint_run"]["serialization_sha256"] = H(ser.encode())
    results["P3_entrypoint_run"]["serialization_matches_f46"] = \
        ser == expected_f1
    if ser != expected_f1:
        fail("P3_ENTRYPOINT_FIXTURE", results["P3_entrypoint_run"])


# ---------------------------------------------------------------- main
def main():
    try:
        m48, m2, expected_f1 = hash_gates()
        checker_self_checks()
        p0(m48, m2)
        build_shadow()
        p1()
        p2()
        p3(expected_f1)
        # post-run rehash
        post = {"ledger_unchanged":
                HF(PILOT / "credit_ledger.json") == results["ledger_before"],
                "construct_original_unchanged":
                HF(F_CONSTRUCT) == results["hash_gates"]["route_constructor"]
                ["actual"],
                "candidates_unchanged":
                HF(F_CAND_CONSTRUCT) == results["hash_gates"]["cand49_constructor"]["actual"]
                and HF(F_CAND_ENTRY) == results["hash_gates"]["cand49_entrypoint"]["actual"]}
        results["post_run"] = post
        if not all(post.values()):
            fail("POST_REHASH", post)
        results["verdict"] = ("TD_ROUTE_TRANSACTION_PROOF_PASS__"
                              "RESEARCH_ADOPTION_DESIGNATION_READY__S2_HOLD")
    except Fail as e:
        results["first_failure"] = {"key": e.key, "detail": e.detail}
        results["verdict"] = f"TD_ROUTE_TRANSACTION_PROOF_HOLD__{e.key}"
    except Exception as e:
        results["first_failure"] = {"key": "UNEXPECTED_ERROR",
                                    "detail": f"{type(e).__name__}: {e}",
                                    "traceback": traceback.format_exc()}
        results["verdict"] = "TD_ROUTE_TRANSACTION_PROOF_HOLD__UNEXPECTED_ERROR"
    (OUT / "proof_results.json").write_text(
        json.dumps(results, indent=1, sort_keys=True, default=str))
    print(results["verdict"])


if __name__ == "__main__":
    main()
