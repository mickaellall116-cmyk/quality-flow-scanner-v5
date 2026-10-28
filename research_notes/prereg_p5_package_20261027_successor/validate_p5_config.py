#!/usr/bin/env python3
"""Fail-closed validator / verifier for the P5 per-fill config.

SUCCESSOR of the validator committed in bb90d72
(research_notes/prereg_p5_package_20261027/). The only behavioral change:
nested provenance entries now carry EXACT key sets (point 2 below). The
predecessor checked that a provenance entry had a status and a citation /
requires_review, but an entry carrying additional keys - or a PROPOSED
entry missing its derivation - still validated. No parameter value,
status, or other check changes.

Independently encodes the frozen expectations of PREREG_V10.md sections 7
and 8 (it does NOT import the generator): a config is accepted only if

  1. the SHA-256 of its exact bytes equals the expected hash (the value
     pinned in the freeze record via SHA256_MANIFEST.txt);
  2. its structure matches the schema exactly - unknown keys, missing
     keys, or wrong types are rejected at every level, INCLUDING the
     nested provenance entries: a PINNED entry carries exactly
     {status, citation} and a PROPOSED entry exactly
     {status, requires_review, derivation};
  3. every PINNED parameter equals the value stated in the frozen text;
  4. every PROPOSED parameter is internally consistent and still flagged
     requires_review (a provenance status flip is a rejection);
  5. cross-field arithmetic holds (per-fill = round-trip / 2 per view).

Any failure exits 1 with the reason on stderr. Success exits 0.
Stdlib only; offline; computes no performance quantity.

Usage: python3 validate_p5_config.py <config_path> --expected-sha256 <hex>
"""
import argparse
import hashlib
import json
import sys

EXPECTED_TOP_KEYS = {
    "artifact", "schema_version", "stage", "protocol",
    "parameters", "provenance", "predecessor",
}
EXPECTED_ARTIFACT = "QF-PREREG-V10-P5-PER-FILL-CONFIG"
EXPECTED_SCHEMA_VERSION = 1
EXPECTED_STAGE = 2
EXPECTED_PROTOCOL = "prereg_v10_20261026"

# Values stated in the frozen text (PREREG_V10.md S7/S8). A config carrying
# anything else under these keys is not the frozen convention.
PINNED_VALUES = {
    "verdict_round_trip_bps": 25,
    "verdict_per_fill_bps": 12.5,
    "sensitivity_round_trip_bps": [4, 10],
    "fill_cost_formula":
        "cost_dollars = (per_fill_bps / 10000) * shares_filled * fill_price",
    "net_pnl_formula":
        "net_pnl_dollars = sum(exit_fill_notionals) - entry_fill_notional"
        " - sum(fill_costs)",
    "net_r_formula":
        "net_r = net_pnl_dollars / (shares * (entry_price - initial_stop_price))",
    "partial_fills": False,
    "fill_price_basis": "stated_bar_open_or_close",
    "tp1_fill_rule": "bar_high_touches_limit",
    "e1_stop_slippage_atr": 0.05,
    "e2_tp1_exceed_margin_atr": 0.05,
    "hbuy_descriptive_cost_bps": 25,
    "not_modeled": ["financing", "borrow", "dividends", "taxes"],
    "cost_currency": "USD",
}

PROPOSED_KEYS = {
    "sensitivity_per_fill_bps",
    "adjustment_precedence",
    "rounding_mode",
    "min_cost_per_fill_applies",
}

EXPECTED_PRECEDENCE = [
    "determine_raw_fill_price",
    "apply_arm_price_adjustments",
    "compute_per_fill_cost_on_executed_price",
    "aggregate_net_pnl_and_r",
]
ALLOWED_ROUNDING_MODES = {"none_full_precision"}

EXPECTED_PREDECESSOR_KEYS = {
    "stage1_config_pin", "stage1_cost_views_flat",
    "claims_carry_across_stages",
}

# Exact key sets for nested provenance entries (successor tightening:
# the predecessor enforced presence of individual keys only, so an entry
# with extra keys - or a PROPOSED entry with no derivation - validated).
EXPECTED_PINNED_PROV_KEYS = {"status", "citation"}
EXPECTED_PROPOSED_PROV_KEYS = {"status", "requires_review", "derivation"}
EXPECTED_STAGE1_PIN = \
    "87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706"

ALL_PARAM_KEYS = set(PINNED_VALUES) | PROPOSED_KEYS


def reject(reason):
    print(f"REJECT: {reason}", file=sys.stderr)
    return 1


