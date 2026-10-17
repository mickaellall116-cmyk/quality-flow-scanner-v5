#!/usr/bin/env python3
"""Trial harness for QF-TD-CREDENTIAL-HELPER-PATH-BINDING-20261017-08.

The full r2 dispatch matrix (32 trials) adapted to the r3 path-bound
gate (helper seam = exact path + pinned hash via the shared resolver;
H05 premise corrected: the real sanctioned path is present and
surface-valid) plus targeted origin/path cases P01-P08.

Proves the executable dispatch gate (dispatch_gate.py) around the pinned
-04 driver: all-12-gates green dry-run, green fake dispatch (transport
factory seam + construction spy proving armed construction only after
the PASS receipt is durable), default-factory wiring via a spy
LiveHttpsTransport, each single-gate failure refusing with zero
namespace/ledger/transport access, token binding/replay, live-mode seam
refusal, and direct-arm boundary checks. Executed under `unshare -n`
(network denied). Usage:
  run_dispatch_gate_trials.py <trials_root> <output_json>
Output is normalized (no abs paths, no pids, no wall clock - the
injected test clock is fixed) so two runs must be byte-identical.
"""
import copy
import importlib.util
import inspect
import json
import os
import sys

PKG = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.join(PKG, "..")
sys.path.insert(0, PKG)
import dispatch_gate_r3 as G  # noqa: E402
import credential_resolver as RES  # noqa: E402
import types  # noqa: E402

STUB_PATH = os.path.join(PKG, "helper_stub", "dynamic_credentials.py")
STUB_SHA = G.H(open(STUB_PATH, "rb").read())
STUB_LOG = os.path.join(PKG, "helper_stub", "calls.jsonl")
OTHER_COPY_PATH = "/opt/hatch/workflow-skills/custom-connector-setup/bin/dynamic_credentials.py"


def stub_call_count():
    try:
        with open(STUB_LOG) as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def lease_free(t):
    fd, _path, res = G.acquire_lease(t.ns, G.EXPECTED_RUN_ID, G.PIN_MANIFEST, "0" * 64)
    if fd is None:
        return False
    os.close(fd)
    return True

DRIVER_PATH = os.path.join(NOTES, "td_fresh_live_driver_integration_evidence_20261016", "live_driver.py")
spec = importlib.util.spec_from_file_location("qf_live_driver_spy", DRIVER_PATH)
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)

NOW = 1792224000  # 2026-10-17T14:00:00Z, fixed injected test clock
DAY = "2026-10-17"
R1PKG = os.path.join(NOTES, "td_fresh_full_manifest_preflight_evidence_20261016")
MANIFEST_BYTES = open(os.path.join(R1PKG, "fresh_manifest.json"), "rb").read()
IDS = [r["request_id"] for r in json.loads(MANIFEST_BYTES)["requests"]]
LOCK_BYTES = open(os.path.join(NOTES, "td_nl_env_rebuild_evidence_20261016", "lock_copy.txt"), "rb").read()
REAL_LEDGER = os.path.join(NOTES, "pilot_harness", "credit_ledger.json")
OLD_STATE = os.path.join(NOTES, "twelve_data_stage0", "snapshots", "acquisition_state_spot8")


def hash_tree(path):
    out = {}
    for root, _dirs, files in os.walk(path):
        for fn in sorted(files):
            p = os.path.join(root, fn)
            out[os.path.relpath(p, path)] = G.H(open(p, "rb").read())
    return out


