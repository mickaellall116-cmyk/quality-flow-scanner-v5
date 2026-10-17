#!/usr/bin/env python3
"""Trial harness for QF-TD-FRESH-LIVE-DRIVER-INTEGRATION-20261016-04 r1.

Proves the INTEGRATED entrypoint (live_driver.py) - not a parallel model -
against injected FakeTransport only. Usage:
  run_integration_trials.py <trials_root> <output_json>
Executed by the packet author under `unshare -n` (network denied).
Output is normalized (no paths, no pids, no wall-clock) so two runs must
be byte-identical (the two-process race artifacts assert split-invariant
totals only, as in r2).
"""
import copy
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_driver as D

PKG = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.join(PKG, "..")
R1PKG = os.path.join(NOTES, "td_fresh_full_manifest_preflight_evidence_20261016")
MANIFEST_BYTES = open(os.path.join(R1PKG, "fresh_manifest.json"), "rb").read()
SUPPLEMENT_BYTES = open(os.path.join(R1PKG, "fresh_supplement.json"), "rb").read()
MANIFEST = json.loads(MANIFEST_BYTES)
IDS = [r["request_id"] for r in MANIFEST["requests"]]
REQS = {r["request_id"]: r for r in MANIFEST["requests"]}
OLD_STATE = os.path.join(NOTES, "twelve_data_stage0", "snapshots",
                         "acquisition_state_spot8")
WORKER = os.path.join(PKG, "ledger_worker_i.py")


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
        self.ledger_path = os.path.join(self.dir, "account", "limiter_ledger.json")
        self.checks = []
        self.facts = {}

    def check(self, label, cond):
        self.checks.append(label)
        if not cond:
            raise AssertionError(label)

    def runner(self, transport=None, clock=None, supp_bytes=None,
               manifest=None, ns=None, ledger_path=None, **kw):
        return D.Runner(ns if ns is not None else self.ns,
                        manifest if manifest is not None else MANIFEST_BYTES,
                        supp_bytes if supp_bytes is not None else SUPPLEMENT_BYTES,
                        transport if transport is not None else D.FakeTransport(),
                        clock if clock is not None else D.FakeClock(),
                        shared_ledger_path=ledger_path if ledger_path is not None
                        else self.ledger_path, **kw)

    def expect_refusal(self, label, **kw):
        t = kw.pop("transport", None) or D.FakeTransport()
        try:
            r = self.runner(transport=t, **kw)
            r.close()
            self.check(label + ":refused", False)
            return None
        except D.Refusal as e:
            self.check(label + ":refused", True)
            self.facts[label + "_code"] = str(e)
            self.check(label + ":zero_calls", t.calls == [])
            return str(e)


def closed_variant_body(req, mutate):
    obj = json.loads(D.build_closed_body(req))
    mutate(obj)
    return json.dumps(obj, sort_keys=True).encode()


def i01(t):
    files = {
        "pilot_acquire": ("pilot_harness/pilot_acquire.py", D.PILOT_ACQUIRE_SHA256),
        "rate_limiter": ("pilot_harness/rate_limiter.py", D.PILOT_RATE_LIMITER_SHA256),
        "validate_input": ("pilot_harness/validate_input.py", D.NL_MECHANISM_MODULE_SHA256),
        "env_lock": ("td_nl_env_rebuild_evidence_20261016/lock_copy.txt", D.NL_ENV_LOCK_SHA256),
    }
    for label, (rel, pin) in files.items():
        actual = D.H(open(os.path.join(NOTES, rel), "rb").read())
        t.check("pin_" + label, actual == pin)
        t.facts["pin_" + label] = actual[:12]
    t.check("manifest_pin", D.H(MANIFEST_BYTES) == D.EXPECTED_MANIFEST_DIGEST)
    t.check("supplement_pin", D.H(SUPPLEMENT_BYTES) == D.EXPECTED_SUPPLEMENT_SHA256)
    t.check("endpoint_pin", D.LIVE_ENDPOINT == MANIFEST["endpoint"]
            == "https://api.twelvedata.com/time_series")
    t.check("cred_ref_is_name_only", D.LIVE_CREDENTIAL_REF == "custom.twelvedata")
    t.check("allowed_hosts", D.LIVE_ALLOWED_HOSTS == ["api.twelvedata.com"])
    src = open(os.path.join(PKG, "live_driver.py")).read()
    t.check("driver_no_apikey_assignment", "apikey=" not in src)
    t.check("adapter_contract_pin_in_driver",
            D.ADAPTER_CONTRACT_SHA256.startswith("ec877a04"))


