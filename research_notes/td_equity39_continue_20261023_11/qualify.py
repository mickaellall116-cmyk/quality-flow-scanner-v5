#!/usr/bin/env python3
"""Per-leg qualification for QF-TD-EQUITY39-CONTINUE-20261023-11, gates G-1..G-6 + G-7
disclosure, mirroring the -02/-08 calendar-bound admission on the pinned 751-session
table (sha256 00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f).
Admission rule (-02, generic): a bar is admitted iff its bar-open instant falls inside a
pinned session [09:30, close) on the 1h grid (:30 opens; early close 13:00 -> bars
09:30,10:30,11:30,12:30). Everything else is excluded and must be exactly the generic
class (e.g. the known phantom 15:30 stamps on 13:00 early-close dates).
Labels: accepted legs passing G-1..G-6 = CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED
(G-7 VBASIS disclosed, checker unadopted - NEVER 'QUALIFIED')."""
import json, os, hashlib, sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
BASE = "/home/hatch/workspace/qf_td11_stage"
STORE = os.path.join(BASE, "store")
WORK = os.path.join(BASE, "work")
CHILD_ROOT = "c5628652c5bf59d870103e41fd7e22a23fe4d811c61662fda78a8790abd0444f"
PARENT_ROOT = "ca49892062f1ac5d4ec6d20eaadd37b519aec84ad0b23a995fb11db74dccfd64"

table = json.load(open(os.path.join(WORK, "session_table.json")))
sessions = {s["date"]: s for s in table["sessions"]}
assert table["session_count"] == 751

def expected_stamps(date_str):
    s = sessions[date_str]
    close = datetime.strptime(s["close"], "%H:%M")
    t = datetime.strptime("09:30", "%H:%M")
    out = []
    while t < close:
        out.append(f"{date_str} {t.strftime('%H:%M')}:00")
        t += timedelta(hours=1)
    return out

# window date ranges from the child manifest
manifest = json.load(open(os.path.join(STORE, "child_manifest.json")))
child_check = dict(manifest); cr = child_check.pop("root_digest_sha256")
child_check.pop("root_digest_construction")
assert hashlib.sha256(json.dumps(child_check, sort_keys=True,
                                 separators=(",", ":")).encode()).hexdigest() == cr == CHILD_ROOT

summary = json.load(open(os.path.join(WORK, "run_summary.json")))
leg_state = {l["leg_id"]: l for l in summary["legs"]}

def verify_chain():
    """G-1: walk receipts in manifest order, verify genesis + hash links + raw hashes."""
    prev = "GENESIS:" + CHILD_ROOT
    ok, n = True, 0
    for spec in manifest["legs"]:
        lid = spec["leg_id"]
        rp = os.path.join(STORE, "receipts", lid.replace("/", "__") + ".receipt.json")
        st = leg_state.get(lid)
        if st and st["outcome"] == "OK":
            if not os.path.exists(rp):
                return False, f"missing receipt for accepted leg {lid}"
            r = json.load(open(rp))
            if r["chain"]["prev_receipt_hash"] != prev:
                return False, f"chain break at {lid}"
            raw = open(os.path.join(STORE, "raw", lid.replace("/", "__") + ".json"), "rb").read()
            if hashlib.sha256(raw).hexdigest() != r["response"]["sha256"]:
                return False, f"raw hash mismatch {lid}"
            if r["manifest_root_digest_sha256"] != CHILD_ROOT or \
               r["parent_manifest_root_digest_sha256"] != PARENT_ROOT:
                return False, f"root pin mismatch {lid}"
            prev = r["chain"]["receipt_hash"]
            n += 1
        else:
            if os.path.exists(rp):
                return False, f"receipt exists for non-accepted leg {lid}"
    return True, f"{n} receipts chained from GENESIS(child root)"

chain_ok, chain_msg = verify_chain()

