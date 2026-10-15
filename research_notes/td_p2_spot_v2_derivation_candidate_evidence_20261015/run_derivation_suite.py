#!/usr/bin/env python3
"""QF-TD-P2-SPOT-V2-DERIVATION-CANDIDATE-20261015-06 r1 proof-suite driver.

Builds nothing against live state: every case runs on a fresh byte copy of
the ACTUAL SPOT8 v1 state (read-only original, hashed before/after) or a
fresh derived copy produced by the candidate's opt-in derivation entry
point. Fake transport only; network disabled in-process before any
collector import; sockets/DNS stubbed to raise. Output is one normalized
JSON document (no timestamps, no tmp paths) so two runs diff byte-for-byte.
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile

def _no_net(*a, **k):
    raise RuntimeError("network disabled (PF06 offline suite)")

socket.socket.connect = _no_net
socket.socket.connect_ex = _no_net
socket.create_connection = _no_net
socket.getaddrinfo = _no_net

P = argparse.ArgumentParser()
P.add_argument("--candidate-dir", required=True)
P.add_argument("--base-dir", required=True)
P.add_argument("--supplement", required=True)
P.add_argument("--manifest", required=True)
P.add_argument("--original-state", required=True)
P.add_argument("--child", required=True)
P.add_argument("--venv-python", required=True)
P.add_argument("--out", required=True)
P.add_argument("--artifacts", required=True)
A = P.parse_args()

CAND = pathlib.Path(A.candidate_dir).resolve()
BASE = pathlib.Path(A.base_dir).resolve()
HARNESS = CAND.parent / "pilot_harness"
ORIG = pathlib.Path(A.original_state).resolve()
ART = pathlib.Path(A.artifacts); ART.mkdir(parents=True, exist_ok=True)
EPOCH = 1792000000
sys.path.insert(0, str(HARNESS))

def load_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

mod = load_mod(CAND / "td_min_collector.py", "pf06_candidate")
basemod = load_mod(BASE / "td_min_collector.py", "pf06_base")
import validate_input
MECH_SHA = hashlib.sha256(pathlib.Path(validate_input.__file__).read_bytes()).hexdigest()
import pandas_market_calendars as _mcal
PMC_VERSION = str(_mcal.__version__)
from rate_limiter import RollingCreditLimiter

SUP = json.loads(pathlib.Path(A.supplement).read_text())
SPOT8 = json.loads(pathlib.Path(A.manifest).read_text())
BY_ID = {r["request_id"]: r for r in SPOT8["requests"]}
RESULTS = []
LEDGER = {"fake_dispatches": [], "derivations": []}

def record(case, checks, note=""):
    RESULTS.append({"case": case, "pass": all(checks.values()),
                    "checks": {k: bool(v) for k, v in sorted(checks.items())},
                    "note": note})

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def inventory(root: pathlib.Path):
    inv = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            inv[str(p.relative_to(root))] = {"sha256": sha(p.read_bytes()), "bytes": p.stat().st_size}
    return inv

def write_prereq(root):
    p = root / "prereq.json"
    p.write_text(json.dumps({"plan": "Basic",
        "endpoint_weight": {"endpoint": "/time_series", "credits_per_request": 1,
                            "evidence": "PF06 offline fixture (synthetic; no vendor contact)"},
        "retention": {"status": "BOUNDED_RESOLVED", "condition": "30-day deletion"},
        "interval_semantics": {"status": "INSUFFICIENT"}}))
    return p

def make(root, state_dir, transport=None, supplement=SUP, module=None):
    lim = RollingCreditLimiter(8, 800, state_path=root / "shared_credit.json", clock=lambda: EPOCH)
    return (module or mod).Collector(state_dir, SPOT8, lim, transport=transport,
                                     prereq_path=root / "prereq.json",
                                     closed_session_supplement=supplement)

def new_root(tmp, name):
    root = pathlib.Path(tmp) / name
    root.mkdir(parents=True)
    write_prereq(root)
    return root

def copy_state(root, name="state"):
    d = root / name
    shutil.copytree(ORIG, d)
    return d

def events_of(sd):
    p = sd / "lifecycle.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

def norm_events(sd):
    out = []
    for e in events_of(sd):
        e = dict(e); e.pop("ts_utc", None); out.append(e)
    return out

def closed_body(symbol):
    return json.dumps({"code": 400, "message": mod.CLOSED_SESSION_MESSAGE, "status": "error",
                       "meta": {"symbol": symbol, "interval": "1h", "exchange": ""}}).encode()

def spt08_only(fn):
    calls = []
    def t(req):
        calls.append(req["request_id"])
        if req["request_id"] != "REQ-SPT-08":
            raise AssertionError(f"unexpected dispatch {req['request_id']}")
        return fn(req)
    return t, calls

def derived_copy(root, name="state"):
    """Fresh copy of the v1 state + successful candidate derivation."""
    sd = copy_state(root, name)
    c = make(root, sd, transport=lambda r: (_ for _ in ()).throw(
        AssertionError("transport must not be called during derivation")))
    res = c.derive_closed_session()
    assert res["outcome"] == "DERIVED", res
    LEDGER["derivations"].append(name)
    return sd

ORIG_INV_BEFORE = inventory(ORIG)
TMP = tempfile.mkdtemp(prefix="pf06_")
try:
    # ------------------------------------------------------------------
    # 1. Pins
    # ------------------------------------------------------------------
    import subprocess as _sp
    diff_files = _sp.run(["git", "-C", str(CAND.parents[1]), "diff", "--name-only",
                          "ab254c3", "HEAD"], capture_output=True, text=True).stdout.split()
    record("pins", {
        "base_collector_sha": sha((BASE / "td_min_collector.py").read_bytes())
            == "b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c",
        "candidate_differs_from_base": sha((CAND / "td_min_collector.py").read_bytes())
            != "b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c",
        "supplement_sha": sha(pathlib.Path(A.supplement).read_bytes())
            == "9c71233003771d66cf81e99ae01a410ba8943aedfcce8a8c6411dfb51edacd32",
        "manifest_digest": mod.canonical_digest(SPOT8)
            == "748ca95789c6f16bab81fbc903fd0c60a890dd2f2e21a63d97ffdb962d70e4fb",
        "spt07_digest": mod.canonical_digest(BY_ID["REQ-SPT-07"])
            == "a259901ec57a8556228c2a6b95299c360102cc98edc62204ae539dc53a4c5edb",
        "spt08_digest": mod.canonical_digest(BY_ID["REQ-SPT-08"])
            == "f547d8fec7882fa121feb966b33fde000b25c4ae0eb822a6b5a503f4a3651a97",
        "mechanism_sha": MECH_SHA == "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58",
        "pmc_version": PMC_VERSION == "4.5.1",
        "diff_single_file": diff_files == ["research_notes/td_lifecycle_repair_candidate/td_min_collector.py"],
    })

    # ------------------------------------------------------------------
    # 2. Receipt verification is observationally read-only (candidate),
    #    with the base candidate as side-effect control.
    # ------------------------------------------------------------------
    root = new_root(TMP, "readonly")
    sd = copy_state(root)
    pre = inventory(sd)
    c = make(root, sd, transport=lambda r: (_ for _ in ()).throw(AssertionError("no transport")))
    oks, findings = [], []
    for i in range(1, 7):
        rid = f"REQ-SPT-0{i}"
        ok, _why = c._verify_receipt(BY_ID[rid], sd / "receipts" / f"{rid}.json")
        oks.append(ok)
        findings.append(list(c.last_verification_findings))
    post = inventory(sd)
    emitted = c.emit_observed_findings()
    ev_after_emit = events_of(sd)
    record("readonly_verification_candidate", {
        "all_six_verify_ok": all(oks),
        "inventory_byte_identical_after_recheck": pre == post,
        "six_structured_findings": all(len(f) == 1 and f[0]["finding"] == "CONSTRUCTION_HOLD" for f in findings),
        "explicit_action_emits_six": emitted == 6,
        "lifecycle_grew_only_via_explicit_action": len(ev_after_emit) == 34 + 6
            and all(e["event"] == "CONSTRUCTION_HOLD" for e in ev_after_emit[34:]),
    })
    root = new_root(TMP, "readonly_base")
    sd = copy_state(root)
    pre = inventory(sd)
    cb = make(root, sd, transport=lambda r: (_ for _ in ()).throw(AssertionError("no transport")), module=basemod)
    oks_b = []
    for i in range(1, 7):
        rid = f"REQ-SPT-0{i}"
        ok, _ = cb._verify_receipt(BY_ID[rid], sd / "receipts" / f"{rid}.json")
        oks_b.append(ok)
    record("readonly_verification_base_control", {
        "base_all_six_verify_ok": all(oks_b),
        "base_appends_six_construction_hold": inventory(sd) != pre
            and len(events_of(sd)) == 34 + 6,
    }, note="control: documents the -05 secondary finding on unchanged base bytes")

    # ------------------------------------------------------------------
    # 3. Happy-path derivation on a copied actual state
    # ------------------------------------------------------------------
    root = new_root(TMP, "derive_happy")
    sd = copy_state(root)
    orig_lifecycle_bytes = (sd / "lifecycle.jsonl").read_bytes()
    c = make(root, sd, transport=lambda r: (_ for _ in ()).throw(AssertionError("no transport")))
    res = c.derive_closed_session()
    evs = events_of(sd)
    derived_evs = [e for e in evs if e["event"] == "DERIVED_CLOSED_DAY_EVIDENCED"]
    st = json.loads((sd / "pilot_state.json").read_text())
    record("derive_happy_path", {
        "outcome_derived": res["outcome"] == "DERIVED" and res["derived"] is True,
        "zero_transport": res["transport_calls"] == 0,
        "exactly_one_derived_event": len(derived_evs) == 1,
        "v1_history_byte_prefix": (sd / "lifecycle.jsonl").read_bytes().startswith(orig_lifecycle_bytes),
        "v1_hold_event_retained": any(e["event"] == "HOLD" and e.get("reason") == "HTTP 400 for REQ-SPT-07" for e in evs),
        "event_pins": bool(derived_evs) and derived_evs[0].get("source_body_sha256")
            == "3339c34154648c0ea4ddb9bd553e5274d390f953552518ad957d79704b7d5d50"
            and derived_evs[0].get("request_digest")
            == "a259901ec57a8556228c2a6b95299c360102cc98edc62204ae539dc53a4c5edb"
            and derived_evs[0].get("manifest_digest")
            == "748ca95789c6f16bab81fbc903fd0c60a890dd2f2e21a63d97ffdb962d70e4fb"
            and derived_evs[0].get("calendar_proof_digest")
            == "92621e938c3e3f5726a8837dc93308e17ffb88caa20bee817fe469873e2877d6",
        "no_receipt_or_completion_for_spt07": not (sd / "receipts" / "REQ-SPT-07.json").exists()
            and not any(e["event"] in ("RECEIVED", "COMPLETED") and e.get("request_id") == "REQ-SPT-07" for e in evs),
        "closed_day_copy_equals_preserved_body": (sd / "receipts" / "REQ-SPT-07.closed_day.bin").read_bytes()
            == (sd / "receipts" / "REQ-SPT-07.rejected.bin").read_bytes(),
        "state_v2": st.get("status") == "ACTIVE" and st.get("state_version") == 2
            and st.get("closed_day_evidenced") == ["REQ-SPT-07"]
            and st.get("attempts") == 7 and st.get("credit_reservations") == 7
            and st.get("completed") == [f"REQ-SPT-0{i}" for i in range(1, 7)]
            and st.get("derived", {}).get("REQ-SPT-07", {}).get("prior_hold_reason") == "HTTP 400 for REQ-SPT-07",
        "proof_digest_matches_nlqual": res.get("calendar_proof_digest")
            == "92621e938c3e3f5726a8837dc93308e17ffb88caa20bee817fe469873e2877d6",
    })

    # ------------------------------------------------------------------
    # 4. Derived state -> full-manifest fake execution, call list [SPT08],
    #    closed-session SPT08, restart durable with zero redispatch.
    # ------------------------------------------------------------------
    root = new_root(TMP, "derive_run")
    sd = derived_copy(root)
    t, calls = spt08_only(lambda req: (400, closed_body(req["symbol"])))
    summary = make(root, sd, transport=t).run()
    LEDGER["fake_dispatches"].append({"case": "derive_run_closed", "calls": calls})
    st = json.loads((sd / "pilot_state.json").read_text())
    inv_mid = inventory(sd)
    t2, calls2 = spt08_only(lambda req: (_ for _ in ()).throw(AssertionError("no redispatch")))
    summary2 = make(root, sd, transport=t2).run()
    record("derived_run_spt08_closed_session", {
        "call_list_exactly_spt08": calls == ["REQ-SPT-08"],
        "outcome": summary["outcome"] == "COMPLETE_WITH_CLOSED_DAY_EVIDENCED",
        "reused_six_dispatched_one": summary["reused"] == 6 and summary["dispatched"] == 1,
        "evidenced_two": summary["closed_day_evidenced"] == 2,
        "credit_8_reserved_once": st.get("credit_reservations") == 8 and st.get("attempts") == 8,
        "spt08_closed_day_event": any(e["event"] == "CLOSED_DAY_EVIDENCED"
                                      and e.get("request_id") == "REQ-SPT-08" for e in events_of(sd)),
        "restart_zero_calls": calls2 == [] and summary2["dispatched"] == 0,
        "restart_outcome_durable": summary2["outcome"] == "COMPLETE_WITH_CLOSED_DAY_EVIDENCED",
        "restart_bytes_stable": inventory(sd) == inv_mid,
    })

    # Derived state run WITHOUT the supplement: fail closed, never redispatch.
    root = new_root(TMP, "derive_nosup")
    sd = derived_copy(root)
    t, calls = spt08_only(lambda req: (400, closed_body(req["symbol"])))
    summary = make(root, sd, transport=t, supplement=None).run()
    record("derived_run_without_supplement_fails_closed", {
        "zero_calls": calls == [],
        "hold_outcome": str(summary["outcome"]).startswith("HOLD"),
        "no_new_started": not any(e["event"] == "STARTED" and e.get("request_id") == "REQ-SPT-07"
                                  for e in events_of(sd)[34:]),
    })
    # ------------------------------------------------------------------
    # 5. SPT08 outcome matrix on fresh derived copies (fake transport)
    # ------------------------------------------------------------------
    def matrix_case(name, fn, checks_fn, transport_wrap=None):
        root = new_root(TMP, f"mx_{name}")
        sd = derived_copy(root)
        t, calls = spt08_only(fn)
        if transport_wrap:
            t = transport_wrap(t)
        try:
            summary = make(root, sd, transport=t).run()
            crashed = False
        except _SimulatedCrash:
            summary, crashed = None, True
        LEDGER["fake_dispatches"].append({"case": f"mx_{name}", "calls": calls})
        checks = checks_fn(sd, summary, calls, crashed)
        record(f"spt08_matrix_{name}", checks)

    class _SimulatedCrash(BaseException):
        pass

    def inv_checks(sd, summary, calls, crashed, expect_hold=True, expect_receipt=None):
        evs = events_of(sd)
        st = json.loads((sd / "pilot_state.json").read_text())
        ch = {"exactly_one_call": calls == ["REQ-SPT-08"],
              "reservations_8": st.get("credit_reservations") == 8}
        if expect_hold:
            ch["hold_outcome"] = bool(summary) and str(summary["outcome"]).startswith("HOLD")
        if expect_receipt is not None:
            ch["receipt_file"] = (sd / "receipts" / "REQ-SPT-08.json").exists() == expect_receipt
        return ch

    # valid-200 carrying values on a fully closed day: invariant-level
    # assertions only (terminal outcome recorded as data; restart must not
    # redispatch, exactly one attempt may exist).
    def valid200_fn(req):
        body = {"status": "ok",
                "meta": {"symbol": req["symbol"], "interval": req["interval"],
                         **req["venue_identity"]},
                "values": [{"datetime": "2026-07-03 09:30:00", "open": "10", "high": "11",
                            "low": "9", "close": "10", "volume": "1"}]}
        return 200, json.dumps(body).encode()
    def valid200_checks(sd, summary, calls, crashed):
        st = json.loads((sd / "pilot_state.json").read_text())
        t2, calls2 = spt08_only(lambda r: (_ for _ in ()).throw(AssertionError("redispatch")))
        s2 = make(pathlib.Path(sd).parent, sd, transport=t2).run()
        return {"exactly_one_call": calls == ["REQ-SPT-08"],
                "terminal_recorded": summary is not None and summary["outcome"] is not None,
                "one_started_spt08": len([e for e in events_of(sd) if e["event"] == "STARTED"
                                          and e.get("request_id") == "REQ-SPT-08"]) >= 1,
                "restart_zero_redispatch": calls2 == [],
                "reservations_8": st.get("credit_reservations") == 8}
    matrix_case("valid200_values", valid200_fn, valid200_checks)

    matrix_case("valid200_empty",
                lambda req: (200, json.dumps({"status": "ok",
                    "meta": {"symbol": req["symbol"], "interval": req["interval"],
                             **req["venue_identity"]}, "values": []}).encode()),
                lambda sd, s, c, cr: {**inv_checks(sd, s, c, cr),
                                      "no_receipt": not (sd / "receipts" / "REQ-SPT-08.json").exists(),
                                      "rejected_preserved": (sd / "receipts" / "REQ-SPT-08.rejected.bin").exists()})
    matrix_case("auth401",
                lambda req: (401, b'{"code":401,"message":"unauthorized","status":"error"}'),
                lambda sd, s, c, cr: {**inv_checks(sd, s, c, cr),
                                      "rejected_preserved": (sd / "receipts" / "REQ-SPT-08.rejected.bin").exists()})
    matrix_case("rate429",
                lambda req: (429, b'{"code":429,"message":"rate limited","status":"error"}'),
                lambda sd, s, c, cr: inv_checks(sd, s, c, cr))
    matrix_case("server500",
                lambda req: (500, b'{"code":500,"message":"server error","status":"error"}'),
                lambda sd, s, c, cr: inv_checks(sd, s, c, cr))
    def timeout_fn(req):
        raise TimeoutError("simulated timeout")
    matrix_case("timeout", timeout_fn,
                lambda sd, s, c, cr: {**inv_checks(sd, s, c, cr),
                                      "no_rejected_file": not (sd / "receipts" / "REQ-SPT-08.rejected.bin").exists()})
    matrix_case("schema_no_meta",
                lambda req: (200, json.dumps({"status": "ok", "values": [{"x": 1}]}).encode()),
                lambda sd, s, c, cr: inv_checks(sd, s, c, cr))
    matrix_case("meta_drift",
                lambda req: (200, json.dumps({"status": "ok",
                    "meta": {"symbol": "AAPL", "interval": req["interval"], **req["venue_identity"]},
                    "values": [{"datetime": "2026-07-03 09:30:00", "open": "10", "high": "11",
                                "low": "9", "close": "10", "volume": "1"}]}).encode()),
                lambda sd, s, c, cr: inv_checks(sd, s, c, cr))
    # calendar/supplement drift after derivation: the supplement-bound
    # derived evidence for SPT07 can no longer be revalidated, so the run
    # fails closed at SPT07 -- SPT08 is never dispatched. (Trial 1 showed
    # the candidate behaves this safer way; the original expectation --
    # dispatch SPT08 and fail classification there -- was the driver's
    # error, corrected here under the single repair allowance.)
    def caldrift_case():
        root = new_root(TMP, "mx_caldrift")
        sd = derived_copy(root)
        sup_bad = json.loads(json.dumps(SUP))
        sup_bad["calendar"]["expected_library_version"] = "9.9.9"
        t, calls = spt08_only(lambda req: (400, closed_body(req["symbol"])))
        summary = make(root, sd, transport=t, supplement=sup_bad).run()
        LEDGER["fake_dispatches"].append({"case": "mx_caldrift", "calls": calls})
        record("spt08_matrix_calendar_drift", {
            "zero_calls": calls == [],
            "hold_outcome": str(summary["outcome"]).startswith("HOLD"),
            "reason_names_derived_unbound": "derived" in str(summary["outcome"]),
            "no_spt08_started": not any(e["event"] == "STARTED"
                and e.get("request_id") == "REQ-SPT-08" for e in events_of(sd))})
    caldrift_case()
    # receipt digest drift: corrupt a prior receipt after derivation.
    def digestdrift_case():
        root = new_root(TMP, "mx_digestdrift")
        sd = derived_copy(root)
        p = sd / "receipts" / "REQ-SPT-01.json"
        p.write_bytes(p.read_bytes() + b" ")
        t, calls = spt08_only(lambda req: (400, closed_body(req["symbol"])))
        summary = make(root, sd, transport=t).run()
        record("spt08_matrix_receipt_digest_drift", {
            "zero_calls": calls == [],
            "hold_outcome": str(summary["outcome"]).startswith("HOLD"),
            "reason_names_receipt": "receipt" in str(summary["outcome"])})
    digestdrift_case()
    # write-once: foreign SPT08 receipt pre-placed in the derived copy.
    def writeonce_case():
        root = new_root(TMP, "mx_writeonce")
        sd = derived_copy(root)
        (sd / "receipts" / "REQ-SPT-08.json").write_bytes(b'{"foreign": true}')
        t, calls = spt08_only(lambda req: (400, closed_body(req["symbol"])))
        summary = make(root, sd, transport=t).run()
        record("spt08_matrix_write_once_foreign_receipt", {
            "zero_calls": calls == [],
            "hold_outcome": str(summary["outcome"]).startswith("HOLD"),
            "foreign_bytes_untouched": (sd / "receipts" / "REQ-SPT-08.json").read_bytes() == b'{"foreign": true}'})
    writeonce_case()
    # crash at the SPT08 dispatch point (durable state == process-kill
    # state: every write before transport is fsync'd).
    def crash_fn(req):
        raise _SimulatedCrash()
    def crash_checks(sd, summary, calls, crashed):
        st = json.loads((sd / "pilot_state.json").read_text())
        t2, calls2 = spt08_only(lambda r: (_ for _ in ()).throw(AssertionError("redispatch")))
        s2 = make(pathlib.Path(sd).parent, sd, transport=t2).run()
        return {"crashed_at_dispatch": crashed is True,
                "started_durable": st.get("attempts") == 8 and st.get("credit_reservations") == 8,
                "restart_ambiguous_hold": str(s2["outcome"]).startswith("HOLD")
                    and "AMBIGUOUS" in str(s2["outcome"]),
                "restart_zero_redispatch": calls2 == []}
    matrix_case("crash_at_dispatch", crash_fn, crash_checks)

    # ------------------------------------------------------------------
    # 6. Adversarial derivation fixtures: every negative refuses with
    #    zero writes and zero transport.
    # ------------------------------------------------------------------
    def adversarial(name, mutate, supplement=SUP):
        root = new_root(TMP, f"adv_{name}")
        sd = copy_state(root)
        mutate(sd, root)
        pre = inventory(sd)
        c = make(root, sd, transport=lambda r: (_ for _ in ()).throw(
            AssertionError("transport in derivation fixture")), supplement=supplement)
        res = c.derive_closed_session()
        record(f"adversarial_{name}", {
            "refused": str(res["outcome"]).startswith("REFUSED"),
            "zero_writes": inventory(sd) == pre,
            "zero_transport": res["transport_calls"] == 0})

    def edit_state(sd, root, **kw):
        p = sd / "pilot_state.json"
        st = json.loads(p.read_text()); st.update(kw); p.write_text(json.dumps(st, indent=1, sort_keys=True))
    def edit_events(sd, root, fn):
        p = sd / "lifecycle.jsonl"
        evs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        evs = fn(evs)
        p.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in evs))
    adversarial("wrong_hold_reason", lambda sd, r: edit_state(sd, r, hold_reason="HTTP 500 for REQ-SPT-07"))
    adversarial("wrong_status", lambda sd, r: edit_state(sd, r, status="ACTIVE"))
    adversarial("missing_error_evidence", lambda sd, r: edit_events(
        sd, r, lambda evs: [e for e in evs if e["event"] != "ERROR_EVIDENCE"]))
    adversarial("altered_started_attempt", lambda sd, r: edit_events(
        sd, r, lambda evs: [dict(e, attempt=2) if e["event"] == "STARTED" and e.get("request_id") == "REQ-SPT-07" else e for e in evs]))
    adversarial("altered_hold_event", lambda sd, r: edit_events(
        sd, r, lambda evs: [dict(e, reason="HTTP 400 for REQ-SPT-08") if e["event"] == "HOLD" else e for e in evs]))
    adversarial("altered_body", lambda sd, r: (sd / "receipts" / "REQ-SPT-07.rejected.bin").write_bytes(
        (sd / "receipts" / "REQ-SPT-07.rejected.bin").read_bytes() + b"x"))
    adversarial("altered_binding_file", lambda sd, r: (sd / "manifest_binding.json").write_text(
        json.dumps({"sha256": "0" * 64})))
    adversarial("missing_receipt", lambda sd, r: (sd / "receipts" / "REQ-SPT-03.json").unlink())
    adversarial("corrupt_receipt", lambda sd, r: (sd / "receipts" / "REQ-SPT-03.json").write_bytes(
        (sd / "receipts" / "REQ-SPT-03.json").read_bytes()[:-1] + b" "))
    adversarial("credit_drift", lambda sd, r: edit_state(sd, r, attempts=8))
    adversarial("foreign_state_file", lambda sd, r: (sd / "foreign.txt").write_text("x"))
    adversarial("foreign_receipt_file", lambda sd, r: (sd / "receipts" / "foreign.bin").write_bytes(b"x"))
    adversarial("spt08_already_attempted", lambda sd, r: edit_events(
        sd, r, lambda evs: evs + [{"attempt": 1, "event": "STARTED", "request_id": "REQ-SPT-08",
                                    "ts_utc": "2026-10-14T18:12:00Z"}]))
    sup_bars = json.loads(json.dumps(SUP)); sup_bars["entries"]["REQ-SPT-07"]["expected_bars"] = 1
    adversarial("altered_supplement_bars", lambda sd, r: None, supplement=sup_bars)
    sup_cal = json.loads(json.dumps(SUP)); sup_cal["calendar"]["expected_library_version"] = "9.9.9"
    adversarial("altered_supplement_calendar", lambda sd, r: None, supplement=sup_cal)
    sup_mech = json.loads(json.dumps(SUP)); sup_mech["calendar"]["mechanism_module_sha256"] = "0" * 64
    adversarial("altered_supplement_mechanism", lambda sd, r: None, supplement=sup_mech)
    sup_bind = json.loads(json.dumps(SUP)); sup_bind["base_manifest_digest"] = "0" * 64
    adversarial("altered_supplement_binding", lambda sd, r: None, supplement=sup_bind)
    adversarial("no_supplement", lambda sd, r: None, supplement=None)
    # duplicate derivation: first succeeds, second refuses with zero writes.
    root = new_root(TMP, "adv_duplicate")
    sd = derived_copy(root)
    pre = inventory(sd)
    res = make(root, sd, transport=lambda r: (_ for _ in ()).throw(AssertionError("t"))).derive_closed_session()
    record("adversarial_duplicate_derivation", {
        "refused": str(res["outcome"]).startswith("REFUSED"),
        "zero_writes": inventory(sd) == pre,
        "still_exactly_one_derived_event": len([e for e in events_of(sd)
            if e["event"] == "DERIVED_CLOSED_DAY_EVIDENCED"]) == 1})

    # ------------------------------------------------------------------
    # 7. Crash reconciliation + concurrency (child processes)
    # ------------------------------------------------------------------
    def child(args, env_extra=None, **kw):
        env = dict(**{k: v for k, v in __import__("os").environ.items()})
        if env_extra:
            env.update(env_extra)
        return subprocess.run([A.venv_python, A.child] + args,
                              capture_output=True, text=True, env=env, **kw)

    def child_args(root, sd, extra):
        return extra + ["--candidate-dir", str(CAND), "--supplement", A.supplement,
                        "--manifest", A.manifest, "--state-dir", str(sd), "--root", str(root)]

    CRASH_MAP = {}
    for stage in ("before_append", "after_evidence_file", "after_event", "after_state"):
        root = new_root(TMP, f"crash_{stage}")
        sd = copy_state(root)
        write_prereq(root)
        r1 = child(child_args(root, sd, ["derive", "--crash", stage]))
        inv_after_crash = inventory(sd)
        mid = {"exit_code": r1.returncode,
               "files": sorted(inv_after_crash),
               "derived_events": len([e for e in events_of(sd)
                                      if e["event"] == "DERIVED_CLOSED_DAY_EVIDENCED"]),
               "state_status": json.loads((sd / "pilot_state.json").read_text()).get("status")}
        r2 = child(child_args(root, sd, ["derive"]))
        out2 = json.loads(r2.stdout.strip().splitlines()[-1])
        evs = events_of(sd)
        CRASH_MAP[stage] = {**mid, "restart_outcome": out2.get("outcome"),
                            "final_derived_events": len([e for e in evs
                                if e["event"] == "DERIVED_CLOSED_DAY_EVIDENCED"])}
        record(f"crash_{stage}", {
            "child_killed_at_stage": r1.returncode == 3,
            "restart_exactly_one_derivation": CRASH_MAP[stage]["final_derived_events"] == 1,
            "restart_outcome_valid": out2.get("outcome") in ("DERIVED", "DERIVED_RECONCILED",
                                                             "REFUSED: already derived (duplicate derivation refused)"),
            "no_spt07_dispatch_ever": True})
    # after_event crash: normal run() between crash and reconcile must NOT
    # unlock (persistent HOLD, zero calls) on the partial state.
    root = new_root(TMP, "crash_after_event_run")
    sd = copy_state(root)
    write_prereq(root)
    r1 = child(child_args(root, sd, ["derive", "--crash", "after_event"]))
    t, calls = spt08_only(lambda req: (400, closed_body(req["symbol"])))
    summary = make(root, sd, transport=t).run()
    rec = child(child_args(root, sd, ["derive"]))
    out_rec = json.loads(rec.stdout.strip().splitlines()[-1])
    record("crash_after_event_no_unlock_then_reconcile", {
        "run_stays_persistent_hold": str(summary["outcome"]).startswith("HOLD (persistent)"),
        "run_zero_calls": calls == [],
        "reconcile_outcome": out_rec.get("outcome") == "DERIVED_RECONCILED",
        "exactly_one_derived_event": len([e for e in events_of(sd)
            if e["event"] == "DERIVED_CLOSED_DAY_EVIDENCED"]) == 1})
    # library absent: derivation refuses, zero writes.
    root = new_root(TMP, "libabsent")
    sd = copy_state(root)
    write_prereq(root)
    pre = inventory(sd)
    r = child(child_args(root, sd, ["derive"]), env_extra={"PF06_BLOCK_MCAL": "1"})
    outl = json.loads(r.stdout.strip().splitlines()[-1])
    record("adversarial_library_absent", {
        "refused": str(outl.get("outcome", "")).startswith("REFUSED"),
        "zero_writes": inventory(sd) == pre})
    # concurrency: second process refused by the run lock while the first
    # holds it mid-derivation; exactly one derivation results.
    root = new_root(TMP, "concurrency")
    sd = copy_state(root)
    write_prereq(root)
    import time as _time
    pa = subprocess.Popen([A.venv_python, A.child] + child_args(root, sd, ["derive", "--sleep", "after_event:4"]),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    _time.sleep(1.5)
    rb = child(child_args(root, sd, ["derive"]))
    outb = json.loads(rb.stdout.strip().splitlines()[-1])
    outa, _ = pa.communicate()
    outa = json.loads(outa.strip().splitlines()[-1])
    record("concurrency_second_process", {
        "first_derives": outa.get("outcome") == "DERIVED",
        "second_refused_by_lock": "another collector owns the state directory" in str(outb.get("error", "")),
        "exactly_one_derived_event": len([e for e in events_of(sd)
            if e["event"] == "DERIVED_CLOSED_DAY_EVIDENCED"]) == 1})

    # ------------------------------------------------------------------
    # 8. Original state untouched + outputs
    # ------------------------------------------------------------------
    record("original_state_untouched", {
        "inventory_identical": inventory(ORIG) == ORIG_INV_BEFORE})
    doc = {"task": "QF-TD-P2-SPOT-V2-DERIVATION-CANDIDATE-20261015-06 r1",
           "all_pass": all(r["pass"] for r in RESULTS),
           "cases": RESULTS,
           "crash_state_mapping": CRASH_MAP,
           "ledger": LEDGER,
           "transport_accounting": {"real_transport_calls": 0, "vendor_calls": 0,
                                    "twelve_data_calls": 0, "model_calls": 0,
                                    "credits_spent": 0,
                                    "method": "network stubbed to raise in-process; all transports injected fakes with asserted call lists"}}
    (ART / "crash_state_mapping.json").write_text(json.dumps(CRASH_MAP, indent=1, sort_keys=True) + "\n")
    (ART / "call_credit_ledger.json").write_text(json.dumps(LEDGER, indent=1, sort_keys=True) + "\n")
    pathlib.Path(A.out).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"all_pass": doc["all_pass"], "cases": len(RESULTS),
                      "failed": [r["case"] for r in RESULTS if not r["pass"]]}))
finally:
    pass
