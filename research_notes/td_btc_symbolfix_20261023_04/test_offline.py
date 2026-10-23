#!/usr/bin/env python3
"""Offline regression tests for QF-TD-BTC-SYMBOL-FIX-20261023-04 (Phase 0).
Network-disabled (run under unshare -n). Synthetic bytes only - no vendor calls.
Covers: alias mapping (BTC/USD accepted as request form, BTC-USD rejected),
exact six windows/outputsize, meta.symbol provider-form check, UTC/DST crypto
grid validation (spring + fall), volume policy (missing/null = coverage hold),
truncation, receipt chain recompute, frozen membership pins, no-scan guard."""
import json, hashlib, sys, os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capture_btc_fix as drv

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
BASE = "/home/hatch/workspace/qf_td_btc_fix_20261023"
PASS, FAIL = [], []

def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f" :: {detail}" if detail and not cond else ""))

# ---------- 1. alias mapping ----------
for leg in drv.LEGS:
    p = drv.build_params(leg)
    assert p["symbol"] == "BTC/USD", p
check("alias: all six legs build request symbol BTC/USD", True)
try:
    drv.assert_request_form({"symbol": "BTC-USD"})
    check("alias: BTC-USD as request form rejected", False)
except ValueError:
    check("alias: BTC-USD as request form rejected", True)
try:
    drv.assert_request_form(drv.build_params(drv.LEGS[0]))
    check("alias: BTC/USD request form accepted by guard", True)
except ValueError:
    check("alias: BTC/USD request form accepted by guard", False)
try:
    drv.request_symbol_for("ETH-USD")
    check("alias: unmapped symbol raises (no loosening for other symbols)", False)
except ValueError:
    check("alias: unmapped symbol raises (no loosening for other symbols)", True)

# ---------- 2. exact six windows / outputsize ----------
PINNED = [
    ("BTC-USD/HO-C1",  "BTC-USD", "W_HO",  "2023-10-19", "2024-05-13", 4992),
    ("BTC-USD/HO-C2",  "BTC-USD", "W_HO",  "2024-05-14", "2024-09-15", 3000),
    ("BTC-USD/DEV-C1", "BTC-USD", "W_DEV", "2024-09-16", "2025-04-11", 4992),
    ("BTC-USD/DEV-C2", "BTC-USD", "W_DEV", "2025-04-12", "2025-11-05", 4993),
    ("BTC-USD/DEV-C3", "BTC-USD", "W_DEV", "2025-11-06", "2026-06-01", 4991),
    ("BTC-USD/DEV-C4", "BTC-USD", "W_DEV", "2026-06-02", "2026-10-16", 3288),
]
check("legs: exact six pinned windows + expected rows", list(drv.LEGS) == PINNED)
p0 = drv.build_params(drv.LEGS[0])
check("params: outputsize/interval/adjust/timezone/order pinned",
      p0["outputsize"] == "5000" and p0["interval"] == "1h" and p0["adjust"] == "splits"
      and p0["timezone"] == "America/New_York" and p0["order"] == "ASC")
check("params: start/end suffixes T00:00:00 / T23:59:59",
      p0["start_date"] == "2023-10-19T00:00:00" and p0["end_date"] == "2024-05-13T23:59:59")

# ---------- 3. manifest pins ----------
man = json.load(open(os.path.join(BASE, "store", "capture_manifest.json")))
body = {k: v for k, v in man.items() if k != "root_digest"}
recomputed = hashlib.sha256(drv.canonical(body)).hexdigest()
check("manifest: root digest recomputes", recomputed == man["root_digest"] == drv.MANIFEST_ROOT,
      f"{recomputed} vs {man['root_digest']}")
check("manifest: frozen membership digests unchanged",
      man["frozen_universe"]["membership_sha256_sorted"] == "b5d8877ee7d6ddd105904d7f4ca35901ebb611dac7afeab2f7676529c112e6a2"
      and man["frozen_universe"]["ordered_digest_sha256"] == "8f0778df2502e31d4dc0bfeaec42cb51c209e38bf8d91195c61270c3a7ba16c0")
