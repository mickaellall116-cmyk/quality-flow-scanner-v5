#!/usr/bin/env python3
"""Trial harness for QF-TD-FRESH-FULL-MANIFEST-PREFLIGHT-20261016-03 r2.

Runs the r1 matrix (unchanged trial set T01-T22) plus the new r2 cases
(T23-T29: cross-process shared-ledger and supplement-hash enforcement)
against preflight_driver_r2 with fake transport only.
Usage: run_trials_r2.py <trials_root> <output_json>
Executed by the packet author under `unshare -n` (network denied).
Output is normalized (no paths, no pids, no wall-clock) so two runs must
be byte-identical.

r2 harness deltas vs r1 (all consequences of the two source repairs):
- the supplement is passed to the driver as canonical bytes;
- every trial models ONE account: its runs share one account ledger at
  <trial>/account/limiter_ledger.json, outside the run namespace(s);
- supplement-mutation trials (T06/T07/T13) now refuse pre-dispatch with
  SUPPLEMENT_SHA_MISMATCH - the exact-pin enforcement subsumes the r1
  semantic checks for mutated supplements (see r2 memo).
"""
import copy
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preflight_driver_r2 as D

PKG = os.path.dirname(os.path.abspath(__file__))
R1PKG = os.path.join(PKG, "..", "td_fresh_full_manifest_preflight_evidence_20261016")
MANIFEST_BYTES = open(os.path.join(R1PKG, "fresh_manifest.json"), "rb").read()
SUPPLEMENT_BYTES = open(os.path.join(R1PKG, "fresh_supplement.json"), "rb").read()
SUPPLEMENT = json.loads(SUPPLEMENT_BYTES)
OLD_STATE = os.path.join(PKG, "..", "twelve_data_stage0", "snapshots", "acquisition_state_spot8")
IDS = [r["request_id"] for r in json.loads(MANIFEST_BYTES)["requests"]]
WORKER = os.path.join(PKG, "ledger_worker.py")
START_TS = D.FakeClock().now()


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
        self.dir = os.path.join(root, name)
        os.makedirs(self.dir)
        self.ns = os.path.join(self.dir, "ns")
        self.account = os.path.join(self.dir, "account")
        self.ledger_path = os.path.join(self.account, "limiter_ledger.json")
        self.checks = []
        self.facts = {}

    def check(self, label, cond):
        self.checks.append(label)
        if not cond:
            raise AssertionError(label)

    def runner(self, transport=None, clock=None, supp_bytes=None, manifest=None,
               ns=None, ledger_path=None, **kw):
        return D.Runner(ns if ns is not None else self.ns,
                        manifest if manifest is not None else MANIFEST_BYTES,
                        supp_bytes if supp_bytes is not None else SUPPLEMENT_BYTES,
                        transport if transport is not None else D.FakeTransport(),
                        clock if clock is not None else D.FakeClock(),
                        shared_ledger_path=ledger_path if ledger_path is not None
                        else self.ledger_path, **kw)

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
    t.check("supplement_pin_enforced", D.H(SUPPLEMENT_BYTES) == D.EXPECTED_SUPPLEMENT_SHA256)
    t.check("ledger_outside_namespace", not os.path.exists(os.path.join(t.ns, "limiter_ledger.json"))
            and os.path.exists(t.ledger_path))
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
        t.expect_refusal(label, supp_bytes=D.canon(supp))


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
    ledger = json.load(open(t.ledger_path))
    tss = sorted(x["ts"] for x in ledger["reservations"])
    worst = max(sum(1 for x in tss if ts < x <= ts + 60) for ts in tss)
    t.check("limiter_minute_cap_never_exceeded", worst <= 8)
    t.facts.update({"outcome": res["outcome"], "calls": len(res["transport_calls"]),
                    "reservations": res["reservations"], "pacing_waits": res["pacing_waits"],
                    "max_reservations_any_60s": worst})
    r.close()
    return (t.ns, t.ledger_path)


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
    # r1 semantics (classification disabled without a calendar proof) are
    # subsumed by the exact-pin enforcement: a proof-stripped supplement
    # is not the pinned supplement, so it refuses pre-dispatch.
    supp = copy.deepcopy(SUPPLEMENT)
    supp["calendar_proofs"] = {}
    tr = D.FakeTransport()
    try:
        r = t.runner(supp_bytes=D.canon(supp), transport=tr)
        r.close()
        t.check("proof_stripped_supplement_refused", False)
    except D.Refusal as e:
        t.check("proof_stripped_supplement_refused:" + str(e),
                str(e) == "SUPPLEMENT_SHA_MISMATCH")
    t.check("zero_calls", tr.calls == [])
    t.check("namespace_not_created", not os.path.exists(t.ns))
    t.facts.update({"outcome": "REFUSED_PREDISPATCH", "calls": 0})


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
    obj = json.loads(D.build_ok_body(req, 3))
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
    ledger = json.load(open(t.ledger_path))
    day = D.day_of(clock.now())
    ledger["reservations"] = [{"rid": "PRIOR-RUN-%03d" % i, "ts": clock.now() - 3600,
                               "day": day, "weight": 1} for i in range(795)]
    json.dump(ledger, open(t.ledger_path, "w"))
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


