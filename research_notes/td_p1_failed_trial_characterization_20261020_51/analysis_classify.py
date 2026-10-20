#!/usr/bin/env python3
"""-51 classification + transformation verification. Consumes /tmp/td51_diff.json
(the faithful canonicalized comparison) and the two raw matrices. Pure static
analysis; no chain code imported or executed."""
import json, re
from collections import Counter, defaultdict

acc = json.load(open('/tmp/td51_wt/research_notes/td_policy_a_live_readiness_packet_20261017_11/dispatch_matrix_run2.json'))
cand = json.load(open('/tmp/td51_wt/research_notes/td_route_transaction_proof_checker_correction_rerun_20261020_50/gate_matrix.json'))
diff = json.load(open('/tmp/td51_diff.json'))
names = [t['trial'] for t in acc['trials']]
A = {t['trial']: t for t in acc['trials']}
C = {t['trial']: t for t in cand['trials']}

# ---------- transformation verification ----------
COLLECTOR_CODE = "6:PIN_MISMATCH:collector"
PASS_ARTIFACT_KEYS = {"receipt_clock_mode", "lifecycle_outcome", "replay_guard",
                      "spy_constructions", "lease_artifact_name", "helper_route",
                      "shadow_imported"}
residuals = []
def gate6_code_merge(a_codes):
    """expected candidate gate-6 code string given accepted codes (bad-set union)."""
    for c in a_codes:
        if c.startswith("6:PIN_MISMATCH:"):
            bad = set(c.split(":", 2)[2].split(",")) | {"collector"}
            return "6:PIN_MISMATCH:" + ",".join(sorted(bad))
    return COLLECTOR_CODE

for name in names:
    af, cf = A[name]["facts"], C[name]["facts"]
    if name == "C01_contention_two_process":
        if cf != {}:
            residuals.append((name, "C01 candidate facts not empty", cf))
        continue
    afg = af.get("failed_gates", []); cfg = cf.get("failed_gates", [])
    acodes = af.get("gate_codes", []); ccodes = cf.get("gate_codes", [])
    if name in ("P05_post_gate_swap", "P08_handoff_shadow_installed"):
        # recorded-summary substitution: gate 6 preempts the gate-9 recording
        if cfg != [6] or ccodes != [COLLECTOR_CODE]:
            residuals.append((name, "P05/P08 pattern", (cfg, ccodes)))
        if cf.get("gates_passed") != af.get("gates_passed"):
            residuals.append((name, "P05/P08 gates_passed", (af.get("gates_passed"), cf.get("gates_passed"))))
        continue
    if name == "G02_green_dispatch_and_replay":
        # facts hold the FIRST dispatch summary (trial aborts at decision_pass check)
        if cfg != [6] or ccodes != [COLLECTOR_CODE] or cf.get("gates_passed") != 11:
            residuals.append((name, "G02 pattern", (cfg, ccodes, cf.get("gates_passed"))))
        if cf.get("decision") != af.get("decision"):
            residuals.append((name, "G02 decision", (af.get("decision"), cf.get("decision"))))
        continue
    # general single-summary trials
    exp_failed = sorted(set(afg) | {6})
    if cfg != exp_failed:
        residuals.append((name, "failed_gates set", (afg, cfg)))
    exp_codes = set(acodes) | {gate6_code_merge(acodes)}
    exp_codes = {c for c in exp_codes if not (c.startswith("6:PIN_MISMATCH:") and c != gate6_code_merge(acodes))}
    if set(ccodes) != exp_codes:
        residuals.append((name, "gate_codes set", (acodes, ccodes)))
    if 6 not in afg:
        if cf.get("gates_passed") != af.get("gates_passed", 0) - 1:
            residuals.append((name, "gates_passed", (af.get("gates_passed"), cf.get("gates_passed"))))
    dec_a, dec_c = af.get("decision"), cf.get("decision")
    if dec_a in ("PASS", "PASS_DRY_RUN") and 6 not in afg:
        if dec_c != "HOLD":
            residuals.append((name, "decision flip", (dec_a, dec_c)))
    elif dec_c != dec_a:
        residuals.append((name, "decision", (dec_a, dec_c)))
    for k in set(af) | set(cf):
        if k in ("failed_gates", "gate_codes", "gates_passed", "decision"):
            continue
        va, vc = af.get(k, "<ABSENT>"), cf.get(k, "<ABSENT>")
        if va == vc:
            continue
        if vc == "<ABSENT>" and k in PASS_ARTIFACT_KEYS:
            continue
        if k in ("ledger_unchanged", "ns_created_by_call") and dec_a in ("PASS", "PASS_DRY_RUN"):
            continue  # state consequence of the decision flip (zero-access HOLD)
        if k.startswith(("holder.", "contender.")):
            continue
        residuals.append((name, f"fact key {k}", (va, vc)))
print("TRANSFORMATION RESIDUALS:", len(residuals))
for r in residuals:
    print("  ", r)

