#!/usr/bin/env python3
"""Static candidate-package linter for QF-TD-ROUTE-ADOPTION-TRANSACTION-PREP-20261020-48.
Reads candidate/original files as TEXT/BYTES ONLY and recomputes hashes.
Imports NO chain module; executes NO chain code. Usage:
  python3 candidate_linter.py <repo_research_notes_dir> <package_dir>
Exit 0 iff every check passes."""
import hashlib
import json
import os
import re
import sys

RN = sys.argv[1]
PKG = sys.argv[2]
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (" :: " + detail if detail else ""))


def H(b):
    return hashlib.sha256(b).hexdigest()


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()


def rd(path):
    with open(path, "rb") as f:
        return f.read()


def fh(path):
    return H(rd(path))


VAL = "ca3bafd87e7cb439d538ddf924aa08a029dd2c9bb32b485f61acbeea91429cc6"
EP = "442e56cc16bbbb7ba8f3a62910d92bfcd07d85d0bb88ca2346d26b0bdcd2cba6"
CTOR = "d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd"
OLD_MECH = "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58"
OLD_SUPP = "3cbdbf63fd49b021dc74f63727098551753949f8684967981c65f66101f95a86"
OLD_PROOF = "36bc3a89bd266b9d7478d7f6082addd7b764a824bac45afdcbe534eb1d37f21a"
MANIFEST = "71aade8bfbb1f94b25d780bdf68f08f7f127740fc745c1755432acc5f74044db"
LOCK = "08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068"
COLLECTOR = "b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c"

P_SUPP = os.path.join(PKG, "fresh_supplement_v2_candidate.json")
P_DRV = os.path.join(PKG, "live_driver_r5_candidate.py")
P_GATE = os.path.join(PKG, "dispatch_gate_r5_candidate.py")
P_ADP = os.path.join(PKG, "live_dry_run_adapter_r5_candidate.py")
P_EXE = os.path.join(PKG, "live_readiness_executor_r5_candidate.py")
SUPP_NEW, DRV_NEW, GATE_NEW, ADP_NEW, EXE_NEW = map(fh, (P_SUPP, P_DRV, P_GATE, P_ADP, P_EXE))

# C1 route manifest vs actual bytes
rm = json.loads(rd(os.path.join(PKG, "ROUTE_MANIFEST_CANDIDATE.json")))
cc = rm["chain_candidates"]
check("C1.route_manifest_status", rm["status"] == "OFFLINE_CANDIDATE_NOT_ADOPTED")
check("C1.route_hashes_match_files",
      cc["supplement"]["sha256"] == SUPP_NEW and cc["driver"]["sha256"] == DRV_NEW
      and cc["gate"]["sha256"] == GATE_NEW and cc["adapter"]["sha256"] == ADP_NEW
      and cc["executor"]["sha256"] == EXE_NEW)
check("C1.route_triple_files",
      fh(os.path.join(RN, rm["route"]["entrypoint"]["path"].replace("research_notes/", "", 1))) == EP
      and fh(os.path.join(RN, rm["route"]["validator"]["path"].replace("research_notes/", "", 1))) == VAL
      and fh(os.path.join(RN, rm["route"]["constructor"]["path"].replace("research_notes/", "", 1))) == CTOR)
check("C1.governance_recorded",
      "authoritative for TD receipts" in rm["governance"]["precedence"]
      and rm["governance"]["split_exclusion"]["status"].startswith("REQUIREMENT_RECORDED")
      and rm["governance"]["direct_cli_refusal"]["status"].startswith("REQUIREMENT_RECORDED"))