def t19(t, ns08, ledger08):
    r = D.Runner(ns08, MANIFEST_BYTES, SUPPLEMENT_BYTES, D.FakeTransport(),
                 D.FakeClock(), shared_ledger_path=ledger08)
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
    os.makedirs(t.ns)
    foreign = os.path.join(t.ns, "foreign.txt")
    with open(foreign, "wb") as f:
        f.write(b"foreign bytes - not part of this run")
    before = D.H(open(foreign, "rb").read())
    t.expect_refusal("foreign_namespace")
    t.check("foreign_bytes_untouched", D.H(open(foreign, "rb").read()) == before)


def t22(t):
    r = t.runner()
    r.close()
    with open(t.ledger_path, "w") as f:
        f.write("{corrupt")
    before = D.H(open(t.ledger_path, "rb").read())
    t.expect_refusal("corrupt_ledger")
    t.check("corrupt_ledger_never_reset", D.H(open(t.ledger_path, "rb").read()) == before)


# ---------------- new r2 cases ----------------

def spawn_worker(t, tag, prefix, attempts, go=False, crash_after=0, ledger_path=None):
    out_json = os.path.join(t.dir, "worker_%s.json" % tag)
    go_file = os.path.join(t.dir, "go_%s" % tag) if go else "-"
    argv = [sys.executable, WORKER, PKG, ledger_path or t.ledger_path, out_json,
            prefix, str(attempts), str(START_TS), go_file, str(crash_after)]
    return subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), out_json, go_file


def t23(t):
    # Two distinct run namespaces/processes, ONE account ledger: the
    # rolling-60s cap holds across processes (8 total, never 16).
    other_ns = os.path.join(t.dir, "ns_b")
    ra = t.runner()
    rb = D.Runner(other_ns, MANIFEST_BYTES, SUPPLEMENT_BYTES, D.FakeTransport(),
                  D.FakeClock(), shared_ledger_path=t.ledger_path)
    ra.close()
    rb.close()
    pa, out_a, go_a = spawn_worker(t, "a", "PROCA", 8, go=True)
    pb, out_b, go_b = spawn_worker(t, "b", "PROCB", 8, go=True)
    import time
    time.sleep(0.5)
    open(go_a, "w").write("go")
    open(go_b, "w").write("go")
    rca, rcb = pa.wait(timeout=60), pb.wait(timeout=60)
    t.check("workers_exit_0", rca == 0 and rcb == 0)
    a = json.load(open(out_a))
    b = json.load(open(out_b))
    total_ok = a["ok"] + b["ok"]
    t.check("cross_process_minute_cap_total_8", total_ok == 8)
    t.check("remaining_attempts_waited", a["wait"] + b["wait"] == 8)
    ledger = json.load(open(t.ledger_path))
    rids = [r["rid"] for r in ledger["reservations"]]
    t.check("ledger_exactly_8", len(rids) == 8)
    t.check("no_lost_or_duplicated_reservation",
            sorted(rids) == sorted(a["ok_rids"] + b["ok_rids"]) and len(set(rids)) == 8)
    t.facts.update({"total_ok": total_ok, "ledger_reservations": len(rids)})