def i02(t):
    before = hash_tree(OLD_STATE)
    tr = D.FakeTransport()
    r = t.runner(transport=tr)
    out = r.run()
    r.close()
    states = out["states"]
    t.check("outcome_complete", out["outcome"] == "COMPLETE")
    t.check("calls_exact_order", out["transport_calls"] == IDS)
    t.check("completed_49", sum(1 for v in states.values() if v == "COMPLETED") == 49)
    t.check("closed_2", sum(1 for v in states.values() if v == "CLOSED_DAY_EVIDENCED") == 2)
    t.check("closed_are_spt0708",
            states["REQ-SPT-07"] == states["REQ-SPT-08"] == "CLOSED_DAY_EVIDENCED")
    t.check("reservations_51", out["reservations"] == 51)
    rec = os.listdir(os.path.join(t.ns, "receipts"))
    t.check("receipts_49", sum(1 for f in rec if f.endswith(".json")) == 49)
    t.check("closed_bins_2", sum(1 for f in rec if f.endswith(".closed_day.bin")) == 2)
    body = open(os.path.join(t.ns, "receipts", "REQ-SPT-07.closed_day.bin"), "rb").read()
    obj = json.loads(body)
    t.check("closed_body_real_schema",
            set(obj) == {"code", "message", "status", "meta"}
            and set(obj["meta"]) == {"symbol", "interval", "exchange"}
            and obj["meta"]["exchange"] == "")
    t.check("old_spot8_untouched", hash_tree(OLD_STATE) == before)


def _closed_negative(t, label, rid, body, expect_outcome, expect_calls):
    tr = D.FakeTransport({rid: ("raw", 400, body)})
    r = t.runner(transport=tr)
    out = r.run()
    r.close()
    t.check(label + "_outcome", out["outcome"] == expect_outcome)
    t.check(label + "_calls", len(out["transport_calls"]) == expect_calls)
    t.check(label + "_not_classified",
            out["states"].get(rid) == "ERROR_EVIDENCED")


def i03(t):
    req = REQS["REQ-SPT-07"]
    pos = D.FakeTransport()
    r = t.runner(transport=pos)
    out = r.run()
    r.close()
    t.check("positive_classified",
            out["states"]["REQ-SPT-07"] == "CLOSED_DAY_EVIDENCED")
    variants = [
        ("three_key", lambda o: o.pop("meta")),
        ("meta_missing_exchange", lambda o: o["meta"].pop("exchange")),
        ("meta_exchange_nonempty", lambda o: o["meta"].update(exchange="NASDAQ")),
        ("meta_symbol_wrong", lambda o: o["meta"].update(symbol="ZZZZ")),
        ("meta_interval_wrong", lambda o: o["meta"].update(interval="4h")),
        ("extra_values_key", lambda o: o.update(values=[])),
        ("code_as_string", lambda o: o.update(code="400")),
        ("message_mutated", lambda o: o.update(message="No data.")),
        ("status_not_error", lambda o: o.update(status="ok")),
    ]
    for label, mut in variants:
        sub = Trial("i03_" + label, t.dir)
        _closed_negative(sub, label, "REQ-SPT-07",
                         closed_variant_body(req, mut), "HOLD_HTTP_400", 50)
        t.checks += [label + ":" + c for c in sub.checks]
    # closed body on an unregistered request (first request) -> HOLD, 1 call
    sub = Trial("i03_unregistered", t.dir)
    _closed_negative(sub, "unregistered", "REQ-P1H-01",
                     D.build_closed_body(REQS["REQ-P1H-01"]), "HOLD_HTTP_400", 1)
    t.checks += ["unregistered:" + c for c in sub.checks]
    # real-schema closed body under HTTP 200 -> not classified, status HOLD
    sub = Trial("i03_http200", t.dir)
    tr = D.FakeTransport({"REQ-SPT-07": ("raw", 200, D.build_closed_body(req))})
    r = sub.runner(transport=tr)
    out = r.run()
    r.close()
    t.check("http200_not_classified", out["states"]["REQ-SPT-07"] == "ERROR_EVIDENCED"
            and out["outcome"] == "HOLD_API_STATUS_NOT_OK")


