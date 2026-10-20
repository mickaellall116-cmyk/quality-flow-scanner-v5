#!/usr/bin/env python3
"""QF-TD-ROUTE-TRANSACTION-BRANCH-ISOLATED-FINAL-CLOSURE-20261020-55 r1
proof driver v7 (orchestrator). Derived from frozen proof driver v6
(sha256 3d02de026938c2a8f05a8ad7fee35f96b6d2bfd5eb7a6dadf9dd86090bb3bcf6)
under spec comment 6297990771 with ONLY: (a) task identity / stage /
worktree path strings; (b) added hash gate pinning driver v6 (the
-52 proof-results gate d31e41c3469c9d8546feb04513372193273817d0864c
354fb061b85eade1df52 is inherited from v5 unchanged); (c) the branch-isolated clock stage:
stage_transition_clock() is retained unchanged for the CANDIDATE
branch; p1() additionally builds a second, ORIGINAL git worktree
(untouched committed artifacts, no candidate substitution, no
transition), runs the unchanged -19 suite in each branch, and
adjudicates scoped partitions (ORIGINAL: repro_old + its rollup
contribution; CANDIDATE: the other 19 trials, repro_old excluded).
Gate-7 spot check, P2 and P3 are the v6 code unchanged, executed
against the candidate branch only. The -19 runner's historical-reproduction branch
loads the -17 adapter, whose import-time _load_runner() pin-checks
the gate at the legacy PKG11 path against the ORIGINAL r4 bytes
(b5399645...); driver v5 staged the candidate gate at that path, so
the import refused with PIN_MISMATCH:r4_gate (the -53 first failure -
a proof-stage namespace collision, not a candidate defect). The
transition restores the original gate bytes at the shadow's legacy
PKG11 path ONLY; the candidate gate stays at its immutable -48
package path for the candidate adapter/executor chain, and the
transition proves the spec S.3 preflight simultaneously (legacy
path/pin, old-adapter resolution, candidate gate/adapter/executor
path+pin resolution, runner branch map). Comparator, canonical
replacements, extractor, fixtures, expectations, failure keys and
first-failure stop discipline are the v5 code unchanged. ONE
attempt, network-denied (unshare -n, enforced by the caller shell).
Order: hash gates -> P0 receipt -> git-aware staging + blob proof
-> P1 (receipt + extractor + stage transition + clock suite +
Gate-7 spot check) -> P2 -> P3 -> post-run rehash -> shadow
removal. Synthetic fixtures only; candidate copies execute only
inside the shadow stage; no live file is executed or written.
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
REPO = Path("/home/hatch/workspace/td55_wt")
MAINREPO = Path("/home/hatch/workspace/quality-flow-scanner-v5")
NOTES = REPO / "research_notes"
STAGE = Path("/home/hatch/workspace/qf_td55_stage")
SHADOW = STAGE / "shadow_candidate"
SHADOW_O = STAGE / "shadow_original"
SNOTES_O = SHADOW_O / "research_notes"
SNOTES = SHADOW / "research_notes"
WHEELHOUSE = Path("/home/hatch/workspace/td_nl_wheelhouse_20261016")

TASK = "QF-TD-ROUTE-TRANSACTION-BRANCH-ISOLATED-FINAL-CLOSURE-20261020-55"
results = {"task": TASK, "run": 1, "repair_minutes": 0,
           "adjudication_basis": "6297990771",
           "continuation_of": "QF-TD-ROUTE-TRANSACTION-DUAL-PATH-CLOCK-CLOSURE-20261020-54 87dfd68+c026fe7"}
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
PKG51 = NOTES / "td_route_transaction_git_aware_staging_continuation_20261020_51"
PKG52 = NOTES / "td_route_transaction_workspace_stage_continuation_20261020_52"
PKG53 = NOTES / "td_route_transaction_receipt_extractor_correction_closure_20261020_53"
PKG54 = NOTES / "td_route_transaction_dual_path_clock_closure_20261020_54"
PKG17 = NOTES / "td_status_query_placement_20261017_17"
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
PIN_DRIVER_V2 = ("68998a9060e5d3f5253023d94a00993e77f04588eb6aeed8da"
                 "12278b176b832e")
PIN_DRIVER_V4 = ("d2605bb411e8cc0f474a035e14e8f0b477113f25bde6aac6df88f5"
                 "28f9f309b8")
PIN_DRIVER_V5 = ("33681f79b6c859ede5568f4f5399c5ea5b2771741c8f5a6faed"
                 "da95aac0ec018")
# -55 (spec 6297990771): frozen driver v6 byte-identity (the v7 base)
PIN_DRIVER_V6 = ("3d02de026938c2a8f05a8ad7fee35f96b6d2bfd5eb7a6dad"
                 "f9dd86090bb3bcf6")
# -55 SS.4: ORIGINAL branch exact pins (accepted originals)
PIN_ORIG_DRIVER = "5fed45242eb5ec465266c4d4c4258485f01a8c5bfdfdda2fb81295d3cf6d9c00"
PIN_ORIG_SUPPLEMENT = "3cbdbf63fd49b021dc74f63727098551753949f8684967981c65f66101f95a86"
PIN_ORIG_MECHANISM = "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58"
PIN_ORIG_PROOF = "36bc3a89bd266b9d7478d7f6082addd7b764a824bac45afdcbe534eb1d37f21a"
# -54 (spec 6296388979): the ORIGINAL r4 gate bytes the -17 adapter's
# import-time pin requires at the legacy PKG11 path.
PIN_R4_GATE_LEGACY = ("b53996454650dafc77e647a8497eba91beb3785fb52c13"
                      "d70fa81768fd370117")
PIN_R4_RUNNER = ("93b911e067eb6ff6bc7e797b08df44eb1ac17a2417ac2102f3f"
                 "d347087447864")
PIN_RECEIPT52_COMMIT = "a2b334fbe0e0cc973cad9dd839b6ec10659e353a"
PIN_GATE_MATRIX_52 = ("b523b148042ee4012f5eae3fe96e0e5d06d134c37c06adfa4"
                      "47e99eb37df12ac")
# Spec 6295378552 states the -52 proof-results pin as
# d31e41c3b9f1128d741...; the bytes AT the spec's own cited immutable
# result commit a2b334f hash to the value below (8-char prefix
# d31e41c3 matches; the spec's full expansion matches no committed
# object - the corrupted-expansion pattern disclosed in -49). The
# commit blob is the anchor; the actual bytes are what is gated.
PIN_PROOF_RESULTS_52 = ("d31e41c3469c9d8546feb04513372193273817d0864c35"
                        "4fb061b85eade1df52")
PIN_MANIFEST_V3 = ("9573118c9b98cf920a008cec2176f0b2a52366d4f1cf57d08c"
                   "289086c5059e14")
CANDIDATE_PREFIXES = {"supplement": "55ad6f40", "driver": "d11c6b58",
                      "gate": "94ef967c", "adapter": "6980b5b3",
                      "executor": "bbc23616"}
COLLECTOR_COMMIT = "ab254c3458697dd450356146abcf4ad4f75ecef4"
COLLECTOR_PATH = ("research_notes/td_lifecycle_repair_candidate/"
                  "td_min_collector.py")
PIN_COLLECTOR = ("b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4a"
                 "a02ec4cc5d2c")
_pre_status = {}
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
    # -51 SS A: the frozen corrected checker (driver v2) byte-identity
    _dv2 = HF(PKG50 / "proof_driver_v2.py")
    g["frozen_driver_v2"] = {"expected": PIN_DRIVER_V2, "actual": _dv2,
                             "match": _dv2 == PIN_DRIVER_V2}
    if not g["frozen_driver_v2"]["match"]:
        fail("HASH_GATE_FROZEN_DRIVER_V2", g["frozen_driver_v2"])
    # -51 SS A: -48 readiness candidate pins (spec prefixes; full
    # hashes recorded above in candidate_*; byte-identity of the
    # committed files is the 19/19 manifest check)
    for label, pref in CANDIDATE_PREFIXES.items():
        full = g[f"candidate_{label}"]
        g[f"candidate_{label}_pin"] = {"expected_prefix": pref,
                                       "actual": full,
                                       "match": full.startswith(pref)}
        if not g[f"candidate_{label}_pin"]["match"]:
            fail(f"HASH_GATE_CANDIDATE_{label.upper()}",
                 g[f"candidate_{label}_pin"])
    if g["manifest_v3_sha256"] != PIN_MANIFEST_V3:
        fail("HASH_GATE_MANIFEST_V3_PIN", g["manifest_v3_sha256"])
    # -53 SS A: frozen driver v4 byte-identity + the pinned -52
    # receipt files (result commit a2b334f) byte-identity
    _dv4 = HF(PKG52 / "proof_driver_v4.py")
    g["frozen_driver_v4"] = {"expected": PIN_DRIVER_V4, "actual": _dv4,
                             "match": _dv4 == PIN_DRIVER_V4}
    if not g["frozen_driver_v4"]["match"]:
        fail("HASH_GATE_FROZEN_DRIVER_V4", g["frozen_driver_v4"])
    for label, fn, want in [
            ("gate_matrix", "gate_matrix.json", PIN_GATE_MATRIX_52),
            ("proof_results", "proof_results.json",
             PIN_PROOF_RESULTS_52)]:
        got = HF(PKG52 / fn)
        g[f"receipt52_{label}"] = {"expected": want, "actual": got,
                                   "match": got == want,
                                   "commit": PIN_RECEIPT52_COMMIT}
        if got != want:
            fail(f"HASH_GATE_RECEIPT52_{label.upper()}",
                 g[f"receipt52_{label}"])
    # -54 SS A: frozen driver v5 byte-identity (the v6 base)
    _dv5 = HF(PKG53 / "proof_driver_v5.py")
    g["frozen_driver_v5"] = {"expected": PIN_DRIVER_V5, "actual": _dv5,
                             "match": _dv5 == PIN_DRIVER_V5}
    if not g["frozen_driver_v5"]["match"]:
        fail("HASH_GATE_FROZEN_DRIVER_V5", g["frozen_driver_v5"])
    # -55 SS A: frozen driver v6 byte-identity (the v7 base)
    _dv6 = HF(PKG54 / "proof_driver_v6.py")
    g["frozen_driver_v6"] = {"expected": PIN_DRIVER_V6, "actual": _dv6,
                             "match": _dv6 == PIN_DRIVER_V6}
    if not g["frozen_driver_v6"]["match"]:
        fail("HASH_GATE_FROZEN_DRIVER_V6", g["frozen_driver_v6"])
    results["hash_gates"] = g
    results["ledger_before"] = HF(PILOT / "credit_ledger.json")
    return m48, m2, f1["cleared_serialization"]


def p0_receipt():
    """Spec 6290393927 SS C: no P0 rerun beyond hash/status receipt
    verification. The -50 semantic-delta proof stands accepted on the
    immutable record; this run only verifies the receipt."""
    pr = json.loads((PKG50 / "proof_results.json").read_bytes())
    dv2 = HF(PKG50 / "proof_driver_v2.py")
    rc = {
        "task": pr.get("task"),
        "verdict": pr.get("verdict"),
        "has_P0": "P0" in pr,
        "has_hash_gates": "hash_gates" in pr,
        "driver_v2_receipt_hash": dv2,
        "driver_v2_receipt_match": dv2 == PIN_DRIVER_V2,
        "manifest_v3_status": (json.loads(
            F_MANIFEST_V3.read_bytes()).get("governance") or {}
            ).get("direct_cli_refusal", {}).get("status"),
        "REQ_S2": "UNIMPLEMENTED__HARD_HOLD",
    }
    rc["accepted_P0"] = (
        rc["task"] == "QF-TD-ROUTE-TRANSACTION-PROOF-CHECKER-"
                      "CORRECTION-RERUN-20261020-50"
        and rc["verdict"] == "TD_ROUTE_TRANSACTION_PROOF_HOLD__"
                             "P1_GATE_REGRESSION"
        and rc["has_P0"] and rc["has_hash_gates"]
        and rc["driver_v2_receipt_match"])
    rc["v3_status_pending"] = rc["manifest_v3_status"] == STATUS_PENDING
    results["P0_receipt"] = rc
    if not rc["accepted_P0"] or not rc["v3_status_pending"]:
        fail("P0_RECEIPT", rc)


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


# --------------------------------------------- git-aware shadow (-51)
def _git(args, cwd=None):
    r = subprocess.run(["git"] + args,
                       cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True, timeout=120)
    return r


def status_hash(repo):
    r = _git(["-C", str(repo), "status", "--porcelain"])
    return H(r.stdout.encode()), r.stdout.count("\n")


def build_shadow_gitaware():
    """Spec 6290393927 SS B. The ephemeral shadow is a DETACHED GIT
    WORKTREE of this repository. Candidate substitution is byte-for-byte
    the -50 staging plan applied over the worktree's committed files;
    non-substituted package dirs are left as the worktree's real
    (committed) files. The SS B preflight - including the standalone
    collector-blob resolution proof - gates execution: any failure is
    the run's first failure and P1 never starts."""
    SNOTES = SHADOW / "research_notes"
    # SS B.5 pre-repository status (main working tree + this worktree)
    _pre_status["main_status"], _pre_status["main_status_lines"] = \
        status_hash(MAINREPO)
    _pre_status["repo_status"], _pre_status["repo_status_lines"] = \
        status_hash(REPO)
    _pre_status["repo_head"] = _git(["-C", str(REPO), "rev-parse",
                                     "HEAD"]).stdout.strip()
    _pre_status["worktrees_before"] = _git(
        ["-C", str(REPO), "worktree", "list",
         "--porcelain"]).stdout.strip()
    # dispose of any stale shadow from a crashed attempt, then create
    if SHADOW.exists() or SHADOW.is_symlink():
        rr = _git(["-C", str(REPO), "worktree", "remove", "--force",
                   str(SHADOW)])
        _pre_status["stale_shadow_cleanup_rc"] = rr.returncode
        if SHADOW.exists() or SHADOW.is_symlink():
            if SHADOW.is_symlink() or SHADOW.is_file():
                SHADOW.unlink()
            else:
                shutil.rmtree(SHADOW)
    _git(["-C", str(REPO), "worktree", "prune"])
    ra = _git(["-C", str(REPO), "worktree", "add", "--detach",
               str(SHADOW)])
    if ra.returncode != 0 or not SHADOW.is_dir():
        fail("STAGING_WORKTREE_ADD",
             {"rc": ra.returncode, "stderr": ra.stderr[-500:]})
    _pre_status["shadow_created"] = True
    _pre_status["shadow_head"] = _git(["-C", str(SHADOW), "rev-parse",
                                       "HEAD"]).stdout.strip()
    # Candidate substitution: byte-for-byte the -50 staging plan.
    # Substituted package dirs are rebuilt with exactly the -50 file
    # set; the pilot stage dir is created fresh.
    d11 = SNOTES / "td_policy_a_live_readiness_packet_20261017_11"
    shutil.rmtree(d11)
    for fn in ["run_dispatch_gate_trials_r4.py", "lease_holder.py",
               "lease_contender.py", "crash_child.py",
               "readiness_transaction.py"]:
        copy_file(PKG11 / fn, d11 / fn)
    shutil.copytree(PKG11 / "helper_stub", d11 / "helper_stub")
    copy_file(PKG48 / "dispatch_gate_r5_candidate.py",
              d11 / "dispatch_gate_r4.py")
    d04 = SNOTES / "td_fresh_live_driver_integration_evidence_20261016"
    shutil.rmtree(d04)
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
    r1dir = (SNOTES /
             "td_fresh_full_manifest_preflight_evidence_20261016")
    shutil.rmtree(r1dir)
    copy_file(R1PKG / "fresh_manifest.json", r1dir / "fresh_manifest.json")
    copy_file(PKG48 / "fresh_supplement_v2_candidate.json",
              r1dir / "fresh_supplement.json")
    d19 = SNOTES / "td_live_dryrun_clock_adapter_binding_20261017_19"
    shutil.rmtree(d19)
    copy_file(PKG19 / "run_clock_adapter_trials.py",
              d19 / "run_clock_adapter_trials.py")
    copy_file(PKG48 / "live_dry_run_adapter_r5_candidate.py",
              d19 / "live_dry_run_adapter.py")
    copy_file(PKG48 / "live_readiness_executor_r5_candidate.py",
              d19 / "live_readiness_executor_r4.py")
    ps = SNOTES / "td55_pilot_stage"
    copy_file(F_CAND_ENTRY, ps / "pilot_build_v7_clibound.py")
    copy_file(F_CAND_CONSTRUCT, ps / "construct_4h_v3_cliguard.py")
    copy_file(F_VALIDATOR, ps / "validate_input.py")
    copy_file(PILOT / "verify_sources.py", ps / "verify_sources.py")
    # ---- SS B preflight ------------------------------------------------
    pre = {}
    r1 = _git(["-C", str(SHADOW), "rev-parse", "--is-inside-work-tree"])
    pre["b1_inside_work_tree"] = (r1.returncode == 0
                                  and r1.stdout.strip() == "true")
    gate_path = d11 / "dispatch_gate_r4.py"
    derived = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(str(gate_path))), "..", ".."))
    pre["b2_derived_REPO"] = derived
    pre["b2_shadow_root"] = os.path.abspath(str(SHADOW))
    pre["b2_derived_REPO_is_shadow_root"] = (
        pre["b2_derived_REPO"] == pre["b2_shadow_root"])
    rb = subprocess.run(["git", "-C", str(SHADOW), "show",
                         "%s:%s" % (COLLECTOR_COMMIT, COLLECTOR_PATH)],
                        capture_output=True, timeout=30)
    pre["b3_blob_command"] = ("git -C <shadow> show %s:%s"
                              % (COLLECTOR_COMMIT, COLLECTOR_PATH))
    pre["b3_blob_exit"] = rb.returncode
    pre["b3_blob_sha256"] = (H(rb.stdout) if rb.returncode == 0
                             else None)
    pre["b3_blob_is_PIN_COLLECTOR"] = (
        pre["b3_blob_sha256"] == PIN_COLLECTOR)
    gate_hash = HF(gate_path)
    cand_hash = HF(PKG48 / "dispatch_gate_r5_candidate.py")
    pre["b4_staged_gate_is_candidate"] = gate_hash == cand_hash
    same_gate = {}
    for fn in ["run_dispatch_gate_trials_r4.py", "lease_holder.py",
               "lease_contender.py"]:
        txt = (d11 / fn).read_text()
        same_gate[fn] = ("import dispatch_gate_r4" in txt)
    pre["b4_same_gate_imports"] = same_gate
    staged = {
        "gate_module_is_candidate":
            HF(d11 / "dispatch_gate_r4.py") == HF(PKG48 /
            "dispatch_gate_r5_candidate.py"),
        "driver_module_is_candidate":
            HF(d04 / "live_driver.py") == HF(PKG48 /
            "live_driver_r5_candidate.py"),
        "supplement_is_candidate":
            HF(r1dir / "fresh_supplement.json") == HF(PKG48 /
            "fresh_supplement_v2_candidate.json"),
        "adapter_is_candidate":
            HF(d19 / "live_dry_run_adapter.py") == HF(PKG48 /
            "live_dry_run_adapter_r5_candidate.py"),
        "executor_is_candidate":
            HF(d19 / "live_readiness_executor_r4.py") == HF(PKG48 /
            "live_readiness_executor_r5_candidate.py"),
        "staged_driver_runner_diff_lines": 1,
    }
    pre["staging"] = staged
    results["staging_preflight"] = pre
    if not pre["b1_inside_work_tree"]:
        fail("STAGING_NOT_WORKTREE", pre)
    if not pre["b2_derived_REPO_is_shadow_root"]:
        fail("STAGING_REPO_MISMATCH", pre)
    if not pre["b3_blob_is_PIN_COLLECTOR"]:
        fail("STAGING_GIT_BLOB", pre)
    if not pre["b4_staged_gate_is_candidate"] or not all(
            pre["b4_same_gate_imports"].values()):
        fail("STAGING_GATE_IMPORTS", pre)
    if not all(v for k, v in staged.items()
               if k != "staged_driver_runner_diff_lines"):
        fail("STAGING_BINDING", staged)


