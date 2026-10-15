#!/usr/bin/env python3
"""QF-TD-P2-SPOT-V2-EXECUTION-PREFLIGHT-20261015-04 r1 driver.

Offline execution preflight for P2-SPOT v2 / REQ-SPT-08. Fake transport only;
network disabled in-process before any collector import. Drives the IMMUTABLE
candidate collector (ab254c3, b683d277...) with the REAL NL-20261015
environment (pandas_market_calendars 4.5.1, pinned mechanism 1b83cdcd...) and
the REAL RollingCreditLimiter (fixed wall clock). No candidate bytes are
modified. Output: one normalized JSON document (no timestamps, no tmp paths)
so two runs can be diffed byte-for-byte.

Modes: main | vmismatch | libabsent | mechraise (perturbation modes run the
NLQUAL N10 pattern: a closed-day request + preserved body must HOLD).
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import socket
import sys
import tempfile


def _no_net(*a, **k):
    raise RuntimeError("network disabled (PF04 offline preflight)")


socket.socket.connect = _no_net
socket.socket.connect_ex = _no_net
socket.create_connection = _no_net
socket.getaddrinfo = _no_net

P = argparse.ArgumentParser()
P.add_argument("--mode", default="main",
               choices=["main", "vmismatch", "libabsent", "mechraise"])
P.add_argument("--candidate-dir", required=True)
P.add_argument("--supplement", required=True)
P.add_argument("--preserved-body", required=True)
P.add_argument("--manifest", required=True)
P.add_argument("--out", required=True)
ARGS = P.parse_args()

CAND = pathlib.Path(ARGS.candidate_dir).resolve()
HARNESS = CAND.parent / "pilot_harness"
EPOCH = 1792000000

if ARGS.mode == "libabsent":
    sys.modules["pandas_market_calendars"] = None

sys.path.insert(0, str(HARNESS))

spec = importlib.util.spec_from_file_location("pf04_collector", CAND / "td_min_collector.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

import validate_input
MECH_SHA = hashlib.sha256(pathlib.Path(validate_input.__file__).read_bytes()).hexdigest()

PMC_VERSION = None
if ARGS.mode != "libabsent":
    import pandas_market_calendars as _mcal
    PMC_VERSION = str(_mcal.__version__)
    if ARGS.mode == "vmismatch":
        _mcal.__version__ = "9.9.9"
if ARGS.mode == "mechraise":
    def _boom(day):
        raise ImportError("simulated calendar unavailability (PF04 control)")
    validate_input.xnys_schedule = _boom

from rate_limiter import RollingCreditLimiter

SUP_NL = json.loads(pathlib.Path(ARGS.supplement).read_text())
SPOT8 = json.loads(pathlib.Path(ARGS.manifest).read_text())
PRESERVED = pathlib.Path(ARGS.preserved_body).read_bytes()
BY_ID = {r["request_id"]: r for r in SPOT8["requests"]}
RESULTS = []


def record(case, checks, note=""):
    RESULTS.append({"case": case, "pass": all(checks.values()),
                    "checks": {k: bool(v) for k, v in sorted(checks.items())},
                    "note": note})


def closed_body(symbol):
    return json.dumps({"code": 400, "message": mod.CLOSED_SESSION_MESSAGE,
                       "status": "error",
                       "meta": {"symbol": symbol, "interval": "1h",
                                "exchange": ""}}).encode()


def valid_body(req):
    """OK body whose bars are the REAL calendar's expected 1H starts for the
    request window, so the real validator accepts them."""
    import pandas as pd
    from validate_input import expected_1h_starts, xnys_schedule
    from datetime import date, timedelta
    d0 = date.fromisoformat(req["start_date"][:10])
    d1 = date.fromisoformat(req["end_date"][:10])
    values = []
    cur = d0
    while cur <= d1:
        sched = xnys_schedule(pd.Timestamp(cur.isoformat()))
        if sched is not None:
            for t in expected_1h_starts(*sched):
                values.append({"datetime": t.strftime("%Y-%m-%d %H:%M:%S"),
                               "open": "10", "high": "11", "low": "9",
                               "close": "10", "volume": "1"})
        cur += timedelta(days=1)
    meta = {"symbol": req["symbol"], "interval": req["interval"]}
    meta.update(req["venue_identity"])
    return json.dumps({"status": "ok", "meta": meta, "values": values}).encode()


def write_prereq(root, bad=False):
    p = root / "prereq.json"
    doc = {"plan": "Basic" if not bad else "Grow",
           "endpoint_weight": {"endpoint": "/time_series", "credits_per_request": 1,
                               "evidence": "PF04 offline fixture (synthetic prerequisite; no vendor contact)"},
           "retention": {"status": "BOUNDED_RESOLVED", "condition": "30-day deletion"},
           "interval_semantics": {"status": "INSUFFICIENT"}}
    p.write_text(json.dumps(doc))
    return p


def fresh_root():
    tmp = tempfile.TemporaryDirectory()
    root = pathlib.Path(tmp.name)
    write_prereq(root)
    return tmp, root


def make_collector(root, manifest, supplement, transport, limiter=None, sd_name="state"):
    lim = limiter or RollingCreditLimiter(8, 800, state_path=root / "shared_credit.json",
                                          clock=lambda: EPOCH)
    return mod.Collector(root / sd_name, manifest, lim, transport=transport,
                         prereq_path=root / "prereq.json",
                         closed_session_supplement=supplement)


def norm_events(sd):
    p = sd / "lifecycle.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        if line.strip():
            e = json.loads(line)
            e.pop("ts_utc", None)
            out.append(e)
    return out


def read_state(sd):
    return json.loads((sd / "pilot_state.json").read_text())


def spot8_transport(calls, spt08="closed", spt07_body=None):
    def transport(req):
        rid = req["request_id"]
        calls.append(rid)
        if rid == "REQ-SPT-07":
            return 400, (spt07_body if spt07_body is not None else PRESERVED)
        if rid == "REQ-SPT-08":
            if spt08 == "closed":
                return 400, closed_body("QQQ")
            if spt08 == "valid":
                return 200, valid_body(req)
        return 200, valid_body(req)
    return transport


# ---------------------------------------------------------------------------
if ARGS.mode != "main":
    # NLQUAL N10 pattern: closed-day synthetic request must HOLD when the
    # calendar gate is perturbed (version drift / library absent / raise).
    def make_req(rid, symbol, start, end, bound):
        r = dict(request_id=rid, symbol=symbol, leg="SPOT", interval="1h",
                 start_date=start, end_date=end, timezone="America/New_York",
                 adjust="splits", order="asc", outputsize=5000, max_attempts=1,
                 pagination=False, credit_weight=1, expected_credits=1,
                 output_name=f"{rid}.json", one_response_bound_bars=bound,
                 venue_identity={"exchange": "NASDAQ", "currency": "USD"})
        r["identity"] = f"{symbol}|/time_series|1h|{start}|{end}|America/New_York|adjust=splits"
        return r
    req = make_req("REQ-TST-07", "AAPL", "2026-07-03T00:00:00", "2026-07-03T23:59:59", 7)
    man = {"endpoint": mod.ENDPOINT, "requests": [req]}
    sup = {"supplement_id": "P2-SPOT", "version": "v2",
           "base_manifest_digest": mod.canonical_digest(man),
           "calendar": json.loads(json.dumps(SUP_NL["calendar"])),
           "entries": {"REQ-TST-07": {"expected_bars": 0,
                                      "request_digest": mod.canonical_digest(req)}}}
    tmp, root = fresh_root()
    calls = []
    def transport(r):
        calls.append(r["request_id"])
        return 400, PRESERVED
    c = make_collector(root, man, sup, transport)
    s = c.run()
    ev = norm_events(root / "state")
    record(f"N10_{ARGS.mode}", {
        "outcome_hold": s["outcome"].startswith("HOLD"),
        "none_evidenced": s["closed_day_evidenced"] == 0,
        "one_call_only": calls == ["REQ-TST-07"],
        "no_class_event": not any(e["event"] == "CLOSED_DAY_EVIDENCED" for e in ev),
    }, "perturbed throwaway process; expect HOLD, no classification")
    pathlib.Path(ARGS.out).write_text(json.dumps(
        {"mode": ARGS.mode, "results": RESULTS}, indent=1, sort_keys=True) + "\n")
    raise SystemExit(0)

# ============================== MAIN ========================================
SPT08 = BY_ID["REQ-SPT-08"]
ONE_REQ_MANIFEST = {"manifest_id": "TD-P2-SPOT-V2-SPT08-EXECUTION-20261015",
                    "endpoint": SPOT8["endpoint"],
                    "status": "PREFLIGHT ARTIFACT — not adopted, not authorized for dispatch",
                    "requests": [json.loads(json.dumps(SPT08))]}

# -- §1 freeze / drift detection ---------------------------------------------
record("freeze_candidate_set", {
    "collector_sha": hashlib.sha256((CAND / "td_min_collector.py").read_bytes()).hexdigest()
        == "b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c",
    "supplement_sha": hashlib.sha256(pathlib.Path(ARGS.supplement).read_bytes()).hexdigest()
        == "9c71233003771d66cf81e99ae01a410ba8943aedfcce8a8c6411dfb51edacd32",
    "manifest_digest": mod.canonical_digest(SPOT8)
        == "748ca95789c6f16bab81fbc903fd0c60a890dd2f2e21a63d97ffdb962d70e4fb",
    "spt08_digest": mod.canonical_digest(SPT08)
        == "f547d8fec7882fa121feb966b33fde000b25c4ae0eb822a6b5a503f4a3651a97",
    "spt07_digest": mod.canonical_digest(BY_ID["REQ-SPT-07"])
        == "a259901ec57a8556228c2a6b95299c360102cc98edc62204ae539dc53a4c5edb",
    "supplement_binds_base": SUP_NL["base_manifest_digest"] == mod.canonical_digest(SPOT8),
    "supplement_spt08_entry": SUP_NL["entries"]["REQ-SPT-08"]["request_digest"]
        == mod.canonical_digest(SPT08),
    "mechanism_sha": MECH_SHA == "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58",
    "pmc_version": PMC_VERSION == "4.5.1",
    "preserved_body_sha": hashlib.sha256(PRESERVED).hexdigest()
        == "3339c34154648c0ea4ddb9bd553e5274d390f953552518ad957d79704b7d5d50",
    "spot8_manifest_valid": mod.validate_manifest(SPOT8) == [],
})

# -- §2 one-request SPT08 execution manifest ----------------------------------
canon_req_bytes = json.dumps(SPT08, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode()
record("spt08_one_request_manifest", {
    "validates": mod.validate_manifest(ONE_REQ_MANIFEST) == [],
    "exactly_one_request": len(ONE_REQ_MANIFEST["requests"]) == 1,
    "request_object_identical": ONE_REQ_MANIFEST["requests"][0] == SPT08,
    "max_attempts_1": SPT08["max_attempts"] == 1,
    "pagination_disabled": not SPT08.get("pagination"),
    "credit_weight_1": SPT08["credit_weight"] == 1 and SPT08["expected_credits"] == 1,
    "output_name": SPT08["output_name"] == "REQ-SPT-08.json",
    "canonical_bytes_sha": hashlib.sha256(canon_req_bytes).hexdigest()
        == hashlib.sha256(json.dumps(SPT08, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    "one_req_digest_differs_from_base": mod.canonical_digest(ONE_REQ_MANIFEST)
        != mod.canonical_digest(SPOT8),
}, "one-request manifest digest != supplement-bound base digest 748ca957...: "
   "classification binding consequence proven in the next case")

# -- §2b one-request manifest + NL supplement: fail-closed on closed session --
tmp, root = fresh_root()
calls = []
c = make_collector(root, ONE_REQ_MANIFEST, SUP_NL,
                   lambda r: (calls.append(r["request_id"]), (400, closed_body("QQQ")))[1])
s = c.run()
ev = norm_events(root / "state")
record("spt08_single_manifest_supplement_unbound_fails_closed", {
    "outcome_hold": s["outcome"].startswith("HOLD"),
    "exactly_one_call": calls == ["REQ-SPT-08"],
    "no_classification": not any(e["event"] == "CLOSED_DAY_EVIDENCED" for e in ev),
    "no_receipt": not (root / "state" / "receipts" / "REQ-SPT-08.json").exists(),
    "rejected_preserved": (root / "state" / "receipts" / "REQ-SPT-08.rejected.bin").exists(),
}, "supplement binds base digest 748ca957 only; a one-request manifest cannot "
   "carry the closed-session classification (fail-closed by construction)")

# -- §2c full spot8 end-to-end rehearsal (fake transport) ----------------------
tmp, root = fresh_root()
calls = []
c = make_collector(root, SPOT8, SUP_NL, spot8_transport(calls))
s = c.run()
sd = root / "state"
st = read_state(sd)
ev = norm_events(sd)
rec = sd / "receipts"
cde = [e for e in ev if e["event"] == "CLOSED_DAY_EVIDENCED"]
record("full_spot8_end_to_end", {
    "outcome": s["outcome"] == "COMPLETE_WITH_CLOSED_DAY_EVIDENCED",
    "calls_exactly_once_each_in_order": calls == [f"REQ-SPT-0{i}" for i in range(1, 9)],
    "completed_6": sorted(st["completed"]) == [f"REQ-SPT-0{i}" for i in range(1, 7)],
    "evidenced_07_08": st.get("closed_day_evidenced") == ["REQ-SPT-07", "REQ-SPT-08"],
    "credits_reserved_8": st["credit_reservations"] == 8,
    "receipts_01_06": all((rec / f"REQ-SPT-0{i}.json").exists() for i in range(1, 7)),
    "no_receipts_07_08": not (rec / "REQ-SPT-07.json").exists()
        and not (rec / "REQ-SPT-08.json").exists(),
    "closed_bins_byte_equal": (rec / "REQ-SPT-07.closed_day.bin").read_bytes() == PRESERVED
        and (rec / "REQ-SPT-08.closed_day.bin").read_bytes() == closed_body("QQQ"),
    "class_events_2": len(cde) == 2
        and all(e["lifecycle_class"] == "EXPECTED_EMPTY_CLOSED_SESSION" for e in cde),
    "spt08_event_digest": any(e["request_id"] == "REQ-SPT-08"
                              and e["request_digest"] == "f547d8fec7882fa121feb966b33fde000b25c4ae0eb822a6b5a503f4a3651a97"
                              for e in cde),
    "no_completed_events_07_08": not any(e["event"] == "COMPLETED"
                                        and e["request_id"] in ("REQ-SPT-07", "REQ-SPT-08") for e in ev),
    "state_active": st["status"] == "ACTIVE",
})

# -- §2d restart: already-evidenced/completed never redispatch -----------------
calls2 = []
def boom_transport(r):
    calls2.append(r["request_id"])
    raise AssertionError("transport must not be called on restart")
c2 = make_collector(root, SPOT8, SUP_NL, boom_transport)
s2 = c2.run()
st2 = read_state(sd)
record("restart_idempotent_zero_redispatch", {
    "zero_calls": calls2 == [],
    "outcome": s2["outcome"] == "COMPLETE_WITH_CLOSED_DAY_EVIDENCED",
    "reused_6": s2["reused"] == 6,
    "evidenced_again_2": s2["closed_day_evidenced"] == 2,
    "state_unchanged_counts": st2["credit_reservations"] == 8 and st2["attempts"] == 8,
})

# -- §2e one-request manifest against spot8-bound state: refused ----------------
calls3 = []
c3 = make_collector(root, ONE_REQ_MANIFEST, SUP_NL,
                    lambda r: (calls3.append(r["request_id"]), (200, b"{}"))[1])
try:
    c3.run()
    refused = False
except mod.CollectorError:
    refused = True
record("single_manifest_against_bound_state_refused", {
    "collector_error": refused,
    "zero_calls": calls3 == [],
}, "manifest binding mismatch refuses receipt/state reuse; no dispatch")

# -- §5 prerequisite failure -> zero calls ---------------------------------------
for label, bad in (("prereq_wrong_plan", True),):
    tmp, root = fresh_root()
    write_prereq(root, bad=True)
    calls = []
    c = make_collector(root, ONE_REQ_MANIFEST, SUP_NL,
                       lambda r: (calls.append(r["request_id"]), (200, b"{}"))[1])
    try:
        c.run()
        raised = False
    except mod.CollectorError:
        raised = True
    record(label, {"collector_error": raised, "zero_calls": calls == [],
                   "no_started": not (root / "state" / "lifecycle.jsonl").exists()
                   or "STARTED" not in (root / "state" / "lifecycle.jsonl").read_text()})
tmp, root = fresh_root()
(root / "prereq.json").unlink()
calls = []
c = make_collector(root, ONE_REQ_MANIFEST, SUP_NL,
                   lambda r: (calls.append(r["request_id"]), (200, b"{}"))[1])
try:
    c.run()
    raised = False
except mod.CollectorError:
    raised = True
record("prereq_missing", {"collector_error": raised, "zero_calls": calls == []})

# -- §5 limiter exhaustion -> zero dispatch ---------------------------------------
tmp, root = fresh_root()
lim = RollingCreditLimiter(8, 800, state_path=root / "shared_credit.json", clock=lambda: EPOCH)
for _ in range(8):
    assert lim.try_acquire(1, label="prefill")
calls = []
c = make_collector(root, ONE_REQ_MANIFEST, SUP_NL,
                   lambda r: (calls.append(r["request_id"]), (200, b"{}"))[1], limiter=lim)
s = c.run()
record("limiter_exhaustion", {
    "refused_outcome": s["outcome"].startswith("REFUSED"),
    "zero_calls": calls == [],
    "zero_dispatched": s["dispatched"] == 0,
})

# -- §5/§4 response-class matrix (single open-day stand-in request) --------------
def make_req(rid, symbol, start, end, bound):
    r = dict(request_id=rid, symbol=symbol, leg="SPOT", interval="1h",
             start_date=start, end_date=end, timezone="America/New_York",
             adjust="splits", order="asc", outputsize=5000, max_attempts=1,
             pagination=False, credit_weight=1, expected_credits=1,
             output_name=f"{rid}.json", one_response_bound_bars=bound,
             venue_identity={"exchange": "NASDAQ", "currency": "USD"})
    r["identity"] = f"{symbol}|/time_series|1h|{start}|{end}|America/New_York|adjust=splits"
    return r

OPEN_REQ = make_req("REQ-TST-OPEN", "AAPL", "2026-07-06T00:00:00", "2026-07-06T23:59:59", 7)
OPEN_MAN = {"endpoint": mod.ENDPOINT, "requests": [OPEN_REQ]}

def matrix_case(name, response, expect_hold, extra=None):
    tmp, root = fresh_root()
    calls = []
    def transport(r):
        calls.append(r["request_id"])
        if isinstance(response, Exception):
            raise response
        return response
    c = make_collector(root, OPEN_MAN, None, transport)
    s = c.run()
    checks = {"exactly_one_call": calls == ["REQ-TST-OPEN"]}
    if expect_hold:
        checks["outcome_hold"] = s["outcome"].startswith("HOLD")
    else:
        checks["outcome_complete"] = s["outcome"] == "COMPLETE"
        checks["receipt_written"] = (root / "state" / "receipts" / "REQ-TST-OPEN.json").exists()
    if extra:
        checks.update(extra(root, s))
    record(name, checks)

matrix_case("resp_valid_200", (200, valid_body(OPEN_REQ)), expect_hold=False)
matrix_case("resp_auth_401", (401, b'{"status":"error"}'), expect_hold=True,
            extra=lambda root, s: {"rejected_preserved":
                (root / "state" / "receipts" / "REQ-TST-OPEN.rejected.bin").exists()})
matrix_case("resp_rate_429", (429, b'{"status":"error"}'), expect_hold=True)
matrix_case("resp_server_500", (500, b'{"status":"error"}'), expect_hold=True)
matrix_case("resp_transport_timeout", TimeoutError("simulated"), expect_hold=True,
            extra=lambda root, s: {"no_rejected_bin":
                not (root / "state" / "receipts" / "REQ-TST-OPEN.rejected.bin").exists()})
matrix_case("resp_unparseable_200", (200, b"\x00\x01not-json"), expect_hold=True)
_bad_meta = json.loads(valid_body(OPEN_REQ))
_bad_meta["meta"]["symbol"] = "MSFT"
matrix_case("resp_meta_mismatch_200", (200, json.dumps(_bad_meta).encode()), expect_hold=True)
_err_status = json.loads(valid_body(OPEN_REQ))
_err_status["status"] = "error"
matrix_case("resp_api_status_error_200", (200, json.dumps(_err_status).encode()), expect_hold=True)

# -- §4 unknown billed credit: transport error after reservation ------------------
tmp, root = fresh_root()
calls = []
def timeout_transport(r):
    calls.append(r["request_id"])
    raise TimeoutError("simulated post-dispatch timeout")
c = make_collector(root, ONE_REQ_MANIFEST, SUP_NL, timeout_transport)
s = c.run()
st = read_state(root / "state")
calls_b = []
c = make_collector(root, ONE_REQ_MANIFEST, SUP_NL,
                   lambda r: (calls_b.append(r["request_id"]), (200, b"{}"))[1])
s_b = c.run()
record("unknown_billed_credit_no_redispatch", {
    "first_hold": s["outcome"].startswith("HOLD"),
    "reservation_stands": st["credit_reservations"] == 1 and st["attempts"] == 1,
    "restart_still_hold": s_b["outcome"].startswith("HOLD"),
    "restart_zero_calls": calls_b == [],
}, "credit outcome unknown after dispatch failure; reservation stands spent; "
   "persistent HOLD blocks any redispatch (reconciliation required)")

# -- §5 crash ambiguity: STARTED durable, process dies before response ------------
tmp, root = fresh_root()
calls = []
def crash_transport(r):
    calls.append(r["request_id"])
    raise KeyboardInterrupt()
c = make_collector(root, ONE_REQ_MANIFEST, SUP_NL, crash_transport)
try:
    c.run()
    crashed = False
except KeyboardInterrupt:
    crashed = True
calls_b = []
c = make_collector(root, ONE_REQ_MANIFEST, SUP_NL,
                   lambda r: (calls_b.append(r["request_id"]), (200, b"{}"))[1])
s_b = c.run()
st = read_state(root / "state")
record("crash_after_started_ambiguous", {
    "crash_propagated": crashed,
    "restart_hold_ambiguous": "AMBIGUOUS" in s_b["outcome"] or st["status"] == "HOLD",
    "restart_zero_calls": calls_b == [],
    "attempts_1": st["attempts"] == 1,
}, "STARTED with no RECEIVED/completion -> AMBIGUOUS terminal HOLD, never recalled")

# -- §5 write-once collision: foreign receipt file ----------------------------------
tmp, root = fresh_root()
sd = root / "state"
(sd / "receipts").mkdir(parents=True)
(sd / "receipts" / "REQ-TST-OPEN.json").write_bytes(b'{"foreign": true}')
calls = []
c = make_collector(root, OPEN_MAN, None,
                   lambda r: (calls.append(r["request_id"]), (200, valid_body(OPEN_REQ)))[1])
try:
    s = c.run()
    refused = s["outcome"].startswith("HOLD")
    how = "hold_summary"
except mod.CollectorError:
    # Stronger fail-closed: _bind_manifest refuses unbound foreign evidence
    # before any receipt reuse or dispatch (legacy/unbound evidence rule).
    refused = True
    how = "collector_error_unbound_evidence"
record("write_once_collision_foreign_receipt", {
    "refused": refused,
    "zero_calls": calls == [],
    "foreign_bytes_untouched": (sd / "receipts" / "REQ-TST-OPEN.json").read_bytes() == b'{"foreign": true}',
}, f"refusal path: {how}")

# -- §5 tampered supplement: SPT-08 classification disabled ---------------------------
tmp, root = fresh_root()
sup_t = json.loads(json.dumps(SUP_NL))
sup_t["entries"]["REQ-SPT-08"]["expected_bars"] = 1
calls = []
c = make_collector(root, SPOT8, sup_t, spot8_transport(calls))
s = c.run()
ev = norm_events(root / "state")
record("tampered_supplement_expected_bars", {
    "outcome_hold": s["outcome"].startswith("HOLD"),
    "calls_stop_at_spt08": calls == [f"REQ-SPT-0{i}" for i in range(1, 9)],
    "spt07_still_classified": any(e["event"] == "CLOSED_DAY_EVIDENCED"
                                  and e["request_id"] == "REQ-SPT-07" for e in ev),
    "spt08_not_classified": not any(e["event"] == "CLOSED_DAY_EVIDENCED"
                                    and e["request_id"] == "REQ-SPT-08" for e in ev),
    "spt08_rejected_preserved": (root / "state" / "receipts" / "REQ-SPT-08.rejected.bin").exists(),
})

# -- §5 tampered manifest: request drift breaks supplement binding ----------------------
tmp, root = fresh_root()
man_t = json.loads(json.dumps(SPOT8))
man_t["requests"][7]["end_date"] = "2026-07-04T23:59:59"
man_t["requests"][7]["one_response_bound_bars"] = 14
man_t["requests"][7]["identity"] = ("QQQ|/time_series|1h|2026-07-03T00:00:00|"
                                    "2026-07-04T23:59:59|America/New_York|adjust=splits")
calls = []
try:
    c = make_collector(root, man_t, SUP_NL, spot8_transport(calls))
    s = c.run()
    ev = norm_events(root / "state")
    drift_hold = s["outcome"].startswith("HOLD")
    no_class08 = not any(e["event"] == "CLOSED_DAY_EVIDENCED"
                         and e["request_id"] == "REQ-SPT-08" for e in ev)
except mod.CollectorError:
    drift_hold, no_class08 = True, True  # invalid manifest refused pre-dispatch
record("tampered_manifest_request_drift", {
    "fails_closed": drift_hold,
    "spt08_not_classified": no_class08,
    "digest_differs": mod.canonical_digest(man_t) != mod.canonical_digest(SPOT8),
})

pathlib.Path(ARGS.out).write_text(json.dumps(
    {"mode": "main", "results": RESULTS,
     "all_pass": all(r["pass"] for r in RESULTS)}, indent=1, sort_keys=True) + "\n")
print(json.dumps({"cases": len(RESULTS), "all_pass": all(r["pass"] for r in RESULTS)}))
