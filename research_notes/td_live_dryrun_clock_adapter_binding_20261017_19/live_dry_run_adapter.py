#!/usr/bin/env python3
"""Dedicated LIVE readiness dry-run adapter
(QF-TD-LIVE-DRYRUN-CLOCK-ADAPTER-BINDING-20261017-19 r1 candidate).

WHY THIS FILE EXISTS (failure memory: LIVE_DRYRUN_TEST_CLOCK_LEAK,
UNBOUND_DRYRUN_ADAPTER). The -14/-17 adapter (r4_dry_run_adapter.py,
7a56d86a...) routed the live dry-run through the -11 TRIAL harness
(run_dispatch_gate_trials_r4.py), whose Trial.dispatch() injects a
fixed FakeClock(NOW) with NOW = 1792224000 == 2026-10-17T08:00:00Z
(the runner's own comment mislabels it 14:00:00Z). In live run -18
the vendor evidence (timestamp 2026-10-17 21:01:03Z, ~1 s old) sat
~13 h AHEAD of that frozen clock, gate 3 emitted
ACCOUNT_EVIDENCE_STALE, the dry-run scored 11/12 and the transaction
rolled back a sound adoption. The trial harness is a fixture tool;
its clock must never reach a live evaluation.

This adapter is the dedicated live replacement:

- It loads the accepted r4 gate (dispatch_gate_r4.py) DIRECTLY by
  exact path + sha256 pin. It never imports the trial harness and
  never touches base_evidence()/Trial.
- It derives ONE canonical evaluation anchor from the immutable
  executor evidence file (the refrozen evidence.json): facts.
  evaluated_at, the epoch the executor itself recorded when it
  evaluated gate 3 live. The anchor must be a finite number; it is
  cross-checked against the vendor timestamp under the SAME bounds
  the -10 Policy A candidate enforces (MAX_AGE_S = 3600 past,
  FUTURE_SKEW_S = 60 future). That single anchor is used for BOTH
  the gate clock and the dispatch window. No fixture constant, no
  wall-clock substitution: the clock cannot drift from the evidence
  it judges.
- Every evidence field is built explicitly here from pinned inputs:
  packet identity (txn, GO record) from the executor packet; gate
  adjudication/run/manifest/supplement/driver/policy pins from the
  pin-loaded gate module itself; the environment record from the
  pinned NL lock file (freeze hash + pandas_market_calendars line)
  and the running interpreter; the account section verbatim from
  the executor's status facts; credential/stop-rule/retention
  sections are the standing attestations of the adjudicated -05
  execution packet, restated here as literals of THIS packet.
- The gate is invoked in its test seam (mode="test", token=None ->
  PASS_DRY_RUN ceiling: it can never arm a transport or run the
  screen) with an AnchorClock at the evidence anchor and the -11
  helper stub as the gate-9 preflight override (path + sha pinned
  here; the executor verifies the REAL sanctioned helper separately
  in its own HELPER_OK phase).

Refusals raise LiveDryRunRefusal with a stable code; the executor
treats any refusal as a dry-run failure (HOLD / rollback), never as
a pass.
"""
import calendar
import datetime
import hashlib
import importlib.util
import json
import math
import os
import platform

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.dirname(HERE)
PKG11 = os.path.join(NOTES, "td_policy_a_live_readiness_packet_20261017_11")
GATE_PATH = os.path.join(PKG11, "dispatch_gate_r4.py")
PIN_R4_GATE = "b53996454650dafc77e647a8497eba91beb3785fb52c13d70fa81768fd370117"
LOCK_PATH = os.path.join(NOTES, "td_nl_env_rebuild_evidence_20261016",
                         "lock_copy.txt")
STUB_PATH = os.path.join(PKG11, "helper_stub", "dynamic_credentials.py")
PIN_STUB_SHA = "8f80417de2eee56d5936d637b510583841b4fd778ef8a9ea26b14dae3a49e520"
# Freshness bounds: the -10 Policy A candidate's own pins
# (gate3_policy_candidate.py 7e44a2e0...: MAX_AGE_S / FUTURE_SKEW_S).
MAX_AGE_S = 3600
FUTURE_SKEW_S = 60
WINDOW_HALF_S = 3600