def i04(t):
    def enc(o):
        return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()

    mutations = [
        ("base_binding", lambda o: o.update(base_manifest_canonical_digest="0" * 64)),
        ("entry_bars", lambda o: o["entries"]["REQ-SPT-07"].update(expected_bars=7)),
        ("collector_pin", lambda o: o["classifier_pins"].update(collector_sha256="0" * 64)),
        ("notes_field", lambda o: o.update(notes=["tampered"])),
        ("status_field", lambda o: o.update(status="ADOPTED")),
        ("proof_closed", lambda o: o["calendar_proofs"][
            "36bc3a89bd266b9d7478d7f6082addd7b764a824bac45afdcbe534eb1d37f21a"].update(closed=False)),
    ]
    for label, mut in mutations:
        o = copy.deepcopy(json.loads(SUPPLEMENT_BYTES))
        mut(o)
        tr = D.FakeTransport()
        try:
            r = t.runner(transport=tr, supp_bytes=enc(o),
                         ns=os.path.join(t.dir, "ns_" + label),
                         ledger_path=os.path.join(t.dir, "acct_" + label, "ledger.json"))
            r.close()
            t.check("mut_" + label + ":refused", False)
        except D.Refusal as e:
            t.check("mut_" + label + ":refused", True)
            t.facts["mut_" + label + "_code"] = str(e)
        t.check("mut_" + label + ":zero_calls", tr.calls == [])
        t.check("mut_" + label + ":no_namespace",
                not os.path.exists(os.path.join(t.dir, "ns_" + label)))
        t.check("mut_" + label + ":no_ledger",
                not os.path.exists(os.path.join(t.dir, "acct_" + label, "ledger.json")))
    pretty = json.dumps(json.loads(SUPPLEMENT_BYTES), indent=2).encode()
    t.expect_refusal("supp_pretty", supp_bytes=pretty)
    t.facts["supp_pretty_code"] = t.facts.get("supp_pretty_code")
    t.expect_refusal("supp_garbage", supp_bytes=b"{not json")
    mo = copy.deepcopy(MANIFEST)
    mo["requests"][0]["symbol"] = "ZZZZ"
    t.expect_refusal("manifest_mutated", manifest=enc(mo))


def i05(t):
    tr = D.FakeTransport({"REQ-P1H-05": ("raw", 500, b"server error")})
    r = t.runner(transport=tr)
    out = r.run()
    r.close()
    t.check("outcome", out["outcome"] == "HOLD_HTTP_500")
    t.check("calls_stop_at_5", out["transport_calls"] == IDS[:5])
    t.check("later_untouched", len(out["states"]) == 5)


def i06(t):
    bad_body = D.build_ok_body(REQS["REQ-P4H-01"], 3).replace(
        REQS["REQ-P4H-01"]["venue_identity"]["exchange"].encode(), b"XXXX")
    tr = D.FakeTransport({"REQ-P4H-01": ("raw", 200, bad_body)})
    r = t.runner(transport=tr)
    out = r.run()
    r.close()
    t.check("outcome", out["outcome"] == "HOLD_META_VENUE_MISMATCH")
    t.check("calls_stop", out["transport_calls"] == IDS[:21])


def i07(t):
    tr = D.FakeTransport()
    r = t.runner(transport=tr, account_mode="unknown")
    out = r.run()
    r.close()
    t.check("outcome", out["outcome"] == "HOLD_UNKNOWN_CREDIT_STATE")
    t.check("zero_calls", out["transport_calls"] == [])


def _preload(t, ledger_path, n, clock):
    # Direct ledger construction with all reservations on the runner's
    # day and >1h old (the r2 T24 technique): deterministic, no fake-day
    # spill, no minute-window interference.
    start = D.FakeClock().now()
    day = D.day_of(start)
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    preload = {"reservations": [
        {"rid": "PRE-%04d" % i, "ts": start - 3600, "day": day, "weight": 1}
        for i in range(n)]}
    with open(ledger_path, "w") as f:
        json.dump(preload, f)


def i08(t):
    clock = D.FakeClock()
    _preload(t, t.ledger_path, 795, clock)
    tr = D.FakeTransport()
    r = t.runner(transport=tr, clock=clock)
    out = r.run()
    r.close()
    t.check("outcome", out["outcome"] == "REFUSED_LIMITER_DAY_CAP")
    t.check("five_calls_fit", out["transport_calls"] == IDS[:5])
    t.check("ledger_exactly_800", out["reservations"] == 800)


