#!/usr/bin/env python3
"""QF-TD-NLQUAL-STAGE-COMPLETION-REGRESSION-20261020-47 r1 — Family C ONLY.

Runs the NLQUAL 28-case matrix (staged runner, byte-identical to the
-44/-45/-46 staged runner 91cfa59b...) against the frozen candidate pair
(validator candidate ca3bafd8... in the mechanism position; entrypoint
candidate 442e56cc... hash-gated for the record — Family C drives the
collector, not the entrypoint). The stage carries the collector's
COMPLETE import closure: validate_input (candidate), rate_limiter and
verify_sources from the pinned repo harness, PLUS the runtime data
closure verify_directory(ARCHIVAL_DIR, PINNED) resolves relative to the
staged verify_sources.py (the pinned archival sources). The -46 staging
omission (verify_sources.py absent -> ModuleNotFoundError at collector
line 35, 0/28 executed) is the defect this task closes.

Discipline: hash gates BEFORE the run; matrix run twice (mode pristine);
require counts {total: 28, passed: 28} on both runs and byte-identical
outputs; mechanism_module_sha256 recorded in the output must equal the
candidate validator hash. First material failure stops; nothing is
repaired and nothing is rerun.
"""
import hashlib
import json
import pathlib
import subprocess
import sys

STAGE = pathlib.Path("/tmp/td47_stage")
OUTDIR = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("/tmp/td47_out")
REPO = pathlib.Path("/home/hatch/workspace/quality-flow-scanner-v5")

CAND_VAL_SHA = "ca3bafd87e7cb439d538ddf924aa08a029dd2c9bb32b485f61acbeea91429cc6"
CAND_ENT_SHA = "442e56cc16bbbb7ba8f3a62910d92bfcd07d85d0bb88ca2346d26b0bdcd2cba6"

EXPECTED = {
    # staged files
    "stage/run_nlqual_matrix.py": "91cfa59b2677f2205ed471bb2d34f0e47814dc9ccd84bfa0fbdb0cf9c8a262e2",
    "stage/nlqual_supplement.json": "7fe1fd2f7c2217515f364a603e5effa6134550027bd7e95a09b239e04a755bbb",
    "stage/integration_requirements.lock": "08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068",
    "stage/candidate_validator.py": CAND_VAL_SHA,
    "stage/candidate_entrypoint.py": CAND_ENT_SHA,
    "stage/nlqual/td_lifecycle_repair_candidate/td_min_collector.py":
        "b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c",
    "stage/nlqual/td_lifecycle_repair_candidate/p2_spot_supplement_v2.json":
        "cccd52260b2c80a7110559ed100111cf3634e7901daef2f883c6517b68255b31",
    "stage/nlqual/pilot_harness/validate_input.py": CAND_VAL_SHA,
    "stage/nlqual/pilot_harness/rate_limiter.py":
        "06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64",
    "stage/nlqual/pilot_harness/verify_sources.py":
        "a0bd2e4cdce44be5d9fcc1d7c21046391d36c9bd366a959df03bf5d19c9a79e0",
    "stage/nlqual/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/pine_backtest.py":
        "447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5",
    "stage/nlqual/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/scanner_rules.py":
        "7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac",
    # repo inputs consumed by the matrix
    "repo/preserved_body_REQ-SPT-07.rejected.bin":
        "3339c34154648c0ea4ddb9bd553e5274d390f953552518ad957d79704b7d5d50",
    "repo/acquisition_manifest_v2_spot8.json":
        "ddff040fa654303cf4289f4c39c2a5b5af998bd4065ceddd4e4f5d52fcb8c28d",
    # repo pinned originals (must be unchanged; mechanism original NOT staged)
    "repo/pilot_harness/validate_input.py":
        "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58",
    "repo/pilot_harness/verify_sources.py":
        "a0bd2e4cdce44be5d9fcc1d7c21046391d36c9bd366a959df03bf5d19c9a79e0",
    "repo/pilot_harness/rate_limiter.py":
        "06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64",
    "repo/pilot_harness/pilot_build.py":
        "257d5bb99bcbae50442491b71429abb6b37b8c5cbcd1e4bf93b6010ad9e5a508",
    "repo/pilot_harness/construct_4h.py":
        "d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd",
}

