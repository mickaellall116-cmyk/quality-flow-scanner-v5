#!/usr/bin/env python3
"""Build the immutable CHILD continuation manifest for QF-TD-EQUITY39-CONTINUE-20261023-11.
Parent: QF-CAPTURE-MANIFEST-EQUITY39-PREP-20261023 root ca49892062f1ac5d4ec...
(prep commit a3ec37e05fc2a0ab6260926fd35a826d927c9894). Child = parent legs minus
ONLY PLTR/HO (77 legs, original relative order), plus parent linkage, the -10 stop
record, the prior quarantine pin, the explicit acquisition-only policy amendment,
and the CH-1 disclosure. Root digest construction identical to the parent's:
sha256 of canonical JSON (sorted keys, compact separators) with the root fields omitted."""
import json, hashlib, copy

PARENT_PATH = "/home/hatch/workspace/qf_td10_stage/store/capture_manifest.json"
OUT_PATH = "/home/hatch/workspace/qf_td11_stage/store/child_manifest.json"
PARENT_ROOT = "ca49892062f1ac5d4ec6d20eaadd37b519aec84ad0b23a995fb11db74dccfd64"
CH1_TEXT = ("CH-1 disclosed assumption (three-gate freeze a126ce5): the adopted 751-session "
            "calendar rests on the NYSE Group/ICE release of 2022-12-21 for the 2023 window; "
            "in-era 2023 core-hours documentation pursued in parallel, non-blocking.")