def i09(t):
    tr = D.FakeTransport({"REQ-P1H-11": ("crash",)})
    r = t.runner(transport=tr)
    crashed = False
    try:
        r.run()
    except D.SimulatedCrash:
        crashed = True
    r.close()  # process death releases the owner flock in the real model
    t.check("crash_raised", crashed)
    t.check("calls_before_crash", tr.calls == IDS[:11])
    tr2 = D.FakeTransport()
    r2 = t.runner(transport=tr2)
    out = r2.run()
    r2.close()
    t.check("restart_outcome", out["outcome"] == "HOLD_AMBIGUOUS_STARTED")
    t.check("restart_zero_calls", out["transport_calls"] == [])
    t.check("prior_receipts_intact",
            sum(1 for f in os.listdir(os.path.join(t.ns, "receipts"))
                if f.endswith(".json")) == 10)


def i10(t):
    r = t.runner()
    out1 = r.run()
    r.close()
    tr2 = D.FakeTransport()
    r2 = t.runner(transport=tr2)
    out2 = r2.run()
    r2.close()
    t.check("first_complete", out1["outcome"] == "COMPLETE")
    t.check("restart_complete", out2["outcome"] == "COMPLETE")
    t.check("restart_zero_calls", out2["transport_calls"] == [])
    t.check("reservations_unchanged", out2["reservations"] == 51)


def i11(t):
    r = t.runner()
    r.run()
    r.close()
    p = os.path.join(t.ns, "receipts", "REQ-P1H-01.json")
    data = bytearray(open(p, "rb").read())
    data[10] ^= 0xFF
    open(p, "wb").write(bytes(data))
    r2 = t.runner(transport=D.FakeTransport())
    out = r2.run()
    r2.close()
    t.check("outcome", out["outcome"] == "HOLD_RECEIPT_REVALIDATION_FAILED")
    t.check("zero_calls", out["transport_calls"] == [])


def i12(t):
    r1 = t.runner()
    t.expect_refusal("duplicate_owner")
    r1.close()
    r2 = t.runner()  # after release, a fresh owner is admitted
    r2.close()
    t.check("owner_after_release_ok", True)


def i13(t):
    os.makedirs(t.ns, exist_ok=True)
    with open(os.path.join(t.ns, "foreign.txt"), "w") as f:
        f.write("foreign")
    t.expect_refusal("foreign_namespace_file")
    ns2 = os.path.join(t.dir, "ns_other")
    os.makedirs(ns2, exist_ok=True)
    with open(os.path.join(ns2, "manifest_binding.json"), "w") as f:
        f.write(json.dumps({"run_id": "OTHER-RUN", "manifest_digest": "0" * 64}))
    t.expect_refusal("other_identity_binding", ns=ns2)


def _spawn(t, tag, attempts, go=False, crash_after=0, ledger_path=None):
    out_json = os.path.join(t.dir, tag + ".json")
    go_file = os.path.join(t.dir, "go")
    args = [sys.executable, WORKER, PKG,
            ledger_path if ledger_path is not None else t.ledger_path,
            out_json, tag, str(attempts), str(D.FakeClock().now()),
            go_file if go else "-", str(crash_after)]
    return subprocess.Popen(args), out_json, go_file


def i14(t):
    pa, oa, go = _spawn(t, "WA", 8, go=True)
    pb, ob, _ = _spawn(t, "WB", 8, go=True)
    open(go, "w").write("go")
    pa.wait()
    pb.wait()
    a = json.load(open(oa))
    b = json.load(open(ob))
    t.check("minute_cap_total_8", a["ok"] + b["ok"] == 8)
    t.check("rids_unique", len(set(a["ok_rids"]) | set(b["ok_rids"])) == 8)
    t.check("ledger_8", D.Limiter(t.ledger_path).count() == 8)
    # day cap across processes: preload 795, two workers x4 -> exactly 5 fit
    lp2 = os.path.join(t.dir, "acct2", "ledger.json")
    clock = D.FakeClock()
    _preload(t, lp2, 795, clock)
    pa, oa, go = _spawn(t, "WC", 4, go=True, ledger_path=lp2)
    pb, ob, _ = _spawn(t, "WD", 4, go=True, ledger_path=lp2)
    open(go, "w").write("go")
    pa.wait()
    pb.wait()
    a = json.load(open(oa))
    b = json.load(open(ob))
    t.check("day_cap_new_5", a["ok"] + b["ok"] == 5)
    t.check("ledger_exactly_800", D.Limiter(lp2).count() == 800)


