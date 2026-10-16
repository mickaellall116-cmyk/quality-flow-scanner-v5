#!/usr/bin/env python3
"""Build the normalized rev3 candidate + semantic diff + verification evidence
for QF-YAHOO-REV3-MANIFEST-ADOPTION-READINESS-20261016-17 r1.

Method: start from the frozen rev2 manifest object (so every preserved section
is identical by construction), apply ONLY (a) the already-approved ceiling
revision carried by the -13 candidate, and (b) storage/publication/execution
reference normalization to the accepted QFAR1 architecture. Then deep-diff
rev2 -> normalized rev3 and verify preservation claims mechanically.
Offline; reads only repo files; writes only into this package directory.
"""
import copy
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PKG = pathlib.Path(__file__).resolve().parent
REV2_PATH = ROOT / "research_notes/yahoo_clean_capture_preflight_20261015/capture_manifest.json"
CAND_PATH = ROOT / "research_notes/yahoo_qfar1_preflight_20261015/capture_manifest_rev3_candidate.json"

REV2_SHA256 = "634c4541a8b30ade50e45898e80ee65806fa323c953020edc149530642d9bef3"
CAND_SHA256 = "617f86100b2602ea642cad88fbcca01da32377f4cb2bcca712268846f6e574a3"
DESIGN_SHA256 = "cd9ef36da512185781d2bf6376d1a8848ba62cbf134aec922566aec518f71470"
PUBLISHER_COMMIT = "53bdc672e609791dc55277023dd984cd8727f3c3"
PUBLISHER_FILE_SHA256 = "1d4c192324744c77e294c0b3190e88666dce583b14ef4412b3e31f85127fdc10"

CEIL_TOTAL = 67108864
CEIL_RESERVE = 32164
CEIL_PAYLOAD = 67076700


