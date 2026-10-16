"""Programmatic minimal delta: r2 candidate 261a7557... -> -18 r3 candidate.

Separates the three verification pin domains (independent 156 / sealed 158 /
container pin), rewrites final_verification to domain-correct equalities, and
makes the public anchor self-sufficient (carries both pin maps + canonical
digests). Emits the candidate, a leaf-level semantic diff, and a preservation
proof (every change confined to the allowed path set)."""
import copy, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
SRC = os.path.join(REPO, "research_notes/yahoo_rev3_ledger_separation_20261016_r2/capture_manifest_rev3_ledger_separated_candidate.json")
R2_SHA = "261a75574cfcc27757ef363af6a5bb1d36f0c37c4b9bbd45740b5f5914772b49"

raw = open(SRC, "rb").read()
assert hashlib.sha256(raw).hexdigest() == R2_SHA, "r2 candidate pin mismatch"
r2 = json.loads(raw)
c = copy.deepcopy(r2)

# ---- 1. pin domains, defined without overlap ----
c["publication_binding"]["pin_domains"] = {
    "independent_validation_pins": {
        "scope": "exactly the 156 payload members",
        "form": "rel -> sha256 (hex)",
        "produced": "computed from the capture's payload bytes by the independent validator BEFORE publication; the _require_pins input to the publisher; never derived from the container",
        "excludes": "the two bookkeeping members (manifest.json, SHA256SUMS) and the container digest",
    },
    "sealed_member_pins": {
        "scope": "exactly the 158 physical members (156 payloads + manifest.json + SHA256SUMS)",
        "form": "rel -> {length, sha256}",
        "produced": "sealed by the publisher into the QFJ2 intent record at container build time",
        "projection_rule": "the 156-payload projection of the sealed set MUST equal independent_validation_pins exactly; the two bookkeeping entries are canonical under the acyclic binding graph (manifest.json binds the 156 payloads only; SHA256SUMS binds exactly 157)",
    },
    "container_pin": {
        "scope": "the single QFAR1 container",
        "form": "one sha256 (hex) — CONTAINER_SHA256, the trailer digest (SHA-256 over all container bytes preceding the 32-byte trailer)",
        "produced": "publisher-derived at build time and sealed in the QFJ2 intent record; verified ONLY by recomputation from the exact fetched blob bytes",
        "excludes": "membership in either pin map; it is never an element of, or compared against, a pin map",
    },
    "non_substitution_rule": "the three domains are disjoint in scope and are never substituted for one another: the container pin is compared only to the sealed intent value; the sealed 158 set is compared only to parsed container members; the independent 156 set is compared only to the payload projection of the parsed members",
}

# ---- 2. final_verification rewritten to domain-correct equalities ----
fv = c["publication_binding"]["final_verification"]
assert len(fv) == 5
fv[1] = ("fetch the blob by its exact pinned blob id and recompute CONTAINER_SHA256 from the fetched bytes; "
         "it must equal the container pin — the CONTAINER_SHA256 sealed in the QFJ2 intent record "
         "(publication_binding.pin_domains.container_pin). The container pin is compared ONLY to that sealed "
         "value, never to either pin map. The public anchor does not exist yet at this step and is never an "
         "input to verification")
fv[2] = ("parse the container and verify all 158 members against the sealed member pins (QFJ2 intent record): "
         "member set, lengths and SHA-256 equal the sealed 158 set exactly; then verify the 156-payload "
         "projection of the parsed members equals the independent validation pins exactly. The independent "
         "pins are never compared against the two bookkeeping members or the container digest")
c["publication_binding"]["final_verification"] = fv

# ---- 3. anchor self-sufficiency: carry both pin maps + canonical digests ----
anchor = c["archive"]["ledger_objects"]["public_archive_anchor"]
cont = anchor["contents"]
assert "member_count = 158" in cont
i = cont.index("member_count = 158")
cont[i + 1:i + 1] = [
    "sealed member pins: exact 158 rel -> {length, sha256} map (the QFJ2 intent sealed set)",
    "sealed member pins canonical digest: sha256 of the canonical JSON (sorted keys) of the sealed member pin map",
    "independent validation pins: exact 156 payload rel -> sha256 map",
    "independent validation pins canonical digest: sha256 of the canonical JSON (sorted keys) of the independent validation pin map",
]
anchor["contents"] = cont
anchor["role"] = anchor["role"] + (
    " The anchor is SELF-SUFFICIENT for a later consumer: given only the anchor bytes and the designated "
    "repo's objects, the consumer re-verifies the exact commit/tree/blob, recomputes the container pin, "
    "checks all 158 members against the carried sealed pin map and the 156-payload projection against the "
    "carried independent pin map; the two canonical pin-map digests make any pin-map alteration detectable. "
    "No local journals, publisher process state or out-of-band pins are required; no branch-tip trust.")

