#!/usr/bin/env python3
"""Build the amended BTC capture manifest for QF-TD-BTC-SYMBOL-FIX-20261023-04.

Correction by lineage: the ONLY change vs the Card A lineage is the provider
request symbol form for the single crypto leg. Root digest =
sha256(canonical_json(manifest without the root_digest field)).
"""
import json, hashlib, os

BASE = "/home/hatch/workspace/qf_td_btc_fix_20261023"
OUT = os.path.join(BASE, "store", "capture_manifest.json")

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

REQUEST_COMMON = {
    "endpoint_class": "/time_series",
    "interval": "1h",
    "adjust": "splits",
    "outputsize": 5000,
    "order": "ASC",
    "timezone": "America/New_York",
    "start_suffix": "T00:00:00",
    "end_suffix": "T23:59:59",
}

# leg_id, window, start_date, end_date, expected_rows — identical windows/rows to Card A (-03)
RAW_LEGS = [
    ("BTC-USD/HO-C1",  "W_HO",  "2023-10-19", "2024-05-13", 4992),
    ("BTC-USD/HO-C2",  "W_HO",  "2024-05-14", "2024-09-15", 3000),
    ("BTC-USD/DEV-C1", "W_DEV", "2024-09-16", "2025-04-11", 4992),
    ("BTC-USD/DEV-C2", "W_DEV", "2025-04-12", "2025-11-05", 4993),
    ("BTC-USD/DEV-C3", "W_DEV", "2025-11-06", "2026-06-01", 4991),
    ("BTC-USD/DEV-C4", "W_DEV", "2026-06-02", "2026-10-16", 3288),
]

legs = []
for leg_id, window, sd, ed, expected in RAW_LEGS:
    legs.append({
        "leg_id": leg_id,
        "internal_symbol": "BTC-USD",
        "request_symbol": "BTC/USD",
        "window": window,
        "start_date": sd,
        "end_date": ed,
        "expected_rows": expected,
        "request": dict(REQUEST_COMMON),
    })

manifest = {
    "manifest_id": "QF-TD-BTC-CAPTURE-MANIFEST-AMEND-20261023-04",
    "task": "QF-TD-BTC-SYMBOL-FIX-20261023-04",
    "status": "CANDIDATE AMENDMENT - authorizes nothing by itself; execution under Mike's standing GO for this bounded task (chat 2026-10-23 12:21 ET)",
    "lineage": ("readiness manifest edc44d9 (root 79ccdd128e0b36537f56f8ae36a731b719e989b9756f65856b7dc47344327122) "
                "-> Card A continuation pin 7823538 -> -03 pilot 86aee48 (refusal archive qf-data-archive abf2d53) "
                "-> this amendment 20261023-04 (symbol-form correction ONLY; prior packages and archives byte-untouched)"),
    "correction": {
        "scope": "provider request symbol form for the single crypto leg BTC-USD; nothing else",
        "defect": "-03 pinned request form carried the UX51 universe name BTC-USD; Twelve Data rejected it HTTP 404 (invalid symbol)",
        "fix": "transport alias only: requests carry BTC/USD; universe/manifest identity stays BTC-USD",
    },
    "symbol_map": [
        {"internal_symbol": "BTC-USD", "provider": "Twelve Data",
         "request_symbol": "BTC/USD",
         "mapping": "explicit one-to-one transport alias; the ONLY mapped symbol in this manifest; no other symbol's request form changes"}
    ],
    "frozen_universe": {
        "name": "UX51 (Option A freeze, commit 2705c02) - membership UNCHANGED by this amendment",
        "membership_sha256_sorted": "b5d8877ee7d6ddd105904d7f4ca35901ebb611dac7afeab2f7676529c112e6a2",
        "ordered_digest_sha256": "8f0778df2502e31d4dc0bfeaec42cb51c209e38bf8d91195c61270c3a7ba16c0",
    },
    "provider": "Twelve Data",
    "calendar": {"crypto": "S-C1..S-C6 continuous: session = ET date, [D 09:30 ET, D+1 09:30 ET); stamps are bar-opens; validation on absolute UTC instants"},
    "legs": legs,
    "validation": {
        "meta_symbol_must_equal": "request_symbol (BTC/USD) - the provider form, NOT the internal universe token",
        "stamp_grid": "bar-open ET wall stamps resolve to UTC instants (fold-aware, strictly increasing); stamp minutes == {30}; consecutive instant delta == 3600s exactly",
        "rows": "rows == expected_rows exactly; rows == 5000 is a fail-closed truncation defect",
        "volume_missing_or_null": "SCHEMA_COVERAGE_HOLD (failure) - never recorded as zero, never synthesized",
        "volume_zero_with_nonzero_range": "counted; >0 = SMCI-class volume-completeness failure -> quarantine, abort",
        "nonfinite_or_negative": "failure",
    },
    "budget": {
        "accounting": "BLOCK-BRACKET-10 (unit 1 credit/call; blocks of <=10 attempts; one /api_usage read opens a phase, one closes every block; <=2 attempts per leg)",
        "expected_credits": 8,
        "hard_max_incremental_credits": 15,
        "includes": "preflight + data attempts + retries + block/closing usage reads",
        "cost": "$0 free tier only; no paid upgrade",
        "program_td_total_before": 21,
    },
    "archive": {
        "repo": "qf-data-archive (private, append-only)",
        "namespace": "captures/td_pilot_btc_fix_20261023/",
        "prior_namespace_immutable": "captures/td_pilot_btc_20261023/ (from -03; NOT modified by this task)",
    },
    "root_digest_method": "root_digest = sha256(canonical_json(manifest object without the root_digest field)); canonical = json.dumps(sort_keys=True, separators=(',',':'))",
}

root = hashlib.sha256(canonical(manifest)).hexdigest()
manifest["root_digest"] = root
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(manifest, f, indent=1, sort_keys=True)
print(json.dumps({"manifest": OUT, "root_digest": root}))