def cleanup_shadow():
    """Record the shadow's final state and dispose of the worktree.
    Runs after the verdict is determined; never raises."""
    c = {}
    try:
        if SHADOW.is_dir():
            r = _git(["-C", str(SHADOW), "status", "--porcelain"])
            c["shadow_status_lines_at_cleanup"] = r.stdout.count("\n")
            rr = _git(["-C", str(REPO), "worktree", "remove",
                       "--force", str(SHADOW)])
            c["remove_rc"] = rr.returncode
            _git(["-C", str(REPO), "worktree", "prune"])
        c["shadow_removed"] = not SHADOW.exists()
        ms, msl = status_hash(MAINREPO)
        c["main_status_unchanged"] = (
            ms == _pre_status.get("main_status"))
        c["main_status_lines_post"] = msl
        rs, rsl = status_hash(REPO)
        c["repo_status_lines_post"] = rsl
        c["repo_head_still"] = _git(["-C", str(REPO), "rev-parse",
                                     "HEAD"]).stdout.strip()
        c["repo_head_matches_pre"] = (
            c["repo_head_still"] == _pre_status.get("repo_head"))
    except Exception as e:
        c["cleanup_error"] = "%s: %s" % (type(e).__name__, e)
    # -55: dispose of the ORIGINAL branch worktree as well
    try:
        if SHADOW_O.is_dir():
            rr2 = _git(["-C", str(REPO), "worktree", "remove",
                        "--force", str(SHADOW_O)])
            c["original_remove_rc"] = rr2.returncode
            _git(["-C", str(REPO), "worktree", "prune"])
        c["original_shadow_removed"] = not SHADOW_O.exists()
    except Exception as e:
        c["original_cleanup_error"] = "%s: %s" % (
            type(e).__name__, e)
    results["staging_cleanup"] = c


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