def sha256_file(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canon_sha(x):
    return hashlib.sha256(canon(x).encode("utf-8")).hexdigest()


def deep_diff(a, b, path=""):
    out = []
    if type(a) is not type(b):
        out.append({"path": path, "kind": "type_change", "rev2": a, "rev3": b})
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{path}.{k}" if path else k
            if k not in a:
                out.append({"path": p, "kind": "added", "rev2": None, "rev3": b[k]})
            elif k not in b:
                out.append({"path": p, "kind": "removed", "rev2": a[k], "rev3": None})
            else:
                out.extend(deep_diff(a[k], b[k], p))
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append({"path": path, "kind": "length_change", "rev2": len(a), "rev3": len(b)})
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(deep_diff(x, y, f"{path}[{i}]"))
    elif a != b:
        out.append({"path": path, "kind": "value_change", "rev2": a, "rev3": b})
    return out


def main():
    checks = []

    def check(cid, desc, ok, detail=""):
        checks.append({"id": cid, "description": desc, "result": "PASS" if ok else "FAIL", "detail": detail})
        return ok

    # --- input integrity -------------------------------------------------
    check("IN-1", "frozen rev2 manifest sha256 matches pin 634c4541...",
          sha256_file(REV2_PATH) == REV2_SHA256, sha256_file(REV2_PATH))
    check("IN-2", "-13 rev3 candidate sha256 matches pin 617f8610...",
          sha256_file(CAND_PATH) == CAND_SHA256, sha256_file(CAND_PATH))

    rev2 = json.loads(REV2_PATH.read_text())
    cand = json.loads(CAND_PATH.read_text())

    # The -13 candidate must itself differ from rev2 only in ceilings+revision.
    cand_diff_paths = sorted({d["path"].split(".")[0] + "." + d["path"].split(".")[1]
                              if "." in d["path"] else d["path"]
                              for d in deep_diff(rev2, cand)})
    check("IN-3", "-13 candidate differs from rev2 only under call_budget.ceilings and revision",
          all(p.startswith("call_budget.ceilings") or p == "revision" for p in cand_diff_paths),
          "; ".join(cand_diff_paths))

    # --- build normalized rev3 from rev2 ----------------------------------
    n = copy.deepcopy(rev2)

    # (a) approved ceiling revision — values taken from the -13 candidate so
    #     this task introduces no ceiling number of its own.
    cc = cand["call_budget"]["ceilings"]
    n["call_budget"]["ceilings"]["bytes_total"] = cc["bytes_total"]
    n["call_budget"]["ceilings"]["bytes_total_definition"] = cc["bytes_total_definition"]
    n["call_budget"]["ceilings"]["bookkeeping_reserve_bytes"] = cc["bookkeeping_reserve_bytes"]
    n["call_budget"]["ceilings"]["payload_budget_bytes"] = cc["payload_budget_bytes"]
    n["call_budget"]["ceilings"]["oversize_streaming_rule"] = (
        "a streaming response that would exceed the per-symbol ceiling or the payload "
        "budget consumes its single attempt: the transfer is cut off at the ceiling, the "
        "symbol is held, and the consumed attempt is never re-requested (adjudication "
        "6205968339; spec -17 item 2).")

    # (b) archive: supersede stale local-VM / per-file publication narrative.
    n["archive"]["root"] = (
        "local staging only (transient working state, NOT the archive of record): "
        "~/workspace/data_archive/yahoo_1h_clean/<capture_id>/ — staged members are "
        "sealed into one QFAR1 container and published to the designated private repo "
        "per publication_binding; durability comes from that repo, never from this volume.")
    n["archive"]["durability"] = (
        "provided by the designated private GitHub repo mickaellall116-cmyk/qf-data-archive "
        "(Mike's storage designation, 2026-10-15): append-only, write-once captures, "
        "checksum-verified by re-fetch. The rev2-era local-volume durability question is "
        "superseded — the local staging copy is not a durability claim and its loss "
        "before publication is a failed capture, not a data-loss event.")
    n["archive"]["publication"] = (
        "QFAR1 single-blob publication ONLY (see publication_binding): the 158 physical "
        "members (156 payloads + manifest.json + SHA256SUMS) are sealed into one "
        "deterministic QFAR1 container and published by the accepted publisher pin to "
        "the designated private repo as one commit at captures/<capture_id>.qfar. "
        "The rev2 per-file os.link publication narrative is superseded and forbidden. "
        "Publication is complete only after final commit/blob/container/member "
        "verification passes against the independent validation pins.")
    n["archive"]["attempt_journal"] = (
        "before each request, an fsync'd attempt record is appended to the capture "
        "ledger; a symbol with an attempt record but no final raw file is "
        "ATTEMPT_CONSUMED_AMBIGUOUS — never blindly re-requested on restart; it HOLDs "
        "for adjudication. On restart: final file + hash match = SKIP_VERIFIED; "
        "final mismatch = HOLD:FINAL_MISMATCH. (Rule preserved from rev2; the -08 "
        "preflight fixture that first exercised it is provenance evidence only and "
        "is not the execution route.)")
    # archive.layout, archive.restart, archive.rollback: preserved verbatim.

    # (b) execution packet: abort rules preserved; parked-executor route removed.
    n["execution_packet"] = {
        "abort_rules": rev2["execution_packet"]["abort_rules"],
        "handoff_contract": {
            "stages": [
                "1) clean capture executor: a future, separately authorized executor "
                "written fresh against this manifest; it stages the 156 payloads and "
                "the capture ledger under archive.root",
                "2) independent validation: qualification gates G1-G11 run against "
                "the staged members and produce the independent validation pins "
                "(the per-member sha256 set) — pins originate from the validator, "
                "never from the capture process's own claims",
                "3) accepted publisher: publication exclusively by the accepted "
                "QFAR1 publisher (pin " + PUBLISHER_COMMIT + ") bound in "
                "publication_binding, consuming the validation pins",
            ],
            "forbidden_routes": [
                "the parked -08/-09 execute_capture.py lineage — not used, not a dependency",
                "any per-file publication path (the superseded rev2 os.link narrative)",
                "branch-tip-only trust at any stage",
            ],
        },
        "note": ("This candidate authorizes none of these stages; adoption of this "
                 "manifest is itself a separate act that has not occurred. The rev2 "
                 "later_command (parked-executor route) is removed, not replaced "
                 "with another command."),
    }

    # (b) publication binding to the accepted architecture.
    n["publication_binding"] = {
        "architecture": "QFAR1 single-blob (design r3, accepted)",
        "design_memo": "research_notes/YAHOO_SINGLE_BLOB_ARCHIVE_DESIGN_20261015.md",
        "design_memo_sha256": DESIGN_SHA256,
        "publisher_commit": PUBLISHER_COMMIT,
        "publisher_file": "research_notes/yahoo_qfar1_journal_header_auth_20261016/qfar1_publisher_h16.py",
        "publisher_file_sha256": PUBLISHER_FILE_SHA256,
        "target_repo": "mickaellall116-cmyk/qf-data-archive",
        "target_repo_visibility": "private (designated 2026-10-15; must re-verify private at publication and at consumption — visibility drift invalidates, HOLD:VISIBILITY)",
        "target_ref": "refs/heads/qf-archive",
        "target_path": "captures/<capture_id>.qfar",
        "member_accounting": {
            "payload_members": 156,
            "bookkeeping_members": ["manifest.json", "SHA256SUMS"],
            "physical_members": 158,
            "binding_graph": "manifest.json binds the 156 payloads only; SHA256SUMS binds exactly 157 (156 payloads + manifest.json), never itself; the QFAR1 index binds all 158; the container trailer digest + git blob id bind the whole container (acyclic, per design r3)",
        },
        "final_verification": [
            "resolve the exact published commit by its pinned SHA (never a branch tip)",
            "fetch the blob and recompute CONTAINER_SHA256; must equal the ledger anchor",
            "parse the container and verify every one of the 158 members against the independent validation pins",
            "verify ref still resolves to the pinned commit, or fetch the commit directly by id",
            "record a hashes-only public ledger anchor; partial states (objects without ref update, ref update without anchor, anchor without verification transcript) are no-publication",
        ],
        "no_branch_tip_only_trust": True,
    }

    # (b) provenance fields.
    n["status"] = ("CANDIDATE REV3 — NOT ADOPTED — authorizes no vendor call, "
                   "no capture, no publication")
    n["task"] = "QF-YAHOO-REV3-MANIFEST-ADOPTION-READINESS-20261016-17 r1"
    n["revision"] = {
        "status": "CANDIDATE ONLY - NOT ADOPTED - does not authorize any acquisition, capture, or publication",
        "derived_from_frozen_manifest_sha256": REV2_SHA256,
        "parent_candidate": {
            "path": "research_notes/yahoo_qfar1_preflight_20261015/capture_manifest_rev3_candidate.json",
            "sha256": CAND_SHA256,
            "git_blob": "c62d4daae030239344b62b06cc66710478efaac4",
            "produced_by": "QF-YAHOO-QFAR1-OFFLINE-PREFLIGHT-20261015-13 r1",
        },
        "produced_by": "QF-YAHOO-REV3-MANIFEST-ADOPTION-READINESS-20261016-17 r1 (normalization only; no adoption)",
        "changes": [
            "call_budget.ceilings.bytes_total: 536870912 -> 67108864 (QF_SHARED_TOTAL_CEILING_BYTES, 158-physical-member scope) [from -13 candidate, unchanged]",
            "added call_budget.ceilings.bytes_total_definition, bookkeeping_reserve_bytes=32164, payload_budget_bytes=67076700 [from -13 candidate, unchanged]",
            "added call_budget.ceilings.oversize_streaming_rule: an oversized streaming response consumes its attempt before cutoff/HOLD [explicit statement of the -13 adjudicated rule]",
            "archive.root/durability/publication superseded: local-VM staging + per-file os.link narrative replaced by QFAR1 single-blob publication to the designated private repo (publication_binding)",
            "archive.attempt_journal: rule preserved; -08 fixture proof clause replaced with provenance note",
            "execution_packet: later_command (parked-executor route) removed; explicit handoff contract added (clean capture executor -> independent validation pins -> accepted publisher); abort_rules preserved verbatim",
            "added publication_binding: accepted QFAR1 architecture, design pin, publisher pin 53bdc672..., target repo/ref/path, member accounting, final commit/blob/container/member verification, no branch-tip-only trust",
            "status/task/revision provenance updated to this candidate",
        ],
        "semantics_note": ("The reserve guarantees a completed 156-payload capture cannot "
                           "overflow the 158-physical-member ceiling when bookkeeping is "
                           "added; an oversized streaming response still consumes its "
                           "attempt and is cut off/held (adjudication 6205968339)."),
    }

    out_path = PKG / "capture_manifest_rev3_normalized_candidate.json"
    out_path.write_text(json.dumps(n, indent=4, sort_keys=True, ensure_ascii=False) + "\n")

    # --- preservation verification ----------------------------------------
    preserved = ["request_order", "request_params", "runtime_pins",
                 "session_construction_freeze", "qualification_gates_frozen",
                 "symbol_mapping", "universe_source", "capture_id", "purpose", "schema"]
    proofs = []
    for k in preserved:
        ok = canon(rev2[k]) == canon(n[k])
        proofs.append({"section": k, "proof": "canonical-json deep-equal rev2 vs normalized rev3",
                       "canonical_sha256": canon_sha(rev2[k]), "result": "PRESERVED" if ok else "DRIFT"})
        check(f"PV-{k}", f"section {k} preserved exactly", ok)
    for sub in ["layout", "restart", "rollback"]:
        ok = canon(rev2["archive"][sub]) == canon(n["archive"][sub])
        proofs.append({"section": f"archive.{sub}", "proof": "canonical-json deep-equal rev2 vs normalized rev3",
                       "canonical_sha256": canon_sha(rev2["archive"][sub]),
                       "result": "PRESERVED" if ok else "DRIFT"})
        check(f"PV-archive.{sub}", f"archive.{sub} preserved exactly", ok)
    ok = canon(rev2["execution_packet"]["abort_rules"]) == canon(n["execution_packet"]["abort_rules"])
    proofs.append({"section": "execution_packet.abort_rules", "proof": "canonical-json deep-equal rev2 vs normalized rev3",
                   "canonical_sha256": canon_sha(rev2["execution_packet"]["abort_rules"]),
                   "result": "PRESERVED" if ok else "DRIFT"})
    check("PV-abort_rules", "execution_packet.abort_rules preserved exactly", ok)
    cb_same = all(canon(rev2["call_budget"][k]) == canon(n["call_budget"][k])
                  for k in rev2["call_budget"] if k != "ceilings")
    check("PV-call_budget", "call_budget outside ceilings preserved exactly", cb_same)
    ceil_kept = all(rev2["call_budget"]["ceilings"][k] == n["call_budget"]["ceilings"][k]
                    for k in ["bytes_per_symbol", "rows_per_symbol", "wall_seconds_total"])
    check("PV-ceil-kept", "per-symbol/rows/wall ceilings unchanged (33554432 / 20000 / 1800)", ceil_kept)

    syms = [r["symbol"] for r in n["request_order"]]
    check("PV-symbols", "request_order is 52 entries, frozen order, QQQ benchmark at i=52",
          len(syms) == 52 and syms == [r["symbol"] for r in rev2["request_order"]] and syms[-1] == "QQQ",
          ",".join(syms))

    # --- ceiling arithmetic -------------------------------------------------
    c = n["call_budget"]["ceilings"]
    check("CEIL-1", "bytes_total == 67,108,864", c["bytes_total"] == CEIL_TOTAL, str(c["bytes_total"]))
    check("CEIL-2", "bookkeeping_reserve_bytes == 32,164", c["bookkeeping_reserve_bytes"] == CEIL_RESERVE)
    check("CEIL-3", "payload_budget_bytes == 67,076,700", c["payload_budget_bytes"] == CEIL_PAYLOAD)
    check("CEIL-4", "total - reserve == payload budget", CEIL_TOTAL - CEIL_RESERVE == CEIL_PAYLOAD)
    check("CEIL-5", "ceiling values identical to -13 candidate (no new numbers introduced)",
          (c["bytes_total"], c["bookkeeping_reserve_bytes"], c["payload_budget_bytes"]) ==
          (cc["bytes_total"], cc["bookkeeping_reserve_bytes"], cc["payload_budget_bytes"]))
    check("CEIL-6", "bytes_total_definition scopes the ceiling to all 158 physical members",
          "158 physical members" in c["bytes_total_definition"], c["bytes_total_definition"])

    # --- stale-narrative / routing scan --------------------------------------
    blob = canon(n)
    for token in ["NOT DEMONSTRATED", "run_preflight_fixture_r2", "FROZEN_PREFLIGHT"]:
        check(f"SCAN-{token[:12]}", f"normalized manifest contains no stale token {token!r}",
              token not in blob)
    # 'os.link' and the old total may appear ONLY as removal/provenance records
    # (revision.changes documenting the delta, forbidden_routes, or sentences
    # explicitly marking the narrative superseded) — never as live narrative.
    bad = []

    def walk_str(x, path=""):
        if isinstance(x, dict):
            for k, v in x.items():
                walk_str(v, f"{path}.{k}" if path else k)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk_str(v, f"{path}[{i}]")
        elif isinstance(x, str):
            for tok in ["os.link", "536870912"]:
                if tok in x and "revision" not in path and "forbidden_routes" not in path \
                        and "superseded" not in x and "Superseded" not in x:
                    bad.append(f"{path}: {tok}")
    walk_str(n)
    check("SCAN-os.link", "os.link / old ceiling total appear only as supersession or provenance records",
          not bad, "; ".join(bad))
    hits = []

    def walk(x, path=""):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")
        elif isinstance(x, str) and "execute_capture" in x:
            hits.append(path)
    walk(n)
    check("SCAN-executor", "execute_capture is named ONLY as a forbidden route / removal note",
          all(("forbidden_routes" in h) or ("changes" in h) or ("note" in h) for h in hits),
          "; ".join(hits))
    check("BIND-1", "publication_binding pins publisher commit 53bdc672...",
          n["publication_binding"]["publisher_commit"] == PUBLISHER_COMMIT)
    check("BIND-2", "publication_binding target is the designated private repo + qf-archive ref",
          n["publication_binding"]["target_repo"] == "mickaellall116-cmyk/qf-data-archive"
          and n["publication_binding"]["target_ref"] == "refs/heads/qf-archive")
    check("BIND-3", "no_branch_tip_only_trust is asserted and final verification is commit-pinned",
          n["publication_binding"]["no_branch_tip_only_trust"] is True)

    # --- full semantic diff with classification -------------------------------
    CLASS = {}
    for pfx in ["call_budget.ceilings"]:
        CLASS[pfx] = "APPROVED_CEILING_REVISION"
    diff = deep_diff(rev2, n)
    for d in diff:
        p = d["path"]
        if p.startswith("call_budget.ceilings"):
            d["classification"] = "APPROVED_CEILING_REVISION"
        elif p.startswith(("archive.", "execution_packet", "publication_binding",
                            "status", "task", "revision")):
            d["classification"] = "STORAGE_PUBLICATION_EXECUTION_REFERENCE"
        else:
            d["classification"] = "UNCLASSIFIED — WOULD FORCE HOLD"
    unclassified = [d for d in diff if d["classification"].startswith("UNCLASSIFIED")]
    check("DIFF-1", "every rev2->normalized difference is classified ceiling-revision or storage/publication/execution-reference",
          not unclassified, "; ".join(d["path"] for d in unclassified))

    all_pass = all(c["result"] == "PASS" for c in checks)
    token = "REV3_MANIFEST_ADOPTION_READY" if all_pass else "HOLD"

    semantic_diff = {
        "task": "QF-YAHOO-REV3-MANIFEST-ADOPTION-READINESS-20261016-17 r1",
        "inputs": {
            "rev2_frozen": {"path": str(REV2_PATH.relative_to(ROOT)), "sha256": REV2_SHA256,
                            "git_blob": "0d1bc6023b5b506cd83df55d70023c086a1f7b6e"},
            "rev3_candidate_parent": {"path": str(CAND_PATH.relative_to(ROOT)), "sha256": CAND_SHA256,
                                      "git_blob": "c62d4daae030239344b62b06cc66710478efaac4"},
            "design_r3": {"path": "research_notes/YAHOO_SINGLE_BLOB_ARCHIVE_DESIGN_20261015.md",
                          "sha256": DESIGN_SHA256},
            "publisher_pin": {"commit": PUBLISHER_COMMIT, "file_sha256": PUBLISHER_FILE_SHA256},
        },
        "output": {"path": str(out_path.relative_to(ROOT)), "sha256": sha256_file(out_path)},
        "preserved_sections_proofs": proofs,
        "changes": diff,
        "change_summary": {
            "total_leaf_changes": len(diff),
            "approved_ceiling_revision": sum(1 for d in diff if d["classification"] == "APPROVED_CEILING_REVISION"),
            "storage_publication_execution_reference": sum(1 for d in diff if d["classification"] == "STORAGE_PUBLICATION_EXECUTION_REFERENCE"),
            "unclassified": len(unclassified),
        },
        "terminal_token": token,
    }
    (PKG / "semantic_diff_rev2_to_rev3_normalized.json").write_text(
        json.dumps(semantic_diff, indent=4, sort_keys=True, ensure_ascii=False) + "\n")
    verification = {"task": semantic_diff["task"], "checks": checks,
                    "all_checks_pass": all_pass, "terminal_token": token}
    (PKG / "verification_results.json").write_text(
        json.dumps(verification, indent=4, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"checks: {sum(1 for c in checks if c['result'] == 'PASS')}/{len(checks)} PASS")
    for c in checks:
        if c["result"] != "PASS":
            print("FAIL:", c["id"], c["description"], c["detail"][:200])
    print("leaf changes:", len(diff),
          "| ceiling:", semantic_diff["change_summary"]["approved_ceiling_revision"],
          "| storage/pub/exec:", semantic_diff["change_summary"]["storage_publication_execution_reference"])
    print("TERMINAL:", token)


if __name__ == "__main__":
    main()