PATHS = {
    "stage/run_nlqual_matrix.py": STAGE / "run_nlqual_matrix.py",
    "stage/nlqual_supplement.json": STAGE / "nlqual_supplement.json",
    "stage/integration_requirements.lock": STAGE / "integration_requirements.lock",
    "stage/candidate_validator.py": STAGE / "candidate_validator.py",
    "stage/candidate_entrypoint.py": STAGE / "candidate_entrypoint.py",
    "stage/nlqual/td_lifecycle_repair_candidate/td_min_collector.py":
        STAGE / "nlqual/td_lifecycle_repair_candidate/td_min_collector.py",
    "stage/nlqual/td_lifecycle_repair_candidate/p2_spot_supplement_v2.json":
        STAGE / "nlqual/td_lifecycle_repair_candidate/p2_spot_supplement_v2.json",
    "stage/nlqual/pilot_harness/validate_input.py":
        STAGE / "nlqual/pilot_harness/validate_input.py",
    "stage/nlqual/pilot_harness/rate_limiter.py":
        STAGE / "nlqual/pilot_harness/rate_limiter.py",
    "stage/nlqual/pilot_harness/verify_sources.py":
        STAGE / "nlqual/pilot_harness/verify_sources.py",
    "stage/nlqual/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/pine_backtest.py":
        STAGE / "nlqual/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/pine_backtest.py",
    "stage/nlqual/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/scanner_rules.py":
        STAGE / "nlqual/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/scanner_rules.py",
    "repo/preserved_body_REQ-SPT-07.rejected.bin":
        REPO / "research_notes/twelve_data_stage0/snapshots/acquisition_state_spot8/receipts/REQ-SPT-07.rejected.bin",
    "repo/acquisition_manifest_v2_spot8.json":
        REPO / "research_notes/td_v2_spot_batch_preflight_evidence_20261014/acquisition_manifest_v2_spot8.json",
    "repo/pilot_harness/validate_input.py":
        REPO / "research_notes/pilot_harness/validate_input.py",
    "repo/pilot_harness/verify_sources.py":
        REPO / "research_notes/pilot_harness/verify_sources.py",
    "repo/pilot_harness/rate_limiter.py":
        REPO / "research_notes/pilot_harness/rate_limiter.py",
    "repo/pilot_harness/pilot_build.py":
        REPO / "research_notes/pilot_harness/pilot_build.py",
    "repo/pilot_harness/construct_4h.py":
        REPO / "research_notes/pilot_harness/construct_4h.py",
}

results = {"task": "QF-TD-NLQUAL-STAGE-COMPLETION-REGRESSION-20261020-47 r1",
           "spec": "Issue #1 comment 6284741482",
           "hash_gates": {}, "import_closure": None, "family_c_nlqual": None,
           "first_failure": None, "verdict": None}

WHEELHOUSE_MANIFEST_SHA = "210b8273a15cc7317b4a8029198f8d6e1401c1e375acdbe7f8602167c13e815b"


class ProofFailure(Exception):
    def __init__(self, key, detail):
        self.key = key
        self.detail = detail


def sha256_file(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def fail(key, detail):
    raise ProofFailure(key, detail)


def derive_import_closure():
    """Static (AST) derivation of the local import closure of the staged
    collector + runner + sibling harness modules, per spec point 2.
    Local = a module that must be satisfied by a staged sibling file.
    Also resolves verify_sources.ARCHIVAL_DIR relative to the STAGED
    verify_sources.py and checks its PINNED targets (extracted by AST
    from the staged bytes) exist at that resolved path."""
    import ast
    STDLIB = set(sys.stdlib_module_names)
    ENV = {"numpy", "pandas", "pandas_market_calendars", "exchange_calendars"}
    LOCAL_FILES = {"validate_input": STAGE / "nlqual/pilot_harness/validate_input.py",
                   "rate_limiter": STAGE / "nlqual/pilot_harness/rate_limiter.py",
                   "verify_sources": STAGE / "nlqual/pilot_harness/verify_sources.py"}

    def imports_of(path):
        tree = ast.parse(pathlib.Path(path).read_bytes().decode())
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module.split(".")[0])
        return mods

    members = {
        "td_min_collector.py": STAGE / "nlqual/td_lifecycle_repair_candidate/td_min_collector.py",
        "run_nlqual_matrix.py": STAGE / "run_nlqual_matrix.py",
        "validate_input.py(candidate)": LOCAL_FILES["validate_input"],
        "rate_limiter.py": LOCAL_FILES["rate_limiter"],
        "verify_sources.py": LOCAL_FILES["verify_sources"],
    }
    closure = {"members": {}, "local_imports_required": sorted(LOCAL_FILES),
               "unsatisfied_local": [], "archival_resolution": {}}
    required_local = set()
    for label, path in members.items():
        mods = imports_of(path)
        local = sorted(m for m in mods if m in LOCAL_FILES)
        required_local.update(local)
        closure["members"][label] = {
            "imports_all": sorted(mods),
            "imports_local": local,
            "imports_env": sorted(m for m in mods if m in ENV),
            "imports_stdlib": sorted(m for m in mods if m in STDLIB),
            "imports_other": sorted(m for m in mods
                                    if m not in LOCAL_FILES and m not in ENV
                                    and m not in STDLIB)}
    closure["local_imports_exercised"] = sorted(required_local)
    for m in sorted(required_local):
        if not LOCAL_FILES[m].exists():
            closure["unsatisfied_local"].append(m)
    # archival path resolution from the staged verify_sources.py bytes
    vs = STAGE / "nlqual/pilot_harness/verify_sources.py"
    tree = ast.parse(vs.read_bytes().decode())
    pinned = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PINNED":
            pinned = ast.literal_eval(node.value)
    archival_dir = (vs.resolve().parent.parent / "recovery_4h_20261004"
                    / "cp1_evidence_closure" / "archival_sources_v1")
    closure["archival_resolution"] = {
        "archival_dir_resolved": str(archival_dir),
        "pinned_from_staged_verify_sources": pinned,
        "targets": {name: (archival_dir / name).exists()
                    and sha256_file(archival_dir / name) == expect
                    for name, expect in (pinned or {}).items()}}
    if closure["unsatisfied_local"]:
        fail("STAGE_IMPORT_CLOSURE", closure)
    if not all(closure["archival_resolution"]["targets"].values()):
        fail("STAGE_ARCHIVAL_RESOLUTION", closure["archival_resolution"])
    return closure


