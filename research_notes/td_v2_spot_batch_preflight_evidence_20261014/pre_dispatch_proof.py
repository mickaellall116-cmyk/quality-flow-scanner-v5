#!/usr/bin/env python3
"""QF-TD-V2-SPOT-BATCH-PREFLIGHT-20261014-12 r1 — pre-dispatch proof.

Runs entirely against the git-archive export of candidate b18db3c with
a FRESH disposable state + disposable limiter ledgers under /tmp.
No vendor transport exists in the pinned build (TransportDisabled);
the only transports constructed here are (a) none (default disabled)
and (b) a local stub returning a synthetic wrong-venue payload.
Executed under a loopback-only socket guard + git-blocking PATH shim.
"""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

EXPORT = Path("/tmp/td12_export")
EV = EXPORT / "research_notes/td_acquisition_adapter_preflight_evidence_20261013"
WORK = Path("/tmp/td12_state")
if WORK.exists():
    shutil.rmtree(WORK)
WORK.mkdir(parents=True)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(v): return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

proof = {}

# --- pinned collector from the export -----------------------------------
COL_PATH = EXPORT / "research_notes/td_lifecycle_repair_candidate/td_min_collector.py"
assert sha(COL_PATH) == "bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b"
spec = importlib.util.spec_from_file_location("td_min_collector", COL_PATH)
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
proof["collector_pin_sha256"] = sha(COL_PATH)
proof["limiter_pin_sha256"] = sha(EXPORT / "research_notes/pilot_harness/rate_limiter.py")
proof["adapter_pin_sha256"] = sha(EXPORT / "research_notes/td_transport_adapter/td_http_transport_adapter.py")
proof["driver_pin_sha256"] = sha(EXPORT / "research_notes/td_transport_adapter/driver.py")

# --- contract binding (export bytes) -------------------------------------
contract = json.loads((EV / "adapter_contract.json").read_text())
binds = contract["binds"]["manifest"]
bound_path = EXPORT / binds["path"]
proof["contract_binding"] = {
    "path": binds["path"], "manifest_id": binds["manifest_id"],
    "contract_canonical_sha256": binds["canonical_sha256"],
    "bound_file_exists_in_export": bound_path.exists(),
    "bound_file_sha256": sha(bound_path),
    "bound_file_canonical_digest": canon(json.loads(bound_path.read_text())),
    "pin_file_has_v2_line": "4a6e3a55ba6cacf80d60c26870817a272534d62cd73eb09d1dfc889d571c547d" in (EV / "SHA256_MANIFEST.txt").read_text(),
    "pin_file_has_subset_line": "ddff040fa654303cf4289f4c39c2a5b5af998bd4065ceddd4e4f5d52fcb8c28d" in (EV / "SHA256_MANIFEST.txt").read_text(),
}
assert proof["contract_binding"]["bound_file_sha256"] == "4a6e3a55ba6cacf80d60c26870817a272534d62cd73eb09d1dfc889d571c547d"
assert proof["contract_binding"]["bound_file_canonical_digest"] == binds["canonical_sha256"] == "4d5b7a560d9d222d8012cd674fc065de3ef014c2adeb4034e39f8efb99aed646"

# --- subset exactness from export bytes ----------------------------------
v2 = json.loads((EV / "acquisition_manifest_v2.json").read_text())
subset = json.loads((EV / "acquisition_manifest_v2_spot8.json").read_text())
v2map = {r["request_id"]: r for r in v2["requests"]}
per_req = {}
for r in subset["requests"]:
    per_req[r["request_id"]] = {
        "deep_equal_to_v2": r == v2map[r["request_id"]],
        "canonical_digest": canon(r),
        "digest_matches_v2_counterpart": canon(r) == canon(v2map[r["request_id"]]),
    }
proof["subset"] = {
    "file_sha256": sha(EV / "acquisition_manifest_v2_spot8.json"),
    "canonical_digest": canon(subset),
    "requests": len(subset["requests"]),
    "ids_in_v2_order": [r["request_id"] for r in subset["requests"]] ==
                       [r["request_id"] for r in v2["requests"] if r["leg"] == "SPOT"],
    "all_deep_equal_and_digest_equal": all(p["deep_equal_to_v2"] and p["digest_matches_v2_counterpart"] for p in per_req.values()),
    "per_request": per_req,
    "budget": subset["budget"],
    "sum_credit_weight": sum(r["credit_weight"] for r in subset["requests"]),
    "sum_expected_credits": sum(r["expected_credits"] for r in subset["requests"]),
    "max_attempts_all_1": all(r["max_attempts"] == 1 for r in subset["requests"]),
    "validate_manifest_errors": c.validate_manifest(subset),
    "validate_manifest_errors_v2_full": c.validate_manifest(v2),
}

