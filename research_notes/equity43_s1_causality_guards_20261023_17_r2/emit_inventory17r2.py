"""QF-EQUITY43-S1-CAUSALITY-GUARDS-20261023-17 r2 — structured pin
inventory emitter.

Governing text: Issue #1 comment 6380534722. The -17 r1 comparison
artifact recorded its pin evidence as one free-form string,
"PASS (ref P0/P1 as -15)", and report17.py accepted any string
starting with "PASS". This emitter replaces that label with a
STRUCTURED exact pin inventory in a successor artifact:

  * the base artifact is the COMMITTED r1 artifact (read from
    origin/main, research_notes/equity43_s1_causality_guards_
    20261023_17/compare17_fork17.json) — every section except
    `inventory` is carried byte-identical; NO decision content is
    regenerated and no comparison is re-run;
  * the pin VALUES are recomputed here, from the same committed
    stage sources the r1 run used, by re-running phase0()/phase1()
    of the pinned -13 reference driver in the r1 stage harness
    (~/workspace/qf_td17_stage/harness) — file pins, archive
    SHA256SUMS verification, PAUSED production pins, receipt-chain
    re-walk, manifest roots, pilot receipts — plus the sector-map
    hash recomputed exactly as decision_compare17.py computes it,
    and the fork observer module hash taken from the committed
    package blob. Nothing is transcribed from the r1 text.

Exit 0 iff every recomputation matches the frozen expected values
(the reference driver records any mismatch in ref.failures).
"""
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

R1_STAGE = os.path.expanduser("~/workspace/qf_td17_stage")
HARNESS = os.path.join(R1_STAGE, "harness")
REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "compare17r2_fork17.json")
PKG_REL = "research_notes/equity43_s1_causality_guards_20261023_17"


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def git_show(rel):
    return subprocess.run(["git", "-C", REPO, "show",
                           f"origin/main:{rel}"],
                          capture_output=True, check=True).stdout


def main():
    # ---- base artifact: the committed r1 JSON, from origin/main
    base_raw = git_show(f"{PKG_REL}/compare17_fork17.json")
    base = json.loads(base_raw)
    assert base["sections"]["inventory"] == \
        {"pins": "PASS (ref P0/P1 as -15)"}, base["sections"]["inventory"]

    # ---- re-run the pinned P0/P1 verification (r1 stage harness)
    spec = importlib.util.spec_from_file_location(
        "ref13drv", os.path.join(HARNESS, "reference_run_study13.py"))
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)
    child_manifest = json.load(open(os.path.join(HARNESS,
                                                 "child_manifest.json")))
    ref.phase0()
    ref.phase1(child_manifest)
    if ref.failures:
        print("P0/P1 RE-VERIFICATION FAILED:", ref.failures)
        return 2
    p0 = ref.report["phases"]["P0_pins"]
    p1 = ref.report["phases"]["P1_chains"]

    # ---- sector map hash, recomputed as decision_compare17.py does
    from pine_exposure import SECTOR  # engine path inserted by ref drv
    symbols43 = ref.PILOT + [l["symbol"] for l in child_manifest["legs"]
                             if l["window"] == "W_DEV"]
    assert len(symbols43) == 43 and len(set(symbols43)) == 43
    sector_sha = sha256_bytes(json.dumps(
        {s: SECTOR[s] for s in symbols43}, sort_keys=True).encode())
    assert sector_sha == base["sections"]["config_pins"][
        "sector_map_sha256"], sector_sha

    # ---- fork observer module hash: committed package blob, and the
    # two stage copies must agree with it byte-for-byte
    obs_blob_sha = sha256_bytes(git_show(f"{PKG_REL}/fwd_observer17.py"))
    for p in (os.path.join(R1_STAGE, "work", "fwd_observer17.py"),
              os.path.join(R1_STAGE, "pkg17", "observer",
                           "fwd_observer.py")):
        with open(p, "rb") as f:
            assert sha256_bytes(f.read()) == obs_blob_sha, p

    pins = {
        "observer_module": base["observer_module"],
        "observer_module_sha256": obs_blob_sha,
        "source_pins": dict(p0["pins"]),
        "experiment_config_sha256": p0["experiment_config_sha256"],
        "sector_map_sha256": sector_sha,
        "child_manifest_root_sha256": p1["child_root_recomputed"],
        "parent_manifest_root_sha256": p1["parent_root_recomputed"],
        "pilot_manifest_root_sha256": ref.PILOT_ROOT,
        "child_chain_receipts_verified":
            p1["child_chain_receipts_verified"],
        "child_chain_head": p1["child_chain_head"],
        "legs_without_receipt_quarantined":
            p1["legs_without_receipt_quarantined"],
        "pilot_receipts": {
            s: {"response_sha256": v["response_sha256"],
                "rows": v["rows"]}
            for s, v in p1["pilot_receipts"].items()},
        "archive_continue11_files": p0["archive_continue11_files"],
        "archive_continue11_mismatches":
            p0["archive_continue11_mismatches"],
        "archive_pilot_files": p0["archive_pilot_files"],
        "archive_pilot_mismatches": p0["archive_pilot_mismatches"],
        "paused_harness_sha256":
            p0["paused_production_before"]["harness_sha256"],
        "pause_new_entries_present":
            p0["paused_production_before"]["pause_new_entries_present"],
        "resume_new_entries_present":
            p0["paused_production_before"]["resume_new_entries_present"],
    }
    # pilot receipt ok-flags were enforced by phase1 via ref.failures;
    # assert them explicitly as well
    assert all(v["ok"] for v in p1["pilot_receipts"].values())
    assert p1["child_root_committed"] == p1["child_root_recomputed"]
    assert p1["parent_root_committed"] == p1["parent_root_recomputed"]

    doc = copy.deepcopy(base)
    doc["revision"] = "r2"
    doc["artifact_note"] = (
        "r2 successor artifact (Issue #1 comment 6380534722): identical "
        "to the committed -17 r1 artifact except (a) sections.inventory "
        "replaced by the structured exact pin inventory below, "
        "recomputed by emit_inventory17r2.py re-running the pinned "
        "P0/P1 verification against the same committed stage sources "
        "(no decision content regenerated, no comparison re-run), and "
        "(b) this note and the revision tag added at top level.")
    doc["sections"]["inventory"] = {
        "pin_inventory_version": "structured-v1",
        "pins": pins,
    }
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, default=str)
    print(f"wrote {OUT}")
    print(json.dumps(pins, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