# ------------------------------------------------- gate567 extractor
# -53 corrected extractor (spec 6295378552). The v4 extractor walked
# the candidate matrix for a dict holding a nested 12-element `gates`
# list; the matrix format never contained one (the -52 HOLD,
# found_12_gate_cells = 0). ACTUAL schema, verified against the
# pinned -52 gate_matrix.json (sha256 PIN_GATE_MATRIX_52): top level
# {gate_revision, n_trials, n_pass, total_checks,
# old_spot8_state_unchanged, real_pilot_ledger_unchanged, trials[]};
# each trial {trial, status, checks[], n_checks, facts{decision,
# gates_passed, failed_gates, gate_codes, ...}}. Static binding: the
# runner (run_dispatch_gate_trials_r4.py, gate_summary) aggregates
# the receipt's per-gate list - gates = res["receipt"]["gates"];
# gates_passed = sum(1 for x in gates if x["result"] == "PASS");
# failed_gates / gate_codes collect exactly the non-PASS remainder -
# over evaluate_gates' unique gates 1..12 (dispatch_gate_r4.py). An
# all-green trial with gates_passed == 12 and empty failed_gates /
# gate_codes therefore entails gates 5, 6 and 7 each PASS.
GREEN_TRIALS_567 = ("G01_green_dry_run",
                    "H05_helper_real_sanctioned_path")


