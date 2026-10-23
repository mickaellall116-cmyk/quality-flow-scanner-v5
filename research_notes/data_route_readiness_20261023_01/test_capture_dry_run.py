"""Network-disabled dry-run tests for the candidate capture wrapper.
Run under `unshare -n` with the pinned venv. Synthetic fixtures only."""
import copy
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capture_wrapper import (CaptureRefused, disabled_transport, run_leg)

RESULTS = []


def check(name, fn):
    try:
        fn()
        RESULTS.append((name, "PASS"))
    except AssertionError as e:
        RESULTS.append((name, f"FAIL {e}"))


def bar(stamp, close="100.0"):
    return {"datetime": stamp, "open": "100.0", "high": "101.0",
            "low": "99.0", "close": close, "volume": "1000"}


def payload(stamps, symbol="FIX"):
    return {"meta": {"symbol": symbol, "interval": "1h", "currency": "USD",
                     "exchange": "FIXTURE", "type": "Common Stock"},
            "values": [bar(s) for s in stamps], "status": "ok"}


DAY = [f"2026-10-20T{h:02d}:30:00-04:00" for h in range(9, 16)]  # 09:30..15:30 ET
LEG = {"leg_id": "FIX/HO", "symbol": "FIX", "window": "W_HO",
       "start_date": "2026-10-20", "end_date": "2026-10-20", "expected_rows": 7}
ROOT = "FIXTURE_ROOT"


def expect_refusal(name, transport, reason):
    def fn():
        try:
            run_leg(transport, LEG, ROOT, "GENESIS")
        except CaptureRefused as e:
            assert e.reason == reason, f"{e.reason} != {reason}"
            return
        raise AssertionError("leg was not refused")
    check(name, fn)


def t_valid_chain():
    r1 = run_leg(lambda leg: payload(DAY), LEG, ROOT, "GENESIS")
    assert r1["response"]["rows"] == 7 and r1["response"]["row_delta"] == 0
    canon = json.dumps({k: v for k, v in r1.items()}, sort_keys=True, separators=(",", ":"))
    # receipt_hash recompute over the receipt minus the hash field itself
    r1c = copy.deepcopy(r1)
    h = r1c["chain"].pop("receipt_hash")
    canon = json.dumps(r1c, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canon).hexdigest() == h, "receipt hash does not recompute"
    leg2 = dict(LEG, leg_id="FIX/DEV")
    r2 = run_leg(lambda leg: payload(DAY), leg2, ROOT, h)
    assert r2["chain"]["prev_receipt_hash"] == h, "chain link broken"


check("T2 valid payload -> chained receipts, hash recomputes", t_valid_chain)

expect_refusal("T1a disabled transport -> NETWORK_DISABLED, no receipt",
               disabled_transport, "NETWORK_DISABLED")


def bad_schema(leg):
    p = payload(DAY)
    p["values"][0] = {"datetime": DAY[0], "open": "1", "high": "1", "low": "1", "volume": "1"}
    return p
expect_refusal("T3 schema mutation (missing close) -> SCHEMA_VIOLATION", bad_schema, "SCHEMA_VIOLATION")


def bad_tz(leg):
    # July stamp carrying a winter (-05:00) offset: inconsistent with ET rules
    return payload([s.replace("-04:00", "-05:00") for s in
                    [f"2026-07-14T{h:02d}:30:00-04:00" for h in range(9, 16)]])
expect_refusal("T4 timezone mutation (wrong offset) -> TIMEZONE_VIOLATION", bad_tz, "TIMEZONE_VIOLATION")


def dup(leg):
    return payload(DAY[:3] + [DAY[2]] + DAY[3:])
expect_refusal("T5a duplicate instant -> DUPLICATE_INSTANT", dup, "DUPLICATE_INSTANT")


def fall_back(leg):
    # 2026-11-01 repeated hour: 01:30 occurs at -04:00 and again at -05:00.
    # Distinct UTC instants - must be ACCEPTED (the -94 lesson).
    stamps = ["2026-11-01T00:30:00-04:00", "2026-11-01T01:30:00-04:00",
              "2026-11-01T01:30:00-05:00", "2026-11-01T02:30:00-05:00"]
    return payload(stamps)
def t_fallback():
    r = run_leg(fall_back, dict(LEG, expected_rows=4, max_gap_seconds=7200), ROOT, "GENESIS")
    assert r["response"]["rows"] == 4
check("T5b fall-back repeated hour (distinct instants) accepted", t_fallback)


def gap(leg):
    return payload(DAY[:3] + DAY[4:])
expect_refusal("T6 gap mutation (dropped bar) -> GAP_VIOLATION", gap, "GAP_VIOLATION")


def nonfinite(leg):
    p = payload(DAY)
    p["values"][2]["close"] = "NaN"
    return p
expect_refusal("T7 non-finite close -> NONFINITE_VALUE", nonfinite, "NONFINITE_VALUE")


def t_no_fabrication():
    receipts = []
    prev = "GENESIS"
    for transport in (lambda leg: payload(DAY), bad_schema, lambda leg: payload(DAY)):
        try:
            r = run_leg(transport, LEG, ROOT, prev)
            receipts.append(r)
            prev = r["chain"]["receipt_hash"]
        except CaptureRefused:
            pass
    assert len(receipts) == 2, f"expected exactly 2 receipts, got {len(receipts)}"
    assert receipts[1]["chain"]["prev_receipt_hash"] == receipts[0]["chain"]["receipt_hash"]
check("T8 refused leg emits no receipt; chain skips it (no fabrication)", t_no_fabrication)


def t_cli():
    out = "/tmp/qf_dry_run_receipts.jsonl"
    if os.path.exists(out):
        os.remove(out)
    p = subprocess.run([sys.executable, "dry_run_cli.py", out],
                       capture_output=True, text=True,
                       cwd=os.path.dirname(os.path.abspath(__file__)))
    assert p.returncode == 3, f"exit {p.returncode} != 3; stdout={p.stdout!r}"
    assert "FAIL_CLOSED" in p.stdout and "NETWORK_DISABLED" in p.stdout
    assert not os.path.exists(out), "receipt file created despite refusal"
check("T1b CLI under network-off: exit 3, FAIL_CLOSED, no receipt file", t_cli)


fails = 0
for name, res in RESULTS:
    print(f"{res:>4}  {name}")
    fails += res != "PASS"
print(f"TOTAL {len(RESULTS) - fails}/{len(RESULTS)} PASS")
sys.exit(1 if fails else 0)
