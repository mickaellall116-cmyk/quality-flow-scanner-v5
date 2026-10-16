#!/usr/bin/env python3
"""Trial harness for QF-TD-FRESH-FULL-MANIFEST-PREFLIGHT-20261016-03 r1.
Runs the 23-trial offline matrix against preflight_driver with fake
transport only. Usage: run_trials.py <trials_root> <output_json>
Executed by the packet author under `unshare -n` (network denied).
Output is normalized (no paths, no wall-clock) so two runs must be
byte-identical."""
import copy
import hashlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preflight_driver as D

PKG = os.path.dirname(os.path.abspath(__file__))
MANIFEST_BYTES = open(os.path.join(PKG, "fresh_manifest.json"), "rb").read()
SUPPLEMENT = json.load(open(os.path.join(PKG, "fresh_supplement.json")))
OLD_STATE = os.path.join(PKG, "..", "twelve_data_stage0", "snapshots", "acquisition_state_spot8")
IDS = [r["request_id"] for r in json.loads(MANIFEST_BYTES)["requests"]]


def hash_tree(path):
    out = {}
    for root, _dirs, files in os.walk(path):
        for fn in sorted(files):
            p = os.path.join(root, fn)
            out[os.path.relpath(p, path)] = D.H(open(p, "rb").read())
    return out


class Trial:
    def __init__(self, name, root):
        self.name = name
        self.ns = os.path.join(root, name)
        os.makedirs(self.ns)
        self.checks = []
        self.facts = {}

    def check(self, label, cond):
        self.checks.append(label)
        if not cond:
            raise AssertionError(label)

    def runner(self, transport=None, clock=None, supp=None, manifest=None, **kw):
        return D.Runner(self.ns, manifest if manifest is not None else MANIFEST_BYTES,
                        supp if supp is not None else copy.deepcopy(SUPPLEMENT),
                        transport if transport is not None else D.FakeTransport(),
                        clock if clock is not None else D.FakeClock(), **kw)

    def expect_refusal(self, label, **kw):
        t = D.FakeTransport()
        try:
            r = self.runner(transport=t, **kw)
            r.close()
            self.check(label + ":refused", False)
        except D.Refusal as e:
            self.check(label + ":refused:" + str(e), True)
        self.check(label + ":zero_calls", t.calls == [])
        self.facts["calls"] = 0


def t01(t):
    r = t.runner()
    t.check("digest_pin", r.digest == D.EXPECTED_MANIFEST_DIGEST)
    t.check("shape_51_20", len(r.manifest["requests"]) == 51)
    t.check("run_id", r.manifest["run_id"] == "TD-FRESH-FM-20261016-03-R1")
    t.check("supplement_bound", r.supp["base_manifest_canonical_digest"] == r.digest)
    t.facts["outcome"] = "FROZEN"
    r.close()


def tamper(t, mutate_manifest=None, mutate_supp=None, label=""):
    if mutate_manifest:
        obj = json.loads(MANIFEST_BYTES)
        mutate_manifest(obj)
        t.expect_refusal(label, manifest=D.canon(obj))
    else:
        supp = copy.deepcopy(SUPPLEMENT)
        mutate_supp(supp)
        t.expect_refusal(label, supp=supp)


def t02(t):
    def m(o): o["requests"][0]["symbol"] = "ZZZZ"
    tamper(t, m, label="symbol")


def t03(t):
    def m(o): o["requests"][0], o["requests"][1] = o["requests"][1], o["requests"][0]
    tamper(t, m, label="order_swap")


def t04(t):
    def m(o): o["budget"]["max_credits"] = 52
    tamper(t, m, label="budget")


def t05(t):
    def m(o): o["requests"] = o["requests"][:50]
    tamper(t, m, label="drop_request")


def t06(t):
    def s(x): x["base_manifest_canonical_digest"] = "0" * 64
    tamper(t, mutate_supp=s, label="supp_binding")


def t07(t):
    def s(x): x["entries"]["REQ-SPT-07"]["expected_bars"] = 7
    tamper(t, mutate_supp=s, label="supp_expected_bars")


