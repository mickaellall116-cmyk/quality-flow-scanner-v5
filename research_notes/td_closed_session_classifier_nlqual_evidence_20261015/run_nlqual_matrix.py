#!/usr/bin/env python3
"""NLQUAL real-calendar matrix for the EXPECTED_EMPTY_CLOSED_SESSION classifier
(QF-TD-CLOSED-SESSION-CLASSIFIER-NLQUAL-20261015-02 r1; spec Issue #1
comment 6183716994).

Drives the IMMUTABLE -17 candidate collector (ab254c3, td_min_collector.py
b683d277...) against the QUALIFIED NL-20261015 environment: real
pandas_market_calendars 4.5.1 and the real pinned mechanism
pilot_harness/validate_input.py (1b83cdcd...) ::xnys_schedule. The calendar
interface and library version are NEVER stubbed on any positive path.
Transport is fake; the network is disabled in-process before any import of
the collector. Limiter and prerequisites follow the established
test_pinned_integration pattern (real RollingCreditLimiter, fixed wall
clock; synthetic prereq fixture). Bar validation is the REAL validator:
follow-request bodies are generated from the real calendar's expected 1H
starts. No _validate_bars override anywhere.

Modes:
  pristine   full matrix (positives + negatives + real-manifest proofs)
  vmismatch  negative control: real library version attribute drifted to
             9.9.9 in this throwaway process -> F1 shape must HOLD
  libabsent  negative control: library import blocked in this throwaway
             process -> F1 shape must HOLD
  mechraise  negative control: real mechanism's xnys_schedule made to raise
             in this throwaway process -> F1 shape must HOLD
Perturbation modes touch throwaway processes only; the candidate bytes, the
installed environment and the supplement candidate are never modified.

Output: one normalized JSON document (no timestamps, no tmp paths) so two
runs can be diffed byte-for-byte.
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import socket
import sys
import tempfile

# --- network disabled before anything else loads ---------------------------
def _no_net(*a, **k):
    raise RuntimeError("network disabled (NLQUAL offline proof)")

socket.socket.connect = _no_net
socket.socket.connect_ex = _no_net
socket.create_connection = _no_net
socket.getaddrinfo = _no_net

P = argparse.ArgumentParser()
P.add_argument("--mode", default="pristine",
               choices=["pristine", "vmismatch", "libabsent", "mechraise"])
P.add_argument("--candidate-dir", required=True)
P.add_argument("--supplement", required=True)
P.add_argument("--preserved-body", required=True)
P.add_argument("--manifest", required=True)
P.add_argument("--lock", required=True)
P.add_argument("--out", required=True)
ARGS = P.parse_args()

CAND = pathlib.Path(ARGS.candidate_dir).resolve()
HARNESS = CAND.parent / "pilot_harness"
EPOCH = 1792000000  # fixed wall clock for the real limiter (determinism)

if ARGS.mode == "libabsent":
    sys.modules["pandas_market_calendars"] = None  # import -> ImportError

sys.path.insert(0, str(HARNESS))

spec = importlib.util.spec_from_file_location("nlqual_collector", CAND / "td_min_collector.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

import validate_input  # real pinned mechanism (resolves via HARNESS path)
MECH_SHA = hashlib.sha256(pathlib.Path(validate_input.__file__).read_bytes()).hexdigest()

PMC_VERSION = None
if ARGS.mode != "libabsent":
    import pandas_market_calendars as _mcal
    PMC_VERSION = str(_mcal.__version__)
    if ARGS.mode == "vmismatch":
        _mcal.__version__ = "9.9.9"  # drift simulation, this process only
if ARGS.mode == "mechraise":
    def _boom(day):
        raise ImportError("simulated calendar unavailability (NLQUAL N10 control)")
    validate_input.xnys_schedule = _boom

from rate_limiter import RollingCreditLimiter  # real limiter (fd03906 lineage)

SUP_TEMPLATE = json.loads(pathlib.Path(ARGS.supplement).read_text())
CAL_BLOCK = SUP_TEMPLATE["calendar"]
PRESERVED = pathlib.Path(ARGS.preserved_body).read_bytes()
EXACT_SHA256 = "3339c34154648c0ea4ddb9bd553e5274d390f953552518ad957d79704b7d5d50"
FOLLOW_RID = "REQ-FOLLOW-01"


def make_req(rid, symbol, start, end, bound):
    r = dict(request_id=rid, symbol=symbol, leg="SPOT", interval="1h",
             start_date=start, end_date=end, timezone="America/New_York",
             adjust="splits", order="asc", outputsize=5000, max_attempts=1,
             pagination=False, credit_weight=1, expected_credits=1,
             output_name=f"{rid}.json", one_response_bound_bars=bound,
             venue_identity={"exchange": "NASDAQ", "currency": "USD"})
    r["identity"] = f"{symbol}|/time_series|1h|{start}|{end}|America/New_York|adjust=splits"
    return r


def follow_req():
    return make_req(FOLLOW_RID, "AAPL", "2026-07-06T00:00:00", "2026-07-06T23:59:59", 7)


def follow_body():
    """OK body whose bars are the REAL calendar's expected 1H starts for
    2026-07-06 (full XNYS session), so the real validator accepts them."""
    import pandas as pd
    from validate_input import expected_1h_starts, xnys_schedule
    sched = xnys_schedule(pd.Timestamp("2026-07-06", tz="America/New_York"))
    starts = expected_1h_starts(*sched)
    values = [{"datetime": t.strftime("%Y-%m-%d %H:%M:%S"), "open": "10",
               "high": "11", "low": "9", "close": "10", "volume": "1"}
              for t in starts]
    return json.dumps({"status": "ok",
                       "meta": {"symbol": "AAPL", "interval": "1h",
                                "exchange": "NASDAQ", "currency": "USD"},
                       "values": values}).encode()


def make_supplement(man, entries_spec):
    by_id = {r["request_id"]: r for r in man["requests"]}
    return {"supplement_id": "P2-SPOT", "version": "v2",
            "base_manifest_digest": mod.canonical_digest(man),
            "calendar": json.loads(json.dumps(CAL_BLOCK)),
            "entries": {rid: {"expected_bars": eb,
                              "request_digest": mod.canonical_digest(by_id[rid])}
                        for rid, eb in entries_spec.items()}}


def run_batch(closed_req, closed_response, supplement="AUTO", entries_spec="AUTO",
              state_dir=None, manifest=None):
    tmp = None
    if state_dir is None:
        tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(tmp.name)
    else:
        root = state_dir.parent
    prereq = root / "prereq.json"
    if not prereq.exists():
        prereq.write_text(json.dumps({
            "plan": "Basic",
            "endpoint_weight": {"endpoint": "/time_series", "credits_per_request": 1,
                                "evidence": "NLQUAL offline fixture (synthetic prerequisite; no vendor contact)"},
            "retention": {"status": "BOUNDED_RESOLVED", "condition": "30-day deletion"},
            "interval_semantics": {"status": "INSUFFICIENT"}}))
    man = manifest if manifest is not None else {"endpoint": mod.ENDPOINT,
                                                 "requests": [closed_req, follow_req()]}
    if entries_spec == "AUTO":
        entries_spec = {closed_req["request_id"]: 0}
    sup = make_supplement(man, entries_spec) if supplement == "AUTO" else supplement
    calls = []

    def transport(req):
        calls.append(req["request_id"])
        if req["request_id"] == closed_req["request_id"]:
            return closed_response
        return 200, follow_body()

    lim = RollingCreditLimiter(8, 800, state_path=root / "shared_credit.json",
                               clock=lambda: EPOCH)
    sd = state_dir if state_dir is not None else root / "state"
    c = mod.Collector(sd, man, lim, transport=transport,
                      prereq_path=prereq, closed_session_supplement=sup)
    summary = c.run()
    state = json.loads((sd / "pilot_state.json").read_text())
    events = [json.loads(l) for l in
              (sd / "lifecycle.jsonl").read_text().splitlines() if l.strip()]
    out = {"summary": summary, "calls": calls, "state": state, "events": events,
           "receipts": sd / "receipts", "collector": c, "root": root,
           "state_dir": sd, "manifest": man, "supplement": sup, "_tmp": tmp}
    return out


def norm_classified(r, rid, body):
    s, st = r["summary"], r["state"]
    ev = [e for e in r["events"] if e["event"] == "CLOSED_DAY_EVIDENCED"]
    checks = {
        "outcome": s["outcome"] == "COMPLETE_WITH_CLOSED_DAY_EVIDENCED",
        "counts": s["closed_day_evidenced"] == 1 and s["completed"] == 1,
        "continued": r["calls"] == [rid, FOLLOW_RID],
        "state_active": st["status"] == "ACTIVE" and st["completed"] == [FOLLOW_RID]
                        and st["closed_day_evidenced"] == [rid],
        "credit_spent": st["credit_reservations"] == 2,
        "event_class": len(ev) == 1 and ev[0]["lifecycle_class"] == "EXPECTED_EMPTY_CLOSED_SESSION",
        "event_sha": len(ev) == 1 and ev[0]["sha256"] == hashlib.sha256(body).hexdigest(),
        "proof_digest": len(ev) == 1 and bool(ev[0]["calendar_proof_digest"]),
        "supp_digest": len(ev) == 1 and ev[0]["supplement_digest"] == mod.canonical_digest(r["supplement"]),
        "no_receipt_events": not any(e["event"] in ("RECEIVED", "COMPLETED")
                                     and e["request_id"] == rid for e in r["events"]),
        "follow_receipt": (r["receipts"] / f"{FOLLOW_RID}.json").exists(),
        "no_receipt": not (r["receipts"] / f"{rid}.json").exists(),
        "raw_preserved": (r["receipts"] / f"{rid}.closed_day.bin").exists()
                         and (r["receipts"] / f"{rid}.closed_day.bin").read_bytes() == body,
        "no_rejected_bin": not (r["receipts"] / f"{rid}.rejected.bin").exists(),
    }
    return checks


def norm_hold(r, rid):
    s, st = r["summary"], r["state"]
    checks = {
        "outcome_hold": s["outcome"].startswith("HOLD"),
        "none_evidenced": s["closed_day_evidenced"] == 0,
        "terminated": r["calls"] == [rid],
        "state_hold": st["status"] == "HOLD",
        "no_event": not any(e["event"] == "CLOSED_DAY_EVIDENCED" for e in r["events"]),
        "no_closed_bin": not (r["receipts"] / f"{rid}.closed_day.bin").exists(),
        "no_follow_receipt": not (r["receipts"] / f"{FOLLOW_RID}.json").exists(),
    }
    return checks


RESULTS = []


def record(case, checks, note=""):
    RESULTS.append({"case": case, "pass": all(checks.values()),
                    "checks": {k: bool(v) for k, v in sorted(checks.items())},
                    "note": note})


D = "2026-07-03T00:00:00"
E = "2026-07-03T23:59:59"

if ARGS.mode in ("vmismatch", "libabsent", "mechraise"):
    req = make_req("REQ-TST-07", "AAPL", D, E, 7)
    r = run_batch(req, (400, PRESERVED))
    record(f"N10_{ARGS.mode}", norm_hold(r, "REQ-TST-07"),
           "negative control in perturbed throwaway process; expect HOLD")
else:
    # -- provenance: preserved live evidence, not a reconstruction -----------
    record("provenance", {
        "len_180": len(PRESERVED) == 180,
        "sha_matches": hashlib.sha256(PRESERVED).hexdigest() == EXACT_SHA256})

    # -- calendar sanity under the REAL mechanism ------------------------------
    import pandas as pd
    record("calendar_sanity", {
        "jul03_closed": validate_input.xnys_schedule(pd.Timestamp("2026-07-03")) is None,
        "jul04_closed": validate_input.xnys_schedule(pd.Timestamp("2026-07-04")) is None,
        "jul05_closed": validate_input.xnys_schedule(pd.Timestamp("2026-07-05")) is None,
        "jul06_open": validate_input.xnys_schedule(pd.Timestamp("2026-07-06")) is not None,
        "pmc_real_version": PMC_VERSION == "4.5.1",
        "mechanism_sha": MECH_SHA == "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58"})

    # -- positives ---------------------------------------------------------------
    req = make_req("REQ-TST-07", "AAPL", D, E, 7)
    record("F1_single_closed_day", norm_classified(run_batch(req, (400, PRESERVED)), "REQ-TST-07", PRESERVED))
    req = make_req("REQ-TST-F2", "AAPL", D, "2026-07-05T23:59:59", 21)
    record("F2_multiday_all_closed", norm_classified(run_batch(req, (400, PRESERVED)), "REQ-TST-F2", PRESERVED))

    # -- negatives ---------------------------------------------------------------
    req = make_req("REQ-TST-N1", "AAPL", D, "2026-07-06T23:59:59", 28)
    record("N1_mixed_window", norm_hold(run_batch(req, (400, PRESERVED)), "REQ-TST-N1"))

    body = PRESERVED.replace(b"dates. Try", b"dates! Try")
    req = make_req("REQ-TST-N2", "AAPL", D, E, 7)
    record("N2_message_mutated", norm_hold(run_batch(req, (400, body)), "REQ-TST-N2"))

    base = json.loads(PRESERVED)
    for i, mut in enumerate([
            lambda v: v.update(code="400"), lambda v: v.update(code=401),
            lambda v: v.pop("status"), lambda v: v.update(status="err")]):
        v = json.loads(PRESERVED); mut(v)
        rid = f"REQ-TST-N3{i}"
        req = make_req(rid, "AAPL", D, E, 7)
        record(f"N3_variant{i}", norm_hold(run_batch(req, (400, json.dumps(v).encode())), rid))

    body = json.dumps({"status": "ok", "meta": {"symbol": "AAPL", "interval": "1h",
                       "exchange": "NASDAQ", "currency": "USD"}, "values": []}).encode()
    req = make_req("REQ-TST-N4", "AAPL", D, E, 7)
    record("N4_http200_empty_values", norm_hold(run_batch(req, (200, body)), "REQ-TST-N4"))

    req = make_req("REQ-TST-N5", "AAPL", D, E, 7)
    record("N5_http200_exact_body", norm_hold(run_batch(req, (200, PRESERVED)), "REQ-TST-N5"))

    v = json.loads(PRESERVED)
    v["message"] = "Invalid api key. Please check your API key and try again."
    req = make_req("REQ-TST-N6", "AAPL", D, E, 7)
    record("N6_auth_message", norm_hold(run_batch(req, (400, json.dumps(v).encode())), "REQ-TST-N6"))

    for st in (401, 403, 429, 500):
        rid = f"REQ-TST-N7{st}"
        req = make_req(rid, "AAPL", D, E, 7)
        record(f"N7_status{st}", norm_hold(run_batch(req, (st, PRESERVED)), rid))

    req = make_req("REQ-TST-N8", "AAPL", D, E, 7)
    record("N8_unparseable", norm_hold(run_batch(req, (400, b"not json{{")), "REQ-TST-N8"))

    req = make_req("REQ-TST-N9", "AAPL", D, E, 7)
    record("N9_entry_absent", norm_hold(run_batch(req, (400, PRESERVED), entries_spec={}), "REQ-TST-N9"))
    record("N9_expected_bars_nonzero",
           norm_hold(run_batch(req, (400, PRESERVED), entries_spec={"REQ-TST-N9": 7}), "REQ-TST-N9"))

    v = json.loads(PRESERVED); v["values"] = []
    req = make_req("REQ-TST-N11", "AAPL", D, E, 7)
    record("N11_values_present", norm_hold(run_batch(req, (400, json.dumps(v).encode())), "REQ-TST-N11"))

    req = make_req("REQ-TST-N12", "AAPL", D, E, 7)
    man = {"endpoint": mod.ENDPOINT, "requests": [req, follow_req()]}
    sup = make_supplement(man, {req["request_id"]: 0}); sup["base_manifest_digest"] = "0" * 64
    record("N12_manifest_digest", norm_hold(run_batch(req, (400, PRESERVED), supplement=sup), "REQ-TST-N12"))
    sup = make_supplement(man, {req["request_id"]: 0})
    sup["entries"][req["request_id"]]["request_digest"] = "0" * 64
    record("N12_request_digest", norm_hold(run_batch(req, (400, PRESERVED), supplement=sup), "REQ-TST-N12"))

    body = PRESERVED.replace(b'"symbol":"AAPL"', b'"symbol":"QQQ"')
    req = make_req("REQ-TST-S1", "AAPL", D, E, 7)
    record("S1_meta_symbol_mismatch", norm_hold(run_batch(req, (400, body)), "REQ-TST-S1"))

    req = make_req("REQ-TST-S2", "AAPL", D, E, 7)
    record("S2_no_supplement", norm_hold(run_batch(req, (400, PRESERVED), supplement=None), "REQ-TST-S2"))

    # S3 restart: evidenced request is never redispatched
    req = make_req("REQ-TST-S3", "AAPL", D, E, 7)
    r = run_batch(req, (400, PRESERVED))
    ok = all(norm_classified(r, "REQ-TST-S3", PRESERVED).values())
    calls2 = []

    def transport2(req2):
        calls2.append(req2["request_id"])
        return 200, follow_body()

    lim2 = RollingCreditLimiter(8, 800, state_path=r["root"] / "shared_credit.json",
                                clock=lambda: EPOCH)
    c2 = mod.Collector(r["state_dir"], r["manifest"], lim2, transport=transport2,
                       prereq_path=r["root"] / "prereq.json",
                       closed_session_supplement=r["supplement"])
    s2 = c2.run()
    record("S3_restart_no_redispatch", {
        "first_classified": ok, "no_calls": calls2 == [],
        "evidenced_again": s2["closed_day_evidenced"] == 1,
        "reused": s2["reused"] == 1, "no_hold": "HOLD" not in s2["outcome"]})

    # -- REAL07: the actual preserved REQ-SPT-07 request + preserved body ------
    man_full = json.loads(pathlib.Path(ARGS.manifest).read_text())
    spt07 = next(x for x in man_full["requests"] if x["request_id"] == "REQ-SPT-07")
    spt08 = next(x for x in man_full["requests"] if x["request_id"] == "REQ-SPT-08")
    man2 = {"endpoint": mod.ENDPOINT, "requests": [spt07, follow_req()]}
    r = run_batch(spt07, (400, PRESERVED), manifest=man2,
                  entries_spec={"REQ-SPT-07": 0})
    checks = norm_classified(r, "REQ-SPT-07", PRESERVED)
    checks["req_digest_is_preregistered"] = (
        mod.canonical_digest(spt07) == "a259901ec57a8556228c2a6b95299c360102cc98edc62204ae539dc53a4c5edb")
    record("REAL07_preserved_request_and_body", checks,
           "real REQ-SPT-07 request object + preserved 180-byte live body, real calendar")

    # -- ELIG08: SPT-08 eligibility WITHOUT dispatch ------------------------------
    man_bytes = pathlib.Path(ARGS.manifest).read_bytes()
    shipped = json.loads((CAND / "p2_spot_supplement_v2.json").read_text())
    transport_calls = []

    def forbidden_transport(req):
        transport_calls.append(req["request_id"])
        raise AssertionError("transport must not be invoked in the eligibility proof")

    lim3 = RollingCreditLimiter(8, 800, state_path=pathlib.Path(tempfile.mkdtemp()) / "shared_credit.json",
                                clock=lambda: EPOCH)
    c3 = mod.Collector(pathlib.Path(tempfile.mkdtemp()) / "state",
                       man_full,
                       lim3, transport=forbidden_transport,
                       prereq_path=None, closed_session_supplement=SUP_TEMPLATE)
    qqq_body = PRESERVED.replace(b'"symbol":"AAPL"', b'"symbol":"QQQ"')
    proof = c3._classify_closed_session(spt08, 400, qqq_body)
    proof_neg = c3._classify_closed_session(spt08, 400, PRESERVED)  # meta.symbol AAPL != QQQ
    record("ELIG08_spt08_eligible_no_dispatch", {
        "manifest_file_sha": hashlib.sha256(man_bytes).hexdigest()
            == "ddff040fa654303cf4289f4c39c2a5b5af998bd4065ceddd4e4f5d52fcb8c28d",
        "full_manifest_digest": mod.canonical_digest(man_full)
            == "748ca95789c6f16bab81fbc903fd0c60a890dd2f2e21a63d97ffdb962d70e4fb",
        "spt08_digest": mod.canonical_digest(spt08)
            == "f547d8fec7882fa121feb966b33fde000b25c4ae0eb822a6b5a503f4a3651a97",
        "shipped_entry": shipped["entries"]["REQ-SPT-08"]
            == {"expected_bars": 0, "request_digest": "f547d8fec7882fa121feb966b33fde000b25c4ae0eb822a6b5a503f4a3651a97"},
        "candidate_entry_identical": SUP_TEMPLATE["entries"]["REQ-SPT-08"] == shipped["entries"]["REQ-SPT-08"],
        "classifier_proof": proof is not None,
        "proof_window_closed": proof is not None and proof["per_date"] == {"2026-07-03": "closed"},
        "proof_library": proof is not None and proof["library_version"] == "4.5.1",
        "proof_mechanism": proof is not None and proof["mechanism_module_sha256"]
            == "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58",
        "meta_mismatch_control": proof_neg is None,
        "no_dispatch": transport_calls == []},
        "direct classifier precondition evaluation on preserved inputs only; SPT-08 NOT dispatched, NOT attempted")

doc = {
    "task": "QF-TD-CLOSED-SESSION-CLASSIFIER-NLQUAL-20261015-02 r1",
    "mode": ARGS.mode,
    "environment": {
        "python": ".".join(str(x) for x in sys.version_info[:3]),
        "pandas_market_calendars": PMC_VERSION if ARGS.mode != "vmismatch" else "9.9.9 (drifted in-process for N10 control; installed 4.5.1)",
        "mechanism_module_sha256": MECH_SHA,
        "collector_sha256": hashlib.sha256((CAND / "td_min_collector.py").read_bytes()).hexdigest(),
        "supplement_candidate_sha256": hashlib.sha256(pathlib.Path(ARGS.supplement).read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256(pathlib.Path(ARGS.lock).read_bytes()).hexdigest(),
        "network": "disabled in-process (socket connect/getaddrinfo raise)",
    },
    "cases": RESULTS,
    "counts": {"total": len(RESULTS), "passed": sum(1 for x in RESULTS if x["pass"])},
}
pathlib.Path(ARGS.out).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
print(json.dumps(doc["counts"]))
sys.exit(0 if doc["counts"]["passed"] == doc["counts"]["total"] else 1)
