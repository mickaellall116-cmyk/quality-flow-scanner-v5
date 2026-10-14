#!/usr/bin/env python3
"""Deterministic adversarial fixture suite for the Issue #9 offline harness
candidate (QF-ISSUE9-OFFLINE-HARNESS-CORRECTNESS-20261014-04 r1; the -03
fixtures F00-F26 are retained unchanged in expectation, F18 gains the
acceptance-side checks its boundary always implied, and F27-F33 are the
adversarial fixtures for the five -04 correctness gaps).

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
                 ev=None, quota=H.DAILY_QUOTA_CAP_DEFAULT, ledger_name=None):
        self.clock = H.FakeClock(day=day)
        path = os.path.join(tmp, ledger_name or f"{name}.jsonl")
        self.ledger = H.Ledger(path)
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
            "billed_0": sc.ledger.billed_total("A", "S1") == 0})
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

    ok = all(r["match"] for r in RESULTS)
    summary = {"task": "QF-ISSUE9-OFFLINE-HARNESS-CORRECTNESS-20261014-04 r1",
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