class FakeClock:
    def __init__(self, t=NOW):
        self.t = t

    def now(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


class SpyTransport:
    """Stands in for LiveHttpsTransport on a spy copy of the pinned
    driver module: records every construction (with the armed flag and
    whether a PASS gate receipt already existed at that instant) and
    refuses to carry traffic (raises TransportTimeout like a dead
    network)."""
    constructions = []
    receipt_path = None
    exc = None  # set to the TransportTimeout of the module we are installed into

    def __init__(self, armed=False):
        seen = False
        if SpyTransport.receipt_path and os.path.exists(SpyTransport.receipt_path):
            try:
                seen = json.loads(open(SpyTransport.receipt_path, "rb").read())["decision"] == "PASS"
            except Exception:
                seen = False
        SpyTransport.constructions.append({"armed": armed, "receipt_pass_seen": seen})
        self.armed = armed
        self.calls = []

    def __call__(self, req):
        self.calls.append(req["request_id"])
        raise SpyTransport.exc("spy transport: no real call")


def spy_module(receipt_path):
    spec2 = importlib.util.spec_from_file_location("qf_live_driver_spy_inst", DRIVER_PATH)
    m = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(m)
    SpyTransport.constructions = []
    SpyTransport.receipt_path = receipt_path
    SpyTransport.exc = m.TransportTimeout
    m.LiveHttpsTransport = SpyTransport
    return m


def base_evidence(t):
    return {
        "evidence_id": "QF-TD-FRESH-LIVE-DISPATCH-GATE-20261016-05/EVIDENCE",
        "packet": {
            "packet_id": "QF-TD-FRESH-LIVE-DISPATCH-GATE-20261016-05/PACKET",
            "adjudicated_verdict": G.EXPECTED_ADJUDICATION,
            "run_id": G.EXPECTED_RUN_ID,
            "manifest_digest": G.PIN_MANIFEST,
            "supplement_sha256": G.PIN_SUPPLEMENT,
            "entrypoint_sha256": G.PIN_DRIVER,
            "credit_ceiling": 51,
            "state_dir": t.ns,
            "ledger_path": t.ledger_path,
            "receipt_path": t.receipt_path,
            "dispatch_window": {"start": NOW - 3600, "end": NOW + 3600},
            "account_evidence_max_age_s": 3600,
        },
        "authority": {"basis": G.EXPECTED_AUTHORITY_BASIS, "re_requested": False,
                      "task_ceiling_credits": 51, "spend_usd": 0},
        "account": {"observed_at": NOW - 300, "plan": "Basic", "standing": "good",
                    "remaining_daily_credits": 800, "minute_cap": 8,
                    "source": "offline_fixture"},
        "environment": {"interpreter": "CPython 3.12.3",
                        "freeze_sha256": G.H(LOCK_BYTES),
                        "pandas_market_calendars": "4.5.1"},
        "credential": {"ref": "custom.twelvedata",
                       "helper": "dynamic_credentials.url_with_surrogate_query_param",
                       "allowed_hosts": ["api.twelvedata.com"],
                       "material_read_by_entrypoint": False},
        "stop_rules": {"armed": True, "first_error_stops_batch": True,
                       "ambiguous_never_redispatched": True, "unknown_credit_hold": True},
        "retention": {"acknowledged": True, "scope": "private_screen_evidence_only",
                      "indefinite_retention_claimed": False, "redistribution": False},
    }


class Trial:
    def __init__(self, name, root):
        self.name = name
        self.dir = os.path.join(root, name)
        os.makedirs(self.dir)
        self.ns = os.path.join(self.dir, "ns")
        self.ledger_path = os.path.join(self.dir, "account", "limiter_ledger.json")
        self.receipt_path = os.path.join(self.dir, "account", "gate_receipt.json")
        os.makedirs(os.path.dirname(self.ledger_path))
        with open(self.ledger_path, "w") as f:
            f.write(json.dumps({"reservations": []}, sort_keys=True))
        if os.path.exists(STUB_LOG):
            os.remove(STUB_LOG)
        self.checks = []
        self.facts = {}

    def check(self, label, cond):
        self.checks.append(label)
        if not cond:
            raise AssertionError(label)

    def evidence(self, mutate=None):
        ev = base_evidence(self)
        if mutate:
            mutate(ev)
        return G.canon(ev)

    def token(self, ev_bytes, window_shift=0):
        ev = json.loads(ev_bytes)
        win = dict(ev["packet"]["dispatch_window"])
        win["end"] += window_shift
        return G.make_dispatch_token(ev["packet"]["run_id"], ev["packet"]["manifest_digest"],
                                     G.H(ev_bytes), ev["packet"]["ledger_path"], win)

    def ledger_hash(self):
        return G.H(open(self.ledger_path, "rb").read())[:12]

    def dispatch(self, ev_bytes, **kw):
        kw.setdefault("mode", "test")
        kw.setdefault("clock", FakeClock())
        ov = {"helper_path": STUB_PATH, "helper_sha256": STUB_SHA}
        ov.update(kw.pop("paths_override", None) or {})
        if ov.get("helper_path") == "REAL_IMPORT":
            del ov["helper_path"]
            del ov["helper_sha256"]
        if ov.get("helper_sha256") == "NO_PIN":
            del ov["helper_sha256"]
        kw["paths_override"] = ov
        before_ledger = self.ledger_hash()
        ns_existed = os.path.exists(self.ns)
        res = G.dispatch(ev_bytes, **kw)
        self.facts["ledger_unchanged"] = self.ledger_hash() == before_ledger
        self.facts["ns_created_by_call"] = os.path.exists(self.ns) and not ns_existed
        return res

    def gate_summary(self, res):
        gates = res["receipt"]["gates"]
        self.facts["decision"] = res["receipt"]["decision"]
        self.facts["gates_passed"] = sum(1 for x in gates if x["result"] == "PASS")
        self.facts["failed_gates"] = [x["gate"] for x in gates if x["result"] != "PASS"]
        self.facts["gate_codes"] = ["%d:%s" % (x["gate"], x["code"]) for x in gates
                                    if x["result"] != "PASS"]
        return gates

    def expect_hold_zero_access(self, res, factory_calls):
        self.gate_summary(res)
        self.check("decision_hold", res["receipt"]["decision"] == "HOLD")
        self.check("not_armed", res["receipt"]["armed"] is False)
        self.check("no_transport_constructed", res["transport_constructed"] is False)
        self.check("no_outcome", res["outcome"] is None)
        self.check("factory_never_called", factory_calls == [])
        self.check("ledger_unchanged", self.facts["ledger_unchanged"])
        self.check("namespace_not_created", not self.facts["ns_created_by_call"])


class RecordingFactory:
    def __init__(self, t, inner=None):
        self.t = t
        self.inner = inner
        self.calls = []

    def __call__(self):
        seen_pass = False
        if os.path.exists(self.t.receipt_path):
            seen_pass = json.loads(open(self.t.receipt_path, "rb").read())["decision"] == "PASS"
        self.calls.append({"receipt_pass_seen": seen_pass})
        return self.inner if self.inner is not None else D.FakeTransport()


def g01(t):
    """Green dry-run: all 12 gates PASS, receipt written, never arms."""
    fac = RecordingFactory(t)
    res = t.dispatch(t.evidence(), transport_factory=fac)
    gates = t.gate_summary(res)
    t.check("all_12_pass", len(gates) == 12 and t.facts["gates_passed"] == 12)
    t.check("decision_pass_dry_run", res["receipt"]["decision"] == "PASS_DRY_RUN")
    t.check("receipt_written", res["receipt_written"] is True
          and os.path.exists(t.receipt_path))
    t.check("account_mode_derived_known", res["receipt"]["account_mode_derived"] == "known")
    t.check("token_not_requested", res["receipt"]["token_check"] == "not_requested")
    t.check("factory_never_called", fac.calls == [])
    t.check("no_transport_constructed", res["transport_constructed"] is False)
    t.check("ledger_unchanged", t.facts["ledger_unchanged"])
    t.check("namespace_not_created", not t.facts["ns_created_by_call"])
    t.check("lease_acquired_for_pass", res["lease_acquired"] is True)
    t.check("lease_artifact_is_sibling", os.path.exists(G.lease_path_for(t.ns)))
    t.check("lease_released_after_dry_run", lease_free(t))
    t.check("helper_never_invoked", stub_call_count() == 0)
    t.facts["receipt_clock_mode"] = res["receipt"]["clock_mode"]


def g02(t):
    """Green fake dispatch + replay refusal on the same evidence/token."""
    ev = t.evidence()
    fac = RecordingFactory(t)
    res = t.dispatch(ev, dispatch_token=t.token(ev), transport_factory=fac)
    t.gate_summary(res)
    out = res["outcome"]
    t.check("decision_pass", res["receipt"]["decision"] == "PASS")
    t.check("token_valid", res["receipt"]["token_check"] == "valid")
    t.check("factory_called_once", len(fac.calls) == 1)
    t.check("factory_saw_pass_receipt", fac.calls[0]["receipt_pass_seen"] is True)
    t.check("outcome_complete", out["outcome"] == "COMPLETE")
    t.check("calls_exact_order", out["transport_calls"] == IDS)
    states = out["states"]
    t.check("completed_49", sum(1 for v in states.values() if v == "COMPLETED") == 49)
    t.check("closed_2", sum(1 for v in states.values() if v == "CLOSED_DAY_EVIDENCED") == 2)
    t.check("reservations_51", out["reservations"] == 51)
    t.check("lease_acquired_for_dispatch", res["lease_acquired"] is True)
    t.check("lease_released_after_dispatch", lease_free(t))
    t.check("helper_never_invoked", stub_call_count() == 0)
    t.facts["lifecycle_outcome"] = out["outcome"]
    # replay: same evidence + same token must refuse (gate 8 sees the
    # attempts; the already-issued receipt is a second guard).
    fac2 = RecordingFactory(t)
    res2 = t.dispatch(ev, dispatch_token=t.token(ev), transport_factory=fac2)
    t.gate_summary(res2)
    t.check("replay_decision_hold", res2["receipt"]["decision"] == "HOLD")
    t.check("replay_gate8_code", "8:PRIOR_ATTEMPTS_PRESENT" in t.facts["gate_codes"])
    t.check("replay_receipt_not_rewritten", res2["receipt_written"] is False)
    t.check("replay_no_transport", res2["transport_constructed"] is False and fac2.calls == [])
    t.facts["replay_guard"] = res2["receipt"].get("replay_guard")


def g03(t):
    """Default factory wiring: the spy LiveHttpsTransport on a spy copy
    of the pinned module is constructed armed ONLY after the PASS
    receipt exists; its dead-network refusal stops the batch at 1 call."""
    ev = t.evidence()
    m = spy_module(t.receipt_path)
    res = t.dispatch(ev, dispatch_token=t.token(ev),
                     paths_override={"driver_module": m})
    t.gate_summary(res)
    out = res["outcome"]
    t.check("decision_pass", res["receipt"]["decision"] == "PASS")
    t.check("transport_constructed", res["transport_constructed"] is True)
    t.check("spy_constructions", SpyTransport.constructions ==
            [{"armed": True, "receipt_pass_seen": True}])
    t.check("outcome_hold_timeout", out["outcome"] == "HOLD_TRANSPORT_TIMEOUT")
    t.check("exactly_one_call_attempted", out["transport_calls"] == [IDS[0]])
    t.facts["spy_constructions"] = SpyTransport.constructions


def refusal_trial(mutate=None, setup=None, override=None, use_spy=False):
    def fn(t):
        if setup:
            setup(t)
        fac = RecordingFactory(t)
        kw = {"transport_factory": fac}
        ov = dict(override or {})
        if use_spy:
            ov["driver_module"] = spy_module(t.receipt_path)
            kw.pop("transport_factory")
            fac = None
        if ov:
            kw["paths_override"] = ov
        res = t.dispatch(t.evidence(mutate), **kw)
        calls = fac.calls if fac is not None else []
        t.expect_hold_zero_access(res, calls)
        if use_spy:
            t.check("spy_no_construction", SpyTransport.constructions == [])
    return fn


def f_token_mismatch(t):
    ev = t.evidence()
    fac = RecordingFactory(t)
    res = t.dispatch(ev, dispatch_token=t.token(ev, window_shift=1), transport_factory=fac)
    t.gate_summary(res)
    t.check("all_gates_pass", t.facts["gates_passed"] == 12)
    t.check("decision_hold", res["receipt"]["decision"] == "HOLD")
    t.check("token_invalid", res["receipt"]["token_check"] == "invalid")
    t.check("factory_never_called", fac.calls == [] and res["transport_constructed"] is False)
    t.check("namespace_not_created", not t.facts["ns_created_by_call"])
    t.check("ledger_unchanged", t.facts["ledger_unchanged"])


def f_evidence_tamper(t):
    """Evidence edited after issuance (capacity inflated, canonically
    re-encoded): the adjudicator's token no longer binds -> HOLD."""
    ev_good = t.evidence()
    tok = t.token(ev_good)

    def inflate(ev):
        ev["account"]["remaining_daily_credits"] = 99999
        ev["packet"]["receipt_path"] = os.path.join(t.dir, "account", "gate_receipt2.json")
    ev_bad = t.evidence(inflate)
    fac = RecordingFactory(t)
    res = t.dispatch(ev_bad, dispatch_token=tok, transport_factory=fac)
    t.gate_summary(res)
    t.check("decision_hold", res["receipt"]["decision"] == "HOLD")
    t.check("token_invalid", res["receipt"]["token_check"] == "invalid")
    t.check("factory_never_called", fac.calls == [] and res["transport_constructed"] is False)
    t.check("namespace_not_created", not t.facts["ns_created_by_call"])


def f_clock_seam_live(t):
    receipt_before = os.path.exists(t.receipt_path)
    code = None
    try:
        G.dispatch(t.evidence(), mode="live", clock=FakeClock())
        code = "NO_REFUSAL"
    except G.GateRefusal as e:
        code = str(e)
    t.check("live_clock_seam_refused", code == "TEST_SEAM_IN_LIVE_MODE")
    t.check("no_receipt_written", os.path.exists(t.receipt_path) == receipt_before)
    t.check("namespace_not_created", not os.path.exists(t.ns))
    t.facts["refusal_code"] = code


def f_direct_arm_boundary(t):
    sig = inspect.signature(G.dispatch)
    t.check("no_account_mode_param", "account_mode" not in sig.parameters)
    code = None
    try:
        G.dispatch(t.evidence(), mode="test", clock=FakeClock(), account_mode="known")
        code = "NO_REFUSAL"
    except TypeError:
        code = "TYPEERROR"
    t.check("caller_account_mode_rejected", code == "TYPEERROR")
    # the disarmed candidate alone refuses, as in -04:
    code2 = None
    try:
        D.Runner(t.ns, MANIFEST_BYTES,
                 open(os.path.join(R1PKG, "fresh_supplement.json"), "rb").read(),
                 D.LiveHttpsTransport(armed=False), FakeClock(),
                 shared_ledger_path=t.ledger_path)
        code2 = "NO_REFUSAL"
    except D.Refusal as e:
        code2 = str(e)
    t.check("unarmed_candidate_refuses", code2 == "TRANSPORT_NOT_ARMED")
    t.check("namespace_not_created", not os.path.exists(t.ns))
    t.facts["boundary_codes"] = [code, code2]


def setup_ledger_bytes(data):
    def s(t):
        with open(t.ledger_path, "wb") as f:
            f.write(data)
    return s


def setup_ledger_used(weight):
    def s(t):
        res = [{"rid": "REQ-PRIOR-%03d" % i, "ts": NOW - 120, "day": DAY, "weight": 1}
               for i in range(weight)]
        with open(t.ledger_path, "w") as f:
            f.write(json.dumps({"reservations": res}, sort_keys=True))
    return s


def setup_ns_foreign(t):
    os.makedirs(t.ns)
    with open(os.path.join(t.ns, "foreign.txt"), "w") as f:
        f.write("foreign")


def tampered_manifest_override(t):
    data = bytearray(MANIFEST_BYTES)
    i = data.index(b"TD-ACQUISITION-MANIFEST")  # inside manifest_id string
    data[i + 4] ^= 1  # letter flip; JSON still parses, run_id untouched
    p = os.path.join(t.dir, "manifest_tampered.json")
    with open(p, "wb") as f:
        f.write(bytes(data))
    return {"manifest": p}


def tampered_adapter_override(t):
    src = open(os.path.join(NOTES, "td_p2_spot_v2_execution_preflight_evidence_20261015",
                            "adapter_contract.json"), "rb").read()
    data = bytearray(src)
    data[200] ^= 1
    p = os.path.join(t.dir, "adapter_tampered.json")
    with open(p, "wb") as f:
        f.write(bytes(data))
    return {"adapter": p}


def bad_wheelhouse_override(t):
    import shutil
    wh = os.path.join(t.dir, "wheelhouse")
    shutil.copytree(G.WHEELHOUSE, wh)
    pmc = os.path.join(wh, "wheels", "pandas_market_calendars-4.5.1-py3-none-any.whl")
    with open(pmc, "ab") as f:
        f.write(b"tamper")
    return {"wheelhouse": wh}


def patched_mechanism_override(t):
    src = open(os.path.join(NOTES, "pilot_harness", "validate_input.py")).read()
    patched = src.replace("if sched.empty:\n        return None",
                          "if False:\n        return None")
    assert patched != src
    p = os.path.join(t.dir, "validate_input_patched.py")
    with open(p, "w") as f:
        f.write(patched)
    return {"mechanism": p}


def seam_file(t, name, content):
    p = os.path.join(t.dir, name)
    data = content.encode()
    with open(p, "wb") as f:
        f.write(data)
    return {"helper_path": p, "helper_sha256": G.H(data)}


def _gate9_negative(ov, expected_code):
    def fn(t):
        fac = RecordingFactory(t)
        res = t.dispatch(t.evidence(), transport_factory=fac,
                         paths_override=ov)
        t.gate_summary(res)
        t.check("decision_hold", res["receipt"]["decision"] == "HOLD")
        t.check("only_gate9_failed", t.facts["failed_gates"] == [9])
        t.check("gate9_code", ("9:" + expected_code) in t.facts["gate_codes"])
        t.check("no_transport_constructed", res["transport_constructed"] is False and fac.calls == [])
        t.check("ledger_unchanged", t.facts["ledger_unchanged"])
        t.check("namespace_not_created", not t.facts["ns_created_by_call"])
        t.check("no_lease_artifact", not os.path.exists(G.lease_path_for(t.ns)))
        t.check("no_lease_acquired", res["lease_acquired"] is False)
    return fn


def _seam_negative(fname, content, expected_code):
    def fn(t):
        return _gate9_negative(seam_file(t, fname, content), expected_code)(t)
    return fn


def h05_real_sanctioned_path(t):
    """-08 correction of the r2 H05 premise: with NO seam override the
    r3 gate resolves the helper from the exact sanctioned platform
    path (present and surface-valid - probed read-only in
    probe_record.json), so gate 9 PASSes and the helper is never
    invoked. The -06 'absent' fact was absence from the default
    sys.path only."""
    handle = RES.resolve()
    t.check("resolver_origin_is_sanctioned",
            handle.path == os.path.abspath(RES.SANCTIONED_PATH))
    t.check("resolver_sha_matches_pin", handle.sha256 == RES.PIN_SHA256)
    fac = RecordingFactory(t)
    res = t.dispatch(t.evidence(), transport_factory=fac,
                     paths_override={"helper_path": "REAL_IMPORT"})
    t.gate_summary(res)
    t.check("all_12_pass", t.facts["gates_passed"] == 12)
    t.check("decision_pass_dry_run", res["receipt"]["decision"] == "PASS_DRY_RUN")
    t.check("no_transport_constructed", res["transport_constructed"] is False and fac.calls == [])
    t.check("namespace_not_created", not t.facts["ns_created_by_call"])
    t.check("ledger_unchanged", t.facts["ledger_unchanged"])
    t.check("lease_released", lease_free(t))
    t.facts["helper_route"] = "sanctioned_path"


def p01_absent_path(t):
    ov = {"helper_path": os.path.join(t.dir, "no_such_dir", "dynamic_credentials.py"),
          "helper_sha256": STUB_SHA}
    _gate9_negative(ov, "CREDENTIAL_HELPER_PATH_ABSENT")(t)


def p02_shadow_on_default_path(t):
    """A same-named shadow module planted first on sys.path must never
    even be imported: the gate resolves the exact sanctioned path."""
    shadow_dir = os.path.join(t.dir, "shadowbin")
    os.makedirs(shadow_dir)
    marker = os.path.join(t.dir, "shadow_imported.marker")
    with open(os.path.join(shadow_dir, "dynamic_credentials.py"), "w") as f:
        f.write("import os\n"
                "open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'shadow_imported.marker'), 'w').write('x')\n"
                "def url_with_surrogate_query_param(url, credential_ref, allowed_hosts=None):\n"
                "    return url\n")
    saved_path = list(sys.path)
    saved_mod = sys.modules.pop("dynamic_credentials", None)
    sys.path.insert(0, shadow_dir)
    try:
        fac = RecordingFactory(t)
        res = t.dispatch(t.evidence(), transport_factory=fac,
                         paths_override={"helper_path": "REAL_IMPORT"})
    finally:
        sys.path[:] = saved_path
        sys.modules.pop("dynamic_credentials", None)
        if saved_mod is not None:
            sys.modules["dynamic_credentials"] = saved_mod
    t.gate_summary(res)
    t.check("all_12_pass_via_sanctioned", t.facts["gates_passed"] == 12)
    t.check("decision_pass_dry_run", res["receipt"]["decision"] == "PASS_DRY_RUN")
    t.check("shadow_never_imported", not os.path.exists(marker))
    t.check("no_transport_constructed", res["transport_constructed"] is False and fac.calls == [])
    t.facts["shadow_imported"] = False


def p03_wrong_origin(t):
    """The byte-identical platform copy at a NON-sanctioned origin,
    presented as a path relocation WITHOUT its seam pin: refused as an
    origin mismatch (an unpinned path is never trusted). The resolver
    itself loads exactly the path it is configured with - no
    substitution toward or away from the sanctioned origin."""
    _gate9_negative({"helper_path": OTHER_COPY_PATH, "helper_sha256": "NO_PIN"},
                    "CREDENTIAL_HELPER_ORIGIN_MISMATCH")(t)
    h = RES.resolve(OTHER_COPY_PATH, RES.PIN_SHA256)
    t.check("resolver_loads_exact_configured_path", h.path == OTHER_COPY_PATH)
    t.check("configured_origin_is_not_sanctioned",
            h.path != os.path.abspath(RES.SANCTIONED_PATH))


def p04_signature_mismatch(t):
    _seam_negative("dynamic_credentials.py",
                   "def url_with_surrogate_query_param(url, *, allowed_hosts=None):\n    return url\n",
                   "CREDENTIAL_HELPER_BINDING_MISMATCH")(t)


_SWAP_STUB = (
    "import os\n"
    "_p = os.path.abspath(__file__)\n"
    "with open(_p, 'ab') as _f:\n"
    "    _f.write(b'\\n# post-gate swap\\n')\n"
    "def url_with_surrogate_query_param(url, credential_ref, allowed_hosts=None):\n"
    "    return url\n"
)


def p05_post_gate_swap(t):
    """The seam file rewrites ITSELF at import (after the resolver's
    hash check, before arming): the gate's pre-arm reverify must catch
    the swap and HOLD before any transport construction."""
    ov = seam_file(t, "dynamic_credentials.py", _SWAP_STUB)
    fac = RecordingFactory(t)
    res = t.dispatch(t.evidence(), transport_factory=fac, paths_override=ov)
    t.gate_summary(res)
    t.check("decision_hold", res["receipt"]["decision"] == "HOLD")
    t.check("only_gate9_failed", t.facts["failed_gates"] == [9])
    t.check("gate9_code", "9:CREDENTIAL_HELPER_SWAPPED_POST_GATE" in t.facts["gate_codes"])
    t.check("factory_never_called", fac.calls == [] and res["transport_constructed"] is False)
    t.check("namespace_not_created", not t.facts["ns_created_by_call"])
    t.check("ledger_unchanged", t.facts["ledger_unchanged"])
    t.check("lease_released", lease_free(t))


def p06_tampered_bytes(t):
    p = os.path.join(t.dir, "dynamic_credentials.py")
    with open(STUB_PATH, "rb") as f:
        data = f.read()
    with open(p, "wb") as f:
        f.write(data)
    _gate9_negative({"helper_path": p, "helper_sha256": RES.PIN_SHA256},
                    "CREDENTIAL_HELPER_TAMPERED")(t)


def p07_driver_handoff(t):
    """The candidate r3 driver consumes ONLY the gate-verified handle:
    no handle -> refusal even with a same-named module installed (no
    by-name fallback import); handle tampered after issuance -> the
    pre-call reverify refuses. The helper is never invoked."""
    spec3 = importlib.util.spec_from_file_location(
        "qf_live_driver_r3", os.path.join(PKG, "live_driver_r3.py"))
    d3 = importlib.util.module_from_spec(spec3)
    spec3.loader.exec_module(d3)
    handle = RES.resolve(STUB_PATH, STUB_SHA)
    req = {"request_id": "REQ-P07"}
    marker = {"used": False}

    class MarkerMod:
        pass

    mm = MarkerMod()

    def _marker_fn(url, credential_ref, allowed_hosts=None):
        marker["used"] = True
        return url

    mm.url_with_surrogate_query_param = _marker_fn
    saved = sys.modules.get("dynamic_credentials")
    sys.modules["dynamic_credentials"] = mm
    try:
        code = None
        try:
            d3.LiveHttpsTransport(armed=True)(req)
            code = "NO_REFUSAL"
        except d3.Refusal as e:
            code = str(e)
        t.check("driver_no_handle_refuses", code == "CREDENTIAL_HELPER_UNAVAILABLE")
        t.check("driver_no_fallback_import", marker["used"] is False)
        t2 = d3.LiveHttpsTransport(armed=True, helper_handle=handle)
        t.check("driver_holds_verified_callable",
                t2.helper_handle.callable is handle.callable)
        p = os.path.join(t.dir, "dynamic_credentials.py")
        with open(STUB_PATH, "rb") as f:
            data = f.read()
        with open(p, "wb") as f:
            f.write(data)
        h2 = RES.resolve(p, G.H(data))
        with open(p, "ab") as f:
            f.write(b"# tamper\n")
        code = None
        try:
            d3.LiveHttpsTransport(armed=True, helper_handle=h2)(req)
            code = "NO_REFUSAL"
        except d3.Refusal as e:
            code = str(e)
        t.check("driver_reverify_refuses_swap",
                code == "CREDENTIAL_HELPER_SWAPPED_POST_GATE")
    finally:
        if saved is None:
            sys.modules.pop("dynamic_credentials", None)
        else:
            sys.modules["dynamic_credentials"] = saved
    t.check("helper_never_invoked", stub_call_count() == 0)
    t.facts["driver_handoff"] = ["no_handle_refusal", "identity", "reverify_refusal"]


def p08_handoff_shadow_installed(t):
    """A foreign module already occupying the helper's import name at
    the arming instant -> the gate HOLDs before construction (the
    pinned driver's by-name import must never land on a shadow)."""
    class Foreign:
        pass

    foreign = Foreign()
    foreign.__file__ = os.path.join(t.dir, "foreign_dynamic_credentials.py")
    saved = sys.modules.get("dynamic_credentials")
    sys.modules["dynamic_credentials"] = foreign
    try:
        ev = t.evidence()
        fac = RecordingFactory(t)
        res = t.dispatch(ev, dispatch_token=t.token(ev), transport_factory=fac)
    finally:
        if saved is None:
            sys.modules.pop("dynamic_credentials", None)
        else:
            sys.modules["dynamic_credentials"] = saved
    t.gate_summary(res)
    t.check("decision_hold", res["receipt"]["decision"] == "HOLD")
    t.check("only_gate9_failed", t.facts["failed_gates"] == [9])
    t.check("gate9_code", "9:CREDENTIAL_HELPER_SHADOW_INSTALLED" in t.facts["gate_codes"])
    t.check("factory_never_called", fac.calls == [] and res["transport_constructed"] is False)
    t.check("namespace_not_created", not t.facts["ns_created_by_call"])
    t.check("ledger_unchanged", t.facts["ledger_unchanged"])
    t.check("lease_released", lease_free(t))


def g04_lease_lifecycle(t):
    """Green dispatch holds the lease only inside the call: artifact is
    a sibling of the namespace, and the lease is re-acquirable the
    moment dispatch returns (released, not leaked)."""
    ev = t.evidence()
    fac = RecordingFactory(t)
    res = t.dispatch(ev, dispatch_token=t.token(ev), transport_factory=fac)
    t.gate_summary(res)
    t.check("decision_pass", res["receipt"]["decision"] == "PASS")
    t.check("lease_artifact_sibling", os.path.exists(G.lease_path_for(t.ns))
            and not os.path.exists(os.path.join(t.ns, "dispatch_lease.lock"))
            and G.lease_path_for(t.ns) == os.path.abspath(t.ns) + ".dispatch_lease")
    binding = json.loads(open(G.lease_path_for(t.ns), "rb").read())
    t.check("lease_binding_identity", binding["run_id"] == G.EXPECTED_RUN_ID
            and binding["manifest_digest"] == G.PIN_MANIFEST
            and binding["namespace"] == os.path.abspath(t.ns))
    t.check("lease_released", lease_free(t))
    t.facts["lease_artifact_name"] = os.path.basename(G.lease_path_for(t.ns))


def c01_contention(t):
    """Real-process contention: the holder process runs the wrapper
    with the stub helper importable and blocks inside its transport
    factory (lease held, PASS receipt durable, Runner not yet
    constructed). A contender process running the same namespace
    identity must HOLD at gate 8 with zero transport constructions,
    zero namespace creation and zero ledger change."""
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    ev_h = base_evidence(t)
    ev_c = copy.deepcopy(ev_h)
    ev_c["packet"]["receipt_path"] = os.path.join(t.dir, "account", "gate_receipt_contender.json")
    evh_path = os.path.join(t.dir, "evidence_holder.json")
    evc_path = os.path.join(t.dir, "evidence_contender.json")
    with open(evh_path, "wb") as f:
        f.write(G.canon(ev_h))
    with open(evc_path, "wb") as f:
        f.write(G.canon(ev_c))
    ready = os.path.join(t.dir, "holder_ready")
    go = os.path.join(t.dir, "contender_done")
    hout = os.path.join(t.dir, "holder_facts.json")
    cout = os.path.join(t.dir, "contender_facts.json")
    ledger_before = t.ledger_hash()
    holder = subprocess.Popen(
        [sys.executable, os.path.join(here, "lease_holder.py"),
         t.dir, evh_path, ready, go, hout],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = 120
        while not os.path.exists(ready):
            if holder.poll() is not None or deadline <= 0:
                raise AssertionError("holder_died_or_timeout:%s"
                                     % holder.communicate(timeout=10)[1][-300:])
            import time as _time
            _time.sleep(0.05)
            deadline -= 0.05
        r = subprocess.run(
            [sys.executable, os.path.join(here, "lease_contender.py"), evc_path, cout],
            capture_output=True, timeout=120)
        t.check("contender_exit0", r.returncode == 0)
        cf = json.loads(open(cout, "rb").read())
        t.check("contender_hold", cf["decision"] == "HOLD")
        t.check("contender_gate8_lease", cf["gate8"] == ["FAIL", "OWNER_LEASE_HELD"])
        t.check("contender_other_gates_pass", cf["gates_passed"] == 11)
        t.check("contender_zero_factory", cf["factory_calls"] == 0
                and cf["transport_constructed"] is False)
        t.check("contender_no_lease", cf["lease_acquired"] is False)
        t.check("contender_no_namespace", cf["namespace_exists_after"] is False
                and not os.path.exists(t.ns))
        t.check("contender_ledger_unchanged", cf["ledger_hash"][:12] == ledger_before)
        t.facts["contender"] = {k: cf[k] for k in
                                ("decision", "gate8", "gates_passed", "factory_calls")}
    finally:
        with open(go, "w") as f:
            f.write("go")
    _out, _err = holder.communicate(timeout=120)
    t.check("holder_exit0", holder.returncode == 0)
    hf = json.loads(open(hout, "rb").read())
    t.check("holder_pass_complete", hf["decision"] == "PASS" and hf["outcome"] == "COMPLETE")
    t.check("holder_lease_held_at_construction", hf["lease_held_at_construction"] is True)
    t.check("holder_receipt_durable_first", hf["receipt_pass_durable_at_construction"] is True)
    t.check("holder_calls_51", hf["transport_calls"] == 51 and hf["reservations"] == 51)
    t.check("holder_helper_never_invoked", hf["helper_invoked_by_gate_or_holder"] == 0)
    t.check("lease_released_after_holder", lease_free(t))
    t.facts["holder"] = {k: hf[k] for k in
                         ("decision", "outcome", "lease_held_at_construction",
                          "transport_calls", "reservations")}


TRIALS = [
    ("G01_green_dry_run", g01),
    ("G02_green_dispatch_and_replay", g02),
    ("G03_default_factory_spy_wiring", g03),
    ("F01_gate1_packet_digest", refusal_trial(lambda ev: ev["packet"].__setitem__("manifest_digest", "0" * 64))),
    ("F02_gate2_authority", refusal_trial(lambda ev: ev["authority"].__setitem__("re_requested", True))),
    ("F03_gate3_capacity", refusal_trial(lambda ev: ev["account"].__setitem__("remaining_daily_credits", 50))),
    ("F04_gate3_stale", refusal_trial(lambda ev: ev["account"].__setitem__("observed_at", NOW - 7200))),
    ("F05_gate3_partial", refusal_trial(lambda ev: ev["account"].pop("observed_at"))),
    ("F06_gate4_ledger_corrupt", refusal_trial(setup=setup_ledger_bytes(b"garbage{"))),
    ("F07_gate4_day_capacity", refusal_trial(setup=setup_ledger_used(760))),
    ("F08_gate4_ledger_in_namespace", refusal_trial(
        lambda ev: ev["packet"].__setitem__("ledger_path", os.path.join(ev["packet"]["state_dir"], "limiter_ledger.json")))),
    ("F09_gate5_env_freeze_record", refusal_trial(lambda ev: ev["environment"].__setitem__("freeze_sha256", "0" * 64))),
    ("F10_gate6_manifest_tamper", None),  # wired below (needs trial for override)
    ("F11_gate7_wheelhouse_tamper", None),
    ("F12_gate7_mechanism_disagreement", None),
    ("F13_gate8_namespace_foreign", refusal_trial(setup=setup_ns_foreign)),
    ("F14_gate8_namespace_is_spot8", refusal_trial(
        lambda ev: ev["packet"].__setitem__("state_dir", OLD_STATE))),
    ("F15_gate9_credential_ref", refusal_trial(lambda ev: ev["credential"].__setitem__("ref", "custom.other"))),
    ("F16_gate10_adapter_tamper", None),
    ("F17_gate11_stop_rules", refusal_trial(lambda ev: ev["stop_rules"].__setitem__("armed", False))),
    ("F18_gate12_retention", refusal_trial(lambda ev: ev["retention"].__setitem__("acknowledged", False))),
    ("F19_token_mismatch", f_token_mismatch),
    ("F20_evidence_tamper_token", f_evidence_tamper),
    ("F21_clock_seam_live_mode", f_clock_seam_live),
    ("F22_direct_arm_boundary", f_direct_arm_boundary),
    ("G04_lease_lifecycle", g04_lease_lifecycle),
    ("H01_helper_import_fail_seam", _seam_negative("dynamic_credentials.py", "raise RuntimeError('seam import failure')\n", "CREDENTIAL_HELPER_UNAVAILABLE")),
    ("H02_helper_wrong_module", _seam_negative("dynamic_credentials.py", "X = 1\n", "CREDENTIAL_HELPER_CALLABLE_MISSING")),
    ("H03_helper_wrong_callable", _seam_negative("dynamic_credentials.py", "url_with_surrogate_query_param = 42\n", "CREDENTIAL_HELPER_CALLABLE_MISSING")),
    ("H04_helper_wrong_binding", _seam_negative("dynamic_credentials.py", "def url_with_surrogate_query_param(url, ref):\n    return url\n", "CREDENTIAL_HELPER_BINDING_MISMATCH")),
    ("H05_helper_real_sanctioned_path", h05_real_sanctioned_path),
    ("C01_contention_two_process", c01_contention),
    ("P01_helper_absent_path", p01_absent_path),
    ("P02_shadow_on_default_path", p02_shadow_on_default_path),
    ("P03_wrong_origin_no_pin", p03_wrong_origin),
    ("P04_signature_mismatch", p04_signature_mismatch),
    ("P05_post_gate_swap", p05_post_gate_swap),
    ("P06_tampered_bytes", p06_tampered_bytes),
    ("P07_driver_handoff", p07_driver_handoff),
    ("P08_handoff_shadow_installed", p08_handoff_shadow_installed),
]


def main():
    root, out_path = sys.argv[1], sys.argv[2]
    os.makedirs(root, exist_ok=True)
    real_ledger_before = G.H(open(REAL_LEDGER, "rb").read())
    old_state_before = hash_tree(OLD_STATE)
    results = []
    for name, fn in TRIALS:
        t = Trial(name, root)
        if name == "F10_gate6_manifest_tamper":
            fn = refusal_trial(override=tampered_manifest_override(t))
        elif name == "F11_gate7_wheelhouse_tamper":
            fn = refusal_trial(override=bad_wheelhouse_override(t))
        elif name == "F12_gate7_mechanism_disagreement":
            fn = refusal_trial(override=patched_mechanism_override(t))
        elif name == "F16_gate10_adapter_tamper":
            fn = refusal_trial(override=tampered_adapter_override(t))
        status = "PASS"
        try:
            fn(t)
        except AssertionError as e:
            status = "FAIL:" + str(e)
        except Exception as e:  # noqa: BLE001 - recorded, not hidden
            status = "ERROR:%s:%s" % (type(e).__name__, e)
        results.append({"trial": name, "status": status,
                        "checks": t.checks, "n_checks": len(t.checks),
                        "facts": t.facts})
    summary = {
        "task": G.TASK,
        "gate_revision": G.REVISION,
        "trials": results,
        "n_trials": len(results),
        "n_pass": sum(1 for r in results if r["status"] == "PASS"),
        "total_checks": sum(r["n_checks"] for r in results),
        "real_pilot_ledger_unchanged": G.H(open(REAL_LEDGER, "rb").read()) == real_ledger_before,
        "old_spot8_state_unchanged": hash_tree(OLD_STATE) == old_state_before,
    }
    with open(out_path, "w") as f:
        f.write(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"n_trials": summary["n_trials"], "n_pass": summary["n_pass"],
                      "total_checks": summary["total_checks"]}))


if __name__ == "__main__":
    main()
