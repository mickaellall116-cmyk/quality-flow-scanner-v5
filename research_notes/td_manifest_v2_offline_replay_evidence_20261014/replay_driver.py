#!/usr/bin/env python3
"""QF-TD-MANIFEST-V2-OFFLINE-REPLAY-20261014-11 r1 — validation-only replay.

Drives the PINNED collector (sha256 bd003c3c...) unmodified against the
preserved -09 r2 rejected receipt under Manifest V2, in a disposable
state dir, with a local stub transport that returns the preserved bytes.
No vendor transport is constructed. Run under `unshare -n` (no network
namespace interfaces) AND with an in-process socket guard that records
and blocks any connect attempt (defense in depth).
Outputs counts/timestamps/classifications only — never bar data.
"""
import copy
import hashlib
import importlib.util
import json
import socket
import sys
from pathlib import Path

# --- in-process network guard: record + block any connect attempt ------
CONNECT_ATTEMPTS = []


class GuardedSocket(socket.socket):
    def connect(self, address):
        CONNECT_ATTEMPTS.append(("connect", repr(address)))
        raise RuntimeError("network blocked in offline replay (socket guard)")

    def connect_ex(self, address):
        CONNECT_ATTEMPTS.append(("connect_ex", repr(address)))
        raise RuntimeError("network blocked in offline replay (socket guard)")


socket.socket = GuardedSocket


def _blocked_create_connection(*a, **k):
    CONNECT_ATTEMPTS.append(("create_connection", repr(a)))
    raise RuntimeError("network blocked in offline replay (socket guard)")


socket.create_connection = _blocked_create_connection

# --- pinned collector, loaded from the git-archive candidate export ----
EXPORT = Path("/tmp/tdv2/export")
COL_PATH = EXPORT / "research_notes/td_lifecycle_repair_candidate/td_min_collector.py"
COL_SHA = hashlib.sha256(COL_PATH.read_bytes()).hexdigest()
assert COL_SHA == "bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b", COL_SHA
spec = importlib.util.spec_from_file_location("td_min_collector", COL_PATH)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

# --- inputs -------------------------------------------------------------
REPO = Path("/home/hatch/workspace/quality-flow-scanner-v5")
V2_PATH = REPO / "research_notes/td_acquisition_adapter_preflight_evidence_20261013/acquisition_manifest_v2.json"
RECEIPT_PATH = REPO / "research_notes/twelve_data_stage0/snapshots/acquisition_state/receipts/REQ-P1H-01.rejected.bin"
body = RECEIPT_PATH.read_bytes()
RECEIPT_SHA = hashlib.sha256(body).hexdigest()
assert RECEIPT_SHA == "c47bf899422e4585bcd37055c0e9788c96697b6b47482133e4675bf5cb8dbc18", RECEIPT_SHA

payload = json.loads(body)
values = payload["values"]
bar_facts = {
    "values_count": len(values),
    "first_bar_datetime": values[0]["datetime"],
    "last_bar_datetime": values[-1]["datetime"],
    "meta": {k: payload["meta"].get(k) for k in ("symbol", "interval", "currency", "exchange", "mic_code", "exchange_timezone", "type")},
}

v2 = json.loads(V2_PATH.read_text())
assert c.validate_manifest(v2) == []
single = copy.deepcopy(v2)
single["requests"] = [r for r in v2["requests"] if r["request_id"] == "REQ-P1H-01"]
req = single["requests"][0]

# --- disposable state ----------------------------------------------------
STATE = Path("/tmp/tdv2/replay_state")
LEDGER = Path("/tmp/tdv2/replay_ledger.json")
for p in (STATE, LEDGER, Path(str(LEDGER) + ".lock")):
    if p.is_dir():
        import shutil
        shutil.rmtree(p)
    elif p.exists():
        p.unlink()

calls = []


def replay_transport(r):
    """Local stub: returns the preserved receipt bytes. No I/O, no network."""
    calls.append(r["request_id"])
    return (200, body)


limiter = c.RollingCreditLimiter(8, 800, state_path=LEDGER)
col = c.Collector(STATE, single, limiter, transport=replay_transport,
                  semantics_status="INSUFFICIENT",
                  prereq_path=EXPORT / "research_notes/td_minimal_collector/prerequisites.json")
summary = col.run()

# --- cross-check: durable receipt revalidation under V2 ------------------
limiter2 = c.RollingCreditLimiter(8, 800, state_path=LEDGER)
col2 = c.Collector(STATE, single, limiter2, transport=replay_transport,
                   semantics_status="INSUFFICIENT",
                   prereq_path=EXPORT / "research_notes/td_minimal_collector/prerequisites.json")
receipt_file = STATE / "receipts" / req["output_name"]
reverify = None
if receipt_file.exists():
    ok, why = col2._verify_receipt(req, receipt_file)
    reverify = {"ok": ok, "why": why,
                "receipt_sha256": hashlib.sha256(receipt_file.read_bytes()).hexdigest(),
                "receipt_byte_identical_to_preserved": receipt_file.read_bytes() == body}

events = [json.loads(l) for l in (STATE / "lifecycle.jsonl").read_text().splitlines() if l.strip()] \
    if (STATE / "lifecycle.jsonl").exists() else []
pilot_state = json.loads((STATE / "pilot_state.json").read_text()) \
    if (STATE / "pilot_state.json").exists() else None

result = {
    "collector_pin_sha256": COL_SHA,
    "receipt_sha256_verified": RECEIPT_SHA,
    "v2_manifest_sha256": hashlib.sha256(V2_PATH.read_bytes()).hexdigest(),
    "replay_manifest": "V2 reduced to the single request REQ-P1H-01 (same single-request reduction the -09 live screen used); canonical digest in lifecycle events",
    "venue_identity_under_test": req["venue_identity"],
    "bar_facts_counts_and_timestamps_only": bar_facts,
    "transport_calls": calls,
    "run_summary": summary,
    "pilot_state_terminal": pilot_state,
    "lifecycle_events": events,
    "receipt_revalidation_under_v2": reverify,
    "socket_connect_attempts": CONNECT_ATTEMPTS,
}
print(json.dumps(result, indent=1))
