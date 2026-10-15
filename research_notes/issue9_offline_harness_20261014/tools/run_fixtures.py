#!/usr/bin/env python3
"""Deterministic adversarial fixture suite for the Issue #9 offline harness
candidate (QF-ISSUE9-RECONCILIATION-INTEGRITY-20261015-06 r1; the -03
fixtures F00-F26 are retained in expectation, F18 gained the
acceptance-side checks its boundary always implied, F27-F33 are the
adversarial fixtures for the five -04 correctness gaps, and F34-F39 are
the -05 accounting fixtures: usage captured BEFORE rejection, timeout /
connection failure as UNKNOWN + reconciliation-required (never zero),
and resume blocked until an evidence-backed reconciliation record.
F14's checks gain the timeout-accounting assertions; its stop code,
single-dispatch and single-outcome expectations are unchanged. F40-F57
are the -06 reconciliation-integrity fixtures: exact-one-target
refusals, the injected evidence-verification boundary, strict resolved
field validation, cap accounting of reconciled usage exactly once,
nonzero-resolved-cost terminal state, evidence reuse, and restart
persistence. F35 is amended ONLY where the -06 spec changes the
mechanism it exercises (structured verified evidence replaces the bare
string; a wrong-target append now refuses instead of polluting) — its
semantic expectations and the exactly-once total are unchanged).

FAKE TRANSPORT ONLY. The socket layer is patched to raise before anything
runs; the harness receives scripted in-memory transports. No provider/model
calls, no installs, no spend, no live files touched. Ledgers are written to a
temp directory; the clean-control ledger is preserved as package evidence.

Flow per scenario, mirroring the spec: the -02 preflight guard evaluates the
declared dispatch packet BEFORE any dispatch; a BLOCK means zero transport
invocations. Runtime fixtures declare a compliant plan and then let runtime
reality (responses, clock, quota, plan drift) hit the enforcement paths.

Usage: run_fixtures.py [results_out.json] [evidence_dir]
Exit code 0 iff every fixture matches its expectation.
"""
import importlib.util
import json
import os
import socket
import sys
import tempfile

# ---------------------------------------------------------------------------
# Network denial FIRST: any socket use raises, before any dispatch path runs.
# ---------------------------------------------------------------------------
class NetworkDeniedError(RuntimeError):
    pass


def _deny(*a, **k):
    raise NetworkDeniedError("network denied: offline harness candidate")


socket.socket = _deny            # class replaced: any construction raises
socket.create_connection = _deny
socket.getaddrinfo = _deny
socket.gethostbyname = _deny

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
REPO_NOTES = os.path.dirname(PKG)


def _load(mod_name, path):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H = _load("offline_harness", os.path.join(HERE, "offline_harness.py"))
GUARD = _load("preflight_guard", os.path.join(
    REPO_NOTES, "issue9_route_readiness_20261014", "tools",
    "preflight_guard.py"))

PIN = {"provider": "openrouter", "model": "vendor/example-model:free",
       "model_version": "2026-01-01"}
DAY1, DAY2 = "2026-11-02", "2026-11-03"


def price_evidence(**over):
    ev = {"verified_zero_incremental": True,
          "evidence_ref": "synthetic-fixture:catalog-2026-11-02",
          "catalog_pricing": {"prompt": "0", "completion": "0"},
          "expires_day": DAY1}
    ev.update(over)
    return ev


def call(role="propose", prompt=None, est=1000, maxout=500, **kw):
    c = {"role": role, "prompt": prompt or f"frozen prompt for {role}",
         "est_input_tokens": est, "max_output_tokens": maxout}
    c.update(kw)
    return c


def good_response(**over):
    r = {"http_status": 200, "model": PIN["model"],
         "model_version": PIN["model_version"],
         "content": "candidate card text",
         "usage": {"input_tokens": 1000, "output_tokens": 200,
                   "reasoning_tokens": 50, "billed_tokens": 1250},
         "cost_usd": 0}
    r.update(over)
    return r


class ScriptedTransport:
    """Fake transport: pops one scripted action per invocation."""

    def __init__(self, actions, clock=None):
        self.actions = list(actions)
        self.clock = clock
        self.invocations = 0

    def __call__(self, call_spec, idx):
        self.invocations += 1
        action = self.actions.pop(0) if self.actions else ("respond",
                                                           good_response(), 0)
        kind = action[0]
        if kind == "timeout":
            if self.clock and len(action) > 1:
                self.clock.advance(action[1])
            raise TimeoutError("scripted timeout")
        _, resp, advance = action
        if self.clock and advance:
            self.clock.advance(advance)
        return resp


def build_packet(calls, *, route="openrouter_direct", ev=None, pin=None):
    pin = pin or PIN
    ev = ev if ev is not None else price_evidence()
    hashes = [H.sha256_text(c["prompt"]) for c in calls]
    return {
        "route": route, "pin": pin, "arm_pins": {"A": pin, "B": pin},
        "metering": {"usage_fields": ["input_tokens", "output_tokens",
                                      "reasoning_tokens", "billed_tokens"],
                     "reasoning_tokens_exposed": True},
        "cost": {"verified_zero_incremental":
                 ev.get("verified_zero_incremental"),
                 "evidence_ref": ev.get("evidence_ref"),
                 "catalog_pricing": ev.get("catalog_pricing") or {}},
        "routing": {"allow_fallback": False, "fallback_models": [],
                    "via_gateway": None},
        "plan": {"calls": [{"arm": "A", "seed": "S1", "role": c["role"],
                            "prompt_sha256": h}
                           for c, h in zip(calls, hashes)],
                 "worst_case_billed_tokens_per_arm_seed": {"A/S1": 6000},
                 "wall_min_per_arm_seed": 5},
        "registered_prompt_hashes": hashes,
        "ledger_sample": {"lines": [],
                          "totals": {"billed_tokens": 0, "cost_usd": 0}},
        "blinding": {"key_holder": "offline-harness",
                     "grader": "external-review",
                     "shuffle_seed_recorded": True,
                     "seed_order_coin_sha256": H.sha256_text("fixture-coin")},
    }


class Scenario:
    """One arm-seed runtime scenario on a fresh temp ledger."""

    def __init__(self, tmp, name, *, arm="A", seed="S1", day=DAY1,
                 ev=None, quota=H.DAILY_QUOTA_CAP_DEFAULT, ledger_name=None,
                 evidence_verifier=None):
        self.clock = H.FakeClock(day=day)
        path = os.path.join(tmp, ledger_name or f"{name}.jsonl")
        self.ledger = H.Ledger(path, evidence_verifier=evidence_verifier)
        self.ev = ev if ev is not None else price_evidence()
        self.arm, self.seed, self.quota = arm, seed, quota
        self.transport = None

    def runner(self, transport, **kw):
        self.transport = transport
        reg = [H.sha256_text(c["prompt"]) for c in kw.pop("plan_calls")]
        return H.ArmSeedRunner(
            self.ledger, self.clock, transport, run_id="FX-RUN", arm=self.arm,
            seed=self.seed, pin=PIN, price_evidence=self.ev,
            registered_prompt_hashes=reg, daily_quota_cap=self.quota, **kw)


# ---------------------------------------------------------------------------
# -06 reconciliation evidence helpers: structured bundles + an explicit
# FAKE verifier (authenticity = issued ref, not expired; the harness
# itself enforces binding/digest integrity before the verifier runs).
# ---------------------------------------------------------------------------
ISSUED_REF = "synthetic:provider-usage-report-2026-11-02"


def make_evidence(target, *, day=DAY1, ref=ISSUED_REF,
                  provider="openrouter", account_id="acct-fixture-1",
                  expires_day=None):
    ev = {"provider": provider, "account_id": account_id, "day": day,
          "evidence_ref": ref,
          "target_outcome_hash": target["record_hash"]}
    if expires_day is not None:
        ev["expires_day"] = expires_day
    ev["digest"] = H.evidence_digest(ev)
    return ev


class FakeEvidenceVerifier:
    def __init__(self, issued=(ISSUED_REF,), today=DAY1):
        self.issued = set(issued)
        self.today = today

    def __call__(self, evidence, target):
        if evidence.get("evidence_ref") not in self.issued:
            return False
        exp = evidence.get("expires_day")
        if exp and self.today > exp:
            return False
        return True


VERIFIER = FakeEvidenceVerifier()