# ---------- identity scan over all non-equal values ----------
hexre = re.compile(r'\b[0-9a-f]{40,64}\b')
ident_hits = []
for e in diff["divergent"] + diff["only_accepted"] + diff["only_candidate"]:
    for side in ("accepted", "candidate"):
        v = e.get(side)
        if isinstance(v, str) and (hexre.search(v) or "dispatch_gate_r" in v or "live_driver" in v or ".py" in v or "r4-policyA" in v or "r5-route48" in v):
            ident_hits.append((e["path"], side, v))
print("IDENTITY-STRING HITS in non-equal cells:", len(ident_hits))
for h in ident_hits[:20]:
    print("  ", h)

# ---------- per-cell classification ----------
cells = []
def classify(e):
    p = e["path"]
    if p in ("$.n_pass", "$.total_checks"):
        return ("ii", "DERIVED_ROLLUP", "top-level counter aggregating per-trial outcomes")
    m = re.match(r'^\$\.trials\[(\d+)\]\.(.*)$', p)
    trial = names[int(m.group(1))]; rest = m.group(2)
    if rest == "n_checks" or rest.startswith("checks"):
        return ("ii", "DERIVED_EMISSION", "runner check() raises at first failed assertion; emitted-check list/count is a mechanical function of the trial outcome")
    if rest == "status":
        return ("ii", "STATUS_CONSEQUENCE", "trial status transcribes the first failed assertion, tripped by the gate-6 staging failure")
    # facts cells
    field = rest[len("facts."):]
    if field.startswith(("failed_gates", "gate_codes")):
        return ("ii", "GATE6_ROOT", "gate 6 bad-set gained exactly 'collector': git-blob read (dispatch_gate_r4.py:158-163,574-578) failed in the non-git shadow stage; pin+coordinates unchanged by the r5 diff")
    if field == "gates_passed":
        return ("ii", "GATE6_COUNT", "one fewer PASS gate: gate 6 flipped by the staging git-blob failure")
    if field == "decision":
        return ("ii", "DECISION_FLIP", "any gate FAIL forces HOLD (gate contract); flip is a deterministic consequence of the gate-6 staging failure")
    if field in ("ledger_unchanged", "ns_created_by_call"):
        return ("ii", "STATE_CONSEQUENCE", "accepted PASS dispatch created namespace/wrote ledger by design; candidate HOLD performs zero access")
    return ("ii", "PASS_ARTIFACT_ABSENT", "fact recorded only from a PASS receipt/dispatch, which the staging-held run never produced")

for e in diff["divergent"]:
    cls, tag, note = classify(e)
    cells.append({"path": e["path"], "kind": "divergent", "accepted": e["accepted"],
                  "candidate": e["candidate"], "class": cls, "mechanism": tag, "note": note})
for e in diff["only_accepted"]:
    cls, tag, note = classify(e)
    cells.append({"path": e["path"], "kind": "only_accepted", "accepted": e["accepted"],
                  "candidate": None, "class": cls, "mechanism": tag, "note": note})
for e in diff["only_candidate"]:
    cls, tag, note = classify(e)
    cells.append({"path": e["path"], "kind": "only_candidate", "accepted": None,
                  "candidate": e["candidate"], "class": cls, "mechanism": tag, "note": note})

cnt = Counter((c["class"], c["mechanism"]) for c in cells)
print("\nCELL COUNTS by (class, mechanism):")
for k in sorted(cnt):
    print("  ", k, cnt[k])
print("total non-equal cells:", len(cells))
derived = sum(v for (cl, mech), v in cnt.items() if mech.startswith("DERIVED"))
print("derived (counted separately):", derived, "| root cells:", len(cells) - derived)
json.dump(cells, open("/tmp/td51_cells.json", "w"), indent=1)

# ---------- per-trial + per-family rollup ----------
fam = {"G": "green", "F": "gate-refusal (F)", "H": "helper (H)", "C": "contention (C)",
       "P": "path/pin (P)", "A": "policy (A)"}
trial_rows = []
for name in names:
    tcells = [c for c in cells if f".{name}" in c["path"] or c["path"].startswith(f"$.trials[{names.index(name)}]")]
    root = [c for c in tcells if not c["mechanism"].startswith("DERIVED")]
    trial_rows.append({"trial": name, "family": fam[name[0]],
                       "accepted_status": A[name]["status"], "candidate_status": C[name]["status"],
                       "root_cells": len(root), "derived_cells": len(tcells) - len(root),
                       "classes": sorted(set(c["class"] for c in root)),
                       "mechanisms": sorted(set(c["mechanism"] for c in root))})
json.dump({"cells": cells, "trials": trial_rows}, open("/tmp/td51_classification.json", "w"), indent=1)
for r in trial_rows:
    if r["candidate_status"] != "PASS":
        print("FAIL", r["trial"], "root:", r["root_cells"], "derived:", r["derived_cells"], r["mechanisms"])
print("\npassers with root fact cells:", [r["trial"] for r in trial_rows if r["candidate_status"] == "PASS" and r["root_cells"] > 0])
print("passers identical:", [r["trial"] for r in trial_rows if r["candidate_status"] == "PASS" and r["root_cells"] == 0 and r["derived_cells"] == 0])