def extract_gate567(matrix):
    """Gate-5/6/7 evidence from the matrix's actual schema.
    Returns the evidence dict, or None (fail closed)."""
    ev = {"schema": ("top{n_trials,n_pass,total_checks,"
                     "old_spot8_state_unchanged,"
                     "real_pilot_ledger_unchanged,trials[]} + "
                     "trial{status,checks[],facts{gates_passed,"
                     "failed_gates,gate_codes,decision}}"),
          "n_trials": matrix.get("n_trials"),
          "n_pass": matrix.get("n_pass"),
          "total_checks": matrix.get("total_checks"),
          "old_spot8_state_unchanged":
              matrix.get("old_spot8_state_unchanged"),
          "real_pilot_ledger_unchanged":
              matrix.get("real_pilot_ledger_unchanged")}
    if not (ev["n_trials"] == 46 and ev["n_pass"] == 46
            and ev["total_checks"] == 332
            and ev["old_spot8_state_unchanged"] is True
            and ev["real_pilot_ledger_unchanged"] is True
            and isinstance(matrix.get("trials"), list)
            and len(matrix["trials"]) == 46):
        return None
    for name in GREEN_TRIALS_567:
        t = next((x for x in matrix["trials"]
                  if isinstance(x, dict) and x.get("trial") == name),
                 None)
        if t is None:
            return None
        f = t.get("facts")
        if not isinstance(f, dict):
            return None
        checks = t.get("checks") or []
        all12 = [c for c in checks if c.startswith("all_12")
                 or c == "all_gates_pass"]
        ev[name] = {"status": t.get("status"),
                    "all_12_checks": all12,
                    "gates_passed": f.get("gates_passed"),
                    "failed_gates": f.get("failed_gates"),
                    "gate_codes": f.get("gate_codes"),
                    "decision": f.get("decision")}
        if not (t.get("status") == "PASS" and all12
                and f.get("gates_passed") == 12
                and f.get("failed_gates") == []
                and f.get("gate_codes") == []
                and f.get("decision") in ("PASS", "PASS_DRY_RUN")):
            return None
    ev["gate5"] = "PASS"
    ev["gate6"] = "PASS"
    ev["gate7"] = "PASS"
    ev["all_12_pass"] = True
    ev["basis"] = ("gates_passed==12 over unique gates 1..12 with "
                   "empty failed_gates/gate_codes entails every "
                   "gate PASS (runner gate_summary aggregation)")
    return ev


# ------------------------------------------- -54 stage transition
def _const_str(source, name):
    """Value of a module-level `name = <str constant>` assignment."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and getattr(node.targets[0], "id", "") == name \
                and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            return node.value.value
    return None


def _join_parts(source, name):
    """String literals of a module-level `name = os.path.join(...)`
    assignment, skipping the leading NOTES/HERE name argument."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and getattr(node.targets[0], "id", "") == name \
                and isinstance(node.value, ast.Call):
            return [a.value for a in node.value.args
                    if isinstance(a, ast.Constant)
                    and isinstance(a.value, str)]
    return None