# ---- 4. provenance ----
c["task"] = "QF-YAHOO-REV3-VERIFICATION-PIN-SEPARATION-20261016-18 r3"
c["status"] = ("CANDIDATE REV3 — NOT ADOPTED — verification pins separated per -18 r3 — "
               "authorizes no vendor call, no capture, no publication")
rev = c["revision"]
rev["produced_by"] = "QF-YAHOO-REV3-VERIFICATION-PIN-SEPARATION-20261016-18 r3 (candidate only; no adoption)"
rev["status"] = ("CANDIDATE ONLY - NOT ADOPTED - verification pin domains separated per -18 r3; "
                 "does not authorize any acquisition or publication")
rev["supersedes_candidate"] = {
    "path": "research_notes/yahoo_rev3_ledger_separation_20261016_r2/capture_manifest_rev3_ledger_separated_candidate.json",
    "produced_by": "QF-YAHOO-REV3-MANIFEST-LEDGER-SEPARATION-20261016-18 r2",
    "sha256": R2_SHA,
}
rev["changes"] = rev["changes"] + [
    "-18 r3: added publication_binding.pin_domains — independent validation pins (156 payloads), sealed member pins (158 members) and the container pin defined as three disjoint, non-substitutable domains",
    "-18 r3: publication_binding.final_verification steps 2-3 rewritten to domain-correct equalities (container recompute vs the sealed container pin only; 158 members vs sealed pins; 156-payload projection vs independent pins)",
    "-18 r3: public_archive_anchor now carries the exact sealed 158 pin map and the exact independent 156 pin map plus canonical digests of both — the anchor is self-sufficient for a later consumer with no local journals or process state",
]

out = os.path.join(HERE, "capture_manifest_rev3_pin_separated_candidate.json")
blob = (json.dumps(c, indent=1, sort_keys=True) + "\n").encode()
open(out, "wb").write(blob)
cand_sha = hashlib.sha256(blob).hexdigest()

# ---- leaf diff + preservation proof ----
def leaves(o, p=""):
    if isinstance(o, dict):
        for k in sorted(o):
            yield from leaves(o[k], p + "/" + k)
    elif isinstance(o, list):
        for idx, v in enumerate(o):
            yield from leaves(v, f"{p}[{idx}]")
    else:
        yield p, o

a, b = dict(leaves(r2)), dict(leaves(c))
changes = []
for k in sorted(set(a) | set(b)):
    if a.get(k) != b.get(k):
        changes.append({"path": k, "from": a.get(k), "to": b.get(k)})
ALLOWED = ("/publication_binding/pin_domains", "/publication_binding/final_verification",
           "/archive/ledger_objects/public_archive_anchor", "/revision", "/status", "/task")
unallowed = [ch for ch in changes if not any(ch["path"] == p or ch["path"].startswith(p + "/") or ch["path"].startswith(p + "[") for p in ALLOWED)]
named = {
    "request_order_52_identical": r2["request_order"] == c["request_order"] and len(c["request_order"]) == 52,
    "request_params_identical": r2["request_params"] == c["request_params"],
    "runtime_pins_identical": r2["runtime_pins"] == c["runtime_pins"],
    "session_construction_freeze_identical": r2["session_construction_freeze"] == c["session_construction_freeze"],
    "qualification_gates_G1_G11_identical": r2["qualification_gates_frozen"] == c["qualification_gates_frozen"] and len(c["qualification_gates_frozen"]) == 11,
    "call_budget_limiter_ceilings_identical": r2["call_budget"] == c["call_budget"],
    "target_repo_ref_path_identical": all(r2["publication_binding"][k] == c["publication_binding"][k] for k in ("target_repo", "target_ref", "target_path", "target_repo_visibility")),
    "publisher_pin_identical": r2["publication_binding"]["publisher_commit"] == c["publication_binding"]["publisher_commit"] == "53bdc672e609791dc55277023dd984cd8727f3c3",
    "member_accounting_identical": r2["publication_binding"]["member_accounting"] == c["publication_binding"]["member_accounting"],
    "archive_journals_membership_identical": all(r2["archive"][k] == c["archive"][k] for k in ("attempt_journal", "control_directory", "membership_contract", "root", "layout")),
}
proof = {"named_checks": named, "all_named_pass": all(named.values()),
         "total_leaf_changes": len(changes), "unallowed_changes": unallowed,
         "preservation_pass": all(named.values()) and not unallowed}
diff = {"task": "QF-YAHOO-REV3-VERIFICATION-PIN-SEPARATION-20261016-18 r3",
        "from_candidate_sha256": R2_SHA, "to_candidate_sha256": cand_sha,
        "allowed_change_prefixes": list(ALLOWED), "changes": changes, "preservation": proof}
open(os.path.join(HERE, "semantic_diff_r2_to_r3.json"), "w").write(json.dumps(diff, indent=1, sort_keys=True) + "\n")
print("candidate sha256:", cand_sha)
print("leaf changes:", len(changes), "| unallowed:", len(unallowed), "| preservation:", proof["preservation_pass"])
sys.exit(0 if proof["preservation_pass"] else 1)