check("manifest: exactly one alias mapping BTC-USD -> BTC/USD",
      man["symbol_map"] == [{"internal_symbol": "BTC-USD", "provider": "Twelve Data",
                             "request_symbol": "BTC/USD",
                             "mapping": "explicit one-to-one transport alias; the ONLY mapped symbol in this manifest; no other symbol's request form changes"}])
check("manifest: every leg carries BOTH identifiers",
      all(l["internal_symbol"] == "BTC-USD" and l["request_symbol"] == "BTC/USD" for l in man["legs"]))

# ---------- synthetic chunk builder (instants -> ET wall stamps, as provider emits) ----------
def make_doc(start_epoch, n, symbol="BTC/USD", mutate=None):
    vals = []
    for i in range(n):
        ts = datetime.fromtimestamp(start_epoch + 3600 * i, ET)
        v = {"datetime": ts.strftime("%Y-%m-%d %H:%M:%S"),
             "open": "100.0", "high": "101.0", "low": "99.0", "close": "100.5",
             "volume": "12.5"}
        if mutate:
            mutate(v, i)
        vals.append(v)
    return {"status": "ok", "meta": {"symbol": symbol, "interval": "1h"}, "values": vals}

def body_of(doc):
    return json.dumps(doc).encode()

SPRING_START = datetime(2025, 3, 8, 9, 30, tzinfo=ET).astimezone(UTC).timestamp()   # Sat 09:30 EST
FALL_START = datetime(2025, 11, 1, 9, 30, tzinfo=ET).astimezone(UTC).timestamp()    # Sat 09:30 EDT

# ---------- 4. grid/DST validation ----------
doc = make_doc(SPRING_START, 72)  # spans 2025-03-09 spring-forward (no 02:30 wall stamp)
ok, info, detail, _ = drv.validate_chunk("T", body_of(doc), 72)
check("grid: spring-forward chunk validates (23h session day)", ok, str(detail))
check("grid: spring stamps all :30, no 02:30 on 2025-03-09",
      ok and "2025-03-09 02:30:00" not in info["stamps"] and info["stamp_minutes"] == ["30"])

doc = make_doc(FALL_START, 72)  # spans 2025-11-02 fall-back (01:30 wall stamp twice)
ok, info, detail, _ = drv.validate_chunk("T", body_of(doc), 72)
check("grid: fall-back chunk validates (25h session day, repeated hour resolved on UTC instants)",
      ok, str(detail))
check("grid: fall stamps contain 2025-11-02 01:30 exactly twice",
      ok and info["stamps"].count("2025-11-02 01:30:00") == 2)

doc = make_doc(SPRING_START, 72, symbol="BTC-USD")
ok, reason, _, _ = drv.validate_chunk("T", body_of(doc), 72)
check("meta: provider form BTC-USD in meta rejected", not ok and reason == "SCHEMA_VIOLATION", str(reason))

doc = make_doc(SPRING_START, 72)
del doc["values"][10]
ok, reason, _, _ = drv.validate_chunk("T", body_of(doc), 71)
check("grid: dropped bar -> GAP_VIOLATION", not ok and reason == "GAP_VIOLATION", str(reason))

doc = make_doc(SPRING_START, 72)
doc["values"][5]["datetime"] = doc["values"][5]["datetime"][:14] + "00:00"
ok, reason, _, _ = drv.validate_chunk("T", body_of(doc), 72)
check("grid: off-phase stamp -> OFF_GRID_STAMPS", not ok and reason == "OFF_GRID_STAMPS", str(reason))

doc = make_doc(SPRING_START, 72)
doc["values"][7]["datetime"] = doc["values"][6]["datetime"]
ok, reason, _, _ = drv.validate_chunk("T", body_of(doc), 72)
check("grid: duplicated stamp -> DUPLICATE_INSTANT", not ok and reason == "DUPLICATE_INSTANT", str(reason))