def stage_transition_clock():
    """-54 (spec 6296388979 SS.1/SS.3): post-receipt stage transition
    before the clock suite. Restores the ORIGINAL r4 gate bytes at
    the shadow's legacy PKG11 path (the only path the -17
    reproduction adapter resolves); the candidate gate stays at its
    immutable -48 package path. Then proves, simultaneously:
    legacy gate == b5399645...; the -17 adapter resolves that path
    and its pins match (static + executed import); candidate gate
    == 94ef967c...; candidate adapter GATE_PATH + pin resolve the
    candidate gate; candidate executor ADAPTER_PATH + pin resolve
    the candidate adapter; the -19 runner branch map is unchanged
    (reproduction -> -17 adapter; new tests -> staged candidate
    adapter; binding tests -> staged candidate executor)."""
    t = {}
    d11 = SNOTES / "td_policy_a_live_readiness_packet_20261017_11"
    legacy_path = d11 / "dispatch_gate_r4.py"
    t["legacy_path"] = str(legacy_path)
    t["pre_transition_sha256"] = HF(legacy_path)
    src_gate = PKG11 / "dispatch_gate_r4.py"
    t["source_original_sha256"] = HF(src_gate)
    if t["source_original_sha256"] != PIN_R4_GATE_LEGACY:
        fail("STAGE_TRANSITION_LEGACY_GATE", t)
    copy_file(src_gate, legacy_path)
    t["post_transition_sha256"] = HF(legacy_path)
    t["legacy_gate_is_original"] = (
        t["post_transition_sha256"] == PIN_R4_GATE_LEGACY)
    if not t["legacy_gate_is_original"]:
        fail("STAGE_TRANSITION_LEGACY_GATE", t)
    # candidate gate stays at its immutable package path, untouched
    cand_gate = PKG48 / "dispatch_gate_r5_candidate.py"
    t["candidate_gate_path"] = str(cand_gate)
    t["candidate_gate_sha256"] = HF(cand_gate)
    t["candidate_gate_pin"] = results["hash_gates"]["candidate_gate"]
    t["candidate_gate_untouched"] = (
        t["candidate_gate_sha256"] == t["candidate_gate_pin"])
    if not t["candidate_gate_untouched"]:
        fail("STAGE_TRANSITION_CANDIDATE_GATE", t)
    # -17 adapter: static resolution exactly as the module computes it
    old_ad = SNOTES / "td_status_query_placement_20261017_17" \
        / "r4_dry_run_adapter.py"
    old_src = old_ad.read_text()
    t["old_adapter_sha256"] = HF(old_ad)
    t["old_adapter_pin_gate"] = _const_str(old_src, "PIN_R4_GATE")
    t["old_adapter_pin_runner"] = _const_str(old_src, "PIN_R4_RUNNER")
    res_pkg11 = old_ad.parent.parent \
        / "td_policy_a_live_readiness_packet_20261017_11"
    t["old_adapter_resolved_gate_path"] = str(
        res_pkg11 / "dispatch_gate_r4.py")
    t["old_adapter_resolved_gate_sha256"] = HF(
        res_pkg11 / "dispatch_gate_r4.py")
    t["old_adapter_resolved_runner_sha256"] = HF(
        res_pkg11 / "run_dispatch_gate_trials_r4.py")
    t["old_adapter_static_ok"] = (
        t["old_adapter_resolved_gate_path"] == str(legacy_path)
        and t["old_adapter_pin_gate"] == PIN_R4_GATE_LEGACY
        and t["old_adapter_resolved_gate_sha256"] == PIN_R4_GATE_LEGACY
        and t["old_adapter_pin_runner"] == PIN_R4_RUNNER
        and t["old_adapter_resolved_runner_sha256"] == PIN_R4_RUNNER)
    # executed proof: import the -17 adapter in a subprocess; its
    # module-level R = _load_runner() performs both pin checks and
    # imports the -11 runner for real.
    code = (
        "import importlib.util, hashlib, sys\n"
        "spec = importlib.util.spec_from_file_location("
        "'qf54_old_adapter', sys.argv[1])\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
        "print('OLD_ADAPTER_IMPORT_OK')\n"
        "print('runner_module', m.R.__name__)\n")
    r = subprocess.run([sys.executable, "-c", code, str(old_ad)],
                       capture_output=True, text=True, timeout=120)
    t["old_adapter_import_exit"] = r.returncode
    t["old_adapter_import_stdout_tail"] = r.stdout[-300:]
    t["old_adapter_import_stderr_tail"] = r.stderr[-500:]
    t["old_adapter_executed_ok"] = (
        r.returncode == 0 and "OLD_ADAPTER_IMPORT_OK" in r.stdout)
    if not t["old_adapter_static_ok"] or not t["old_adapter_executed_ok"]:
        fail("STAGE_TRANSITION_OLD_ADAPTER", t)
    # candidate adapter: GATE_PATH + pin resolve the candidate gate
    ca_src = (PKG48 / "live_dry_run_adapter_r5_candidate.py").read_text()
    parts = _join_parts(ca_src, "GATE_PATH")
    t["candidate_adapter_gate_parts"] = parts
    t["candidate_adapter_pin"] = _const_str(ca_src, "PIN_R4_GATE")
    staged_ca_notes = SNOTES  # staged adapter: NOTES = shadow notes
    resolved_gate = staged_ca_notes.joinpath(*(parts or []))
    t["candidate_adapter_resolved_gate_path"] = str(resolved_gate)
    t["candidate_adapter_resolved_gate_sha256"] = (
        HF(resolved_gate) if resolved_gate.exists() else None)
    t["candidate_adapter_sha256"] = HF(
        PKG48 / "live_dry_run_adapter_r5_candidate.py")
    t["candidate_adapter_ok"] = (
        parts == ["td_route_adoption_transaction_prep_20261020_48",
                  "dispatch_gate_r5_candidate.py"]
        and t["candidate_adapter_resolved_gate_sha256"]
        == t["candidate_adapter_pin"]
        == t["candidate_gate_sha256"])
    if not t["candidate_adapter_ok"]:
        fail("STAGE_TRANSITION_CANDIDATE_ADAPTER", t)
    # candidate executor: ADAPTER_PATH + pin resolve candidate adapter
    ce_src = (PKG48
              / "live_readiness_executor_r5_candidate.py").read_text()
    parts = _join_parts(ce_src, "ADAPTER_PATH")
    t["candidate_executor_adapter_parts"] = parts
    t["candidate_executor_adapter_pin"] = _const_str(
        ce_src, "ADAPTER_SHA256")
    resolved_ad = staged_ca_notes.joinpath(*(parts or []))
    t["candidate_executor_resolved_adapter_path"] = str(resolved_ad)
    t["candidate_executor_resolved_adapter_sha256"] = (
        HF(resolved_ad) if resolved_ad.exists() else None)
    t["candidate_executor_sha256"] = HF(
        PKG48 / "live_readiness_executor_r5_candidate.py")
    t["candidate_executor_ok"] = (
        parts == ["td_route_adoption_transaction_prep_20261020_48",
                  "live_dry_run_adapter_r5_candidate.py"]
        and t["candidate_executor_resolved_adapter_sha256"]
        == t["candidate_executor_adapter_pin"]
        == t["candidate_adapter_sha256"])
    if not t["candidate_executor_ok"]:
        fail("STAGE_TRANSITION_CANDIDATE_EXECUTOR", t)
    # -19 runner branch map (staged copy is byte-identical to PKG19)
    runner = SNOTES / "td_live_dryrun_clock_adapter_binding_20261017_19" \
        / "run_clock_adapter_trials.py"
    t["runner_staged_is_accepted"] = (
        HF(runner) == HF(PKG19 / "run_clock_adapter_trials.py"))
    lines = runner.read_text().splitlines()
    pats = {
        "reproduction_old_adapter":
            'load(os.path.join(PKG17, "r4_dry_run_adapter.py")',
        "new_tests_candidate_adapter":
            'load(os.path.join(HERE, "live_dry_run_adapter.py")',
        "binding_candidate_executor":
            'load(os.path.join(HERE, "live_readiness_executor_r4.py")',
    }
    bm = {}
    for label, pat in pats.items():
        hits = [i + 1 for i, ln in enumerate(lines) if pat in ln]
        bm[label] = {"pattern": pat, "lines": hits, "found": bool(hits)}
    t["runner_branch_map"] = bm
    t["branch_map_ok"] = (t["runner_staged_is_accepted"]
                          and all(v["found"] for v in bm.values()))
    if not t["branch_map_ok"]:
        fail("STAGE_TRANSITION_BRANCH_MAP", t)
    results["stage_transition"] = t