def i15(t):
    p, _o, _g = _spawn(t, "CRASH", 5, crash_after=3)
    rc = p.wait()
    t.check("worker_died", rc == 42)
    t.check("reservations_survive", D.Limiter(t.ledger_path).count() == 3)
    lp = os.path.join(t.dir, "acct_corrupt", "ledger.json")
    os.makedirs(os.path.dirname(lp), exist_ok=True)
    with open(lp, "wb") as f:
        f.write(b"garbage{")
    before = open(lp, "rb").read()
    try:
        D.Limiter(lp)
        t.check("corrupt_refused", False)
    except D.Refusal as e:
        t.check("corrupt_refused", str(e) == "LIMITER_LEDGER_CORRUPT")
    t.check("corrupt_bytes_unchanged", open(lp, "rb").read() == before)


def i16(t):
    inside = os.path.join(t.ns, "limiter_ledger.json")
    t.expect_refusal("ledger_inside_namespace", ledger_path=inside)
    t.check("namespace_not_created", not os.path.exists(t.ns))


def i17(t):
    r = t.runner()
    out = r.run()
    r.close()
    blob = b""
    for root, _d, files in os.walk(t.ns):
        for fn in files:
            blob += open(os.path.join(root, fn), "rb").read()
    t.check("no_apikey_in_artifacts", b"apikey" not in blob.lower())
    t.check("no_apikey_in_argv",
            all("apikey" not in a.lower() for a in sys.argv))
    try:
        rr = t.runner(ns=os.path.join(t.dir, "ns_to"),
                      ledger_path=os.path.join(t.dir, "acct_to", "ledger.json"),
                      transport=D.FakeTransport({"REQ-P1H-01": ("timeout",)}))
        o = rr.run()
        rr.close()
        t.check("timeout_outcome_clean", o["outcome"] == "HOLD_TRANSPORT_TIMEOUT")
    except Exception as e:  # exceptions must be sanitized too
        t.check("exception_sanitized", "apikey" not in str(e).lower())


def i18(t):
    t.expect_refusal("live_transport_unarmed", transport=D.LiveHttpsTransport())
    t.check("namespace_not_created", not os.path.exists(t.ns))
    t.check("ledger_not_created", not os.path.exists(t.ledger_path))
    u1 = D.build_url(REQS["REQ-P1H-01"])
    u2 = D.build_url(REQS["REQ-P1H-01"])
    t.check("url_deterministic", u1 == u2)
    t.check("url_endpoint", u1.startswith(D.LIVE_ENDPOINT + "?"))
    t.check("url_has_no_credential", "apikey" not in u1.lower())


TRIALS = [("I01", i01), ("I02", i02), ("I03", i03), ("I04", i04),
          ("I05", i05), ("I06", i06), ("I07", i07), ("I08", i08),
          ("I09", i09), ("I10", i10), ("I11", i11), ("I12", i12),
          ("I13", i13), ("I14", i14), ("I15", i15), ("I16", i16),
          ("I17", i17), ("I18", i18)]


def main():
    root, out_path = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    os.makedirs(root, exist_ok=True)
    matrix = []
    for name, fn in TRIALS:
        t = Trial(name, root)
        status, failed = "PASS", None
        try:
            fn(t)
        except AssertionError as e:
            status, failed = "FAIL", str(e)
        except Exception as e:  # noqa: BLE001 - recorded, not hidden
            status, failed = "ERROR", type(e).__name__ + ":" + str(e)
        matrix.append({"trial": name, "status": status, "failed": failed,
                       "checks": t.checks, "facts": t.facts})
        print(name, status, failed or "", flush=True)
    with open(out_path, "w") as f:
        f.write(json.dumps(matrix, indent=1, sort_keys=True) + "\n")
    bad = [m for m in matrix if m["status"] != "PASS"]
    print("TRIALS", len(matrix), "PASS", len(matrix) - len(bad), "FAIL", len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