def recon_attempt(ledger, **kw):
    """append_reconciliation wrapper: returns (stop_code_or_None,
    records_delta). A refusal must have delta 0 — zero append."""
    before = len(ledger.records)
    try:
        ledger.append_reconciliation(**kw)
    except H.HarnessStop as stop:
        return stop.code, len(ledger.records) - before
    return None, len(ledger.records) - before


def timeout_scenario(tmp, name, *, verifier=VERIFIER):
    """Fresh scenario whose only call times out: one UNKNOWN outcome
    (usage + cost), reconciliation_required, run stopped TIMEOUT."""
    sc = Scenario(tmp, name, evidence_verifier=verifier)
    calls = [call(), call("self_critique")]
    tr = ScriptedTransport([("timeout", 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    return sc, tr, calls, code


RESULTS = []


def report(fid, mode, expect, got, checks):
    match = (got == expect) and all(checks.values())
    RESULTS.append({"id": fid, "mode": mode, "expect": expect, "got": got,
                    "checks": checks, "match": match})
    print(f"{fid:38s} expect={expect:28s} got={got:28s} match={match}")


def guard_first(fid, mode, packet):
    """Run the -02 guard; return decision dict. Caller asserts on it."""
    return GUARD.evaluate(packet)


def main():
    results_out = sys.argv[1] if len(sys.argv) > 1 else None
    evidence_dir = sys.argv[2] if len(sys.argv) > 2 else None
    if evidence_dir:
        os.makedirs(evidence_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="issue9_harness_fx_")

    # F00 — network denial is actually installed
    try:
        socket.create_connection(("example.invalid", 443), timeout=1)
        denied = False
    except NetworkDeniedError:
        denied = True
    except Exception:
        denied = False
    report("F00-network-denial", "socket layer patched before any dispatch",
           "NETWORK_DENIED", "NETWORK_DENIED" if denied else "NOT_DENIED",
           {"socket_raises": denied})

    # F01 — clean control: 3 good calls complete; chain + summary verify
    sc = Scenario(tmp, "f01")
    calls = [call("propose"), call("self_critique"), call("propose")]
    dec = guard_first("F01", "", build_packet(calls))
    tr = ScriptedTransport([("respond", good_response(), 5)] * 3, sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    ok_chain, _ = sc.ledger.verify_chain()
    summary = rn.ledger_summary()
    report("F01-clean-control", "3 compliant calls, guard PASS first",
           "COMPLETE", status,
           {"guard_pass": dec["decision"] == "PASS",
            "invocations_3": tr.invocations == 3,
            "accepted_3": len(rn.accepted) == 3,
            "chain_ok": ok_chain,
            "billed_3750": summary["totals"]["billed_tokens"] == 3750,
            "schema_keys": all(k in summary for k in
                               ("run_id", "arm", "seed", "provider", "model",
                                "model_version", "calls", "totals",
                                "budget_ref",
                                "cost_verified_zero_incremental"))})
    if evidence_dir:
        with open(os.path.join(evidence_dir, "f01_clean_control_ledger.jsonl"),
                  "w", encoding="utf-8") as fh:
            with open(sc.ledger.path, encoding="utf-8") as src:
                fh.write(src.read())
        with open(os.path.join(evidence_dir,
                               "f01_clean_control_summary.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=1)
    sc.ledger.close()

    # F02 — empty content + populated reasoning: EMPTY_CONTENT, reasoning
    # counted in the ledger, NEVER substituted as the candidate
    sc = Scenario(tmp, "f02")
    calls = [call()]
    tr = ScriptedTransport([("respond", good_response(
        content="", reasoning="long hidden reasoning text",
        usage={"input_tokens": 1000, "output_tokens": 0,
               "reasoning_tokens": 700, "billed_tokens": 1700}), 5)], sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    out = sc.ledger.outcomes("A", "S1")[0]
    report("F02-empty-content-reasoning",
           "HTTP200, content empty, reasoning populated (pilot failure mode)",
           "EMPTY_CONTENT", code,
           {"invocations_1": tr.invocations == 1,
            "accepted_0": rn.accepted == [],
            "reasoning_counted": out.get("reasoning_tokens") == 700,
            "content_not_substituted": out.get("content_sha256") is None})
    sc.ledger.close()

    # F03 — HTTP 200 with entirely empty body content
    sc = Scenario(tmp, "f03")
    tr = ScriptedTransport([("respond", good_response(
        content=None, usage={"input_tokens": 10, "output_tokens": 0,
                             "reasoning_tokens": 0, "billed_tokens": 10}),
        1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    report("F03-http200-empty", "HTTP200, content null", "EMPTY_CONTENT",
           code, {"accepted_0": rn.accepted == []})
    sc.ledger.close()

    # F04 — usage present but reasoning_tokens not exposed
    sc = Scenario(tmp, "f04")
    tr = ScriptedTransport([("respond", good_response(
        usage={"input_tokens": 100, "output_tokens": 50,
               "billed_tokens": 150}), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    report("F04-unmetered-reasoning", "usage lacks reasoning_tokens",
           "UNMETERED_REASONING", code, {"accepted_0": rn.accepted == []})
    sc.ledger.close()

    # F05 — usage object missing entirely
    sc = Scenario(tmp, "f05")
    tr = ScriptedTransport([("respond", good_response(usage=None), 1)],
                            sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    report("F05-missing-usage", "response carries no usage object",
           "MISSING_USAGE", code, {"accepted_0": rn.accepted == []})
    sc.ledger.close()

    # F06 — reported billed != input+output+reasoning
    sc = Scenario(tmp, "f06")
    tr = ScriptedTransport([("respond", good_response(
        usage={"input_tokens": 100, "output_tokens": 50,
               "reasoning_tokens": 10, "billed_tokens": 165}), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    report("F06-inconsistent-usage", "billed 165 != computed 160",
           "INCONSISTENT_USAGE", code, {"accepted_0": rn.accepted == []})
    sc.ledger.close()

    # F07 — negative usage value
    sc = Scenario(tmp, "f07")
    tr = ScriptedTransport([("respond", good_response(
        usage={"input_tokens": -5, "output_tokens": 50,
               "reasoning_tokens": 10, "billed_tokens": 55}), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    report("F07-negative-usage", "input_tokens = -5", "NEGATIVE_USAGE", code,
           {"accepted_0": rn.accepted == []})
    sc.ledger.close()

    # F08 — nonzero catalog price: preflight guard BLOCKs, zero dispatch
    ev = price_evidence(catalog_pricing={"prompt": "0.0001",
                                         "completion": "0"})
    dec = guard_first("F08", "", build_packet([call()], ev=ev))
    report("F08-nonzero-price", "catalog prompt price 0.0001 (guard, plan-level)",
           "BLOCK:PRICE_NONZERO",
           f"{dec['decision']}:{','.join(dec['reasons'])}",
           {"reason_present": "PRICE_NONZERO" in dec["reasons"]})

    # F09 — unknown catalog price: preflight guard BLOCKs
    ev = price_evidence(catalog_pricing={"prompt": None, "completion": "0"})
    dec = guard_first("F09", "", build_packet([call()], ev=ev))
    report("F09-unknown-price", "catalog prompt price null (guard)",
           "BLOCK:PRICE_UNKNOWN",
           f"{dec['decision']}:{','.join(dec['reasons'])}",
           {"reason_present": "PRICE_UNKNOWN" in dec["reasons"]})

    # F10 — expired price evidence: runtime fail-closed before dispatch
    sc = Scenario(tmp, "f10", ev=price_evidence(expires_day="2026-11-01"))
    tr = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    report("F10-price-evidence-expired", "evidence expired before run day",
           "PRICE_EVIDENCE_EXPIRED", code,
           {"invocations_0": tr.invocations == 0})
    sc.ledger.close()

    # F10b — missing price evidence ref: preflight guard BLOCKs
    ev = price_evidence(evidence_ref=None)
    dec = guard_first("F10b", "", build_packet([call()], ev=ev))
    report("F10b-price-evidence-missing", "no evidence_ref (guard)",
           "BLOCK:COST_NOT_VERIFIED",
           f"{dec['decision']}:{','.join(dec['reasons'])}",
           {"reason_present": "COST_NOT_VERIFIED" in dec["reasons"]})

    # F11 — model alias swap: response model != pinned model
    sc = Scenario(tmp, "f11")
    tr = ScriptedTransport([("respond", good_response(
        model="vendor/other-model:free"), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    report("F11-model-alias-swap", "response model differs from pin",
           "MODEL_MISMATCH", code,
           {"invocations_1": tr.invocations == 1,
            "accepted_0": rn.accepted == []})
    sc.ledger.close()

    # F12 — silent fallback flagged by provider metadata
    sc = Scenario(tmp, "f12")
    tr = ScriptedTransport([("respond", good_response(fallback_used=True), 1)],
                            sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    report("F12-silent-fallback", "response reports fallback_used",
           "FALLBACK_DETECTED", code, {"accepted_0": rn.accepted == []})
    sc.ledger.close()

    # F13 — response carries no model version metadata (alias drift
    # unverifiable -> inconclusive, fail closed)
    sc = Scenario(tmp, "f13")
    tr = ScriptedTransport([("respond", good_response(model_version=None),
                             1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    report("F13-model-version-unverifiable", "no provider version metadata",
           "MODEL_VERSION_UNVERIFIABLE", code,
           {"accepted_0": rn.accepted == []})
    sc.ledger.close()

    # F14 — timeout: exactly one dispatch, recorded once, NO retry
    sc = Scenario(tmp, "f14")
    tr = ScriptedTransport([("timeout", 3), ("respond", good_response(), 1)],
                            sc.clock)
    rn = sc.runner(tr, plan_calls=[call(), call("self_critique")])
    status, code = rn.run([call(), call("self_critique")])
    outs = sc.ledger.outcomes("A", "S1")
    report("F14-timeout-no-retry", "transport times out; spare response unused",
           "TIMEOUT", code,
           {"invocations_1": tr.invocations == 1,
            "one_outcome": len(outs) == 1
            and outs[0]["status"] == "FAILED_TIMEOUT",
            "billed_0": sc.ledger.billed_total("A", "S1") == 0,
            "timeout_unknown_accounting":
            outs[0].get("billed_tokens") is None
            and outs[0].get("usage_or_cost_status")
            == H.UNKNOWN_INTERRUPTED_CALL_USAGE_OR_COST
            and outs[0].get("cost_usd") is None
            and outs[0].get("reconciliation_required") is True})
    sc.ledger.close()

    # F15 — provider free-quota exhaustion (test cap 3, same code path as 50)
    sc = Scenario(tmp, "f15", quota=3)
    calls = [call("propose"), call("self_critique")] * 3
    calls = calls[:5]
    tr = ScriptedTransport([("respond", good_response(), 1)] * 5, sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    report("F15-quota-exhaustion", "daily quota cap 3 (injected), 5 planned",
           "QUOTA_EXHAUSTED", code,
           {"invocations_3": tr.invocations == 3,
            "recorded_3": len(sc.ledger.recorded_calls("A", "S1")) == 3})
    sc.ledger.close()

    # F16a/F16b — call-cap boundaries (declared plan compliant; runtime fed
    # one extra call -> runtime cap enforcement)
    for fid, arm, cap_n in (("F16a-call-cap-A", "A", 8),
                            ("F16b-call-cap-B", "B", 16)):
        sc = Scenario(tmp, fid.lower(), arm=arm)
        role = "propose" if arm == "A" else "proposer"
        declared = [call(role) for _ in range(cap_n)]
        runtime = declared + [call(role)]
        tr = ScriptedTransport([("respond", good_response(), 0)] * (cap_n + 1),
                               sc.clock)
        rn = sc.runner(tr, plan_calls=declared)
        status, code = rn.run(runtime)
        report(fid, f"arm {arm} cap {cap_n}, runtime fed {cap_n + 1} calls",
               "CEILING_CALLS", code,
               {"invocations_at_cap": tr.invocations == cap_n,
                "recorded_at_cap":
                    len(sc.ledger.recorded_calls(arm, "S1")) == cap_n})
        sc.ledger.close()

    # F17 — token-cap boundary: reservation for call 2 would exceed 120k
    sc = Scenario(tmp, "f17")
    big = good_response(usage={"input_tokens": 100000,
                               "output_tokens": 15000,
                               "reasoning_tokens": 4500,
                               "billed_tokens": 119500})
    calls = [call(est=100000, maxout=20000), call(est=400, maxout=200)]
    tr = ScriptedTransport([("respond", big, 1),
                            ("respond", good_response(), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    report("F17-token-cap-boundary",
           "119,500 billed; next reservation 600 -> 120,100 > 120,000",
           "CEILING_TOKENS", code,
           {"invocations_1": tr.invocations == 1,
            "billed_119500": sc.ledger.billed_total("A", "S1") == 119500})
    sc.ledger.close()

    # F18 — wall-time boundary: clock jumps 46 min during call 1
    sc = Scenario(tmp, "f18")
    calls = [call(), call("self_critique")]
    tr = ScriptedTransport([("respond", good_response(), 46 * 60),
                            ("respond", good_response(), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    report("F18-wall-time-boundary",
           "call 1 responds at 46 min: cap fires at acceptance (-04), "
           "call 2 never dispatched",
           "CEILING_WALL", code,
           {"invocations_1": tr.invocations == 1,
            "accepted_0": rn.accepted == [],
            "recorded_0": len(sc.ledger.recorded_calls("A", "S1")) == 0})
    sc.ledger.close()

    # F19 — response larger than reservation: hard stop, content quarantined
    sc = Scenario(tmp, "f19")
    over = good_response(usage={"input_tokens": 1000, "output_tokens": 5000,
                                "reasoning_tokens": 0, "billed_tokens": 6000})
    calls = [call(est=1000, maxout=100), call("self_critique")]
    tr = ScriptedTransport([("respond", over, 1),
                            ("respond", good_response(), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    out = sc.ledger.outcomes("A", "S1")[0]
    report("F19-response-overrun", "output 5000 > reserved 100",
           "OVERRUN", code,
           {"invocations_1": tr.invocations == 1,
            "accepted_0": rn.accepted == [],
            "quarantined": out.get("content_quarantined") is True,
            "usage_counted": out.get("billed_tokens") == 6000})
    sc.ledger.close()

    # F20 — process interruption between response and ledger append:
    # restart sees ORPHANED ledger; no blind resend, no double count
    sc = Scenario(tmp, "f20")
    calls = [call(), call("self_critique")]
    tr = ScriptedTransport([("respond", good_response(), 1)] * 2, sc.clock)

    class CrashOnSecond:
        def __init__(self, inner, runner_holder):
            self.inner, self.holder = inner, runner_holder

        def __call__(self, spec, idx):
            if idx == 1:
                self.holder["rn"].crash_after_response = True
            return self.inner(spec, idx)

    holder = {}
    rn = sc.runner(tr, plan_calls=calls)
    holder["rn"] = rn
    rn.transport = CrashOnSecond(tr, holder)
    crashed = False
    try:
        rn.run(calls)
    except H.SimulatedCrash:
        crashed = True
    sc.ledger.close()
    led2 = H.Ledger(sc.ledger.path)
    state, why = H.resume_state(led2)
    rn2 = H.ArmSeedRunner(led2, sc.clock, tr, run_id="FX-RUN", arm="A",
                          seed="S1", pin=PIN, price_evidence=sc.ev,
                          registered_prompt_hashes=[H.sha256_text(
                              c["prompt"]) for c in calls])
    status2, code2 = rn2.run([call()], start_index=2)
    report("F20-crash-restart-orphan",
           "crash after response, before outcome append; restart refuses",
           "ORPHANED", state,
           {"crashed": crashed,
            "resume_blocked": code2 == "ORPHANED_LEDGER",
            "invocations_2_total": tr.invocations == 2,
            "recorded_1": len(led2.recorded_calls("A", "S1")) == 1,
            "billed_counted_once": led2.billed_total("A", "S1") == 1250})
    led2.close()

    # F21/F22 — interrupted multi-day continuation: quota reset only on
    # verified evidence
    for fid, with_evidence, expect, want_dispatch in (
            ("F21-multiday-no-evidence", False, "QUOTA_RESET_UNVERIFIED", 0),
            ("F22-multiday-with-evidence", True, "COMPLETE", 1)):
        sc = Scenario(tmp, fid.lower(), quota=2,
                      ev=price_evidence(expires_day=DAY2),
                      ledger_name=f"{fid.lower()}.jsonl")
        calls = [call(), call("self_critique"), call()]
        tr = ScriptedTransport([("respond", good_response(), 1)] * 3, sc.clock)
        rn = sc.runner(tr, plan_calls=calls)
        status1, code1 = rn.run(calls)
        sc.ledger.close()
        # next-day process: new clock, same ledger
        led2 = H.Ledger(sc.ledger.path)
        clock2 = H.FakeClock(day=DAY2)
        if with_evidence:
            H.apply_quota_reset(led2, day=DAY2,
                                evidence_ref="synthetic:quota-headroom-day2")
        tr2 = ScriptedTransport([("respond", good_response(), 1)], clock2)
        rn2 = H.ArmSeedRunner(led2, clock2, tr2, run_id="FX-RUN", arm="A",
                              seed="S1", pin=PIN,
                              price_evidence=price_evidence(
                                  expires_day=DAY2),
                              registered_prompt_hashes=[H.sha256_text(
                                  c["prompt"]) for c in calls],
                              daily_quota_cap=2)
        status2, code2 = rn2.run([calls[2]], start_index=2)
        got = status2 if status2 == "COMPLETE" else code2
        report(fid,
               f"day1 quota exhausted; day2 resume "
               f"{'with' if with_evidence else 'without'} reset evidence",
               expect, got,
               {"day1_quota_stop": code1 == "QUOTA_EXHAUSTED",
                "day2_dispatches": tr2.invocations == want_dispatch,
                "reset_recorded": (DAY2 in led2.quota_reset_days())
                == with_evidence})
        led2.close()

    # F23 — prompt contamination at runtime: plan drifts to an unregistered
    # prompt containing cross-arm material -> blocked before dispatch
    sc = Scenario(tmp, "f23")
    clean = call()
    drifted = call("self_critique",
                   prompt="ARM B SEALED OUTPUT leaked into arm A prompt")
    tr = ScriptedTransport([("respond", good_response(), 1)] * 2, sc.clock)
    rn = sc.runner(tr, plan_calls=[clean])   # only clean prompt registered
    status, code = rn.run([clean, drifted])
    report("F23-prompt-contamination", "call 2 prompt unregistered/cross-arm",
           "PROMPT_CONTAMINATION", code,
           {"invocations_1": tr.invocations == 1,
            "recorded_1": len(sc.ledger.recorded_calls("A", "S1")) == 1})
    sc.ledger.close()

    # F24 — forbidden route: preflight guard BLOCKs before any dispatch
    dec = guard_first("F24", "", build_packet([call()], route="omniroute"))
    report("F24-preflight-forbidden-route", "route=omniroute (guard)",
           "BLOCK:ROUTE_FORBIDDEN",
           f"{dec['decision']}:{','.join(dec['reasons'])}",
           {"reason_present": "ROUTE_FORBIDDEN" in dec["reasons"]})

    # F25 — frozen seed order enforced
    guard = H.SeedOrderGuard()
    blocked = None
    try:
        guard.begin("S2")
    except H.HarnessStop as stop:
        blocked = stop.code
    guard2 = H.SeedOrderGuard()
    for s in ("S1", "S2", "S3"):
        guard2.begin(s)
    report("F25-seed-order", "S2 first blocked; S1,S2,S3 accepted in order",
           "SEED_ORDER_VIOLATION", blocked or "NOT_BLOCKED",
           {"order_ok": guard2.started == ["S1", "S2", "S3"]})

    # F26 — provider reports nonzero cost at runtime despite $0 catalog
    sc = Scenario(tmp, "f26")
    tr = ScriptedTransport([("respond", good_response(cost_usd=0.01), 1)],
                            sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    report("F26-nonzero-cost-response", "response cost_usd = 0.01",
           "NONZERO_COST", code, {"accepted_0": rn.accepted == []})
    sc.ledger.close()

    # ------------------------------------------------------------------
    # -04 adversarial fixtures (F27-F33): one or more per correctness gap
    # from ChatGPT's HOLD (Issue #1 comment 6180610281)
    # ------------------------------------------------------------------
    # F27 — gap 1: version SUBSTITUTION (nonempty, != pin) must fail.
    # -03 checked only absence (F13); a substituted version passed.
    sc = Scenario(tmp, "f27")
    tr = ScriptedTransport([("respond", good_response(
        model_version="2026-06-15"), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    out = sc.ledger.outcomes("A", "S1")[0]
    report("F27-version-substitution",
           "response model_version '2026-06-15' != pinned '2026-01-01'",
           "MODEL_VERSION_MISMATCH", code,
           {"invocations_1": tr.invocations == 1,
            "accepted_0": rn.accepted == [],
            "versions_recorded":
                out.get("response_version") == "2026-06-15"
                and out.get("pinned_version") == PIN["model_version"]})
    sc.ledger.close()

    # F28 — gap 2: cost evidence MISSING (key absent) must stop and stay
    # unknown; -03 normalized it to $0 and claimed verified-zero.
    sc = Scenario(tmp, "f28")
    resp = good_response()
    del resp["cost_usd"]
    tr = ScriptedTransport([("respond", resp, 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    out = sc.ledger.outcomes("A", "S1")[0]
    report("F28-cost-missing", "response carries no cost_usd at all",
           "COST_EVIDENCE_MISSING", code,
           {"invocations_1": tr.invocations == 1,
            "accepted_0": rn.accepted == [],
            "recorded_unknown": out.get("cost_usd") is None
            and out.get("cost_evidence_status") == "MISSING"})
    sc.ledger.close()

    # F29 — gap 2: NaN cost is not numeric-finite evidence
    sc = Scenario(tmp, "f29")
    tr = ScriptedTransport([("respond", good_response(
        cost_usd=float("nan")), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    out = sc.ledger.outcomes("A", "S1")[0]
    report("F29-cost-nan", "response cost_usd = NaN",
           "COST_EVIDENCE_INVALID", code,
           {"accepted_0": rn.accepted == [],
            "recorded_unknown": out.get("cost_usd") is None
            and out.get("cost_evidence_status") == "NON_FINITE"})
    sc.ledger.close()

    # F30 — gap 2: string cost "0" is not numeric evidence
    sc = Scenario(tmp, "f30")
    tr = ScriptedTransport([("respond", good_response(cost_usd="0"), 1)],
                            sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    out = sc.ledger.outcomes("A", "S1")[0]
    report("F30-cost-string", "response cost_usd = '0' (string)",
           "COST_EVIDENCE_INVALID", code,
           {"accepted_0": rn.accepted == [],
            "recorded_unknown": out.get("cost_usd") is None
            and out.get("cost_evidence_status") == "NON_NUMERIC"})
    sc.ledger.close()

    # F31 — gap 3: SINGLE/FINAL call arriving at 46 min must be
    # quarantined, never accepted (-03 accepted it; F18 only proved a
    # SECOND call was blocked pre-dispatch)
    sc = Scenario(tmp, "f31")
    calls = [call()]
    tr = ScriptedTransport([("respond", good_response(), 46 * 60)], sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    out = sc.ledger.outcomes("A", "S1")[0]
    report("F31-wall-final-call-overrun",
           "the only call responds after 46 min elapsed",
           "CEILING_WALL", code,
           {"invocations_1": tr.invocations == 1,
            "accepted_0": rn.accepted == [],
            "recorded_0": len(sc.ledger.recorded_calls("A", "S1")) == 0,
            "status_wall_overrun": out.get("status")
            == "FAILED_WALL_OVERRUN",
            "quarantined": out.get("content_quarantined") is True,
            "usage_counted": out.get("billed_tokens") == 1250})
    sc.ledger.close()

    # F32 — gap 4: TAMPERED historical ledger reopened: chain verification
    # gates BEFORE dispatch; zero transport invocations
    sc = Scenario(tmp, "f32")
    calls = [call()]
    tr = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status1, code1 = rn.run(calls)
    path = sc.ledger.path
    sc.ledger.close()
    with open(path, encoding="utf-8") as fh:
        recs = [json.loads(line) for line in fh if line.strip()]
    for r in recs:
        if r["type"] == "call_outcome":
            r["billed_tokens"] = 999999   # history rewritten, hashes stale
    with open(path, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    led2 = H.Ledger(path)
    state, why = H.resume_state(led2)
    tr2 = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn2 = H.ArmSeedRunner(led2, sc.clock, tr2, run_id="FX-RUN", arm="A",
                          seed="S1", pin=PIN, price_evidence=sc.ev,
                          registered_prompt_hashes=[H.sha256_text(
                              calls[0]["prompt"])])
    status2, code2 = rn2.run([call()], start_index=1)
    report("F32-tampered-ledger-no-dispatch",
           "historical outcome rewritten on disk; reopen + resume attempted",
           "CORRUPT", state,
           {"setup_complete": status1 == "COMPLETE",
            "run_blocked": code2 == "LEDGER_CORRUPT",
            "invocations_0": tr2.invocations == 0})
    led2.close()

    # F33 — gap 5 (claim correction): crash after the response on the
    # ONLY call. The interrupted call's true cost is UNKNOWN — preserved
    # as UNKNOWN_INTERRUPTED_CALL_COST + reconciliation-required in the
    # ledger, never silently zero, never silently exact; no resend.
    sc = Scenario(tmp, "f33")
    calls = [call()]
    tr = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=calls, crash_after_response=True)
    crashed = False
    try:
        rn.run(calls)
    except H.SimulatedCrash:
        crashed = True
    sc.ledger.close()
    led2 = H.Ledger(sc.ledger.path)
    state, why = H.resume_state(led2)
    tr2 = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn2 = H.ArmSeedRunner(led2, sc.clock, tr2, run_id="FX-RUN", arm="A",
                          seed="S1", pin=PIN, price_evidence=sc.ev,
                          registered_prompt_hashes=[H.sha256_text(
                              calls[0]["prompt"])])
    status2, code2 = rn2.run([call()], start_index=1)
    stops = [r for r in led2.records if r["type"] == "run_stop"]
    last_stop = stops[-1] if stops else {}
    report("F33-crash-unknown-cost",
           "crash after response, before outcome append; restart refuses",
           "ORPHANED", state,
           {"crashed": crashed,
            "resume_blocked": code2 == "ORPHANED_LEDGER",
            "no_resend": tr.invocations == 1 and tr2.invocations == 0,
            "unknown_state": led2.interrupted_cost_state()
            == H.UNKNOWN_INTERRUPTED_CALL_COST,
            "stop_records_unknown": last_stop.get("interrupted_call_cost")
            == "UNKNOWN_INTERRUPTED_CALL_COST",
            "reconciliation_required":
                last_stop.get("reconciliation_required") is True,
            "interrupted_listed":
                last_stop.get("interrupted_calls") == [
                    {"arm": "A", "seed": "S1", "call_index": 0}],
            "nothing_zero_filled": led2.billed_total("A", "S1") == 0
            and len(led2.outcomes("A", "S1")) == 0})
    led2.close()


    # ------------------------------------------------------------------
    # -05 accounting fixtures (F34-F39): usage captured BEFORE rejection;
    # timeout/connection failure = UNKNOWN + reconciliation-required,
    # never zero; resume blocked until evidence-backed reconciliation.
    # Spec: Issue #1 comment 6181708698, fixtures (a)-(d).
    # ------------------------------------------------------------------
    # F34 — (a) model-version mismatch + valid usage => rejected with the
    # reason preserved, tokens captured and counted exactly once. Cost
    # was authoritatively reported ($0), so no reconciliation is owed.
    sc = Scenario(tmp, "f34")
    tr = ScriptedTransport([("respond", good_response(
        model_version="2026-06-15"), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    out = sc.ledger.outcomes("A", "S1")[0]
    report("F34-mismatch-usage-counted",
           "version substitution + fully valid usage/cost",
           "MODEL_VERSION_MISMATCH", code,
           {"invocations_1": tr.invocations == 1,
            "accepted_0": rn.accepted == [],
            "tokens_counted_once": out.get("billed_tokens") == 1250
            and sc.ledger.billed_total("A", "S1") == 1250,
            "usage_fields_exact": out.get("input_tokens") == 1000
            and out.get("output_tokens") == 200
            and out.get("reasoning_tokens") == 50,
            "versions_recorded": out.get("response_version") == "2026-06-15"
            and out.get("pinned_version") == PIN["model_version"],
            "cost_known_zero": out.get("cost_usd") == 0,
            "no_reconciliation_owed":
                out.get("reconciliation_required") is not True})
    sc.ledger.close()

    # F35 — (b) missing cost + valid usage => rejected, tokens counted,
    # cost UNKNOWN + reconciliation-required; resume stays BLOCKED until
    # an explicit evidence-backed reconciliation record resolves THIS
    # call — no-evidence and wrong-call reconciliations do not clear it.
    sc = Scenario(tmp, "f35", evidence_verifier=VERIFIER)
    resp = good_response()
    del resp["cost_usd"]
    calls = [call(), call("self_critique")]
    tr = ScriptedTransport([("respond", resp, 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    out = sc.ledger.outcomes("A", "S1")[0]
    state1, _ = H.resume_state(sc.ledger)
    tr_b = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn_b = sc.runner(tr_b, plan_calls=calls)
    status_b, code_b = rn_b.run([calls[1]], start_index=1)
    miss_code, miss_delta = recon_attempt(
        sc.ledger, arm="A", seed="S1", call_index=0, evidence=None)
    recon_refused = miss_code == "RECONCILIATION_EVIDENCE_MISSING" \
        and miss_delta == 0
    # -06: a wrong-target reconciliation now REFUSES before append
    # (RECONCILIATION_TARGET_UNKNOWN, zero ledger change) instead of
    # being appended as pollution that merely fails to clear — the
    # semantic expectation (block NOT cleared) is unchanged.
    wrong_code, wrong_delta = recon_attempt(
        sc.ledger, arm="A", seed="S1", call_index=99,
        evidence=make_evidence(out))
    wrong_refused = wrong_code == "RECONCILIATION_TARGET_UNKNOWN" \
        and wrong_delta == 0
    state2, _ = H.resume_state(sc.ledger)
    sc.ledger.append_reconciliation(
        arm="A", seed="S1", call_index=0,
        evidence=make_evidence(out),
        resolved_billed_tokens=1250, resolved_cost_usd=0)
    state3, _ = H.resume_state(sc.ledger)
    tr_c = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn_c = sc.runner(tr_c, plan_calls=calls)
    status_c, code_c = rn_c.run([calls[1]], start_index=1)
    report("F35-cost-unknown-reconciliation",
           "cost key absent + valid usage; resume gated on reconciliation",
           "COST_EVIDENCE_MISSING", code,
           {"invocations_1": tr.invocations == 1,
            "accepted_0": rn.accepted == [],
            "tokens_counted": out.get("billed_tokens") == 1250,
            "cost_unknown": out.get("cost_usd") is None
            and out.get("usage_or_cost_status")
            == H.UNKNOWN_INTERRUPTED_CALL_USAGE_OR_COST
            and out.get("reconciliation_required") is True,
            "resume_state_blocked": state1 == "RECONCILIATION_REQUIRED",
            "resume_refused": code_b == "RECONCILIATION_REQUIRED"
            and tr_b.invocations == 0,
            "recon_needs_evidence": recon_refused,
            "wrong_call_recon_refused": wrong_refused,
            "wrong_call_recon_no_clear":
                state2 == "RECONCILIATION_REQUIRED",
            "recon_clears": state3 == "CLEAN",
            "resume_completes": status_c == "COMPLETE"
            and tr_c.invocations == 1,
            "total_counted_once_each":
                sc.ledger.billed_total("A", "S1") == 2500})
    sc.ledger.close()

    # F36 — (c) HTTP rejection + valid usage in the error body =>
    # rejected, tokens captured and counted exactly once.
    sc = Scenario(tmp, "f36")
    tr = ScriptedTransport([("respond", good_response(http_status=500), 1)],
                            sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    out = sc.ledger.outcomes("A", "S1")[0]
    report("F36-http-rejection-usage-counted",
           "HTTP 500 + fully valid usage/cost in the response body",
           "HTTP_NOT_200", code,
           {"invocations_1": tr.invocations == 1,
            "accepted_0": rn.accepted == [],
            "status_failed_http": out.get("status") == "FAILED_HTTP",
            "tokens_counted_once": out.get("billed_tokens") == 1250
            and sc.ledger.billed_total("A", "S1") == 1250})
    sc.ledger.close()

    # F37 — (c) fallback rejection + valid usage => rejected, tokens
    # captured and counted exactly once.
    sc = Scenario(tmp, "f37")
    tr = ScriptedTransport([("respond", good_response(fallback_used=True),
                             1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    out = sc.ledger.outcomes("A", "S1")[0]
    report("F37-fallback-rejection-usage-counted",
           "fallback_used + fully valid usage/cost",
           "FALLBACK_DETECTED", code,
           {"invocations_1": tr.invocations == 1,
            "accepted_0": rn.accepted == [],
            "status_failed_fallback": out.get("status") == "FAILED_FALLBACK",
            "tokens_counted_once": out.get("billed_tokens") == 1250
            and sc.ledger.billed_total("A", "S1") == 1250})
    sc.ledger.close()

    # F38 — (d) timeout => usage and cost UNKNOWN, reconciliation
    # required, zero resends, no zero-filled accounting, resume BLOCKED.
    sc = Scenario(tmp, "f38")
    calls = [call(), call("self_critique")]
    tr = ScriptedTransport([("timeout", 3), ("respond", good_response(), 1)],
                            sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    outs = sc.ledger.outcomes("A", "S1")
    out = outs[0]
    state, _ = H.resume_state(sc.ledger)
    tr2 = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn2 = sc.runner(tr2, plan_calls=calls)
    status2, code2 = rn2.run([calls[1]], start_index=1)
    report("F38-timeout-unknown-accounting",
           "timeout: UNKNOWN accounting, no resend, resume blocked",
           "TIMEOUT", code,
           {"invocations_1": tr.invocations == 1,
            "one_outcome": len(outs) == 1
            and out["status"] == "FAILED_TIMEOUT",
            "usage_unknown_not_zero": out.get("billed_tokens") is None
            and out.get("usage_or_cost_status")
            == H.UNKNOWN_INTERRUPTED_CALL_USAGE_OR_COST,
            "cost_unknown": out.get("cost_usd") is None
            and out.get("cost_evidence_status") == "UNKNOWN",
            "reconciliation_required":
                out.get("reconciliation_required") is True,
            "resume_blocked": state == "RECONCILIATION_REQUIRED"
            and code2 == "RECONCILIATION_REQUIRED"
            and tr2.invocations == 0,
            "nothing_counted": sc.ledger.billed_total("A", "S1") == 0})
    sc.ledger.close()

    # F39 — (d) connection failure after dispatch => identical UNKNOWN
    # treatment (a non-timeout transport exception zero-filled nothing).
    sc = Scenario(tmp, "f39")

    class ConnFailTransport:
        def __init__(self, clock):
            self.clock = clock
            self.invocations = 0

        def __call__(self, spec, idx):
            self.invocations += 1
            self.clock.advance(2)
            raise ConnectionError("scripted connection reset post-dispatch")

    calls = [call(), call("self_critique")]
    tr = ConnFailTransport(sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    outs = sc.ledger.outcomes("A", "S1")
    out = outs[0]
    state, _ = H.resume_state(sc.ledger)
    tr2 = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn2 = sc.runner(tr2, plan_calls=calls)
    status2, code2 = rn2.run([calls[1]], start_index=1)
    report("F39-connfail-unknown-accounting",
           "ConnectionError post-dispatch: UNKNOWN accounting, resume blocked",
           "TRANSPORT_EXCEPTION", code,
           {"invocations_1": tr.invocations == 1,
            "one_outcome": len(outs) == 1
            and out["status"] == "FAILED_TRANSPORT_EXCEPTION",
            "exception_recorded": out.get("exception_type")
            == "ConnectionError",
            "usage_unknown_not_zero": out.get("billed_tokens") is None
            and out.get("usage_or_cost_status")
            == H.UNKNOWN_INTERRUPTED_CALL_USAGE_OR_COST,
            "cost_unknown": out.get("cost_usd") is None
            and out.get("cost_evidence_status") == "UNKNOWN",
            "reconciliation_required":
                out.get("reconciliation_required") is True,
            "resume_blocked": state == "RECONCILIATION_REQUIRED"
            and code2 == "RECONCILIATION_REQUIRED"
            and tr2.invocations == 0,
            "nothing_counted": sc.ledger.billed_total("A", "S1") == 0})
    sc.ledger.close()

    # ------------------------------------------------------------------
    # -06 reconciliation-integrity fixtures (F40-F58): spec Issue #1
    # comment 6187987162 points 1-6. Every negative must produce ZERO
    # append and ZERO dispatch; the block it guards must remain in force.
    # ------------------------------------------------------------------
    # F40 — arbitrary string evidence (the pre--06 gate) refuses: both
    # as the evidence argument and via the legacy evidence_ref kwarg.
    sc, tr, calls, code0 = timeout_scenario(tmp, "f40")
    out = sc.ledger.outcomes("A", "S1")[0]
    c1, d1 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence="arbitrary string, trust me",
                           resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    c2, d2 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence_ref="arbitrary string, trust me",
                           resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    state, _ = H.resume_state(sc.ledger)
    report("F40-arbitrary-string-evidence",
           "bare-string evidence (old nonempty gate) must not clear",
           "TIMEOUT", code0,
           {"string_evidence_refused":
                c1 == "RECONCILIATION_EVIDENCE_MALFORMED" and d1 == 0,
            "legacy_ref_refused":
                c2 == "RECONCILIATION_EVIDENCE_MALFORMED" and d2 == 0,
            "still_blocked": state == "RECONCILIATION_REQUIRED"})
    sc.ledger.close()

    # F41 — verifier rejects: unissued ref, then expired evidence.
    sc, tr, calls, code0 = timeout_scenario(
        tmp, "f41", verifier=FakeEvidenceVerifier(issued=()))
    out = sc.ledger.outcomes("A", "S1")[0]
    c1, d1 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence=make_evidence(out),
                           resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    sc.ledger.evidence_verifier = VERIFIER
    c2, d2 = recon_attempt(
        sc.ledger, arm="A", seed="S1", call_index=0,
        evidence=make_evidence(out, expires_day="2026-11-01"),
        resolved_billed_tokens=1250, resolved_cost_usd=0)
    state, _ = H.resume_state(sc.ledger)
    report("F41-verifier-rejects-evidence",
           "unissued ref and expired evidence both fail verification",
           "TIMEOUT", code0,
           {"unissued_refused": c1 == "RECONCILIATION_EVIDENCE_UNVERIFIED"
            and d1 == 0,
            "expired_refused": c2 == "RECONCILIATION_EVIDENCE_UNVERIFIED"
            and d2 == 0,
            "still_blocked": state == "RECONCILIATION_REQUIRED"})
    sc.ledger.close()

    # F42 — verifier raises: refusal, never an exception escape.
    def boom_verifier(evidence, target):
        raise RuntimeError("verifier exploded")

    sc, tr, calls, code0 = timeout_scenario(tmp, "f42",
                                            verifier=boom_verifier)
    out = sc.ledger.outcomes("A", "S1")[0]
    c1, d1 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence=make_evidence(out),
                           resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    report("F42-verifier-exception",
           "verifier raising must refuse fail-closed, zero append",
           "TIMEOUT", code0,
           {"verifier_error_refused":
            c1 == "RECONCILIATION_EVIDENCE_VERIFIER_ERROR" and d1 == 0})
    sc.ledger.close()

    # F43 — no verifier injected: even a well-formed bundle cannot clear.
    sc, tr, calls, code0 = timeout_scenario(tmp, "f43", verifier=None)
    out = sc.ledger.outcomes("A", "S1")[0]
    c1, d1 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence=make_evidence(out),
                           resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    report("F43-no-verifier-configured",
           "no injected verifier -> evidence unverifiable, fail closed",
           "TIMEOUT", code0,
           {"unverifiable_refused":
            c1 == "RECONCILIATION_EVIDENCE_UNVERIFIABLE" and d1 == 0})
    sc.ledger.close()

    # F44 — wrong target: no outcome exists at the named call.
    sc, tr, calls, code0 = timeout_scenario(tmp, "f44")
    out = sc.ledger.outcomes("A", "S1")[0]
    c1, d1 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=7,
                           evidence=make_evidence(out),
                           resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    report("F44-wrong-target-refused",
           "reconciliation naming a nonexistent call refuses pre-append",
           "TIMEOUT", code0,
           {"target_unknown_refused":
            c1 == "RECONCILIATION_TARGET_UNKNOWN" and d1 == 0})
    sc.ledger.close()

    # F45 — target exists but is NOT outstanding (clean recorded call).
    sc = Scenario(tmp, "f45", evidence_verifier=VERIFIER)
    tr = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    status, code = rn.run([call()])
    out = sc.ledger.outcomes("A", "S1")[0]
    c1, d1 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence=make_evidence(out),
                           resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    report("F45-target-not-outstanding",
           "reconciling a clean RECORDED call refuses pre-append",
           "COMPLETE", status,
           {"not_outstanding_refused":
            c1 == "RECONCILIATION_TARGET_NOT_OUTSTANDING" and d1 == 0})
    sc.ledger.close()

    # F46 — duplicate reconciliation of an already-resolved call refuses.
    sc, tr, calls, code0 = timeout_scenario(tmp, "f46")
    out = sc.ledger.outcomes("A", "S1")[0]
    c1, d1 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence=make_evidence(out),
                           resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    total_after_first = sc.ledger.billed_total("A", "S1")
    c2, d2 = recon_attempt(
        sc.ledger, arm="A", seed="S1", call_index=0,
        evidence=make_evidence(out, ref=ISSUED_REF + "-second-report"),
        resolved_billed_tokens=1250, resolved_cost_usd=0)
    report("F46-duplicate-reconciliation",
           "second resolution of the same call refuses; totals unchanged",
           "TIMEOUT", code0,
           {"first_accepted": c1 is None and d1 == 1,
            "duplicate_refused": c2 == "RECONCILIATION_DUPLICATE"
            and d2 == 0,
            "total_unchanged": total_after_first == 1250
            and sc.ledger.billed_total("A", "S1") == 1250})
    sc.ledger.close()

    # F47 — evidence honestly issued for a DIFFERENT call's outcome.
    # (The foreign scenario needs a distinct prompt: the suite is fully
    # deterministic, so an identical scenario would produce a byte-
    # identical ledger and the "foreign" outcome hash would coincide.)
    sc, tr, calls, code0 = timeout_scenario(tmp, "f47")
    sc2 = Scenario(tmp, "f47b", evidence_verifier=VERIFIER)
    calls2 = [call(prompt="frozen prompt for propose (foreign f47)"),
              call("self_critique")]
    tr2 = ScriptedTransport([("timeout", 1)], sc2.clock)
    rn2f = sc2.runner(tr2, plan_calls=calls2)
    rn2f.run(calls2)
    out = sc.ledger.outcomes("A", "S1")[0]
    foreign = sc2.ledger.outcomes("A", "S1")[0]
    c1, d1 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence=make_evidence(foreign),
                           resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    report("F47-evidence-target-mismatch",
           "evidence binds another outcome's hash; refuses pre-append",
           "TIMEOUT", code0,
           {"foreign_hash_distinct":
            foreign["record_hash"] != out["record_hash"],
            "target_mismatch_refused":
            c1 == "RECONCILIATION_EVIDENCE_TARGET_MISMATCH" and d1 == 0})
    sc.ledger.close()
    sc2.ledger.close()

    # F48 — bundle digest tampered after issuance.
    sc, tr, calls, code0 = timeout_scenario(tmp, "f48")
    out = sc.ledger.outcomes("A", "S1")[0]
    ev = make_evidence(out)
    ev["digest"] = "0" * 64
    c1, d1 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence=ev, resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    report("F48-evidence-digest-mismatch",
           "digest not recomputing over the bundle refuses pre-append",
           "TIMEOUT", code0,
           {"digest_mismatch_refused":
            c1 == "RECONCILIATION_EVIDENCE_DIGEST_MISMATCH" and d1 == 0})
    sc.ledger.close()

    # F49 — evidence issued for the wrong day (self-consistent digest).
    sc, tr, calls, code0 = timeout_scenario(tmp, "f49")
    out = sc.ledger.outcomes("A", "S1")[0]
    c1, d1 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence=make_evidence(out, day=DAY2),
                           resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    report("F49-evidence-day-mismatch",
           "evidence day != dispatch day refuses pre-append",
           "TIMEOUT", code0,
           {"day_mismatch_refused":
            c1 == "RECONCILIATION_EVIDENCE_DAY_MISMATCH" and d1 == 0})
    sc.ledger.close()

    # F50 — partial resolution: each single-dimension attempt refuses;
    # the target's usage AND cost were both UNKNOWN (timeout).
    sc, tr, calls, code0 = timeout_scenario(tmp, "f50")
    out = sc.ledger.outcomes("A", "S1")[0]
    c1, d1 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence=make_evidence(out),
                           resolved_cost_usd=0)
    c2, d2 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence=make_evidence(out),
                           resolved_billed_tokens=100)
    state, _ = H.resume_state(sc.ledger)
    report("F50-partial-resolution-refused",
           "resolving only one of two unknown dimensions refuses",
           "TIMEOUT", code0,
           {"cost_only_refused":
            c1 == "RECONCILIATION_RESOLUTION_INCOMPLETE" and d1 == 0,
            "tokens_only_refused":
            c2 == "RECONCILIATION_RESOLUTION_INCOMPLETE" and d2 == 0,
            "still_blocked": state == "RECONCILIATION_REQUIRED"})
    sc.ledger.close()

    # F51 — strictly invalid resolved field values all refuse.
    sc, tr, calls, code0 = timeout_scenario(tmp, "f51")
    out = sc.ledger.outcomes("A", "S1")[0]
    bad_tokens = ["1250", True, -5, 1250.5]
    bad_costs = [float("nan"), float("inf"), -0.01, "0", True]
    tok_codes = [recon_attempt(
        sc.ledger, arm="A", seed="S1", call_index=0,
        evidence=make_evidence(out), resolved_billed_tokens=v,
        resolved_cost_usd=0) for v in bad_tokens]
    cost_codes = [recon_attempt(
        sc.ledger, arm="A", seed="S1", call_index=0,
        evidence=make_evidence(out), resolved_billed_tokens=1250,
        resolved_cost_usd=v) for v in bad_costs]
    state, _ = H.resume_state(sc.ledger)
    report("F51-invalid-resolved-fields",
           "string/bool/negative/float tokens; NaN/inf/negative/string/"
           "bool cost — all refuse with zero append",
           "TIMEOUT", code0,
           {"tokens_all_refused": all(
               c == "RECONCILIATION_TOKENS_INVALID" and d == 0
               for c, d in tok_codes),
            "costs_all_refused": all(
                c == "RECONCILIATION_COST_INVALID" and d == 0
                for c, d in cost_codes),
            "still_blocked": state == "RECONCILIATION_REQUIRED"})
    sc.ledger.close()

    # F52 — resolved value contradicting an originally KNOWN dimension
    # is a conflict: (i) tokens vs known usage, (ii) cost vs known cost.
    sc = Scenario(tmp, "f52", evidence_verifier=VERIFIER)
    resp = good_response()
    del resp["cost_usd"]
    tr = ScriptedTransport([("respond", resp, 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=[call()])
    rn.run([call()])
    out = sc.ledger.outcomes("A", "S1")[0]      # usage 1250 KNOWN
    c1, d1 = recon_attempt(sc.ledger, arm="A", seed="S1", call_index=0,
                           evidence=make_evidence(out),
                           resolved_billed_tokens=9999,
                           resolved_cost_usd=0)
    sc_b = Scenario(tmp, "f52b", evidence_verifier=VERIFIER)
    tr_b = ScriptedTransport([("respond", good_response(usage=None), 1)],
                             sc_b.clock)
    rn_b = sc_b.runner(tr_b, plan_calls=[call()])
    rn_b.run([call()])
    out_b = sc_b.ledger.outcomes("A", "S1")[0]  # cost 0 KNOWN, usage unknown
    c2, d2 = recon_attempt(sc_b.ledger, arm="A", seed="S1", call_index=0,
                           evidence=make_evidence(out_b),
                           resolved_billed_tokens=1250,
                           resolved_cost_usd=5)
    report("F52-conflicting-resolution",
           "resolved values contradicting known dimensions refuse",
           "COST_EVIDENCE_MISSING", rn.stopped[0] if rn.stopped else None,
           {"tokens_conflict_refused":
            c1 == "RECONCILIATION_RESOLUTION_CONFLICT" and d1 == 0,
            "cost_conflict_refused":
            c2 == "RECONCILIATION_RESOLUTION_CONFLICT" and d2 == 0,
            "setup_dims": out.get("billed_tokens") == 1250
            and out_b.get("cost_usd") == 0})
    sc.ledger.close()
    sc_b.ledger.close()

    # F53 — unknown usage reconciled NEAR the cap: the effective total
    # governs the next reservation; resume stops at CEILING_TOKENS.
    sc, tr, calls, code0 = timeout_scenario(tmp, "f53")
    out = sc.ledger.outcomes("A", "S1")[0]
    sc.ledger.append_reconciliation(
        arm="A", seed="S1", call_index=0, evidence=make_evidence(out),
        resolved_billed_tokens=119500, resolved_cost_usd=0)
    state, _ = H.resume_state(sc.ledger)
    tr2 = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn2 = sc.runner(tr2, plan_calls=calls)
    status2, code2 = rn2.run([calls[1]], start_index=1)
    report("F53-reconciled-near-cap",
           "resolved 119,500 + next reservation 600 > 120,000 ceiling",
           "TIMEOUT", code0,
           {"recon_clears_block": state == "CLEAN",
            "effective_total": sc.ledger.billed_total("A", "S1") == 119500,
            "resume_ceiling": code2 == "CEILING_TOKENS",
            "zero_dispatch": tr2.invocations == 0})
    sc.ledger.close()

    # F54 — unknown usage reconciled OVER the cap: recorded truthfully,
    # resume can never dispatch again under the ceiling.
    sc, tr, calls, code0 = timeout_scenario(tmp, "f54")
    out = sc.ledger.outcomes("A", "S1")[0]
    sc.ledger.append_reconciliation(
        arm="A", seed="S1", call_index=0, evidence=make_evidence(out),
        resolved_billed_tokens=120001, resolved_cost_usd=0)
    tr2 = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn2 = sc.runner(tr2, plan_calls=calls)
    status2, code2 = rn2.run([calls[1]], start_index=1)
    report("F54-reconciled-over-cap",
           "resolved 120,001 already exceeds the 120,000 ceiling",
           "TIMEOUT", code0,
           {"effective_total": sc.ledger.billed_total("A", "S1") == 120001,
            "resume_ceiling": code2 == "CEILING_TOKENS",
            "zero_dispatch": tr2.invocations == 0})
    sc.ledger.close()

    # F55 — known usage + unknown cost: reconciling cost alone must NOT
    # double-count the already-known 1,250 tokens.
    sc = Scenario(tmp, "f55", evidence_verifier=VERIFIER)
    resp = good_response()
    del resp["cost_usd"]
    calls = [call(), call("self_critique")]
    tr = ScriptedTransport([("respond", resp, 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    out = sc.ledger.outcomes("A", "S1")[0]
    sc.ledger.append_reconciliation(
        arm="A", seed="S1", call_index=0, evidence=make_evidence(out),
        resolved_cost_usd=0)
    mid_total = sc.ledger.billed_total("A", "S1")
    tr2 = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn2 = sc.runner(tr2, plan_calls=calls)
    status2, code2 = rn2.run([calls[1]], start_index=1)
    report("F55-known-usage-not-double-counted",
           "cost-only reconciliation; known usage counted exactly once",
           "COST_EVIDENCE_MISSING", code,
           {"mid_total_once": mid_total == 1250,
            "resume_completes": status2 == "COMPLETE",
            "final_total": sc.ledger.billed_total("A", "S1") == 2500})
    sc.ledger.close()

    # F56 — nonzero resolved cost: recorded authoritatively, terminal
    # NONZERO_COST — never a clean resume under the $0 protocol.
    sc = Scenario(tmp, "f56", evidence_verifier=VERIFIER)
    resp = good_response()
    del resp["cost_usd"]
    calls = [call(), call("self_critique")]
    tr = ScriptedTransport([("respond", resp, 1)], sc.clock)
    rn = sc.runner(tr, plan_calls=calls)
    status, code = rn.run(calls)
    out = sc.ledger.outcomes("A", "S1")[0]
    sc.ledger.append_reconciliation(
        arm="A", seed="S1", call_index=0, evidence=make_evidence(out),
        resolved_cost_usd=0.02)
    rec = [r for r in sc.ledger.records
           if r["type"] == "reconciliation"][0]
    state, _ = H.resume_state(sc.ledger)
    tr2 = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn2 = sc.runner(tr2, plan_calls=calls)
    status2, code2 = rn2.run([calls[1]], start_index=1)
    report("F56-nonzero-resolved-cost",
           "authoritative nonzero cost resolves the unknown but is "
           "terminal, never a clean resume",
           "COST_EVIDENCE_MISSING", code,
           {"recorded_terminal": rec.get("resolution_status")
            == "NONZERO_COST",
            "state_nonzero": state == "NONZERO_COST",
            "run_refused": code2 == "NONZERO_COST",
            "zero_dispatch": tr2.invocations == 0,
            "usage_counted_once": sc.ledger.billed_total("A", "S1")
            == 1250})
    sc.ledger.close()

    # F57 — restart persistence: a valid reconciliation survives close /
    # reopen twice; the resolved value is counted exactly once after
    # every restart, and the resumed run completes.
    sc, tr, calls, code0 = timeout_scenario(tmp, "f57")
    path = sc.ledger.path
    sc.ledger.close()
    led2 = H.Ledger(path, evidence_verifier=VERIFIER)
    state1, _ = H.resume_state(led2)
    out = led2.outcomes("A", "S1")[0]
    led2.append_reconciliation(
        arm="A", seed="S1", call_index=0, evidence=make_evidence(out),
        resolved_billed_tokens=1250, resolved_cost_usd=0)
    state2, _ = H.resume_state(led2)
    led2.close()
    led3 = H.Ledger(path, evidence_verifier=VERIFIER)
    state3, _ = H.resume_state(led3)
    total3 = led3.billed_total("A", "S1")
    tr3 = ScriptedTransport([("respond", good_response(), 1)], sc.clock)
    rn3 = H.ArmSeedRunner(led3, sc.clock, tr3, run_id="FX-RUN", arm="A",
                          seed="S1", pin=PIN, price_evidence=sc.ev,
                          registered_prompt_hashes=[H.sha256_text(
                              c["prompt"]) for c in calls])
    status3, code3 = rn3.run([calls[1]], start_index=1)
    report("F57-restart-after-reconciliation",
           "reopen: blocked -> reconcile -> reopen: clean, counted once, "
           "resume completes",
           "TIMEOUT", code0,
           {"blocked_before": state1 == "RECONCILIATION_REQUIRED",
            "clean_after": state2 == "CLEAN" and state3 == "CLEAN",
            "counted_once_after_restart": total3 == 1250,
            "resume_completes": status3 == "COMPLETE",
            "final_total": led3.billed_total("A", "S1") == 2500})
    led3.close()

    # F58 — evidence reuse across calls: arm A's exact evidence bundle
    # presented for arm B's outstanding call refuses (identity already
    # used); B stays blocked. One shared ledger, sequential runs.
    clock58 = H.FakeClock(day=DAY1)
    led58 = H.Ledger(os.path.join(tmp, "f58.jsonl"),
                     evidence_verifier=VERIFIER)

    def run_timeout58(arm, role):
        c58 = [call(role)]
        tr58 = ScriptedTransport([("timeout", 1)], clock58)
        rn58 = H.ArmSeedRunner(led58, clock58, tr58, run_id="FX-RUN",
                               arm=arm, seed="S1", pin=PIN,
                               price_evidence=price_evidence(),
                               registered_prompt_hashes=[H.sha256_text(
                                   c58[0]["prompt"])])
        rn58.run(c58)
        return tr58

    trA = run_timeout58("A", "propose")
    outA = led58.outcomes("A", "S1")[0]
    evA = make_evidence(outA)
    cA, dA = recon_attempt(led58, arm="A", seed="S1", call_index=0,
                           evidence=evA, resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    trB = run_timeout58("B", "proposer")
    cB, dB = recon_attempt(led58, arm="B", seed="S1", call_index=0,
                           evidence=evA, resolved_billed_tokens=1250,
                           resolved_cost_usd=0)
    state58, _ = H.resume_state(led58)
    report("F58-evidence-reuse-across-calls",
           "identical evidence identity presented for a second call",
           "RECONCILIATION_EVIDENCE_REUSED", cB,
           {"first_accepted": cA is None and dA == 1,
            "b_dispatched": trB.invocations == 1,
            "reuse_zero_append": dB == 0,
            "b_still_blocked": state58 == "RECONCILIATION_REQUIRED",
            "totals": led58.billed_total("A", "S1") == 1250
            and led58.billed_total("B", "S1") == 0})
    led58.close()

    ok = all(r["match"] for r in RESULTS)
    summary = {"task": "QF-ISSUE9-RECONCILIATION-INTEGRITY-20261015-06 r1",
               "fixtures_total": len(RESULTS),
               "fixtures_matched": sum(1 for r in RESULTS if r["match"]),
               "all_match": ok, "results": RESULTS}
    if results_out:
        with open(results_out, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=1)
    print(f"{summary['fixtures_matched']}/{summary['fixtures_total']} "
          f"fixtures matched — {'ALL MATCH' if ok else 'MISMATCH PRESENT'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