# --- driver default-path load (export) ------------------------------------
DRV_PATH = EXPORT / "research_notes/td_transport_adapter/driver.py"
dspec = importlib.util.spec_from_file_location("td_driver", DRV_PATH)
drv = importlib.util.module_from_spec(dspec); dspec.loader.exec_module(drv)
col_mod = drv.load_collector_module()
proof["driver_default_path"] = {
    "collector_path_resolved": str(drv.COLLECTOR_PATH),
    "collector_path_inside_export": str(drv.COLLECTOR_PATH).startswith(str(EXPORT)),
    "collector_sha256_verified_by_loader": sha(drv.COLLECTOR_PATH) == drv.COLLECTOR_SHA256,
    "module_loaded": col_mod is not None,
}

PREREQ = EXPORT / "research_notes/td_minimal_collector/prerequisites.json"

# --- A: fail-closed run, fresh state, default (disabled) transport -------
stateA = WORK / "state_a"; ledgerA = WORK / "ledger_a.json"
limA = c.RollingCreditLimiter(8, 800, state_path=ledgerA)
colA = c.Collector(stateA, subset, limA, semantics_status="INSUFFICIENT", prereq_path=PREREQ)
digestA = colA.manifest_digest
try:
    summaryA = colA.run()
except Exception as e:
    summaryA = {"exception": type(e).__name__ + ": " + str(e)[:200]}
pilotA = json.loads((stateA / "pilot_state.json").read_text()) if (stateA / "pilot_state.json").exists() else None
proof["fresh_state_fail_closed_run"] = {
    "state_dir_fresh": stateA.exists() and str(stateA).startswith(str(WORK)),
    "state_files": sorted(p.name for p in stateA.rglob("*") if p.is_file()) if stateA.exists() else [],
    "manifest_digest_bound": digestA,
    "manifest_digest_is_subset_canonical": digestA == proof["subset"]["canonical_digest"],
    "run_summary": summaryA,
    "pilot_state_terminal": pilotA,
    "disposable_ledger_after": json.loads(ledgerA.read_text()) if ledgerA.exists() else None,
}

# --- B: shared limiter ceiling on a disposable ledger --------------------
ledgerB = WORK / "ledger_b.json"
limB = c.RollingCreditLimiter(8, 800, state_path=ledgerB)
acq = [limB.try_acquire(1, f"REQ-SPT-0{i}") for i in range(1, 9)]
ninth = limB.try_acquire(1, "REQ-SPT-09-WOULD-BE-EXTRA")
proof["limiter_ceiling_disposable"] = {
    "eight_acquisitions": acq, "ninth_within_minute_refused": ninth is False,
    "ledger_b_after": json.loads(ledgerB.read_text()),
}

# --- C: venue fail-closed spot check (single-request reduction, stub) ----
single = json.loads(json.dumps(subset))
single["requests"] = [r for r in subset["requests"] if r["request_id"] == "REQ-SPT-01"]
req1 = single["requests"][0]
bad_payload = {"meta": {"symbol": "AAPL", "interval": "1h", "currency": "USD",
                        "exchange": "NASDAQ", "mic_code": "XNYS",
                        "exchange_timezone": "America/New_York", "type": "Common Stock"},
               "values": [], "status": "ok"}
def stub_bad_venue(r):
    return (200, json.dumps(bad_payload).encode())
stateC = WORK / "state_c"; ledgerC = WORK / "ledger_c.json"
limC = c.RollingCreditLimiter(8, 800, state_path=ledgerC)
colC = c.Collector(stateC, single, limC, transport=stub_bad_venue,
                   semantics_status="INSUFFICIENT", prereq_path=PREREQ)
try:
    summaryC = colC.run()
except Exception as e:
    summaryC = {"exception": type(e).__name__ + ": " + str(e)[:200]}
pilotC = json.loads((stateC / "pilot_state.json").read_text()) if (stateC / "pilot_state.json").exists() else None
proof["venue_fail_closed_spot_check"] = {
    "request": "REQ-SPT-01 with synthetic meta mic_code XNYS (pin XNGS)",
    "run_summary": summaryC, "pilot_state_terminal": pilotC,
}

print(json.dumps(proof, indent=1))