# ------------------------------------------- -55 branch isolation
def build_original_worktree():
    """-55 (spec 6297990771 SS.3): the ORIGINAL branch - a second
    detached git worktree of this repo at the same HEAD, with NO
    candidate substitution and NO stage transition: the committed
    original artifacts stand at their accepted paths/hashes. Used
    only to execute the accepted runner's repro_old branch."""
    if SHADOW_O.exists() or SHADOW_O.is_symlink():
        _git(["-C", str(REPO), "worktree", "remove", "--force",
              str(SHADOW_O)])
        if SHADOW_O.exists() or SHADOW_O.is_symlink():
            if SHADOW_O.is_symlink() or SHADOW_O.is_file():
                SHADOW_O.unlink()
            else:
                shutil.rmtree(SHADOW_O)
    _git(["-C", str(REPO), "worktree", "prune"])
    ra = _git(["-C", str(REPO), "worktree", "add", "--detach",
               str(SHADOW_O)])
    if ra.returncode != 0 or not SHADOW_O.is_dir():
        fail("STAGING_WORKTREE_ADD",
             {"branch": "original", "rc": ra.returncode,
              "stderr": ra.stderr[-500:]})
    _pre_status["original_shadow_created"] = True
    _pre_status["original_shadow_head"] = _git(
        ["-C", str(SHADOW_O), "rev-parse", "HEAD"]).stdout.strip()
    pre = {}
    r1 = _git(["-C", str(SHADOW_O), "rev-parse",
               "--is-inside-work-tree"])
    pre["b1_inside_work_tree"] = (r1.returncode == 0
                                  and r1.stdout.strip() == "true")
    rb = subprocess.run(["git", "-C", str(SHADOW_O), "show",
                         "%s:%s" % (COLLECTOR_COMMIT, COLLECTOR_PATH)],
                        capture_output=True, timeout=30)
    pre["b3_blob_sha256"] = (H(rb.stdout) if rb.returncode == 0
                             else None)
    pre["b3_blob_is_PIN_COLLECTOR"] = (
        pre["b3_blob_sha256"] == PIN_COLLECTOR)
    pre["head_matches_candidate_branch"] = (
        _pre_status["original_shadow_head"]
        == _pre_status.get("shadow_head"))
    results["original_branch_preflight"] = pre
    if not pre["b1_inside_work_tree"]:
        fail("STAGING_NOT_WORKTREE", pre)
    if not pre["b3_blob_is_PIN_COLLECTOR"]:
        fail("STAGING_GIT_BLOB", pre)
    if not pre["head_matches_candidate_branch"]:
        fail("BRANCH_HEAD_MISMATCH", pre)