def t24(t):
    # Daily cap across processes: preload the shared ledger to 795 for
    # today; two racing processes can add exactly 5 combined, stop at 800.
    os.makedirs(t.account, exist_ok=True)
    day = D.day_of(START_TS)
    preload = {"reservations": [{"rid": "PRIOR-%03d" % i, "ts": START_TS - 3600,
                                 "day": day, "weight": 1} for i in range(795)]}
    with open(t.ledger_path, "w") as f:
        json.dump(preload, f)
    pa, out_a, go_a = spawn_worker(t, "a", "DAYA", 8, go=True)
    pb, out_b, go_b = spawn_worker(t, "b", "DAYB", 8, go=True)
    import time
    time.sleep(0.5)
    open(go_a, "w").write("go")
    open(go_b, "w").write("go")
    rca, rcb = pa.wait(timeout=60), pb.wait(timeout=60)
    t.check("workers_exit_0", rca == 0 and rcb == 0)
    a = json.load(open(out_a))
    b = json.load(open(out_b))
    ledger = json.load(open(t.ledger_path))
    rids = [r["rid"] for r in ledger["reservations"]]
    t.check("combined_new_ok_exactly_5", a["ok"] + b["ok"] == 5)
    t.check("combined_refused_day", a["refused_day"] + b["refused_day"] == 11)
    t.check("ledger_stops_exactly_at_800", len(rids) == 800)
    t.check("no_lost_or_duplicated_reservation",
            len(set(rids)) == 800 and sorted(r for r in rids if not r.startswith("PRIOR-"))
            == sorted(a["ok_rids"] + b["ok_rids"]))
    t.facts.update({"new_ok": a["ok"] + b["ok"], "ledger_reservations": len(rids)})


def t25(t):
    # Crash persistence: a process reserves 3 credits then dies hard
    # (os._exit, no cleanup). The reservations survive, still locked
    # correctly, and the ledger remains usable by the next process.
    p, out_json, _go = spawn_worker(t, "crash", "CRASH", 8, crash_after=3)
    rc = p.wait(timeout=60)
    t.check("worker_died_hard", rc == 42)
    t.check("no_clean_output_from_dead_process", not os.path.exists(out_json))
    ledger = json.load(open(t.ledger_path))
    rids = sorted(r["rid"] for r in ledger["reservations"])
    t.check("reservations_survive_process_death",
            rids == ["CRASH-00", "CRASH-01", "CRASH-02"])
    lim = D.Limiter(t.ledger_path)
    t.check("next_process_sees_same_count", lim.count() == 3)
    res, _ = lim.reserve("AFTER-CRASH", 1, D.FakeClock(START_TS))
    t.check("ledger_usable_after_crash", res == "OK" and lim.count() == 4)
    t.facts.update({"survived_reservations": 3, "count_after_reuse": 4})


def t26(t):
    # Corrupt/unreadable shared ledger: HOLD (Refusal) and never reset -
    # both before first use and after live reservations exist.
    os.makedirs(t.account, exist_ok=True)
    bad = b"{not a ledger"
    with open(t.ledger_path, "wb") as f:
        f.write(bad)
    try:
        D.Limiter(t.ledger_path)
        t.check("corrupt_ledger_refused", False)
    except D.Refusal as e:
        t.check("corrupt_ledger_refused:" + str(e), str(e) == "LIMITER_LEDGER_CORRUPT")
    t.check("corrupt_bytes_unchanged_1", open(t.ledger_path, "rb").read() == bad)
    os.remove(t.ledger_path)
    lim = D.Limiter(t.ledger_path)
    clock = D.FakeClock(START_TS)
    lim.reserve("LIVE-1", 1, clock)
    lim.reserve("LIVE-2", 1, clock)
    bad2 = b'{"reservations": "tampered"'
    with open(t.ledger_path, "wb") as f:
        f.write(bad2)
    try:
        lim.reserve("LIVE-3", 1, clock)
        t.check("midlife_corruption_refused", False)
    except D.Refusal as e:
        t.check("midlife_corruption_refused:" + str(e), str(e) == "LIMITER_LEDGER_CORRUPT")
    t.check("corrupt_bytes_unchanged_2", open(t.ledger_path, "rb").read() == bad2)
    t.facts.update({"outcome": "CORRUPT_LEDGER_HOLDS_NEVER_RESET"})


