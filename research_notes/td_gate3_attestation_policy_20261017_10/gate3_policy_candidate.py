#!/usr/bin/env python3
"""QF-TD-GATE3-ATTESTATION-POLICY-20261017-10 r1 — OFFLINE CANDIDATE ONLY.

Candidate replacement body for gate 3 ("account_plan_status_capacity") of
dispatch_gate_r3.py (pin 8564b2da...). The r3 original demands evidence
fields (plan == "Basic", standing == "good", minute_cap) that the only
documented account endpoint, GET /api_usage, never returns. This candidate
validates the DOCUMENTED /api_usage response schema plus mechanically
derived formulas, under a frozen execution policy (A: 52-credit ceiling,
B: 51-credit ceiling). It makes no network calls and is not adopted.

Documented schema (Twelve Data public docs, /api_usage section, retrieved
2026-10-17; preserved snapshot: -09 endpoint_proof.json sha256 4c898a28...):
  {timestamp, current_usage, plan_limit, daily_usage, plan_daily_limit,
   plan_category}; cost 1 API credit per request; documented error body
  {code, message, status} with code table 400/401/403/404/414/429/500.
Documented tier limits (public pricing page, retrieved 2026-10-17, and
preserved program record TD_ACQUISITION_ADAPTER_PREFLIGHT_20261013.md):
  the tier the program names "Basic": 8 credits/minute, 800 credits/day.

Clause labels (see evidence_map.json):
  - freshness: DOCUMENTED field (timestamp, UTC default per docs params)
    + packet max-age pin (3600 s, inherited from r3 packet).
  - plan identity/entitlement: DERIVED - the joint limit pair
    (plan_limit == 8 and plan_daily_limit == 800) identifies the tier's
    entitlements. plan_category is RECORDED, never used as identity proof:
    its value vocabulary is documented only by a single example
    ("enterprise"), so no literal "Basic" string match is possible.
  - standing: DERIVED as "successful authenticated service availability" -
    a schema-complete success response, given the documented error
    semantics (401 invalid key / 403 lacks permission / 429 limit), attests
    key validity + entitlement + not-rate-limited at observation time.
    Account standing as a distinct billing state is UNATTESTABLE from any
    documented route and is NOT a gate clause here.
  - daily capacity: DERIVED WITH FORMULA
        daily_remaining = plan_daily_limit - daily_usage
    Policy A requires daily_remaining >= 52 at evidence time: the status
    request itself costs 1 credit (documented) and is conservatively
    assumed NOT self-counted in its own response, so post-check remaining
    >= 51 for the unchanged 51-request manifest.
    Policy B requires daily_remaining >= 51 and caps the data budget at
    daily_remaining - 1 = 50, which does NOT satisfy the frozen 51-request
    full manifest (see policy_B.json consequence).
  - minute capacity: DERIVED - plan_limit == 8 (tier pin) and
    current_usage < plan_limit at observation time (headroom >= 1). The
    status request is conservatively assumed to occupy one minute credit
    (same documented credit unit); run pacing stays with the limiter.
  - counter consistency: daily_usage <= plan_daily_limit,
    current_usage <= plan_limit, all counters non-negative integers, and
    daily_usage >= the shared ledger's same-day reserved credits (the
    local ledger must never claim less than the vendor counter shows as
    still available; vendor usage below local reservations is a
    contradiction -> FAIL).
"""
import json
from datetime import datetime, timezone

TIER_MINUTE_LIMIT = 8          # documented 8 credits/min tier
TIER_DAILY_LIMIT = 800         # documented 800 credits/day tier
MANIFEST_CREDITS = 51          # frozen full-manifest screen
STATUS_REQUEST_CREDITS = 1     # documented /api_usage cost
MAX_AGE_S = 3600               # packet pin inherited from r3 gate
FUTURE_SKEW_S = 60

REQUIRED_FIELDS = ("timestamp", "current_usage", "plan_limit",
                   "daily_usage", "plan_daily_limit", "plan_category")


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _parse_ts(s):
    # Documented example format "2025-05-07 11:10:12" (UTC default).
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return dt.timestamp()