doc = make_doc(SPRING_START, 5000)
ok, reason, _, _ = drv.validate_chunk("T", body_of(doc), 5000)
check("truncation: exactly 5000 rows -> TRUNCATION_SUSPECT", not ok and reason == "TRUNCATION_SUSPECT", str(reason))

# ---------- 5. volume policy ----------
doc = make_doc(SPRING_START, 72)
del doc["values"][3]["volume"]
ok, reason, _, _ = drv.validate_chunk("T", body_of(doc), 72)
check("volume: missing field -> SCHEMA_COVERAGE_HOLD (not zero)", not ok and reason == "SCHEMA_COVERAGE_HOLD", str(reason))

doc = make_doc(SPRING_START, 72)
doc["values"][3]["volume"] = None
ok, reason, _, _ = drv.validate_chunk("T", body_of(doc), 72)
check("volume: null -> SCHEMA_COVERAGE_HOLD", not ok and reason == "SCHEMA_COVERAGE_HOLD", str(reason))

doc = make_doc(SPRING_START, 72)
doc["values"][3]["volume"] = "0"
ok, info, _, _ = drv.validate_chunk("T", body_of(doc), 72)
check("volume: zero-vol with nonzero range counted (SMCI-class detector)",
      ok and info["zero_vol_range_bars"] == 1)

doc = make_doc(SPRING_START, 72)
doc["values"][3]["volume"] = "-5"
ok, reason, _, _ = drv.validate_chunk("T", body_of(doc), 72)
check("volume: negative -> SCHEMA_VIOLATION", not ok and reason == "SCHEMA_VIOLATION", str(reason))

# ---------- 6. receipt chain ----------
prev = "GENESIS:" + drv.MANIFEST_ROOT
hashes = []
for i in range(2):
    r = {"kind": "capture_receipt", "leg_id": f"L{i}", "internal_symbol": "BTC-USD",
         "request_symbol": "BTC/USD", "chain": {"prev_receipt_hash": prev}}
    rh = hashlib.sha256(drv.canonical(r)).hexdigest()
    r["chain"]["receipt_hash"] = rh
    hashes.append((r, rh))
    prev = rh
r0 = dict(hashes[0][0]); stored = r0.pop("chain")["receipt_hash"]
r0["chain"] = {"prev_receipt_hash": "GENESIS:" + drv.MANIFEST_ROOT}
check("receipt: hash recomputes from canonical form", hashlib.sha256(drv.canonical(r0)).hexdigest() == stored)
check("receipt: chain links prev->next", hashes[1][0]["chain"]["prev_receipt_hash"] == hashes[0][1])
tampered = json.loads(json.dumps(hashes[0][0])); tampered["leg_id"] = "LX"
tampered.pop("chain")
check("receipt: tamper breaks recompute",
      hashlib.sha256(drv.canonical(tampered)).hexdigest() != hashes[0][1])

# ---------- 7. no accidental scan / scope guard ----------
check("scope: exactly 6 legs, all internal BTC-USD",
      len(drv.LEGS) == 6 and {l[1] for l in drv.LEGS} == {"BTC-USD"})
src = open(os.path.join(BASE, "work", "capture_btc_fix.py")).read()
check("scope: driver names no other universe symbol as a symbol literal",
      all(s not in src for s in ['"ETH-USD"', '"SOL-USD"', '"NVDA"', '"SMCI"', "'ETH-USD'",
                                 "yfinance", "watchlist"]))
check("scope: hard cap 15 / max 2 attempts per leg",
      drv.HARD_CAP == 15 and drv.MAX_ATTEMPTS_PER_CHUNK == 2)

print(json.dumps({"passed": len(PASS), "failed": len(FAIL), "failures": FAIL}))
sys.exit(1 if FAIL else 0)