def is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate_file(path, expected_sha256):
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        return reject(f"cannot read config: {exc}")

    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256.lower():
        return reject(
            f"hash mismatch: file sha256 {actual} != expected "
            f"{expected_sha256.lower()}")

    try:
        cfg = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return reject(f"unparseable JSON: {exc}")
    if not isinstance(cfg, dict):
        return reject("top level is not an object")

    keys = set(cfg)
    if keys != EXPECTED_TOP_KEYS:
        return reject(
            f"top-level key set mismatch: missing "
            f"{sorted(EXPECTED_TOP_KEYS - keys)}, unknown "
            f"{sorted(keys - EXPECTED_TOP_KEYS)}")
    if cfg["artifact"] != EXPECTED_ARTIFACT:
        return reject(f"artifact mismatch: {cfg['artifact']!r}")
    if cfg["schema_version"] != EXPECTED_SCHEMA_VERSION:
        return reject(f"schema_version mismatch: {cfg['schema_version']!r}")
    if cfg["stage"] != EXPECTED_STAGE:
        return reject(f"stage mismatch: {cfg['stage']!r}")
    if cfg["protocol"] != EXPECTED_PROTOCOL:
        return reject(f"protocol mismatch: {cfg['protocol']!r}")

    params = cfg["parameters"]
    if not isinstance(params, dict):
        return reject("parameters is not an object")
    pkeys = set(params)
    if pkeys != ALL_PARAM_KEYS:
        return reject(
            f"parameter key set mismatch: missing "
            f"{sorted(ALL_PARAM_KEYS - pkeys)}, unknown "
            f"{sorted(pkeys - ALL_PARAM_KEYS)}")

    for key, expected in PINNED_VALUES.items():
        if params[key] != expected:
            return reject(
                f"pinned parameter {key} = {params[key]!r}, frozen text "
                f"requires {expected!r}")

    # Proposed parameters: values are proposals, structure/consistency is
    # still fail-closed.
    spf = params["sensitivity_per_fill_bps"]
    if (not isinstance(spf, list) or len(spf) != 2
            or not all(is_number(x) for x in spf)):
        return reject("sensitivity_per_fill_bps must be a list of 2 numbers")
    for rt, pf in zip(params["sensitivity_round_trip_bps"], spf):
        if pf != rt / 2:
            return reject(
                f"sensitivity per-fill {pf} != round-trip {rt} / 2")
    if params["verdict_per_fill_bps"] != params["verdict_round_trip_bps"] / 2:
        return reject("verdict per-fill != round-trip / 2")
    if params["adjustment_precedence"] != EXPECTED_PRECEDENCE:
        return reject("adjustment_precedence differs from the recorded "
                      "proposal (a different order is a different config)")
    if params["rounding_mode"] not in ALLOWED_ROUNDING_MODES:
        return reject(f"rounding_mode not allowed: {params['rounding_mode']!r}")
    if params["min_cost_per_fill_applies"] is not False:
        return reject("min_cost_per_fill_applies must be false under the "
                      "recorded proposal")
    for key in ("e1_stop_slippage_atr", "e2_tp1_exceed_margin_atr"):
        if not is_number(params[key]) or params[key] < 0:
            return reject(f"{key} out of range")

    prov = cfg["provenance"]
    if not isinstance(prov, dict) or set(prov) != ALL_PARAM_KEYS:
        return reject("provenance key set must equal the parameter key set")
    for key in ALL_PARAM_KEYS:
        entry = prov[key]
        if not isinstance(entry, dict):
            return reject(f"provenance[{key}] is not an object")
        if key in PINNED_VALUES:
            if set(entry) != EXPECTED_PINNED_PROV_KEYS:
                return reject(
                    f"provenance[{key}] key set mismatch: a PINNED entry "
                    f"carries exactly {sorted(EXPECTED_PINNED_PROV_KEYS)}, "
                    f"got {sorted(entry)}")
            if entry["status"] != "PINNED":
                return reject(f"provenance[{key}] must be PINNED")
            if not isinstance(entry["citation"], str) \
                    or not entry["citation"]:
                return reject(f"provenance[{key}] lacks a citation")
        else:
            if set(entry) != EXPECTED_PROPOSED_PROV_KEYS:
                return reject(
                    f"provenance[{key}] key set mismatch: a PROPOSED entry "
                    f"carries exactly "
                    f"{sorted(EXPECTED_PROPOSED_PROV_KEYS)}, "
                    f"got {sorted(entry)}")
            if entry["status"] != "PROPOSED":
                return reject(f"provenance[{key}] must remain PROPOSED "
                              "until adjudicated")
            if entry["requires_review"] is not True:
                return reject(f"provenance[{key}] must carry "
                              "requires_review: true")
            if not isinstance(entry["derivation"], str) \
                    or not entry["derivation"]:
                return reject(f"provenance[{key}] lacks a derivation")

    pred = cfg["predecessor"]
    if not isinstance(pred, dict) or set(pred) != EXPECTED_PREDECESSOR_KEYS:
        return reject("predecessor key set mismatch")
    if pred["stage1_config_pin"] != EXPECTED_STAGE1_PIN:
        return reject("predecessor stage1_config_pin mismatch")
    if pred["stage1_cost_views_flat"] != ["gross", "4bps", "25bps"]:
        return reject("predecessor stage1_cost_views_flat mismatch")
    if pred["claims_carry_across_stages"] is not False:
        return reject("claims_carry_across_stages must be false (S8 [C05])")

    print(f"VALID: {path} sha256={actual}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--expected-sha256", required=True)
    args = ap.parse_args()
    return validate_file(args.config, args.expected_sha256)


if __name__ == "__main__":
    sys.exit(main())
