#!/usr/bin/env python3
"""Offline synthetic gate for QF-TD-EQUITY39-CONTINUE-20261023-11 (GO 6374566569 item 1).
Exercises the EXACT live Engine code with a stubbed Twelve Data transport. Proves:
 S1 price-moving zero-volume leg -> byte-exact quarantine + recorded failure + NO receipt,
    and the FOLLOWING legs in the same block still attempt and receipt; hash chain runs
    GENESIS(child) -> first accepted receipt -> second accepted receipt, skipping the
    refused leg; bracket reconciliation holds with a refused leg inside the block.
 S2 duplicate-instant leg -> STOP (original fail-closed class unchanged); next leg NOT attempted.
 S3 intra-session gap leg -> STOP; schema-error leg -> STOP.
 S4 transient transport failure -> one retry inside the bracket, leg accepted, reconciled.
No network. Exit 0 iff every assertion holds."""
import json, os, sys, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capture_continue import Engine, canonical

BASE = "/home/hatch/workspace/qf_td11_stage/work/synth"
CHILD_ROOT = hashlib.sha256(b"synthetic-child-manifest").hexdigest()
FAILURES = []

def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" :: {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)

def body(symbol, days, mutate=None):
    vals = []
    for d in days:
        for hh in ("09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"):
            vals.append({"datetime": f"{d} {hh}:00", "open": "100.0", "high": "101.0",
                         "low": "99.0", "close": "100.5", "volume": "1000"})
    if mutate:
        mutate(vals)
    return json.dumps({"meta": {"symbol": symbol, "interval": "1h"}, "status": "ok",
                       "values": vals}).encode()

DAYS = ["2024-01-02", "2024-01-03"]  # Tue, Wed

def zero_vol(vals):
    vals[1]["volume"] = "0"    # 2024-01-02 10:30, high>low -> price-moving
    vals[9]["volume"] = "0"    # 2024-01-03 11:30

def dup_stamp(vals):
    vals[3]["datetime"] = vals[2]["datetime"]

def gap(vals):
    # keep the day shape (7 bars, all :30) but break 3600s continuity:
    # 2024-01-02 last bar 15:30 -> 16:30 leaves a 7200s step inside the session.
    # (A short day is only an anomalous_dates finding under the frozen -10 validator;
    #  the GAP_VIOLATION class is non-3600 spacing at full shape - fixture matches it.)
    vals[6]["datetime"] = "2024-01-02 16:30:00"

def leg(lid, sym, win):
    return {"leg_id": lid, "symbol": sym, "window": win, "start_date": "2024-01-02",
            "end_date": "2024-01-03", "expected_rows_admitted": 14, "status": "NOT_ACQUIRED"}

def manifest(legs):
    return {"manifest_id": "SYNTHETIC", "legs": legs}

class FakeProvider:
    """Counts every call in daily_usage, like the real /api_usage counter."""
    def __init__(self, bodies, start_usage=16, flake_first_series=False):
        self.usage = start_usage
        self.bodies = bodies          # symbol -> bytes OR list of per-attempt results
        self.flake = flake_first_series
        self.series_calls = []
    def __call__(self, kind, params):
        self.usage += 1
        if kind == "usage":
            return 200, {}, json.dumps({"daily_usage": self.usage, "plan_daily_limit": 800,
                                        "plan_limit": 8, "current_usage": 1}).encode()
        sym = params["symbol"]
        self.series_calls.append(sym)
        if self.flake:
            self.flake = False
            raise ConnectionError("simulated transient transport failure")
        return 200, {"api-credits-used": "1"}, self.bodies[sym]

def run_scenario(name, legs, bodies, **kw):
    sdir = os.path.join(BASE, name, "store"); wdir = os.path.join(BASE, name, "work")
    os.makedirs(sdir, exist_ok=True); os.makedirs(wdir, exist_ok=True)
    eng = Engine(manifest(legs), sdir, wdir, FakeProvider(bodies, **kw),
                 hard_cap=50, pace_s=0.0, child_root=CHILD_ROOT,
                 program_td_total_before=27, log=lambda *a: None)
    code = eng.run(required_headroom=10)
    return eng, code, sdir, wdir

# ---------------- S1: quarantine-and-continue + chain + reconciliation
bad = body("AAA", DAYS, zero_vol)
eng, code, sdir, wdir = run_scenario(
    "s1", [leg("AAA/HO", "AAA", "W_HO"), leg("AAA/DEV", "AAA", "W_DEV"),
           leg("BBB/HO", "BBB", "W_HO")],
    {"AAA": bad, "BBB": body("BBB", DAYS)})