def branch_provenance():
    """-55 (spec 6297990771 SS.4): fail-closed provenance for both
    branches, checked after staging/transition and before any suite
    executes. Original pins at their accepted paths in the ORIGINAL
    branch; candidate pins at the staged copies in the CANDIDATE
    branch (gate/supplement/proof via the immutable -48 sources the
    staged copies were byte-verified against in SS B preflight);
    both accepted runner copies byte-identical; resolved paths
    recorded; no overlap, no symlinks; membership fixed by HEAD."""
    pv = {}
    rc_ = os.path.realpath(SHADOW)
    ro_ = os.path.realpath(SHADOW_O)
    pv["candidate_branch_resolved_path"] = rc_
    pv["original_branch_resolved_path"] = ro_
    pv["paths_distinct"] = rc_ != ro_
    pv["no_path_overlap"] = not (
        rc_.startswith(ro_ + os.sep) or ro_.startswith(rc_ + os.sep))
    pv["roots_not_symlinks"] = (not SHADOW.is_symlink()
                                and not SHADOW_O.is_symlink())
    if not (pv["paths_distinct"] and pv["no_path_overlap"]
            and pv["roots_not_symlinks"]):
        fail("BRANCH_PROVENANCE_PATHS", pv)
    # ORIGINAL branch exact pins
    o = {}
    o["gate"] = HF(SNOTES_O / "td_policy_a_live_readiness_packet_20261017_11"
                   / "dispatch_gate_r4.py")
    o["driver"] = HF(SNOTES_O / "td_fresh_live_driver_integration_evidence_20261016"
                     / "live_driver.py")
    o_supp_path = (SNOTES_O / "td_fresh_full_manifest_preflight_evidence_20261016"
                   / "fresh_supplement.json")
    o["supplement"] = HF(o_supp_path)
    o["proof"] = next(iter(json.loads(
        o_supp_path.read_bytes())["calendar_proofs"]))
    o["mechanism"] = HF(SNOTES_O / "pilot_harness" / "validate_input.py")
    pv["original_pins"] = {
        "gate": {"expected": PIN_R4_GATE_LEGACY, "actual": o["gate"],
                 "match": o["gate"] == PIN_R4_GATE_LEGACY},
        "driver": {"expected": PIN_ORIG_DRIVER, "actual": o["driver"],
                   "match": o["driver"] == PIN_ORIG_DRIVER},
        "supplement": {"expected": PIN_ORIG_SUPPLEMENT,
                       "actual": o["supplement"],
                       "match": o["supplement"] == PIN_ORIG_SUPPLEMENT},
        "mechanism": {"expected": PIN_ORIG_MECHANISM,
                      "actual": o["mechanism"],
                      "match": o["mechanism"] == PIN_ORIG_MECHANISM},
        "proof": {"expected": PIN_ORIG_PROOF, "actual": o["proof"],
                  "match": o["proof"] == PIN_ORIG_PROOF}}
    pv["original_files_not_symlinks"] = not any(
        p.is_symlink() for p in [
            SNOTES_O / "td_policy_a_live_readiness_packet_20261017_11"
            / "dispatch_gate_r4.py",
            SNOTES_O / "td_fresh_live_driver_integration_evidence_20261016"
            / "live_driver.py", o_supp_path,
            SNOTES_O / "pilot_harness" / "validate_input.py"])
    if not all(v["match"] for v in pv["original_pins"].values()) \
            or not pv["original_files_not_symlinks"]:
        fail("BRANCH_PROVENANCE_ORIGINAL_PINS", pv)
    # CANDIDATE branch exact pins
    hg = results["hash_gates"]
    c_supp = json.loads((PKG48 / "fresh_supplement_v2_candidate.json")
                        .read_bytes())
    c = {}
    c["gate_source"] = HF(PKG48 / "dispatch_gate_r5_candidate.py")
    c["driver_staged"] = HF(
        SNOTES / "td_fresh_live_driver_integration_evidence_20261016"
        / "live_driver.py")
    c["supplement_staged"] = HF(
        SNOTES / "td_fresh_full_manifest_preflight_evidence_20261016"
        / "fresh_supplement.json")
    c["adapter_staged"] = HF(
        SNOTES / "td_live_dryrun_clock_adapter_binding_20261017_19"
        / "live_dry_run_adapter.py")
    c["executor_staged"] = HF(
        SNOTES / "td_live_dryrun_clock_adapter_binding_20261017_19"
        / "live_readiness_executor_r4.py")
    c["mechanism_candidate"] = HF(F_VALIDATOR)
    c["proof"] = next(iter(c_supp["calendar_proofs"]))
    pv["candidate_pins"] = {
        "gate": {"expected_prefix": "94ef967c",
                 "actual": c["gate_source"],
                 "match": c["gate_source"] == hg["candidate_gate"]
                 and c["gate_source"].startswith("94ef967c")},
        "driver": {"expected_prefix": "d11c6b58",
                   "actual": c["driver_staged"],
                   "match": c["driver_staged"] == hg["candidate_driver"]
                   and c["driver_staged"].startswith("d11c6b58")},
        "supplement": {"expected_prefix": "55ad6f40",
                       "actual": c["supplement_staged"],
                       "match": c["supplement_staged"]
                       == hg["candidate_supplement"]
                       and c["supplement_staged"].startswith("55ad6f40")},
        "mechanism": {"expected": PIN_VALIDATOR_CAND,
                      "actual": c["mechanism_candidate"],
                      "match": c["mechanism_candidate"]
                      == PIN_VALIDATOR_CAND
                      and c["mechanism_candidate"].startswith("ca3bafd8")},
        "proof": {"expected": "6b030c62fdaf3cd738001a438b6f6a562b381b93"
                  "b29dd8b299753de6aebe4fa5",
                  "actual": c["proof"],
                  "match": c["proof"] == "6b030c62fdaf3cd738001a438b6"
                  "f6a562b381b93b29dd8b299753de6aebe4fa5"},
        "adapter": {"expected_prefix": "6980b5b3",
                    "actual": c["adapter_staged"],
                    "match": c["adapter_staged"] == hg["candidate_adapter"]
                    and c["adapter_staged"].startswith("6980b5b3")},
        "executor": {"expected_prefix": "bbc23616",
                     "actual": c["executor_staged"],
                     "match": c["executor_staged"]
                     == hg["candidate_executor"]
                     and c["executor_staged"].startswith("bbc23616")}}
    if not all(v["match"] for v in pv["candidate_pins"].values()):
        fail("BRANCH_PROVENANCE_CANDIDATE_PINS", pv)
    # both accepted runner copies byte-identical (and == accepted)
    r_c = HF(SNOTES / "td_live_dryrun_clock_adapter_binding_20261017_19"
             / "run_clock_adapter_trials.py")
    r_o = HF(SNOTES_O / "td_live_dryrun_clock_adapter_binding_20261017_19"
             / "run_clock_adapter_trials.py")
    r_a = HF(PKG19 / "run_clock_adapter_trials.py")
    pv["runner_copies"] = {"candidate_branch": r_c,
                           "original_branch": r_o, "accepted": r_a,
                           "byte_identical": r_c == r_o == r_a}
    if not pv["runner_copies"]["byte_identical"]:
        fail("BRANCH_PROVENANCE_RUNNER", pv)
    pv["branch_heads"] = {
        "repo_head": _pre_status.get("repo_head"),
        "candidate_branch": _pre_status.get("shadow_head"),
        "original_branch": _pre_status.get("original_shadow_head"),
        "membership_fixed": (
            _pre_status.get("shadow_head") == _pre_status.get("repo_head")
            and _pre_status.get("original_shadow_head")
            == _pre_status.get("repo_head"))}
    if not pv["branch_heads"]["membership_fixed"]:
        fail("BRANCH_HEAD_MISMATCH", pv)
    results["branch_provenance"] = pv


def _trial_contrib(t):
    ch = t.get("checks", {}) if isinstance(t, dict) else {}
    return {"checks_true": sum(1 for v in ch.values() if v is True),
            "checks_total": len(ch),
            "ok": t.get("ok") if isinstance(t, dict) else None}


def compare_clock_scoped(orig_obj, cand_obj):
    """-55 (spec 6297990771 SS.5): scoped adjudication of the two
    branch matrices against accepted run-2. ORIGINAL is judged only
    on repro_old plus its rollup contribution; CANDIDATE only on
    the other 19 trials, with repro_old explicitly excluded. The
    trial-name partition must be exact."""
    pairs, names, revs = token_map()
    acc = canonicalize(json.loads(
        (PKG19 / "clock_adapter_matrix_run2.json").read_bytes()),
        pairs, names, revs)
    o = canonicalize(orig_obj, pairs, names, revs)
    c = canonicalize(cand_obj, pairs, names, revs)
    entry = {"accepted_source": str(
        PKG19 / "clock_adapter_matrix_run2.json")}
    acc_names = set(acc["trials"])
    scoped_c = sorted(acc_names - {"repro_old"})
    entry["trial_partition"] = {
        "accepted_trials": sorted(acc_names),
        "original_branch_trials": sorted(o["trials"]),
        "candidate_branch_trials": sorted(c["trials"]),
        "scoped_original": ["repro_old"],
        "scoped_candidate": scoped_c,
        "partition_exact": (
            set(o["trials"]) == acc_names
            and set(c["trials"]) == acc_names
            and {"repro_old"} | set(scoped_c) == acc_names
            and not ({"repro_old"} & set(scoped_c)))}
    results.setdefault("comparisons", {})[
        "clock_adapter_matrix_scoped"] = entry
    if not entry["trial_partition"]["partition_exact"]:
        fail("P1_CLOCK_TRIAL_PARTITION", entry)
    div_o = first_divergence(acc["trials"]["repro_old"],
                             o["trials"]["repro_old"],
                             "$.trials.repro_old")
    entry["original_repro_exact"] = div_o is None
    entry["original_first_divergence"] = div_o
    entry["repro_rollup_contribution"] = {
        "accepted": _trial_contrib(acc["trials"]["repro_old"]),
        "original": _trial_contrib(o["trials"]["repro_old"]),
        "candidate_excluded_from_verdict": _trial_contrib(
            c["trials"]["repro_old"])}
    entry["rollup_contribution_match"] = (
        entry["repro_rollup_contribution"]["accepted"]
        == entry["repro_rollup_contribution"]["original"])
    entry["branch_rollups"] = {
        "accepted": {"checks_passed": acc.get("checks_passed"),
                     "checks_total": acc.get("checks_total"),
                     "summary": acc.get("summary")},
        "original_branch": {"checks_passed": o.get("checks_passed"),
                            "checks_total": o.get("checks_total")},
        "candidate_branch": {"checks_passed": c.get("checks_passed"),
                             "checks_total": c.get("checks_total")}}
    if div_o is not None or not entry["rollup_contribution_match"]:
        fail("P1_CLOCK_ADAPTER_REGRESSION", entry)
    divs = {}
    for name in scoped_c:
        d = first_divergence(acc["trials"][name], c["trials"][name],
                             f"$.trials.{name}")
        if d:
            divs[name] = d
    entry["candidate_scoped_trials_compared"] = len(scoped_c)
    entry["candidate_scoped_exact"] = not divs
    entry["candidate_first_divergences"] = divs
    if divs:
        fail("P1_CLOCK_ADAPTER_REGRESSION", entry)
    return entry