class LiveDryRunRefusal(Exception):
    def __init__(self, code, detail=""):
        super().__init__(code + (": " + detail if detail else ""))
        self.code = code


def _sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _load_gate():
    """Load the accepted r4 gate by exact path + sha256 pin, under a
    private module name (no sys.path / by-name resolution)."""
    if os.path.islink(GATE_PATH) or not os.path.isfile(GATE_PATH):
        raise LiveDryRunRefusal("GATE_PATH_REFUSED")
    if _sha256_file(GATE_PATH) != PIN_R4_GATE:
        raise LiveDryRunRefusal("GATE_PIN_MISMATCH")
    spec = importlib.util.spec_from_file_location(
        "qf_r4_gate_for_live_adapter", GATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AnchorClock:
    """Gate clock frozen at the evidence anchor. This is not a test
    fixture: the anchor is derived per-run from the immutable
    executor evidence and validated against the vendor timestamp
    before use. advance() is refused so nothing can move the
    evaluation instant away from the evidence."""

    def __init__(self, anchor):
        self._anchor = anchor

    def now(self):
        return self._anchor

    def advance(self, seconds):
        raise LiveDryRunRefusal("ANCHOR_CLOCK_IMMUTABLE")


def _vendor_epoch(raw):
    ts = (raw or {}).get("timestamp")
    try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except Exception:
        raise LiveDryRunRefusal("VENDOR_TS_MALFORMED", repr(ts))
    return calendar.timegm(dt.timetuple())


def _environment_record():
    """Environment evidence from the pinned NL lock file + the
    running interpreter (derived, never a stored literal)."""
    with open(LOCK_PATH, "rb") as f:
        lock = f.read()
    pmc = None
    for line in lock.decode().splitlines():
        if line.startswith("pandas_market_calendars=="):
            pmc = line.split("==", 1)[1].strip()
    if pmc is None:
        raise LiveDryRunRefusal("ENV_LOCK_UNREADABLE")
    interp = "%s %s" % (platform.python_implementation(),
                        platform.python_version())
    return {"interpreter": interp,
            "freeze_sha256": hashlib.sha256(lock).hexdigest(),
            "pandas_market_calendars": pmc}


def build_live_evidence(G, packet, target_path, raw, anchor, window,
                        state_dir, receipt_path):
    """The 12-gate evidence packet, built field-by-field from pinned
    inputs only. Mirrors the accepted -05 packet structure; every
    value names its source in the -19 memo's field map."""
    go = packet.get("go_record") or {}
    if go.get("record_id") != G.GO_RECORD_ID \
            or go.get("comment_id") != G.GO_COMMENT_ID:
        raise LiveDryRunRefusal("GO_RECORD_MISMATCH")
    return {
        "evidence_id": packet["txn_id"] + "/EVIDENCE",
        "packet": {
            "packet_id": packet["txn_id"] + "/PACKET",
            "adjudicated_verdict": G.EXPECTED_ADJUDICATION,
            "run_id": G.EXPECTED_RUN_ID,
            "manifest_digest": G.PIN_MANIFEST,
            "supplement_sha256": G.PIN_SUPPLEMENT,
            "entrypoint_sha256": G.PIN_DRIVER,
            "credit_ceiling": G.CREDIT_CEILING,
            "state_dir": state_dir,
            "ledger_path": target_path,
            "receipt_path": receipt_path,
            "dispatch_window": window,
            "account_evidence_max_age_s": MAX_AGE_S,
            "policy_digest": G.PIN_POLICY_A,
            "go_record": {"record_id": G.GO_RECORD_ID,
                          "comment_id": G.GO_COMMENT_ID,
                          "ceiling_credits": G.CREDIT_CEILING,
                          "status_credits": 1,
                          "manifest_credits": 51,
                          "spend_usd": 0},
        },
        "authority": {"basis": G.EXPECTED_AUTHORITY_BASIS,
                      "re_requested": False,
                      "task_ceiling_credits": G.CREDIT_CEILING,
                      "spend_usd": 0},
        "account": {"api_usage": dict(raw),
                    "source": "readiness_executor"},
        "environment": _environment_record(),
        "credential": {"ref": "custom.twelvedata",
                       "helper": "dynamic_credentials."
                                 "url_with_surrogate_query_param",
                       "allowed_hosts": ["api.twelvedata.com"],
                       "material_read_by_entrypoint": False},
        "stop_rules": {"armed": True, "first_error_stops_batch": True,
                       "ambiguous_never_redispatched": True,
                       "unknown_credit_hold": True},
        "retention": {"acknowledged": True,
                      "scope": "private_screen_evidence_only",
                      "indefinite_retention_claimed": False,
                      "redistribution": False},
    }


def make_live_dry_run_hook(packet, target_path, gate_module=None):
    """Returns hook(evidence_path) -> list of 12 gate results.

    The hook reads the executor's refrozen evidence file (immutable
    once written): txn/candidate bindings are cross-checked against
    the packet, the anchor is taken from facts.evaluated_at, and the
    gate evaluates the account facts at that anchor.
    """
    G = gate_module or _load_gate()
    root = packet["dryrun_root"]
    base = os.path.join(root, "live_dryrun")
    state_dir = os.path.join(base, "ns")
    receipt_path = os.path.join(base, "account", "gate_receipt.json")

    def hook(evidence_path):
        with open(evidence_path, "rb") as f:
            doc = json.loads(f.read().decode())
        if doc.get("txn_id") != packet.get("txn_id"):
            raise LiveDryRunRefusal("EVIDENCE_TXN_MISMATCH")
        if doc.get("candidate_sha") != packet.get("expected_candidate_sha"):
            raise LiveDryRunRefusal("EVIDENCE_CANDIDATE_MISMATCH")
        facts = doc.get("facts") or {}
        raw = facts.get("api_usage") or {}
        anchor = facts.get("evaluated_at")
        if isinstance(anchor, bool) \
                or not isinstance(anchor, (int, float)) \
                or not math.isfinite(anchor):
            raise LiveDryRunRefusal("ANCHOR_MALFORMED", repr(anchor))
        age = anchor - _vendor_epoch(raw)
        if age > MAX_AGE_S:
            raise LiveDryRunRefusal("EVIDENCE_STALE_BEYOND_MAX_AGE",
                                    "age %.3fs" % age)
        if age < -FUTURE_SKEW_S:
            raise LiveDryRunRefusal("VENDOR_FUTURE_SKEW_BEYOND_TOLERANCE",
                                    "age %.3fs" % age)
        declared = packet.get("dispatch_window")
        if declared is not None:
            try:
                start = float(declared["start"])
                end = float(declared["end"])
            except Exception:
                raise LiveDryRunRefusal("DISPATCH_WINDOW_MALFORMED")
            if not (start <= anchor <= end) \
                    or (end - start) > 2 * WINDOW_HALF_S:
                raise LiveDryRunRefusal("STALE_DISPATCH_WINDOW")
            window = {"start": declared["start"], "end": declared["end"]}
        else:
            window = {"start": int(anchor) - WINDOW_HALF_S,
                      "end": int(anchor) + WINDOW_HALF_S}
        os.makedirs(os.path.dirname(receipt_path), exist_ok=True)
        os.makedirs(state_dir, exist_ok=True)
        ev = build_live_evidence(G, packet, target_path, raw, anchor,
                                 window, state_dir, receipt_path)
        res = G.dispatch(
            G.canon(ev), dispatch_token=None, mode="test",
            clock=AnchorClock(anchor), transport_factory=None,
            paths_override={"helper_path": STUB_PATH,
                            "helper_sha256": PIN_STUB_SHA})
        return [g["result"] for g in res["receipt"]["gates"]]

    hook.is_live_adapter = True
    return hook
