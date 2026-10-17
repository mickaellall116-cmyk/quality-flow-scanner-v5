#!/usr/bin/env python3
"""Offline gate-3 policy test suite for QF-TD-...-10 r1.
Deterministic: a fixed NOW is injected; no network, no clock, no RNG.
Prints one canonical JSON matrix line; run twice under `unshare -n` and
the matrices must be byte-identical."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate3_policy_candidate import validate_gate3

NOW = 1792213267  # fixed epoch (2026-10-17T05:01:07Z); fixtures derive from it
from datetime import datetime, timezone
def ts(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def base(**over):
    r = {"timestamp": ts(NOW - 300), "current_usage": 3, "plan_limit": 8,
         "daily_usage": 700, "plan_daily_limit": 800, "plan_category": "basic"}
    r.update(over)
    return r

def pkt(policy, **over):
    p = {"policy_id": policy, "ceiling_credits": {"A": 52, "B": 51}[policy],
         "ledger_same_day_reserved": 0}
    p.update(over)
    return p

CASES = []
def case(name, raw, packet, expect_status, expect_code):
    CASES.append((name, raw, packet, expect_status, expect_code))

# Boundary daily_remaining under policy A (required >= 52 -> usage <= 748)
for rem, st, code in ((50, "FAIL", "ACCOUNT_CAPACITY_INSUFFICIENT"),
                      (51, "FAIL", "ACCOUNT_CAPACITY_INSUFFICIENT"),
                      (52, "PASS", "ACCOUNT_VERIFIED_POLICY_A"),
                      (53, "PASS", "ACCOUNT_VERIFIED_POLICY_A")):
    case("A_remaining_%d" % rem, base(daily_usage=800 - rem), pkt("A"), st, code)
# Boundary daily_remaining under policy B (required >= 51, PASS = shortfall)
for rem, st, code in ((50, "FAIL", "ACCOUNT_CAPACITY_INSUFFICIENT"),
                      (51, "PASS", "ACCOUNT_VERIFIED_POLICY_B_SHORTFALL"),
                      (52, "PASS", "ACCOUNT_VERIFIED_POLICY_B_SHORTFALL")):
    case("B_remaining_%d" % rem, base(daily_usage=800 - rem), pkt("B"), st, code)
# Stale + future timestamps
case("stale_timestamp", base(timestamp=ts(NOW - 7200)), pkt("A"), "FAIL", "ACCOUNT_EVIDENCE_STALE")
case("future_timestamp", base(timestamp=ts(NOW + 3600)), pkt("A"), "FAIL", "ACCOUNT_EVIDENCE_STALE")
# Wrong plan tier (Grow documented pair 55/min is not in docs text; use the
# documented enterprise example pair 20000/100000 as the non-tier fixture)
case("wrong_plan_limits_enterprise", base(plan_limit=20000, plan_daily_limit=100000,
     daily_usage=12500, current_usage=4003, plan_category="enterprise"),
     pkt("A"), "FAIL", "ACCOUNT_PLAN_LIMITS_MISMATCH")
case("wrong_plan_daily_only", base(plan_daily_limit=801), pkt("A"), "FAIL", "ACCOUNT_PLAN_LIMITS_MISMATCH")
# Insufficient minute remainder (minute window full)
case("minute_exhausted", base(current_usage=8), pkt("A"), "FAIL", "ACCOUNT_MINUTE_CAPACITY_EXHAUSTED")
# Inconsistent counters
case("inconsistent_daily_over", base(daily_usage=801), pkt("A"), "FAIL", "ACCOUNT_COUNTERS_INCONSISTENT")
case("inconsistent_minute_over", base(current_usage=9), pkt("A"), "FAIL", "ACCOUNT_COUNTERS_INCONSISTENT")
case("inconsistent_negative", base(daily_usage=-1), pkt("A"), "FAIL", "ACCOUNT_COUNTERS_INCONSISTENT")
case("inconsistent_vs_ledger", base(daily_usage=100), pkt("A", ledger_same_day_reserved=101),
     "FAIL", "ACCOUNT_COUNTERS_INCONSISTENT")
case("consistent_vs_ledger", base(daily_usage=100), pkt("A", ledger_same_day_reserved=100),
     "PASS", "ACCOUNT_VERIFIED_POLICY_A")
# Error response (documented body)
case("error_401", {"code": 401, "message": "Invalid or incorrect API key", "status": "error"},
     pkt("A"), "FAIL", "ACCOUNT_ERROR_RESPONSE")
case("error_429", {"code": 429, "message": "API request limit reached", "status": "error"},
     pkt("A"), "FAIL", "ACCOUNT_ERROR_RESPONSE")
# Absent field / wrong types
r = base(); del r["plan_limit"]
case("absent_plan_limit", r, pkt("A"), "UNKNOWN", "ACCOUNT_FIELD_ABSENT")
r = base(); del r["plan_category"]
case("absent_plan_category", r, pkt("A"), "UNKNOWN", "ACCOUNT_FIELD_ABSENT")
case("absent_response", {}, pkt("A"), "UNKNOWN", "ACCOUNT_FIELD_ABSENT")
case("type_float_counter", base(daily_usage=700.5), pkt("A"), "UNKNOWN", "ACCOUNT_SCHEMA_TYPE")
case("type_bad_timestamp", base(timestamp="not-a-time"), pkt("A"), "UNKNOWN", "ACCOUNT_SCHEMA_TYPE")
# Cost-budget mismatch: ceiling must equal the policy's frozen ceiling
case("budget_mismatch_A_ceiling51", base(), {"policy_id": "A", "ceiling_credits": 51,
     "ledger_same_day_reserved": 0}, "FAIL", "COST_BUDGET_MISMATCH")
case("budget_mismatch_B_ceiling52", base(), {"policy_id": "B", "ceiling_credits": 52,
     "ledger_same_day_reserved": 0}, "FAIL", "COST_BUDGET_MISMATCH")
# plan_category is recorded, never identity proof: a weird category string
# with correct tier limits still passes (identity = joint limit pair)
case("category_recorded_not_proving", base(plan_category="enterprise"), pkt("A"),
     "PASS", "ACCOUNT_VERIFIED_POLICY_A")

def main():
    rows, fails = [], 0
    for name, raw, packet, es, ec in CASES:
        st, code, detail = validate_gate3(raw, packet, NOW)
        ok = (st == es and code == ec)
        fails += (not ok)
        rows.append({"case": name, "status": st, "code": code, "expect": [es, ec], "ok": ok})
    matrix = {"suite": "gate3_policy_r1", "cases": len(rows), "failures": fails, "rows": rows}
    print(json.dumps(matrix, sort_keys=True, separators=(",", ":")))
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