def main():
    for name, p in PATHS.items():
        got = sha256_file(p)
        results["hash_gates"][name] = got
        if got != EXPECTED[name]:
            fail(f"HASH_GATE_{name}", {"expected": EXPECTED[name], "actual": got})
    wh = pathlib.Path("/home/hatch/workspace/td_nl_wheelhouse_20261016/SHA256_MANIFEST.txt")
    results["hash_gates"]["wheelhouse/SHA256_MANIFEST.txt"] = sha256_file(wh)
    if results["hash_gates"]["wheelhouse/SHA256_MANIFEST.txt"] != WHEELHOUSE_MANIFEST_SHA:
        fail("HASH_GATE_wheelhouse_manifest",
             {"expected": WHEELHOUSE_MANIFEST_SHA,
              "actual": results["hash_gates"]["wheelhouse/SHA256_MANIFEST.txt"]})
    results["import_closure"] = derive_import_closure()

    import pandas as pd
    import pandas_market_calendars as mcal
    results["environment"] = {"python": sys.version.split()[0],
                              "pandas": pd.__version__,
                              "pandas_market_calendars": mcal.__version__}

    runner = STAGE / "run_nlqual_matrix.py"
    cand_dir = STAGE / "nlqual" / "td_lifecycle_repair_candidate"
    supplement = STAGE / "nlqual_supplement.json"
    preserved = (REPO / "research_notes" / "twelve_data_stage0" / "snapshots"
                 / "acquisition_state_spot8" / "receipts"
                 / "REQ-SPT-07.rejected.bin")
    manifest = (REPO / "research_notes"
                / "td_v2_spot_batch_preflight_evidence_20261014"
                / "acquisition_manifest_v2_spot8.json")
    lock = STAGE / "integration_requirements.lock"
    outs = []
    run_docs = []
    for i in (1, 2):
        out = OUTDIR / f"nlqual_matrix_run{i}.json"
        cmd = [sys.executable, str(runner), "--mode", "pristine",
               "--candidate-dir", str(cand_dir),
               "--supplement", str(supplement),
               "--preserved-body", str(preserved),
               "--manifest", str(manifest),
               "--lock", str(lock), "--out", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            fail("NLQUAL_REGRESSION",
                 {"run": i, "exit": r.returncode,
                  "stdout_tail": r.stdout[-1200:], "stderr_tail": r.stderr[-1200:]})
        outs.append(out.read_bytes())
        run_docs.append(json.loads(outs[-1]))
    checks = {"runs": 2,
              "counts_run1": run_docs[0]["counts"],
              "counts_run2": run_docs[1]["counts"],
              "byte_identical": outs[0] == outs[1],
              "output_sha256_run1": hashlib.sha256(outs[0]).hexdigest(),
              "output_sha256_run2": hashlib.sha256(outs[1]).hexdigest(),
              "mechanism_sha_recorded": run_docs[0]["environment"].get("mechanism_module_sha256"),
              "collector_sha_recorded": run_docs[0]["environment"].get("collector_sha256"),
              "supplement_sha_recorded": run_docs[0]["environment"].get("supplement_candidate_sha256"),
              "lock_sha_recorded": run_docs[0]["environment"].get("lock_sha256"),
              "pmc_version_recorded": run_docs[0]["environment"].get("pandas_market_calendars"),
              "failed_cases": [c["case"] for c in run_docs[0]["cases"] if not c["pass"]]}
    results["family_c_nlqual"] = checks
    if (run_docs[0]["counts"] != {"total": 28, "passed": 28}
            or run_docs[1]["counts"] != {"total": 28, "passed": 28}
            or outs[0] != outs[1]):
        fail("NLQUAL_REGRESSION", checks)
    if checks["mechanism_sha_recorded"] != CAND_VAL_SHA:
        fail("NLQUAL_MECHANISM_BINDING", checks)
    results["verdict"] = "TD_NLQUAL_REGRESSION_PASS__ROUTE_CANDIDATE_AWAITING_REVIEW"


if __name__ == "__main__":
    try:
        main()
    except ProofFailure as pf:
        results["first_failure"] = {"key": pf.key, "detail": pf.detail}
        results["verdict"] = f"TD_NLQUAL_REGRESSION_HOLD__{pf.key}"
    except Exception as e:
        import traceback
        results["first_failure"] = {"key": "UNEXPECTED_ERROR",
                                    "detail": f"{type(e).__name__}: {e}",
                                    "traceback": traceback.format_exc()}
        results["verdict"] = "TD_NLQUAL_REGRESSION_HOLD__UNEXPECTED_ERROR"
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "proof_results.json").write_text(
        json.dumps(results, indent=1, default=str))
    print(results["verdict"])