def t08(t):
    r = t.runner()
    res = r.run()
    t.check("outcome_complete", res["outcome"] == "COMPLETE")
    t.check("exact_ordered_calls", res["transport_calls"] == IDS)
    t.check("reservations_51", res["reservations"] == 51)
    states = res["states"]
    t.check("completed_49", sum(1 for v in states.values() if v == "COMPLETED") == 49)
    t.check("closed_evidenced_2", states["REQ-SPT-07"] == "CLOSED_DAY_EVIDENCED"
            and states["REQ-SPT-08"] == "CLOSED_DAY_EVIDENCED")
    rec = os.path.join(t.ns, "receipts")
    t.check("no_receipt_for_closed", not os.path.exists(os.path.join(rec, "REQ-SPT-07.json"))
            and not os.path.exists(os.path.join(rec, "REQ-SPT-08.json")))
    for rid in ("REQ-SPT-07", "REQ-SPT-08"):
        body = open(os.path.join(rec, rid + ".closed_day.bin"), "rb").read()
        t.check("closed_body_is_fresh_response_" + rid, D.H(body) == D.H(D.CLOSED_BODY))
    man = {q["request_id"]: q for q in r.manifest["requests"]}
    for rid in ("REQ-P1H-01", "REQ-P4H-01", "REQ-ADJ-01", "REQ-SPT-01"):
        raw = open(os.path.join(rec, rid + ".json"), "rb").read()
        st = r.state["requests"][rid]
        t.check("hash_binding_" + rid, st["receipt_sha256"] == D.H(raw)
                and st["request_digest"] == D.H(D.canon(man[rid]))
                and st["manifest_digest"] == r.digest)
    ledger = json.load(open(os.path.join(t.ns, "limiter_ledger.json")))
    tss = sorted(x["ts"] for x in ledger["reservations"])
    worst = max(sum(1 for x in tss if ts < x <= ts + 60) for ts in tss)
    t.check("limiter_minute_cap_never_exceeded", worst <= 8)
    t.facts.update({"outcome": res["outcome"], "calls": len(res["transport_calls"]),
                    "reservations": res["reservations"], "pacing_waits": res["pacing_waits"],
                    "max_reservations_any_60s": worst})
    r.close()
    return t.ns


def closed_variant(t, script, expect_calls, label):
    r = t.runner(transport=D.FakeTransport(script))
    res = r.run()
    t.check(label + ":hold", res["outcome"].startswith("HOLD"))
    t.check(label + ":calls", res["transport_calls"] == IDS[:expect_calls])
    t.check(label + ":spt08_not_attempted",
            "REQ-SPT-08" not in res["states"] or res["states"].get("REQ-SPT-08") is None)
    t.facts.update({"outcome": res["outcome"], "calls": len(res["transport_calls"])})
    r.close()


def t09(t):
    bad = D.CLOSED_BODY.replace(b"different start/end dates", b"different start/end dateX")
    closed_variant(t, {"REQ-SPT-07": ("raw", 400, bad)}, 50, "mutated_message")


def t10(t):
    body = json.dumps({"meta": {}, "values": [], "status": "ok"}, sort_keys=True).encode()
    closed_variant(t, {"REQ-SPT-07": ("raw", 200, body)}, 50, "empty_200")


def t11(t):
    obj = json.loads(D.CLOSED_BODY)
    obj["values"] = []
    closed_variant(t, {"REQ-SPT-07": ("raw", 400, D.canon(obj))}, 50, "values_field")


def t12(t):
    r = t.runner(transport=D.FakeTransport({"REQ-P1H-01": ("raw", 400, D.CLOSED_BODY)}))
    res = r.run()
    t.check("hold_first_request", res["outcome"].startswith("HOLD"))
    t.check("one_call_only", res["transport_calls"] == ["REQ-P1H-01"])
    t.facts.update({"outcome": res["outcome"], "calls": 1})
    r.close()