parent = json.load(open(PARENT_PATH))
# verify parent root first
pp = dict(parent); pp.pop("root_digest_sha256"); pp.pop("root_digest_construction")
assert hashlib.sha256(json.dumps(pp, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == PARENT_ROOT

child = copy.deepcopy(parent)
child.pop("root_digest_sha256"); child.pop("root_digest_construction")
child["manifest_id"] = "QF-CAPTURE-MANIFEST-EQUITY39-CONTINUE-20261023-11"
child["status"] = ("CHILD continuation manifest under GO QF-TD-EQUITY39-CONTINUE-20261023-11 "
                   "(Issue #1 comment 6374566569). Immutable during execution; exactly the 77 "
                   "never-attempted legs of the parent manifest. Authorizes this one acquisition "
                   "continuation only - no performance, no qualification upgrade.")
child["parent"] = {
    "manifest_id": parent["manifest_id"],
    "root_digest_sha256": PARENT_ROOT,
    "prep_commit": "a3ec37e05fc2a0ab6260926fd35a826d927c9894",
    "parent_task": "QF-TD-EQUITY39-CAPTURE-20261023-10",
    "parent_stop_commit": "a10fc6e14b00cf4ee8a3c7f8082e4cc32e057a8d",
    "parent_bridge_result_commit": "b0c3fb5",
    "parent_archive_commit": "db1b43d",
    "prior_quarantine": {
        "leg_id": "PLTR/HO", "symbol": "PLTR", "window": "W_HO",
        "sha256": "bad09adc737acc3bde90a369965345fcca1ba9840ea169eba89f3e2b7f6521ec",
        "classification": "NOT_EVALUABLE_PROVIDER_VOLUME",
        "defect": "3 price-moving zero-volume bars at 2024-04-09 10:30, 2024-04-10 09:30/10:30 ET",
        "disposition": "preserved in qf-data-archive captures/td_capture_equity39_20261023; "
                       "excluded from this child manifest; NEVER re-requested under this GO",
    },
    "excluded_legs": ["PLTR/HO"],
    "no_retry": "No PLTR/HO or SMCI/HO retry of any kind under this GO.",
}
child["policy_amendment"] = {
    "scope": "ACQUISITION-ONLY (data capture transport policy). Does NOT amend strategy, "
             "data-qualification standards, or any backtest eligibility rule.",
    "amended_policy": "stop-on-first-volume-anomaly (parent / -10 transport safety policy)",
    "new_behavior": "QUARANTINE-BAD-LEG-AND-CONTINUE: on exactly the price-moving-zero-volume "
                    "class (OHLC bar with volume == 0 and high > low), quarantine the entire "
                    "affected response byte-exact at an immutable hash, mark that leg "
                    "NOT_EVALUABLE_PROVIDER_VOLUME, emit NO capture_receipt, do NOT retry the "
                    "leg, reconcile bracket accounting, and proceed to the next unchanged leg.",
    "unchanged": "Every other fatal abort class from -10 remains STOP: schema violation, "
                 "duplicate UTC instant, time/DST ambiguity, gap violation, 5000-row truncation "
                 "suspect, non-finite value, HTTP 429, refused HTTP, bracket exhaustion, "
                 "reconciliation mismatch, insufficient quota, manifest mismatch, corrupt "
                 "receipt/ledger. No imputation, no waivers, no new vendors.",
    "authority": "ChatGPT GO, Issue #1 comment 6374566569, 2026-10-23",
}
child["ch1_disclosure"] = CH1_TEXT
# legs: parent minus PLTR/HO, original relative order, unchanged fields
legs = [l for l in parent["legs"] if l["leg_id"] != "PLTR/HO"]
assert len(legs) == 77 and len({l["leg_id"] for l in legs}) == 77
assert [l["leg_id"] for l in legs] == [l["leg_id"] for l in parent["legs"] if l["leg_id"] != "PLTR/HO"]
assert sum(1 for l in legs if l["symbol"] == "PLTR") == 1 and legs[0]["leg_id"] == "PLTR/DEV"
child["legs"] = legs
child["legs_total"] = 77
child["accounting"] = {
    "scheme": parent["accounting"]["scheme"].replace(
        "a leg exhausting its bracket STOPS the capture",
        "a leg exhausting its bracket STOPS the capture; a price-moving zero-volume leg is "
        "quarantined and the capture CONTINUES (policy amendment, acquisition-only)"),
    "expected": {"attempts": 77, "blocks": 8, "usage_reads": 9, "total_credits": 86},
    "worst": {"attempts": 154, "blocks": 16, "usage_reads": 17, "total_credits": 171},
    "free_tier": parent["accounting"]["free_tier"],
}
child["destination"] = {
    "archive": "qf-data-archive (private), captures/td_capture_equity39_continue_20261023/ - NEW "
               "append-only namespace, write-once, SHA256SUMS verified by re-fetch; the -10 "
               "namespace captures/td_capture_equity39_20261023 is preserved untouched; deletion "
               "only on Mike's approval",
    "local": "working store under ~/workspace/qf_td11_stage, byte-identical to archive copies",
}
child["receipt"] = ("IDENTICAL to the pilot's schema: QF-CAPTURE-RECEIPT-CANDIDATE-20261023-01 "
                    "(kind-discriminated, hash-chained to THIS CHILD manifest's root digest with a "
                    "NEW GENESIS bound to the child digest; capture_receipt emitted ONLY after a leg "
                    "passes every wrapper validation; refused and volume-quarantined legs emit no "
                    "receipt - absence is the failure signal). Receipts additionally carry "
                    "parent_manifest_root_digest_sha256 for lineage. Per -91, receipts carry "
                    "block_id / block_position / bracket-read hashes and do NOT carry per-leg "
                    "usage_before/usage_after/credit_delta fields.")
child["qualification_gates"] = parent["qualification_gates"].replace(
    "every name in this manifest is NOT ACQUIRED / NOT QUALIFIED",
    "names captured under this child manifest are labeled CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED "
    "at best - G1-G6 candidate PASS is NOT FULLY QUALIFIED while the G4/VBASIS checker remains "
    "unadopted; PLTR/DEV capture does NOT qualify PLTR/HO")

canon = json.dumps(child, sort_keys=True, separators=(",", ":")).encode()
child["root_digest_sha256"] = hashlib.sha256(canon).hexdigest()
child["root_digest_construction"] = ("sha256 of the canonical JSON serialization (sorted keys, "
                                     "compact separators) of this manifest object with the "
                                     "root_digest_sha256 and root_digest_construction fields omitted "
                                     "(identical construction to the parent manifest)")
with open(OUT_PATH, "w") as f:
    json.dump(child, f, indent=2, sort_keys=True)
print("child root:", child["root_digest_sha256"])
print("legs:", len(child["legs"]), "first:", child["legs"][0]["leg_id"], "last:", child["legs"][-1]["leg_id"])