# C2 supplement candidate internal consistency
sb = rd(P_SUPP)
supp = json.loads(sb)
check("C2.canonical_bytes", canon(supp) == sb)
check("C2.status", supp["status"] == "OFFLINE_CANDIDATE_NOT_ADOPTED")
check("C2.supplement_id", supp["supplement_id"] == "TD-FRESH-FM-SUPPLEMENT-NL-20261016")
check("C2.base_binding", supp["base_manifest_canonical_digest"] == MANIFEST
      and supp["base_manifest_file_sha256"] == MANIFEST
      and fh(os.path.join(RN, "td_fresh_full_manifest_preflight_evidence_20261016/fresh_manifest.json")) == MANIFEST)
cal = supp["calendar"]
check("C2.calendar_version", cal["expected_library_version"] == "4.5.1"
      and cal["expected_library"] == "pandas_market_calendars")
check("C2.mechanism_pin", cal["mechanism_module_sha256"] == VAL)
check("C2.mechanism_path_resolves",
      fh(os.path.join(RN, cal["mechanism_module"].replace("research_notes/", "", 1))) == VAL)
check("C2.lock_pin", cal["lineage_lock"]["lockfile_sha256"] == LOCK)
proofs = supp["calendar_proofs"]
check("C2.single_proof", len(proofs) == 1)
(pk, prec) = next(iter(proofs.items()))
check("C2.proof_self_digest", H(canon(prec)) == pk)
check("C2.proof_mechanism", prec["mechanism_module_sha256"] == VAL
      and prec["closed"] is True and prec["date"] == "2026-07-03"
      and prec["library_version"] == "4.5.1")
check("C2.entries_point_at_proof",
      all(e["calendar_proof_digest"] == pk for e in supp["entries"].values()))
orig = json.loads(rd(os.path.join(RN, "td_fresh_full_manifest_preflight_evidence_20261016/fresh_supplement.json")))
check("C2.entries_carried_by_value",
      all(supp["entries"][r]["request_digest"] == orig["entries"][r]["request_digest"]
          and supp["entries"][r]["expected_bars"] == 0
          and supp["entries"][r]["window_dates"] == orig["entries"][r]["window_dates"]
          for r in orig["entries"]))
check("C2.pins_carried_by_value",
      supp["classifier_pins"] == orig["classifier_pins"]
      and supp["safety_design_binding"] == orig["safety_design_binding"]
      and supp["class"] == orig["class"] and supp["lifecycle_event"] == orig["lifecycle_event"])
check("C2.provenance_points_at_current", supp["derived_from_supplement"]["sha256"] == OLD_SUPP)

PIN_RE = re.compile(r'^\s*([A-Z][A-Z0-9_]*)\s*=\s*"([0-9a-f]{8,64})"', re.M)
PATH_RE = re.compile(r'^\s*(P_[A-Z_]+)\s*=\s*"(research_notes/[^"]+)"', re.M)


def pins(path):
    return dict(PIN_RE.findall(rd(path).decode()))


def paths(path):
    return dict(PATH_RE.findall(rd(path).decode()))


# C3 driver + gate pins
dp = pins(P_DRV)
check("C3.driver_supp_pin", dp.get("EXPECTED_SUPPLEMENT_SHA256") == SUPP_NEW)
check("C3.driver_manifest_pin", dp.get("EXPECTED_MANIFEST_DIGEST") == MANIFEST)
check("C3.driver_mech_pin", dp.get("NL_MECHANISM_MODULE_SHA256") == VAL)
gp = pins(P_GATE)
gpath = paths(P_GATE)
check("C3.gate_pins", gp.get("PIN_SUPPLEMENT") == SUPP_NEW and gp.get("PIN_DRIVER") == DRV_NEW
      and gp.get("PIN_MECHANISM") == VAL and gp.get("PIN_CALENDAR_PROOF") == pk
      and gp.get("PIN_MANIFEST") == MANIFEST and gp.get("PIN_LOCK") == LOCK
      and gp.get("PIN_COLLECTOR") == COLLECTOR)
for key, want in (("P_DRIVER", DRV_NEW), ("P_SUPPLEMENT", SUPP_NEW), ("P_MECHANISM", VAL),
                  ("P_MANIFEST", MANIFEST), ("P_LOCK", LOCK)):
    rel = gpath.get(key, "").replace("research_notes/", "", 1)
    check("C3.gate_path_" + key, rel and fh(os.path.join(RN, rel)) == want, gpath.get(key, ""))

