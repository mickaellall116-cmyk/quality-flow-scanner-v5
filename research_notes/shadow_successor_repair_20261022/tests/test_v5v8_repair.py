#!/usr/bin/env python3
"""Focused repair tests for the two decisive parity failures.

V5 — market-frame fast-exit, exercised on the REAL LiveAdapter
path with the SAME stub-spy method the independent verification
(shadow_parity_verify_20261022/verify_all.py, check V5) used to
fail the 798de18 successor: fake v54_engine / hybrid_exit_test /
v54_universe_x2 modules injected into sys.modules, a scan
counter on v54_scan_symbols, market download stubbed to raise /
return None / return empty. The successor scored scan_calls=1,
symbols_scanned=250 under both failure modes; required 0. A
positive control (market OK) proves the spy can see a scan when
one happens, so a 0 is evidence, not a vacuous stub.

V8 — hash-chained provenance end to end: every record carries
prev_hash + hash; the chain verifies externally
(core.verify_chain); an externally recorded anchor
(core.check_anchor) detects suffix truncation; field tampering,
record deletion, and mid-log corruption all refuse fail-closed
at startup with NO bytes altered; a torn FINAL line still
recovers exactly as the v1 design specified.

Offline, synthetic, stdlib only. Run: python3 -B test_v5v8_repair.py
Exit 0 iff every case passes.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import types
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

import shadow_signal_core as core  # noqa: E402
import shadow_signal_runner as runner  # noqa: E402

ET = ZoneInfo("America/New_York")
T0 = datetime(2026, 10, 22, 13, 30, tzinfo=ET)
NOW = datetime(2026, 10, 22, 17, 0, tzinfo=ET)
HEALTHY = {"market_ok": True, "scan_complete": True,
           "degraded_symbols": []}

RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'} {name}"
          + (f" — {detail}" if detail and not cond else ""))


# ---------------- V5: the verification's own spy method ----------------

FAKE_SYMS = [f"S{i:03d}" for i in range(250)]


def spy_run(mode):
    """Verbatim method of verify_all.py V5, extended with the
    'empty' failure mode and a market-ok positive control."""
    scan = {"calls": 0, "symbols": 0}
    fake_eng = types.ModuleType("v54_engine")
    fake_m53 = types.ModuleType("m53")

    def dl(sym, interval, period):
        if mode == "raise":
            raise RuntimeError("provider down")
        if mode == "none":
            return None
        if mode == "empty":
            return []
        return [{"close": 1.0}]  # market-ok control frame

    fake_m53.download_data = dl
    fake_m53.MARKET_SYMBOL = "SPY"
    fake_eng.m53 = fake_m53

    def scan_symbols(universe, themes, interval, period):
        scan["calls"] += 1
        scan["symbols"] = len(universe)
        return ([{"symbol": s, "state": "OK"} for s in universe], {})

    fake_eng.v54_scan_symbols = scan_symbols
    fake_eng.v54_qualified_signals = lambda rows: []
    fake_hx = types.ModuleType("hybrid_exit_test")
    fake_hx.UNIVERSE_X = FAKE_SYMS[:51]
    fake_x2 = types.ModuleType("v54_universe_x2")
    fake_x2.UNIVERSE_X2 = FAKE_SYMS[51:]
    saved = {k: sys.modules.get(k) for k in
             ("v54_engine", "hybrid_exit_test", "v54_universe_x2")}
    sys.modules.update({"v54_engine": fake_eng,
                        "hybrid_exit_test": fake_hx,
                        "v54_universe_x2": fake_x2})
    try:
        adapter = runner.LiveAdapter(".")
        cands, health = adapter.fetch()
        return {"scan_calls": scan["calls"],
                "symbols_scanned": scan["symbols"],
                "market_ok_reported": health["market_ok"],
                "scan_complete_reported": health["scan_complete"],
                "candidates": len(cands)}
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


r_raise = spy_run("raise")
case("V5_raise_scan_calls_zero", r_raise["scan_calls"] == 0,
     str(r_raise))
case("V5_raise_symbols_scanned_zero", r_raise["symbols_scanned"] == 0,
     str(r_raise))
case("V5_raise_market_not_ok_no_candidates",
     r_raise["market_ok_reported"] is False
     and r_raise["candidates"] == 0
     and r_raise["scan_complete_reported"] is False, str(r_raise))

r_none = spy_run("none")
case("V5_none_scan_calls_zero", r_none["scan_calls"] == 0, str(r_none))
case("V5_none_symbols_scanned_zero", r_none["symbols_scanned"] == 0,
     str(r_none))

r_empty = spy_run("empty")
case("V5_empty_scan_calls_zero", r_empty["scan_calls"] == 0,
     str(r_empty))

r_ok = spy_run("ok")
case("V5_control_market_ok_scans_once_250",
     r_ok["scan_calls"] == 1 and r_ok["symbols_scanned"] == 250
     and r_ok["market_ok_reported"] is True, str(r_ok))


# ---------------- V8: hash-chained provenance ----------------

def sigrow(sym="NVDA", close="2026-10-22T16:00:00-04:00",
           start="2026-10-22T13:30:00-04:00"):
    return {"signal_id": f"v54:{sym}:4h:{close}:2026-09-15-v54",
            "symbol": sym, "v54_grade": "B",
            "signal_bar_start_at": start, "signal_bar_close_at": close,
            "stop": 1.0, "tp1": 2.0, "market_gate": "CAUTION"}


def read_records(root):
    path = os.path.join(root, core.LOG_FILENAME)
    with open(path, "rb") as fh:
        raw = fh.read()
    lines = raw.decode("utf-8").splitlines()
    return raw, [json.loads(l) for l in lines if l.strip()]


tmp = tempfile.mkdtemp(prefix="v8_")
root = os.path.join(tmp, "shadow")
obs = core.SignalObserver(root, T0, clock=lambda: NOW)
obs.run_cycle([sigrow()], HEALTHY, now=NOW)
obs.run_cycle([], {"market_ok": False, "scan_complete": True,
                   "degraded_symbols": []}, now=NOW)
obs.run_cycle([sigrow("MSFT")], HEALTHY, now=NOW)

raw, recs = read_records(root)
case("V8_every_record_chained",
     len(recs) >= 4 and all(
         r.get("prev_hash") and r.get("hash") for r in recs),
     f"{len(recs)} records")
case("V8_first_prev_is_genesis",
     recs[0]["prev_hash"] == obs.chain_anchor["genesis"])
case("V8_linkage_exact",
     all(recs[i]["prev_hash"] == recs[i - 1]["hash"]
         for i in range(1, len(recs))))

manifest_path = os.path.join(root, core.MANIFEST_FILENAME)
log_path = os.path.join(root, core.LOG_FILENAME)
report = core.verify_chain(log_path, manifest_path)
case("V8_external_verify_ok", report["ok"]
     and report["records"] == len(recs), str(report))
anchor = {"genesis": report["genesis"], "records": report["records"],
          "tail_hash": report["tail_hash"]}
case("V8_anchor_matches_live_observer",
     core.check_anchor(report, dict(obs.chain_anchor)))

# Tamper 1: edit a field inside a middle record.
tampered = list(recs)
mid = dict(tampered[1])
mid["status"] = "HEALTHY" if mid.get("status") != "HEALTHY" else "X"
tampered[1] = mid
troot = os.path.join(tmp, "tampered")
os.makedirs(troot)
with open(os.path.join(troot, core.MANIFEST_FILENAME), "wb") as fh:
    fh.write(open(manifest_path, "rb").read())
with open(os.path.join(troot, core.LOG_FILENAME), "w") as fh:
    for r in tampered:
        fh.write(json.dumps(r, default=str) + "\n")
rep_t = core.verify_chain(os.path.join(troot, core.LOG_FILENAME),
                          os.path.join(troot, core.MANIFEST_FILENAME))
case("V8_field_tamper_detected", not rep_t["ok"], str(rep_t))
before = open(os.path.join(troot, core.LOG_FILENAME), "rb").read()
refused = False
try:
    core.SignalObserver(troot, T0, clock=lambda: NOW)
except core.ShadowError:
    refused = True
case("V8_field_tamper_startup_refuses_bytes_unchanged",
     refused and open(os.path.join(troot, core.LOG_FILENAME),
                      "rb").read() == before)

# Tamper 2: delete a middle record (chain break).
deleted = recs[:1] + recs[2:]
droot = os.path.join(tmp, "deleted")
os.makedirs(droot)
with open(os.path.join(droot, core.MANIFEST_FILENAME), "wb") as fh:
    fh.write(open(manifest_path, "rb").read())
with open(os.path.join(droot, core.LOG_FILENAME), "w") as fh:
    for r in deleted:
        fh.write(json.dumps(r, default=str) + "\n")
rep_d = core.verify_chain(os.path.join(droot, core.LOG_FILENAME),
                          os.path.join(droot, core.MANIFEST_FILENAME))
case("V8_record_deletion_detected", not rep_d["ok"], str(rep_d))

# Tamper 3: suffix truncation — the chain alone stays consistent;
# the EXTERNAL ANCHOR is the control.
sroot = os.path.join(tmp, "suffix")
os.makedirs(sroot)
with open(os.path.join(sroot, core.MANIFEST_FILENAME), "wb") as fh:
    fh.write(open(manifest_path, "rb").read())
with open(os.path.join(sroot, core.LOG_FILENAME), "w") as fh:
    for r in recs[:-1]:
        fh.write(json.dumps(r, default=str) + "\n")
rep_s = core.verify_chain(os.path.join(sroot, core.LOG_FILENAME),
                          os.path.join(sroot, core.MANIFEST_FILENAME))
case("V8_suffix_prefix_self_consistent_disclosed",
     rep_s["ok"] and rep_s["records"] == len(recs) - 1, str(rep_s))
case("V8_suffix_truncation_anchor_mismatch",
     not core.check_anchor(rep_s, anchor))

# Tamper 4: corrupt a NON-final line (mid-log) — must refuse, not
# truncate (the v1 loader silently erased everything after it).
mroot = os.path.join(tmp, "midlog")
os.makedirs(mroot)
with open(os.path.join(mroot, core.MANIFEST_FILENAME), "wb") as fh:
    fh.write(open(manifest_path, "rb").read())
lines = raw.decode("utf-8").splitlines()
lines[1] = "{corrupted"
with open(os.path.join(mroot, core.LOG_FILENAME), "w") as fh:
    fh.write("\n".join(lines) + "\n")
mbefore = open(os.path.join(mroot, core.LOG_FILENAME), "rb").read()
refused = False
try:
    core.SignalObserver(mroot, T0, clock=lambda: NOW)
except core.ShadowError:
    refused = True
case("V8_midlog_corruption_refuses_bytes_unchanged",
     refused and open(os.path.join(mroot, core.LOG_FILENAME),
                      "rb").read() == mbefore)

# Regression of the v1 guarantee: a torn FINAL line still recovers.
with open(log_path, "a", encoding="utf-8") as fh:
    fh.write('{"record_kind": "shadow_cycle", "partial')
obs2 = core.SignalObserver(root, T0, clock=lambda: NOW)
raw2, recs2 = read_records(root)
case("V8_torn_tail_recovered_and_chain_still_verifies",
     obs2.signal_count == 2
     and core.verify_chain(log_path, manifest_path)["ok"]
     and recs2[-1].get("record_kind") == "shadow_recovery",
     f"records={len(recs2)}")
case("V8_recovery_record_itself_chained",
     bool(recs2[-1].get("hash")) and bool(recs2[-1].get("prev_hash")))

# A legacy unchained (v1-shaped) log refuses rather than loading.
lroot = os.path.join(tmp, "legacy")
os.makedirs(lroot)
with open(os.path.join(lroot, core.MANIFEST_FILENAME), "wb") as fh:
    fh.write(open(manifest_path, "rb").read())
legacy_rec = {"record_kind": "shadow_cycle", "schema": "shadow-signal-v1",
              "cohort": "SHADOW_OBSERVATION", "counts_as_trade": False,
              "logged_at": NOW.isoformat(), "status": "HEALTHY"}
with open(os.path.join(lroot, core.LOG_FILENAME), "w") as fh:
    fh.write(json.dumps(legacy_rec) + "\n")
refused = False
try:
    core.SignalObserver(lroot, T0, clock=lambda: NOW)
except core.ShadowError:
    refused = True
case("V8_legacy_unchained_log_refused", refused)

fails = [n for n, ok in RESULTS if not ok]
print(f"{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS")
if fails:
    print("FAILURES:", ", ".join(fails))
sys.exit(0 if not fails else 1)
