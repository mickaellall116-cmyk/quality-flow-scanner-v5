#!/usr/bin/env python3
"""Issue #9 route-readiness: OFFLINE fail-closed PRE-DISPATCH guard (synthetic only).

Repairs defect D-R2-01 (QF-ISSUE9-ROUTE-READINESS-20261014-02): the frozen prep
package states the four pin requirements as prose + a ledger schema, but no code
checked them BEFORE a first call. This guard evaluates a *proposed dispatch
packet* (run-manifest draft + plan + sample ledger + blinding plan) against the
frozen protocol v1.0.0 caps and pin requirements and returns PASS or BLOCK with
stable reason codes. It makes NO network calls and executes nothing.

A PASS means only: "this plan, as declared, violates no offline-checkable rule."
It does NOT verify the route. Same-day catalog price, account quota, response
model identity, per-call usage presence, and fallback absence remain
execution-time checks (see memo §5).

Usage: preflight_guard.py <fixtures.json> [results_out.json]
Each fixture: {"id","mode","expect"("PASS"|"BLOCK"),"packet":{...}}
Exit code 0 iff every fixture's guard decision matches its expectation.
"""
import json
import sys

TOKEN_CAP_PER_ARM_SEED = 120000          # frozen protocol v1.0.0
CALL_CAPS = {"A": 8, "B": 16}            # frozen protocol v1.0.0
WALL_CAP_MIN = 45                        # frozen protocol v1.0.0
FORBIDDEN_ROUTES = {"omniroute", "mirofish", "claude_direct_unmetered"}
ALIAS_MODELS = {"auto", "auto/best-free", "openrouter/auto"}
REQUIRED_USAGE_FIELDS = {"input_tokens", "output_tokens",
                         "reasoning_tokens", "billed_tokens"}


def evaluate(packet):
    reasons = []

    route = packet.get("route")
    if route in FORBIDDEN_ROUTES:
        reasons.append("ROUTE_FORBIDDEN")

    # --- Pin: one model/provider/version, identical for both arms ----------
    pin = packet.get("pin") or {}
    arm_pins = packet.get("arm_pins") or {}
    for arm in ("A", "B"):
        ap = arm_pins.get(arm)
        if not ap or any(ap.get(k) != pin.get(k)
                         for k in ("provider", "model", "model_version")):
            reasons.append("PIN_ARM_MISMATCH")
            break
    model = pin.get("model") or ""
    if (not pin.get("provider") or not model or not pin.get("model_version")
            or model in ALIAS_MODELS or ":latest" in model):
        reasons.append("PIN_ALIAS_OR_UNPINNED")

    # --- Metering: complete per-call usage incl. reasoning -----------------
    metering = packet.get("metering") or {}
    fields = set(metering.get("usage_fields") or [])
    if not REQUIRED_USAGE_FIELDS.issubset(fields):
        reasons.append("METERING_MISSING")
    if metering.get("reasoning_tokens_exposed") is not True:
        reasons.append("REASONING_UNMETERED")

    # --- Cost: verified zero incremental, price known and exactly 0 --------
    cost = packet.get("cost") or {}
    pricing = cost.get("catalog_pricing") or {}
    for leg in ("prompt", "completion"):
        val = pricing.get(leg)
        if val is None:
            reasons.append("PRICE_UNKNOWN")
        elif str(val) not in ("0", "0.0"):
            reasons.append("PRICE_NONZERO")
    if cost.get("verified_zero_incremental") is not True \
            or not cost.get("evidence_ref"):
        reasons.append("COST_NOT_VERIFIED")

    # --- No silent fallback -------------------------------------------------
    routing = packet.get("routing") or {}
    if routing.get("allow_fallback") is True \
            or (routing.get("fallback_models") or []) \
            or routing.get("via_gateway"):
        reasons.append("FALLBACK_ALLOWED")

    # --- Ceilings: calls / tokens / wall per arm-seed -----------------------
    plan = packet.get("plan") or {}
    counts = {}
    for call in plan.get("calls") or []:
        key = (call.get("arm"), call.get("seed"))
        counts[key] = counts.get(key, 0) + 1
    for (arm, _seed), n in counts.items():
        if arm in CALL_CAPS and n > CALL_CAPS[arm]:
            reasons.append("CEILING_CALLS")
    worst = plan.get("worst_case_billed_tokens_per_arm_seed") or {}
    if any(v > TOKEN_CAP_PER_ARM_SEED for v in worst.values()):
        reasons.append("CEILING_TOKENS")
    if (plan.get("wall_min_per_arm_seed") or 0) > WALL_CAP_MIN:
        reasons.append("CEILING_WALL")

    # --- Prompt integrity: only registered frozen prompts, no cross-arm ---
    registered = set(packet.get("registered_prompt_hashes") or [])
    for call in plan.get("calls") or []:
        if call.get("prompt_sha256") not in registered:
            reasons.append("PROMPT_CONTAMINATION")
            break
        if call.get("contains_cross_arm_material") is True:
            reasons.append("PROMPT_CONTAMINATION")
            break

    # --- Ledger continuity (sample lines must be a valid ledger prefix) ---
    ledger = packet.get("ledger_sample") or {}
    lines = ledger.get("lines") or []
    totals = ledger.get("totals") or {}
    idx = [ln.get("call_index") for ln in lines]
    if idx != list(range(len(lines))):
        reasons.append("LEDGER_DISCONTINUITY")
    elif sum(ln.get("billed_tokens", 0) for ln in lines) \
            != totals.get("billed_tokens"):
        reasons.append("LEDGER_DISCONTINUITY")
    if totals.get("cost_usd") not in (0, 0.0, None) and lines:
        reasons.append("LEDGER_DISCONTINUITY")

    # --- Blinding / order preconditions -------------------------------------
    blind = packet.get("blinding") or {}
    if not blind.get("key_holder") or blind.get("key_holder") == blind.get("grader"):
        reasons.append("BLINDING_FAILURE")
    if blind.get("shuffle_seed_recorded") is not True:
        reasons.append("BLINDING_FAILURE")
    if not blind.get("seed_order_coin_sha256"):
        reasons.append("BLINDING_FAILURE")

    return {"decision": "BLOCK" if reasons else "PASS",
            "reasons": sorted(set(reasons))}


def main():
    fixtures = json.load(open(sys.argv[1]))
    results, ok = [], True
    for fx in fixtures:
        got = evaluate(fx["packet"])
        match = got["decision"] == fx["expect"]
        if fx["expect"] == "BLOCK":
            want = set(fx.get("expect_reasons_contains") or [])
            match = match and want.issubset(set(got["reasons"]))
        ok = ok and match
        results.append({"id": fx["id"], "mode": fx["mode"],
                        "expect": fx["expect"], "got": got["decision"],
                        "reasons": got["reasons"], "match": match})
        print(f"{fx['id']:34s} expect={fx['expect']:5s} got={got['decision']:5s} "
              f"match={match} reasons={got['reasons']}")
    if len(sys.argv) > 2:
        json.dump(results, open(sys.argv[2], "w"), indent=1)
    print("ALL FIXTURES MATCH" if ok else "MISMATCH PRESENT")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