# C4 adapter / C5 executor
ap = pins(P_ADP)
adp_text = rd(P_ADP).decode()
check("C4.adapter_gate_pin", ap.get("PIN_R4_GATE") == GATE_NEW)
check("C4.adapter_gate_path", "td_route_adoption_transaction_prep_20261020_48" in adp_text
      and '"dispatch_gate_r5_candidate.py"' in adp_text)
ep_ = pins(P_EXE)
exe_text = rd(P_EXE).decode()
check("C5.executor_gate_pin", ep_.get("PIN_R4_GATE") == GATE_NEW)
check("C5.executor_supp_prefix", ep_.get("PIN_SUPPLEMENT") == SUPP_NEW[:8])
check("C5.executor_manifest_prefix", ep_.get("PIN_MANIFEST") == MANIFEST[:8])
check("C5.executor_adapter_pin", ep_.get("ADAPTER_SHA256") == ADP_NEW)
check("C5.executor_adapter_path", '"live_dry_run_adapter_r5_candidate.py"' in exe_text)

# C6 stale-pin sweep: no authoritative pin constant on old values
stale = []
for label, p in (("driver", P_DRV), ("gate", P_GATE), ("adapter", P_ADP), ("executor", P_EXE)):
    for k, v in pins(p).items():
        if v in (OLD_MECH, OLD_SUPP, OLD_PROOF) or v in ("3cbdbf63", "1b83cdcd", "36bc3a89"):
            stale.append(f"{label}.{k}={v}")
check("C6.no_stale_authoritative_pins", not stale, ";".join(stale))
occ = []
for label, p in (("supplement", P_SUPP), ("driver", P_DRV), ("gate", P_GATE),
                 ("adapter", P_ADP), ("executor", P_EXE)):
    t = rd(p).decode()
    for old, nm in ((OLD_MECH, "OLD_MECH"), (OLD_SUPP, "OLD_SUPP"), (OLD_PROOF, "OLD_PROOF")):
        for i, line in enumerate(t.split("\n"), 1):
            if old in line:
                occ.append(f"{label}:{i}:{nm}")
check("C6.full_old_hash_occurrences_classified",
      occ == ["supplement:1:OLD_SUPP"] or
      all(o.startswith("supplement") and o.endswith("OLD_SUPP") for o in occ),
      "; ".join(occ) if occ else "none")

# C7 DAG acyclic + rollback completeness + orphan check
dag = json.loads(rd(os.path.join(PKG, "dag.json")))
rb = json.loads(rd(os.path.join(PKG, "rollback.json")))
graph = {}
for e in dag["edges"]:
    if e["from"] != e["to"]:
        graph.setdefault(e["from"], set()).add(e["to"])
ids = [n["id"] for n in dag["nodes"]]


def reach(src):
    seen, stack = set(), [src]
    while stack:
        u = stack.pop()
        for v in graph.get(u, ()):
            if v in ids and v not in seen:
                seen.add(v)
                stack.append(v)
    return seen


# The accepted chain contains one intentional mutual binding
# (supplement <-> collector, -41 matrix Edges 2/3): the supplement pins
# the collector hash and the collector checks the supplement digest at
# runtime. A pin-graph cycle is therefore acceptable iff its SCC holds
# at least one node UNCHANGED by this transaction (a fixed anchor), and
# the ordering graph over CHANGING nodes alone is acyclic.
sccs, assigned = [], set()
for u in ids:
    if u in assigned:
        continue
    scc = {v for v in ids if v in reach(u) and u in reach(v)} | {u}
    sccs.append(scc)
    assigned |= scc
multi = [s for s in sccs if len(s) > 1]
by_id = {n["id"]: n for n in dag["nodes"]}
unanchored = [",".join(sorted(s)) for s in multi
              if all(by_id[m]["candidate"] for m in s)]