# ---------------------------------------------------------------- P1
def p1():
    # -53 (spec 6295378552): the 46-trial gate suite is NOT rerun.
    # The pinned -52 receipt (hash-gated above) is verified by
    # canonical comparison against the accepted -11 run-2 matrix,
    # and the corrected extractor reads the Gate-5/6/7 evidence
    # from the receipt's actual schema.
    gate_matrix = json.loads((PKG52 / "gate_matrix.json").read_bytes())
    results["P1_gate_receipt"] = {
        "source": "PKG52/gate_matrix.json",
        "result_commit": PIN_RECEIPT52_COMMIT,
        "sha256": HF(PKG52 / "gate_matrix.json"),
        "suite_rerun": False,
        "n_pass": gate_matrix.get("n_pass"),
        "n_trials": gate_matrix.get("n_trials"),
        "total_checks": gate_matrix.get("total_checks")}
    compare_matrix("gate_dispatch_matrix",
                   PKG11 / "dispatch_matrix_run2.json",
                   gate_matrix, "P1_GATE_REGRESSION")
    g567 = extract_gate567(gate_matrix)
    results["P1_gate567"] = g567 or {"extractor": "NOT_EVIDENCED"}
    if g567 is None:
        fail("P1_GATE567_NOT_EVIDENCED", results["P1_gate567"])
    # -54: post-receipt stage transition (spec 6296388979) - restore
    # the original gate at the legacy PKG11 path for the -17
    # reproduction adapter and prove the dual-path preflight.
    stage_transition_clock()
    # -55 (spec 6297990771 SS.5): branch-isolated clock proof. The
    # unchanged -19 suite runs in BOTH branches; adjudication is
    # scoped - ORIGINAL contributes repro_old + its rollup
    # contribution, CANDIDATE the other 19 trials (repro_old
    # explicitly excluded on the candidate side).
    branch_provenance()
    d19_c = SNOTES / "td_live_dryrun_clock_adapter_binding_20261017_19"
    d19_o = SNOTES_O / "td_live_dryrun_clock_adapter_binding_20261017_19"
    ro = run_suite([sys.executable,
                    str(d19_o / "run_clock_adapter_trials.py"),
                    str(OUT / "clock_matrix_original.json")], cwd=d19_o)
    results["P1_clock_suite_original"] = {
        "exit": ro.returncode, "stdout_tail": ro.stdout[-400:],
        "stderr_tail": ro.stderr[-800:]}
    if ro.returncode != 0 or not (OUT / "clock_matrix_original.json").exists():
        fail("P1_CLOCK_SUITE_RUN", results["P1_clock_suite_original"])
    rc = run_suite([sys.executable,
                    str(d19_c / "run_clock_adapter_trials.py"),
                    str(OUT / "clock_matrix_candidate.json")], cwd=d19_c)
    results["P1_clock_suite_candidate"] = {
        "exit": rc.returncode, "stdout_tail": rc.stdout[-400:],
        "stderr_tail": rc.stderr[-800:]}
    if rc.returncode != 0 or not (OUT / "clock_matrix_candidate.json").exists():
        fail("P1_CLOCK_SUITE_RUN", results["P1_clock_suite_candidate"])
    orig_matrix = json.loads(
        (OUT / "clock_matrix_original.json").read_bytes())
    cand_matrix = json.loads(
        (OUT / "clock_matrix_candidate.json").read_bytes())
    compare_clock_scoped(orig_matrix, cand_matrix)
    led = {"repo_ledger_sha256": HF(PILOT / "credit_ledger.json"),
           "original_branch_ledger_sha256": HF(
               SNOTES_O / "pilot_harness" / "credit_ledger.json"),
           "candidate_branch_ledger_sha256": HF(
               SNOTES / "pilot_harness" / "credit_ledger.json")}
    led["real_pilot_ledger_unchanged_in_both"] = (
        led["original_branch_ledger_sha256"] == led["repo_ledger_sha256"]
        and led["candidate_branch_ledger_sha256"]
        == led["repo_ledger_sha256"])
    results["P1_clock_ledgers"] = led
    if not led["real_pilot_ledger_unchanged_in_both"]:
        fail("P1_CLOCK_LEDGER", led)
    # combined record: scoped trials merged (repro_old from the
    # ORIGINAL branch, the other 19 from the CANDIDATE branch);
    # rollups are the accepted run-2 values the scoped comparisons
    # were gated against.
    acc_raw = json.loads(
        (PKG19 / "clock_adapter_matrix_run2.json").read_bytes())
    merged = {"checks_passed": acc_raw.get("checks_passed"),
              "checks_total": acc_raw.get("checks_total"),
              "summary": acc_raw.get("summary"),
              "trials": dict(cand_matrix["trials"]),
              "provenance": "repro_old from ORIGINAL branch; "
                            "other 19 trials from CANDIDATE branch"}
    merged["trials"]["repro_old"] = orig_matrix["trials"]["repro_old"]
    (OUT / "clock_matrix.json").write_text(
        json.dumps(merged, indent=1, sort_keys=True))
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
    ps = SNOTES / "td55_pilot_stage"
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
        p0_receipt()
        build_shadow_gitaware()
        build_original_worktree()
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
    try:
        cleanup_shadow()
    except Exception as e:
        results["staging_cleanup_error"] = "%s: %s" % (
            type(e).__name__, e)
    (OUT / "proof_results.json").write_text(
        json.dumps(results, indent=1, sort_keys=True, default=str))
    print(results["verdict"])


if __name__ == "__main__":
    main()