def _supp_refusal_case(t, tag, mutate):
    ns = os.path.join(t.dir, "ns_" + tag)
    ledger = os.path.join(t.dir, "acct_" + tag, "limiter_ledger.json")
    supp = copy.deepcopy(SUPPLEMENT)
    mutate(supp)
    tr = D.FakeTransport()
    try:
        r = D.Runner(ns, MANIFEST_BYTES, D.canon(supp), tr, D.FakeClock(),
                     shared_ledger_path=ledger)
        r.close()
        t.check(tag + ":refused", False)
    except D.Refusal as e:
        t.check(tag + ":refused:" + str(e), str(e) == "SUPPLEMENT_SHA_MISMATCH")
    t.check(tag + ":zero_calls", tr.calls == [])
    t.check(tag + ":zero_writes", not os.path.exists(ns) and not os.path.exists(ledger))


def t27(t):
    # Mutations to supplement fields the r1 driver never examined must
    # refuse pre-dispatch with zero calls AND zero writes (gap 2).
    cases = [
        ("classifier_pin", lambda s: s["classifier_pins"].__setitem__("collector_sha256", "0" * 64)),
        ("environment_lock", lambda s: s["calendar"].__setitem__("lineage_lock", "0" * 64)),
        ("adapter_contract", lambda s: s["safety_design_binding"].__setitem__("adapter_contract_sha256", "0" * 64)),
        ("class_field", lambda s: s.__setitem__("class", "SOMETHING_ELSE")),
        ("lifecycle_event", lambda s: s.__setitem__("lifecycle_event", "OTHER_EVENT")),
        ("status_field", lambda s: s.__setitem__("status", "ADOPTED")),
    ]
    for tag, mutate in cases:
        _supp_refusal_case(t, tag, mutate)
    t.facts.update({"mutation_cases": len(cases), "all_refused_zero_calls_zero_writes": True})


def t28(t):
    # Non-canonical / unparseable supplement bytes refuse before any write.
    pretty = json.dumps(SUPPLEMENT, indent=2, sort_keys=True).encode()
    for tag, blob, code in (("pretty_printed", pretty, "SUPPLEMENT_NOT_CANONICAL_BYTES"),
                            ("garbage", b"{not json", "SUPPLEMENT_UNPARSEABLE")):
        ns = os.path.join(t.dir, "ns_" + tag)
        ledger = os.path.join(t.dir, "acct_" + tag, "limiter_ledger.json")
        tr = D.FakeTransport()
        try:
            r = D.Runner(ns, MANIFEST_BYTES, blob, tr, D.FakeClock(),
                         shared_ledger_path=ledger)
            r.close()
            t.check(tag + ":refused", False)
        except D.Refusal as e:
            t.check(tag + ":refused:" + str(e), str(e) == code)
        t.check(tag + ":zero_calls", tr.calls == [])
        t.check(tag + ":zero_writes", not os.path.exists(ns) and not os.path.exists(ledger))
    t.facts.update({"outcome": "NONCANONICAL_SUPPLEMENT_REFUSED"})


def t29(t):
    # A ledger path inside the run namespace is refused outright.
    inside = os.path.join(t.ns, "limiter_ledger.json")
    tr = D.FakeTransport()
    try:
        r = t.runner(transport=tr, ledger_path=inside)
        r.close()
        t.check("inside_namespace_ledger_refused", False)
    except D.Refusal as e:
        t.check("inside_namespace_ledger_refused:" + str(e),
                str(e) == "SHARED_LEDGER_INSIDE_NAMESPACE")
    t.check("zero_calls", tr.calls == [])
    t.check("nothing_written", not os.path.exists(t.ns) and not os.path.exists(inside))
    t.facts.update({"outcome": "LEDGER_PATH_CONTRACT_ENFORCED"})


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
              ("T22_limiter_ledger_corrupt", t22),
              ("T23_cross_process_minute_cap", t23),
              ("T24_cross_process_day_cap_race", t24),
              ("T25_cross_process_crash_persistence", t25),
              ("T26_shared_ledger_corrupt_never_reset", t26),
              ("T27_supplement_unchecked_field_mutations", t27),
              ("T28_supplement_noncanonical_bytes", t28),
              ("T29_ledger_inside_namespace_refused", t29)]
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
                t19(t, ns08[0], ns08[1])
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