check("C7.cycles_anchored_by_unchanged_node", not unanchored,
      ";".join(unanchored) if unanchored else
      "SCCs>1: " + ";".join(",".join(sorted(s)) for s in multi))
changed = {n["id"] for n in dag["nodes"] if n["candidate"]}
WHITE, GRAY, BLACK = 0, 1, 2
color = {u: WHITE for u in changed}
cyc = []


def dfs(u):
    color[u] = GRAY
    for v in graph.get(u, ()):
        if v not in changed:
            continue
        if color[v] == GRAY:
            cyc.append(v)
        elif color[v] == WHITE:
            dfs(v)
    color[u] = BLACK


for u in changed:
    if color[u] == WHITE:
        dfs(u)
check("C7.changed_subgraph_acyclic", not cyc, ",".join(cyc))
rb_by_node = {e["node"]: e for e in rb["entries"]}
missing = [n["id"] for n in dag["nodes"] if n["candidate"]
           and rb_by_node.get(n["id"], {}).get("candidate_sha256") != n["candidate"]["sha256"]]
check("C7.rollback_complete", not missing, ",".join(missing))
cand_paths = {os.path.join(RN, n["candidate"]["path"].replace("research_notes/", "", 1))
              for n in dag["nodes"] if n["candidate"]}
check("C7.no_orphan_candidates",
      {P_SUPP, P_DRV, P_GATE, P_ADP, P_EXE} <= cand_paths
      and fh(os.path.join(RN, "td_validator_dst_repair_requalification_20261019_44/validate_input_v3_dstfix.py")) == VAL)

# C8 originals unchanged (accepted pins)
ORIG = {
    "td_fresh_full_manifest_preflight_evidence_20261016/fresh_supplement.json": OLD_SUPP,
    "td_fresh_live_driver_integration_evidence_20261016/live_driver.py":
        "5fed45242eb5ec465266c4d4c4258485f01a8c5bfdfdda2fb81295d3cf6d9c00",
    "td_policy_a_live_readiness_packet_20261017_11/dispatch_gate_r4.py":
        "b53996454650dafc77e647a8497eba91beb3785fb52c13d70fa81768fd370117",
    "td_live_dryrun_clock_adapter_binding_20261017_19/live_dry_run_adapter.py":
        "e8605669db902c3eb78ec4b3c13b69b3d94b7f1d8bcdac1a9c520b35ffc8c627",
    "td_live_dryrun_clock_adapter_binding_20261017_19/live_readiness_executor_r4.py":
        "e792b8b2b776adc71ce29e628c38fe258c4824bf784a690595f457b9d673c6e1",
    "pilot_harness/validate_input.py": OLD_MECH,
    "pilot_harness/construct_4h.py": CTOR,
    "pilot_harness/pilot_build.py": "257d5bb99bcbae50442491b71429abb6b37b8c5cbcd1e4bf93b6010ad9e5a508",
    "td_validator_dst_repair_requalification_20261019_44/validate_input_v3_dstfix.py": VAL,
    "td_ends_carry_dst_repair_requalification_20261020_45/pilot_build_v6_dstfix.py": EP,
}
bad = [k for k, v in ORIG.items() if fh(os.path.join(RN, k)) != v]
check("C8.originals_unchanged", not bad, ",".join(bad))

# C9 candidate banners / status strings
nb = [p for p in (P_DRV, P_GATE, P_ADP, P_EXE)
      if "OFFLINE_CANDIDATE_NOT_ADOPTED" not in rd(p).decode()]
check("C9.candidate_banners", not nb, ",".join(nb))

fails = [c for c in CHECKS if not c[1]]
print(f"\nLINTER SUMMARY: {len(CHECKS) - len(fails)}/{len(CHECKS)} PASS, {len(fails)} FAIL")
sys.exit(1 if fails else 0)
