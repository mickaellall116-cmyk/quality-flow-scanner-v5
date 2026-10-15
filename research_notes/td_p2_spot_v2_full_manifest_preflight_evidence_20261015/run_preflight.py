#!/usr/bin/env python3
"""QF-TD-P2-SPOT-V2-FULL-MANIFEST-STATE-PREFLIGHT-20261015-05 r1 driver.

Offline copied-state transition preflight. Starts from an immutable byte copy
of the ACTUAL SPOT8 acquisition state (v1, status HOLD after REQ-SPT-07's
HTTP 400), recomputes every -04 pin, inventories/hashes every artifact, and
asks the honest question the -05 spec poses: can the UNCHANGED candidate
collector (ab254c3, b683d277...) derive a v2 state -- SPT01-06 reused from
durable receipts, SPT07 derived from its preserved 180-byte rejected evidence
under the NL supplement, zero transport -- and then dispatch only REQ-SPT-08
under the frozen eight-request SPOT8 manifest?

Fake transport only; network disabled in-process before any collector import.
The original state directory is opened read-only (hashed before and after).
No candidate/supplement/manifest bytes are modified. Output: one normalized
JSON document (no timestamps, no tmp paths) so two runs diff byte-for-byte.
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import shutil
import socket
import sys
import tempfile


def _no_net(*a, **k):
    raise RuntimeError("network disabled (PF05 offline preflight)")


socket.socket.connect = _no_net
socket.socket.connect_ex = _no_net
socket.create_connection = _no_net
socket.getaddrinfo = _no_net

P = argparse.ArgumentParser()
P.add_argument("--candidate-dir", required=True)
P.add_argument("--supplement", required=True)
P.add_argument("--manifest", required=True)
P.add_argument("--original-state", required=True)
P.add_argument("--out", required=True)
P.add_argument("--artifacts", required=True,
               help="dir for side artifacts (inventory, mapping, proof, ledger)")
ARGS = P.parse_args()

CAND = pathlib.Path(ARGS.candidate_dir).resolve()
HARNESS = CAND.parent / "pilot_harness"
ORIG = pathlib.Path(ARGS.original_state).resolve()
ART = pathlib.Path(ARGS.artifacts)
ART.mkdir(parents=True, exist_ok=True)
EPOCH = 1792000000

sys.path.insert(0, str(HARNESS))

spec = importlib.util.spec_from_file_location("pf05_collector", CAND / "td_min_collector.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

import validate_input
MECH_SHA = hashlib.sha256(pathlib.Path(validate_input.__file__).read_bytes()).hexdigest()
import pandas_market_calendars as _mcal
PMC_VERSION = str(_mcal.__version__)

from rate_limiter import RollingCreditLimiter

SUP_NL = json.loads(pathlib.Path(ARGS.supplement).read_text())
SPOT8 = json.loads(pathlib.Path(ARGS.manifest).read_text())
BY_ID = {r["request_id"]: r for r in SPOT8["requests"]}
RESULTS = []
CALL_LEDGER = []


def record(case, checks, note=""):
    RESULTS.append({"case": case, "pass": all(checks.values()),
                    "checks": {k: bool(v) for k, v in sorted(checks.items())},
                    "note": note})


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def inventory(root: pathlib.Path):
    inv = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            inv[str(p.relative_to(root))] = {"sha256": sha(p.read_bytes()),
                                             "bytes": p.stat().st_size}
    return inv


def write_prereq(root):
    p = root / "prereq.json"
    doc = {"plan": "Basic",
           "endpoint_weight": {"endpoint": "/time_series", "credits_per_request": 1,
                               "evidence": "PF05 offline fixture (synthetic prerequisite; no vendor contact)"},
           "retention": {"status": "BOUNDED_RESOLVED", "condition": "30-day deletion"},
           "interval_semantics": {"status": "INSUFFICIENT"}}
    p.write_text(json.dumps(doc))
    return p


def closed_body(symbol):
    return json.dumps({"code": 400, "message": mod.CLOSED_SESSION_MESSAGE,
                       "status": "error",
                       "meta": {"symbol": symbol, "interval": "1h",
                                "exchange": ""}}).encode()


def valid_body(req):
    import pandas as pd
    from validate_input import expected_1h_starts, xnys_schedule
    from datetime import date, timedelta
    d0 = date.fromisoformat(req["start_date"][:10])
    d1 = date.fromisoformat(req["end_date"][:10])
    values = []
    cur = d0
    while cur <= d1:
        sched = xnys_schedule(pd.Timestamp(cur.isoformat()))
        if sched is not None:
            for t in expected_1h_starts(*sched):
                values.append({"datetime": t.strftime("%Y-%m-%d %H:%M:%S"),
                               "open": "10", "high": "11", "low": "9",
                               "close": "10", "volume": "1"})
        cur += timedelta(days=1)
    meta = {"symbol": req["symbol"], "interval": req["interval"]}
    meta.update(req["venue_identity"])
    return json.dumps({"status": "ok", "meta": meta, "values": values}).encode()


def make_collector(root, state_dir, transport, supplement=SUP_NL):
    lim = RollingCreditLimiter(8, 800, state_path=root / "shared_credit.json",
                               clock=lambda: EPOCH)
    return mod.Collector(state_dir, SPOT8, lim, transport=transport,
                         prereq_path=root / "prereq.json",
                         closed_session_supplement=supplement)


def norm_events(sd):
    p = sd / "lifecycle.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        if line.strip():
            e = json.loads(line)
            e.pop("ts_utc", None)
            out.append(e)
    return out


# ---------------------------------------------------------------------------
# 1. Freeze / pin recomputation (spec point 1; all -04 pins)
# ---------------------------------------------------------------------------
record("freeze_candidate_set", {
    "collector_sha": sha((CAND / "td_min_collector.py").read_bytes())
        == "b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c",
    "supplement_sha": sha(pathlib.Path(ARGS.supplement).read_bytes())
        == "9c71233003771d66cf81e99ae01a410ba8943aedfcce8a8c6411dfb51edacd32",
    "manifest_file_sha": sha(pathlib.Path(ARGS.manifest).read_bytes())
        == "ddff040fa654303cf4289f4c39c2a5b5af998bd4065ceddd4e4f5d52fcb8c28d",
    "manifest_digest": mod.canonical_digest(SPOT8)
        == "748ca95789c6f16bab81fbc903fd0c60a890dd2f2e21a63d97ffdb962d70e4fb",
    "spt08_digest": mod.canonical_digest(BY_ID["REQ-SPT-08"])
        == "f547d8fec7882fa121feb966b33fde000b25c4ae0eb822a6b5a503f4a3651a97",
    "spt07_digest": mod.canonical_digest(BY_ID["REQ-SPT-07"])
        == "a259901ec57a8556228c2a6b95299c360102cc98edc62204ae539dc53a4c5edb",
    "supplement_binds_base": SUP_NL["base_manifest_digest"] == mod.canonical_digest(SPOT8),
    "mechanism_sha": MECH_SHA == "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58",
    "pmc_version": PMC_VERSION == "4.5.1",
    "spot8_manifest_valid": mod.validate_manifest(SPOT8) == [],
    "eight_requests": len(SPOT8["requests"]) == 8,
})

# ---------------------------------------------------------------------------
# 2. Original SPOT8 state inventory (spec point 2; original is read-only)
# ---------------------------------------------------------------------------
ORIG_INV = inventory(ORIG)
(ART / "state_inventory_original.json").write_text(
    json.dumps(ORIG_INV, indent=1, sort_keys=True) + "\n")
pilot = json.loads((ORIG / "pilot_state.json").read_text())
binding = json.loads((ORIG / "manifest_binding.json").read_text())
events = [json.loads(l) for l in (ORIG / "lifecycle.jsonl").read_text().splitlines() if l.strip()]
from collections import Counter
counts = Counter(e["event"] for e in events)
err_ev = [e for e in events if e["event"] == "ERROR_EVIDENCE"]
hold_ev = [e for e in events if e["event"] == "HOLD"]
PRESERVED = (ORIG / "receipts" / "REQ-SPT-07.rejected.bin").read_bytes()
record("original_state_inventory", {
    "file_set_exact": sorted(ORIG_INV) == sorted([
        "collector.lock", "lifecycle.jsonl", "manifest_binding.json", "pilot_state.json",
        "receipts/REQ-SPT-01.json", "receipts/REQ-SPT-02.json", "receipts/REQ-SPT-03.json",
        "receipts/REQ-SPT-04.json", "receipts/REQ-SPT-05.json", "receipts/REQ-SPT-06.json",
        "receipts/REQ-SPT-07.rejected.bin"]),
    "binding_is_spot8_digest": binding == {"sha256": "748ca95789c6f16bab81fbc903fd0c60a890dd2f2e21a63d97ffdb962d70e4fb"},
    "pilot_hold": pilot["status"] == "HOLD" and pilot["hold_reason"] == "HTTP 400 for REQ-SPT-07",
    "pilot_counts": pilot["attempts"] == 7 and pilot["credit_reservations"] == 7,
    "pilot_completed_01_06": pilot["completed"] == [f"REQ-SPT-0{i}" for i in range(1, 7)],
    "lifecycle_34_events": len(events) == 34,
    "lifecycle_counts": counts["CREDIT_RESERVED"] == 7 and counts["STARTED"] == 7
        and counts["RECEIVED"] == 6 and counts["COMPLETED"] == 6
        and counts["ERROR_EVIDENCE"] == 1 and counts["HOLD"] == 1,
    "error_evidence_sha_is_preserved_body": len(err_ev) == 1
        and err_ev[0].get("sha256") == sha(PRESERVED)
        and err_ev[0].get("request_id") == "REQ-SPT-07",
    "hold_event_reason": len(hold_ev) == 1
        and hold_ev[0].get("reason") == "HTTP 400 for REQ-SPT-07",
    "preserved_body_pin": sha(PRESERVED)
        == "3339c34154648c0ea4ddb9bd553e5274d390f953552518ad957d79704b7d5d50"
        and len(PRESERVED) == 180,
    "no_spt07_receipt": "receipts/REQ-SPT-07.json" not in ORIG_INV,
    "no_spt08_anything": not any("SPT-08" in k for k in ORIG_INV),
})

# ---------------------------------------------------------------------------
# 3. Copy fidelity + receipt revalidation inside the copy (spec point 2/3)
# ---------------------------------------------------------------------------
tmp = tempfile.TemporaryDirectory()
root = pathlib.Path(tmp.name)
write_prereq(root)
copy_dir = root / "state_v2_copy"
shutil.copytree(ORIG, copy_dir)
COPY_INV = inventory(copy_dir)
record("copy_fidelity", {
    "copy_hashes_equal_original": COPY_INV == ORIG_INV,
})

# The receipt probe gets its OWN copy: the candidate's _verify_receipt is NOT
# side-effect-free (its _validate_bars path emits CONSTRUCTION_HOLD lifecycle
# events for 1h requests), so probing the transition copy would contaminate
# the transition baseline. The side effect itself is recorded as a finding.
probe_dir = root / "state_probe_copy"
shutil.copytree(ORIG, probe_dir)
PROBE_PRE = inventory(probe_dir)
probe = make_collector(root, probe_dir, transport=lambda r: (_ for _ in ()).throw(
    AssertionError("transport must not be called during receipt probe")))
verify = {}
for i in range(1, 7):
    rid = f"REQ-SPT-0{i}"
    ok, why = probe._verify_receipt(BY_ID[rid], probe_dir / "receipts" / f"{rid}.json")
    verify[rid] = (ok, why)
probe_events = norm_events(probe_dir)
appended = probe_events[len(events):]
PROBE_POST = inventory(probe_dir)
record("receipts_revalidate_in_copy", {
    "all_six_ok": all(v[0] for v in verify.values()),
    "reasons_ok": all(v[1] == "ok" for v in verify.values()),
    "side_effect_exactly_6_construction_hold_appends":
        len(appended) == 6
        and all(e["event"] == "CONSTRUCTION_HOLD" for e in appended)
        and sorted(e["request_id"] for e in appended) == [f"REQ-SPT-0{i}" for i in range(1, 7)],
    "side_effect_pilot_state_unchanged":
        PROBE_POST["pilot_state.json"]["sha256"] == PROBE_PRE["pilot_state.json"]["sha256"],
    "side_effect_no_other_file_changed":
        all(PROBE_POST[k]["sha256"] == PROBE_PRE[k]["sha256"]
            for k in PROBE_PRE if k != "lifecycle.jsonl"),
}, "driver-level use of the candidate's own _verify_receipt against a SEPARATE "
   "probe copy: SPT01-06 durable receipts are intact and manifest-bound. "
   "FINDING: _verify_receipt is not read-only -- _validate_bars emits one "
   "CONSTRUCTION_HOLD lifecycle event per 1h receipt (append-only; pilot "
   "state and receipts untouched). Any derivation design must account for "
   "verification-time lifecycle appends (duplicates accumulate on re-verify).")

# ---------------------------------------------------------------------------
# 4. THE TRANSITION ATTEMPT (spec point 3): unchanged candidate, copied v1
#    HOLD state, NL supplement, full eight-request manifest, recording fake
#    transport. Honest expectation per the code: persistent-HOLD short-circuit.
# ---------------------------------------------------------------------------
calls = []
def recording_transport(req):
    calls.append(req["request_id"])
    if req["request_id"] == "REQ-SPT-08":
        return 400, closed_body("QQQ")
    return 200, valid_body(req)

c = make_collector(root, copy_dir, recording_transport)
s = c.run()
CALL_LEDGER.append({"case": "transition_attempt_full_manifest", "calls": calls})
POST_ATTEMPT_INV = inventory(copy_dir)
record("transition_attempt_full_manifest", {
    "outcome_is_persistent_hold": s["outcome"] == "HOLD (persistent): HTTP 400 for REQ-SPT-07",
    "zero_transport_calls": calls == [],
    "zero_dispatched": s["dispatched"] == 0,
    "zero_reused_counted": s["reused"] == 0,
    "zero_evidenced_counted": s["closed_day_evidenced"] == 0,
    "state_bytes_unchanged": POST_ATTEMPT_INV == COPY_INV,
    "lifecycle_bytes_unchanged": sha((copy_dir / "lifecycle.jsonl").read_bytes())
        == ORIG_INV["lifecycle.jsonl"]["sha256"],
    "pilot_state_bytes_unchanged": sha((copy_dir / "pilot_state.json").read_bytes())
        == ORIG_INV["pilot_state.json"]["sha256"],
    "no_spt08_artifacts": not any("SPT-08" in k for k in POST_ATTEMPT_INV),
    "no_closed_day_bin": "receipts/REQ-SPT-07.closed_day.bin" not in POST_ATTEMPT_INV,
}, "DESIGN GAP (empirical): _run_locked returns HOLD (persistent) before any "
   "receipt reuse, evidence derivation, or dispatch; the unchanged candidate "
   "has no entry point that re-classifies durable rejected evidence")

# ---------------------------------------------------------------------------
# 5. Restart of the copied state: same terminal HOLD, still zero calls
#    (spec point 6 restart control, applied to the only state that exists)
# ---------------------------------------------------------------------------
calls_r = []
c_r = make_collector(root, copy_dir,
                     lambda r: (calls_r.append(r["request_id"]), (200, b"{}"))[1])
s_r = c_r.run()
CALL_LEDGER.append({"case": "transition_restart_again", "calls": calls_r})
record("transition_restart_again", {
    "outcome_is_persistent_hold": s_r["outcome"] == "HOLD (persistent): HTTP 400 for REQ-SPT-07",
    "zero_transport_calls": calls_r == [],
    "state_bytes_still_unchanged": inventory(copy_dir) == COPY_INV,
})

# ---------------------------------------------------------------------------
# 6. Direct classifier proof on the preserved evidence (isolates the gap):
#    the classifier + evidence + calendar are sufficient; only the state
#    transition entry point is missing. Pure function; writes nothing.
# ---------------------------------------------------------------------------
probe2 = make_collector(root, copy_dir, transport=lambda r: (_ for _ in ()).throw(
    AssertionError("transport must not be called during classifier proof")))
req07 = BY_ID["REQ-SPT-07"]
proof = probe2._classify_closed_session(req07, 400, PRESERVED)
(ART / "classifier_proof.json").write_text(
    json.dumps(proof, indent=1, sort_keys=True) + "\n")
tampered = json.loads(PRESERVED)
tampered["meta"]["symbol"] = "MSFT"
proof_neg_body = probe2._classify_closed_session(req07, 400, json.dumps(tampered).encode())
proof_neg_status = probe2._classify_closed_session(req07, 200, PRESERVED)
probe3 = make_collector(root, copy_dir, transport=lambda r: (200, b"{}"), supplement=None)
proof_neg_nosup = probe3._classify_closed_session(req07, 400, PRESERVED)
record("classifier_direct_proof_on_preserved_evidence", {
    "proof_returned": proof is not None,
    "proof_all_dates_closed": proof is not None
        and all(v == "closed" for v in proof["per_date"].values())
        and len(proof["per_date"]) >= 1,
    "proof_library_pin": proof is not None and proof["library_version"] == "4.5.1",
    "proof_mechanism_pin": proof is not None
        and proof["mechanism_module_sha256"] == "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58",
    "proof_digest_recomputes": proof is not None
        and proof["proof_digest"] == mod.canonical_digest(
            {k: v for k, v in proof.items() if k != "proof_digest"}),
    "negative_tampered_body_none": proof_neg_body is None,
    "negative_wrong_status_none": proof_neg_status is None,
    "negative_no_supplement_none": proof_neg_nosup is None,
    "classifier_wrote_nothing": inventory(copy_dir) == COPY_INV,
}, "the accepted NL classifier, applied directly to the preserved 180-byte "
   "body + actual REQ-SPT-07 object, returns a full calendar proof; the gap "
   "is NOT classification -- it is the missing state-transition entry point")

# ---------------------------------------------------------------------------
# 7. SYNTHETIC control (NOT the copied v1 state): downstream machinery past
#    a CLOSED_DAY_EVIDENCED event works -- fresh run classifies in-run, and
#    restart reuses receipts + evidenced requests with zero transport. This
#    pins the design gap to exactly one missing step: derivation.
# ---------------------------------------------------------------------------
tmp2 = tempfile.TemporaryDirectory()
root2 = pathlib.Path(tmp2.name)
write_prereq(root2)
calls_s = []
def synth_transport(req):
    calls_s.append(req["request_id"])
    if req["request_id"] == "REQ-SPT-07":
        return 400, PRESERVED
    if req["request_id"] == "REQ-SPT-08":
        return 400, closed_body("QQQ")
    return 200, valid_body(req)
cs = make_collector(root2, root2 / "state", synth_transport)
ss = cs.run()
CALL_LEDGER.append({"case": "synthetic_control_fresh_run", "calls": calls_s})
calls_s2 = []
def boom(r):
    calls_s2.append(r["request_id"])
    raise AssertionError("transport must not be called on synthetic restart")
cs2 = make_collector(root2, root2 / "state", boom)
ss2 = cs2.run()
CALL_LEDGER.append({"case": "synthetic_control_restart", "calls": calls_s2})
record("synthetic_control_downstream_machinery", {
    "fresh_outcome": ss["outcome"] == "COMPLETE_WITH_CLOSED_DAY_EVIDENCED",
    "fresh_calls_in_order": calls_s == [f"REQ-SPT-0{i}" for i in range(1, 9)],
    "restart_zero_calls": calls_s2 == [],
    "restart_outcome": ss2["outcome"] == "COMPLETE_WITH_CLOSED_DAY_EVIDENCED",
    "restart_reused_6_evidenced_2": ss2["reused"] == 6 and ss2["closed_day_evidenced"] == 2,
}, "SYNTHETIC state only (fresh fake run, -04 SS2c/2d pattern): once a "
   "CLOSED_DAY_EVIDENCED event exists, reuse/restart machinery is complete; "
   "no equivalent event can be produced from the v1 HOLD state's durable "
   "rejected evidence by any candidate entry point")

# ---------------------------------------------------------------------------
# 8. Original-vs-derived mapping + original untouched (spec points 2/7)
# ---------------------------------------------------------------------------
mapping = {}
for rel, meta in ORIG_INV.items():
    mapping[rel] = {"original_sha256": meta["sha256"],
                    "copied_sha256": COPY_INV[rel]["sha256"],
                    "post_attempt_sha256": POST_ATTEMPT_INV[rel]["sha256"],
                    "disposition": "unchanged"}
(ART / "original_vs_derived_mapping.json").write_text(
    json.dumps({"mapping": mapping,
                "derived_state_produced": False,
                "derived_state_note": "No v2 state could be derived: the transition "
                "attempt left the copy byte-identical to the v1 original (persistent "
                "HOLD short-circuit). There is no derived state to map."},
               indent=1, sort_keys=True) + "\n")
(ART / "fake_call_ledger.json").write_text(
    json.dumps({"entries": CALL_LEDGER,
                "total_fake_dispatches": sum(len(e["calls"]) for e in CALL_LEDGER),
                "real_transport_calls": 0, "vendor_calls": 0,
                "twelve_data_calls": 0, "model_calls": 0, "credits_spent": 0},
               indent=1, sort_keys=True) + "\n")
FINAL_ORIG_INV = inventory(ORIG)
record("original_state_untouched_final", {
    "original_hashes_unchanged": FINAL_ORIG_INV == ORIG_INV,
})

pathlib.Path(ARGS.out).write_text(json.dumps(
    {"mode": "main", "results": RESULTS,
     "transition_supported": False,
     "all_checks_pass": all(r["pass"] for r in RESULTS)}, indent=1, sort_keys=True) + "\n")
print(json.dumps({"cases": len(RESULTS), "all_checks_pass": all(r["pass"] for r in RESULTS),
                  "transition_supported": False}))