results = {}
for spec in manifest["legs"]:
    lid, sym, win = spec["leg_id"], spec["symbol"], spec["window"]
    st = leg_state.get(lid)
    if st is None:
        results[lid] = {"status": "NOT_ATTEMPTED"}
        continue
    if st["outcome"] == "QUARANTINED_VOLUME":
        results[lid] = {"status": "QUARANTINED_VOLUME",
                        "classification": "NOT_EVALUABLE_PROVIDER_VOLUME",
                        "zero_vol_range_bars": st["zero_vol_range_bars"],
                        "zero_vol_stamps": st["zero_vol_stamps"],
                        "quarantine_sha256": st["quarantine_sha256"]}
        continue
    if st["outcome"] != "OK":
        results[lid] = {"status": st["outcome"]}
        continue
    # accepted leg: admission + completeness on raw bytes
    doc = json.loads(open(os.path.join(STORE, "raw", lid.replace("/", "__") + ".json"),
                          encoding="utf-8").read())
    vals = doc["values"]
    raw_stamps = [v["datetime"] for v in vals]
    win_dates = [d for d in sorted(sessions)
                 if spec["start_date"] <= d <= spec["end_date"]]
    exp = []
    for d in win_dates:
        exp.extend(expected_stamps(d))
    exp_set = set(exp)
    admitted = [s for s in raw_stamps if s in exp_set]
    excluded = [s for s in raw_stamps if s not in exp_set]
    # G-4: excluded rows must sit on pinned early-close dates at 15:30 (the generic class
    # proven in -02: rows appended after a 13:00 close) - anything else fails the gate.
    g4_bad = [s for s in excluded
              if not (sessions.get(s[:10], {}).get("close") == "13:00" and s[11:16] == "15:30")]
    admitted_set = set(admitted)
    missing = [s for s in exp if s not in admitted_set]
    dup = len(raw_stamps) != len(set(raw_stamps))
    zero_vol_admitted = 0
    for v in vals:
        if v["datetime"] in admitted_set and float(v["volume"]) == 0 and float(v["high"]) > float(v["low"]):
            zero_vol_admitted += 1
    gates = {
        "G-1_receipt_integrity": bool(chain_ok),
        "G-2_calendar_admission": len(admitted) == len(exp) and not dup,
        "G-3_completeness_exact": not missing and len(admitted) == spec["expected_rows_admitted"],
        "G-4_phantom_exclusion_generic": not g4_bad,
        "G-5_volume_completeness": zero_vol_admitted == 0,
        "G-6_schema_instant_hygiene": not dup,
    }
    passed = all(gates.values())
    results[lid] = {
        "status": "CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED" if passed else "ACCEPTED_BUT_GATE_FAIL",
        "gates": gates,
        "rows_raw": len(raw_stamps), "rows_admitted": len(admitted),
        "rows_expected": spec["expected_rows_admitted"],
        "excluded_stamps": excluded, "missing_count": len(missing),
        "missing_first": missing[:5], "sha256": st["sha256"],
        "receipt_hash": st.get("receipt_hash"),
        "G-7_VBASIS": "DISCLOSED_NOT_WAIVED - candidate-2 checker unadopted; CONVENTION_BREAK_SUSPECT "
                      "disposition from -02 stands; no threshold touched",
    }

out = {"task": "QF-TD-EQUITY39-CONTINUE-20261023-11", "child_root": CHILD_ROOT,
       "chain": {"ok": chain_ok, "detail": chain_msg}, "legs": results}
with open(os.path.join(WORK, "qualification.json"), "w") as f:
    json.dump(out, f, indent=2, sort_keys=True)
from collections import Counter
print("chain:", chain_ok, chain_msg)
print(Counter(v["status"] for v in results.values()))
for lid, r in results.items():
    if r["status"] not in ("CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED", "QUARANTINED_VOLUME"):
        print("ATTENTION", lid, r["status"], json.dumps(r)[:300])
    if r["status"] == "ACCEPTED_BUT_GATE_FAIL":
        print("GATEFAIL", lid, json.dumps(r)[:500])