def t13(t):
    supp = copy.deepcopy(SUPPLEMENT)
    supp["calendar_proofs"] = {}
    r = t.runner(supp=supp, transport=D.FakeTransport())
    res = r.run()
    t.check("hold_without_calendar_proof", res["outcome"] == "HOLD_HTTP_400")
    t.check("calls_50", res["transport_calls"] == IDS[:50])
    t.facts.update({"outcome": res["outcome"], "calls": len(res["transport_calls"])})
    r.close()


def t14(t):
    r = t.runner(transport=D.FakeTransport({"REQ-P1H-05": ("raw", 500, b"server error")}))
    res = r.run()
    t.check("hold_500", res["outcome"] == "HOLD_HTTP_500")
    t.check("later_not_attempted", res["transport_calls"] == IDS[:5]
            and all(res["states"].get(x) is None for x in IDS[5:]))
    t.facts.update({"outcome": res["outcome"], "calls": len(res["transport_calls"])})
    r.close()


def t15(t):
    req = [q for q in json.loads(MANIFEST_BYTES)["requests"]
           if q["request_id"] == "REQ-P1H-03"][0]
    body = bytearray(D.build_ok_body(req, 3))
    obj = json.loads(bytes(body))
    obj["meta"]["mic_code"] = "XXXX"
    r = t.runner(transport=D.FakeTransport({"REQ-P1H-03": ("raw", 200, D.canon(obj))}))
    res = r.run()
    t.check("hold_venue", res["outcome"] == "HOLD_META_VENUE_MISMATCH")
    t.check("calls_3", res["transport_calls"] == IDS[:3])
    t.facts.update({"outcome": res["outcome"], "calls": len(res["transport_calls"])})
    r.close()


def t16(t):
    r = t.runner(account_mode="unknown")
    res = r.run()
    t.check("hold_unknown_credit", res["outcome"] == "HOLD_UNKNOWN_CREDIT_STATE")
    t.check("zero_calls_zero_reservations", res["transport_calls"] == [] and res["reservations"] == 0)
    t.facts.update({"outcome": res["outcome"], "calls": 0, "reservations": 0})
    r.close()


def t17(t):
    clock = D.FakeClock()
    r = t.runner(clock=clock)
    r.close()
    ledger_path = os.path.join(t.ns, "limiter_ledger.json")
    ledger = json.load(open(ledger_path))
    day = D.day_of(clock.now())
    ledger["reservations"] = [{"rid": "PRIOR-RUN-%03d" % i, "ts": clock.now() - 3600,
                               "day": day, "weight": 1} for i in range(795)]
    json.dump(ledger, open(ledger_path, "w"))
    r2 = t.runner(clock=clock)
    res = r2.run()
    t.check("refused_at_day_cap", res["outcome"] == "REFUSED_LIMITER_DAY_CAP")
    t.check("only_5_calls_fit", res["transport_calls"] == IDS[:5])
    t.check("ledger_at_800", res["reservations"] == 800)
    t.facts.update({"outcome": res["outcome"], "calls": len(res["transport_calls"]),
                    "reservations_total": res["reservations"]})
    r2.close()


def t18(t):
    clock = D.FakeClock()
    t1 = D.FakeTransport({"REQ-P1H-11": ("crash",)})
    r = t.runner(transport=t1, clock=clock)
    crashed = False
    try:
        r.run()
    except D.SimulatedCrash:
        crashed = True
    t.check("crash_propagated", crashed)
    t.check("phase1_calls_11", t1.calls == IDS[:11])
    r.close()  # stands in for the OS releasing the dead process's flock
    t2 = D.FakeTransport()
    r2 = t.runner(transport=t2, clock=clock)
    res = r2.run()
    t.check("restart_hold_ambiguous", res["outcome"] == "HOLD_AMBIGUOUS_STARTED")
    t.check("restart_zero_calls", t2.calls == [])
    t.check("completed_not_redispatched",
            all(res["states"][x] == "COMPLETED" for x in IDS[:10]))
    t.check("ambiguous_marked", res["states"]["REQ-P1H-11"] == "AMBIGUOUS")
    t.check("later_not_attempted", all(res["states"].get(x) is None for x in IDS[11:]))
    t.facts.update({"outcome": res["outcome"], "phase1_calls": len(t1.calls),
                    "restart_calls": 0})
    r2.close()