def validate_gate3(raw, packet, now):
    """Return (status, code, detail). status in {PASS, FAIL, UNKNOWN}.

    raw    = the /api_usage response body as a dict (already fetched in a
             future live task; here always a fixture).
    packet = frozen packet fields: policy_id ("A"/"B"), ceiling_credits,
             ledger_same_day_reserved (int, from the shared ledger).
    now    = evaluation time, epoch seconds (injected; deterministic).
    """
    if not isinstance(raw, dict):
        return ("UNKNOWN", "ACCOUNT_EVIDENCE_MISSING", "response not an object")
    if raw.get("status") == "error" or "code" in raw and "message" in raw:
        return ("FAIL", "ACCOUNT_ERROR_RESPONSE",
                "documented error body, code=%s" % raw.get("code"))
    for f in REQUIRED_FIELDS:
        if f not in raw or raw[f] is None:
            return ("UNKNOWN", "ACCOUNT_FIELD_ABSENT", "missing field %s" % f)
    counters = ("current_usage", "plan_limit", "daily_usage", "plan_daily_limit")
    if not all(_is_int(raw[f]) for f in counters):
        return ("UNKNOWN", "ACCOUNT_SCHEMA_TYPE", "counter not an integer")
    if not isinstance(raw["plan_category"], str) or not raw["plan_category"]:
        return ("UNKNOWN", "ACCOUNT_SCHEMA_TYPE", "plan_category not a string")
    try:
        observed = _parse_ts(raw["timestamp"])
    except Exception:
        return ("UNKNOWN", "ACCOUNT_SCHEMA_TYPE", "timestamp unparseable")

    policy = packet.get("policy_id")
    ceiling = packet.get("ceiling_credits")
    expected_ceiling = {"A": 52, "B": 51}.get(policy)
    if expected_ceiling is None or ceiling != expected_ceiling:
        return ("FAIL", "COST_BUDGET_MISMATCH",
                "packet ceiling %r does not match policy %r" % (ceiling, policy))

    age = now - observed
    if age < -FUTURE_SKEW_S or age > MAX_AGE_S:
        return ("FAIL", "ACCOUNT_EVIDENCE_STALE", "age %.0fs" % age)

    if raw["plan_limit"] != TIER_MINUTE_LIMIT or raw["plan_daily_limit"] != TIER_DAILY_LIMIT:
        return ("FAIL", "ACCOUNT_PLAN_LIMITS_MISMATCH",
                "limits %s/%s, tier pin %s/%s" % (
                    raw["plan_limit"], raw["plan_daily_limit"],
                    TIER_MINUTE_LIMIT, TIER_DAILY_LIMIT))

    if min(raw[f] for f in counters) < 0 or raw["daily_usage"] > raw["plan_daily_limit"] \
            or raw["current_usage"] > raw["plan_limit"]:
        return ("FAIL", "ACCOUNT_COUNTERS_INCONSISTENT", "counter out of range")
    ledger_today = packet.get("ledger_same_day_reserved", 0)
    if raw["daily_usage"] < ledger_today:
        return ("FAIL", "ACCOUNT_COUNTERS_INCONSISTENT",
                "vendor daily_usage %d < ledger same-day reserved %d"
                % (raw["daily_usage"], ledger_today))

    if raw["current_usage"] >= raw["plan_limit"]:
        return ("FAIL", "ACCOUNT_MINUTE_CAPACITY_EXHAUSTED",
                "current_usage %d of %d" % (raw["current_usage"], raw["plan_limit"]))

    daily_remaining = raw["plan_daily_limit"] - raw["daily_usage"]
    if policy == "A":
        # Post-check remaining = daily_remaining - 1 (status credit,
        # conservatively not self-counted) must still fit the manifest.
        if daily_remaining < STATUS_REQUEST_CREDITS + MANIFEST_CREDITS:
            return ("FAIL", "ACCOUNT_CAPACITY_INSUFFICIENT",
                    "daily_remaining %d < 52 (1 status + 51 manifest)" % daily_remaining)
        return ("PASS", "ACCOUNT_VERIFIED_POLICY_A",
                "daily_remaining %d; post-check >= 51; minute headroom %d"
                % (daily_remaining, raw["plan_limit"] - raw["current_usage"]))
    # Policy B: ceiling stays 51; the status credit displaces one data
    # request, so a PASS here certifies only a 50-request data budget.
    if daily_remaining < 51:
        return ("FAIL", "ACCOUNT_CAPACITY_INSUFFICIENT",
                "daily_remaining %d < 51 total ceiling" % daily_remaining)
    return ("PASS", "ACCOUNT_VERIFIED_POLICY_B_SHORTFALL",
            "data budget %d < manifest %d: full-manifest qualification INVALID"
            % (daily_remaining - STATUS_REQUEST_CREDITS, MANIFEST_CREDITS))