# NOTE: AAA/HO and AAA/DEV share the stub body per symbol; DEV body must be clean ->
# rerun S1 with per-leg distinct symbols instead to keep stub honest.
print("--- S1 rerun with distinct symbols (AAA defective HO, CCC clean DEV, BBB clean HO) ---")
import shutil
shutil.rmtree(os.path.join(BASE, "s1"), ignore_errors=True)
eng, code, sdir, wdir = run_scenario(
    "s1", [leg("AAA/HO", "AAA", "W_HO"), leg("CCC/DEV", "CCC", "W_DEV"),
           leg("BBB/HO", "BBB", "W_HO")],
    {"AAA": bad, "CCC": body("CCC", DAYS), "BBB": body("BBB", DAYS)})
outcomes = [l["outcome"] for l in eng.state["legs"]]
check("S1 exit code 0 (no stop)", code == 0 and eng.state["stop"] is None, str(eng.state["stop"]))
check("S1 outcomes", outcomes == ["QUARANTINED_VOLUME", "OK", "OK"], str(outcomes))
qpath = os.path.join(sdir, "quarantine", "AAA__HO.json")
check("S1 quarantine file byte-exact", os.path.exists(qpath) and open(qpath, "rb").read() == bad)
check("S1 NO receipt for quarantined leg",
      not os.path.exists(os.path.join(sdir, "receipts", "AAA__HO.receipt.json")))
check("S1 NO raw body archived for quarantined leg",
      not os.path.exists(os.path.join(sdir, "raw", "AAA__HO.json")))
r_dev = json.load(open(os.path.join(sdir, "receipts", "CCC__DEV.receipt.json")))
r_bbb = json.load(open(os.path.join(sdir, "receipts", "BBB__HO.receipt.json")))
check("S1 chain genesis bound to child root", r_dev["chain"]["prev_receipt_hash"] == "GENESIS:" + CHILD_ROOT)
check("S1 chain skips refused leg", r_bbb["chain"]["prev_receipt_hash"] == r_dev["chain"]["receipt_hash"])
check("S1 receipt carries parent root", r_dev["parent_manifest_root_digest_sha256"].startswith("ca498920"))
check("S1 block reconciled with refused leg inside", eng.state["blocks"][0]["reconciled"] is True)
check("S1 block attempts counted incl. quarantined", eng.state["blocks"][0]["attempts"] == 3)
check("S1 quarantine census stamps", eng.state["quarantines"][0]["zero_vol_stamps"] ==
      ["2024-01-02 10:30:00", "2024-01-03 11:30:00"], str(eng.state["quarantines"]))
check("S1 refusal recorded", any(r["reason"] == "QUARANTINED_VOLUME" for r in eng.state["refusals"]))

# ---------------- S2: duplicate instant -> STOP, next leg not attempted
eng, code, sdir, wdir = run_scenario(
    "s2", [leg("DDD/HO", "DDD", "W_HO"), leg("EEE/DEV", "EEE", "W_DEV")],
    {"DDD": body("DDD", DAYS, dup_stamp), "EEE": body("EEE", DAYS)})
check("S2 STOP on duplicate instant", eng.state["stop"] is not None and
      "DUPLICATE_INSTANT" in eng.state["stop"], str(eng.state["stop"]))
check("S2 next leg NOT attempted", len(eng.state["legs"]) == 1)
check("S2 no receipts", not os.listdir(os.path.join(sdir, "receipts")))

# ---------------- S3a: gap -> STOP ; S3b: schema error -> STOP
eng, code, sdir, wdir = run_scenario(
    "s3a", [leg("FFF/HO", "FFF", "W_HO")], {"FFF": body("FFF", DAYS, gap)})
check("S3a STOP on gap", eng.state["stop"] is not None and "GAP_VIOLATION" in eng.state["stop"],
      str(eng.state["stop"]))
err_body = json.dumps({"status": "error", "code": 400, "message": "bad param"}).encode()
eng, code, sdir, wdir = run_scenario(
    "s3b", [leg("GGG/HO", "GGG", "W_HO")], {"GGG": err_body})
check("S3b STOP on schema error", eng.state["stop"] is not None and
      "SCHEMA_VIOLATION" in eng.state["stop"], str(eng.state["stop"]))

# ---------------- S4: transient transport failure -> retry within bracket -> accepted
eng, code, sdir, wdir = run_scenario(
    "s4", [leg("HHH/HO", "HHH", "W_HO")], {"HHH": body("HHH", DAYS)}, flake_first_series=True)
check("S4 accepted after one retry", [l["outcome"] for l in eng.state["legs"]] == ["OK"] and
      eng.state["legs"][0]["attempts"] == 2, str(eng.state["legs"]))
check("S4 reconciled (delta counts both attempts)", eng.state["blocks"][0]["reconciled"] is True)

print("\nSYNTHETIC GATE:", "PASS" if not FAILURES else f"FAIL ({len(FAILURES)} assertions)")
sys.exit(0 if not FAILURES else 1)