def t19(t, ns08):
    r = D.Runner(ns08, MANIFEST_BYTES, copy.deepcopy(SUPPLEMENT), D.FakeTransport(), D.FakeClock())
    res = r.run()
    t.check("idempotent_complete", res["outcome"] == "COMPLETE")
    t.check("zero_redispatch", res["transport_calls"] == [])
    t.facts.update({"outcome": res["outcome"], "calls": 0})
    r.close()


def t20(t):
    a = t.runner()
    t.expect_refusal("second_owner")
    a.close()
    t.facts["outcome"] = "DUPLICATE_OWNER_REFUSED"


def t21(t):
    foreign = os.path.join(t.ns, "foreign.txt")
    with open(foreign, "wb") as f:
        f.write(b"foreign bytes - not part of this run")
    before = D.H(open(foreign, "rb").read())
    t.expect_refusal("foreign_namespace")
    t.check("foreign_bytes_untouched", D.H(open(foreign, "rb").read()) == before)


def t22(t):
    r = t.runner()
    r.close()
    with open(os.path.join(t.ns, "limiter_ledger.json"), "w") as f:
        f.write("{corrupt")
    t.expect_refusal("corrupt_ledger")


def main():
    root, out_path = sys.argv[1], sys.argv[2]
    os.makedirs(root, exist_ok=True)
    old_before = hash_tree(OLD_STATE)
    matrix = {"trials": {}, "suite_facts": {}}
    simple = [("T01_freeze_verify", t01), ("T02_tamper_manifest_symbol", t02),
              ("T03_tamper_order_swap", t03), ("T04_tamper_budget", t04),
              ("T05_tamper_drop_request", t05), ("T06_tamper_supplement_binding", t06),
              ("T07_tamper_supplement_expected_bars", t07),
              ("T09_closed_message_mutated", t09), ("T10_closed_200_empty_values", t10),
              ("T11_closed_400_with_values_field", t11),
              ("T12_closed_shape_on_unregistered_request", t12),
              ("T13_calendar_proof_missing", t13), ("T14_http_500_fail_closed_stop", t14),
              ("T15_venue_mismatch_stop", t15), ("T16_unknown_credit_state", t16),
              ("T17_shared_limiter_day_cap", t17), ("T18_crash_restart_ambiguous", t18),
              ("T20_duplicate_owner_refused", t20),
              ("T21_foreign_file_namespace_refused", t21),
              ("T22_limiter_ledger_corrupt", t22)]
    ns08 = None
    order = []
    for name, fn in simple[:7]:
        order.append((name, fn))
    order.append(("T08_full_run_success", None))
    for name, fn in simple[7:]:
        order.append((name, fn))
    order.append(("T19_restart_idempotent_after_complete", None))
    for name, fn in order:
        t = Trial(name, root)
        try:
            if name == "T08_full_run_success":
                ns08 = t08(t)
            elif name == "T19_restart_idempotent_after_complete":
                t19(t, ns08)
            else:
                fn(t)
            passed = True
        except Exception as e:
            passed = False
            t.facts["error"] = "%s: %s" % (type(e).__name__, e)
        matrix["trials"][name] = {"passed": passed, "checks": t.checks,
                                  "check_count": len(t.checks), "facts": t.facts}
    old_after = hash_tree(OLD_STATE)
    matrix["suite_facts"] = {
        "old_spot8_state_files": len(old_before),
        "old_spot8_state_byte_identical_after": old_before == old_after,
        "fresh_digest_differs_from_spot8_binding":
            D.EXPECTED_MANIFEST_DIGEST != "748ca95789c6f16bab81fbc903fd0c60a890dd2f2e21a63d97ffdb962d70e4fb",
        "total_trials": len(matrix["trials"]),
        "total_checks": sum(v["check_count"] for v in matrix["trials"].values()),
        "all_passed": all(v["passed"] for v in matrix["trials"].values()),
    }
    with open(out_path, "w") as f:
        f.write(json.dumps(matrix, indent=1, sort_keys=True))
    print(json.dumps(matrix["suite_facts"], sort_keys=True))


if __name__ == "__main__":
    main()
