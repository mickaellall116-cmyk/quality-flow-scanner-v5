#!/usr/bin/env python3
"""QF-TD-LIVE-READINESS-EXECUTOR-FINALIZE-20261017-14 r1 candidate.

The final live-capable readiness-only executor. It wires the accepted
-13 journal transaction semantics (readiness_transaction_r3.py,
db93f07e...) to the exact -11 r4 gate (dispatch_gate_r4.py,
b5399645...), the -08 credential resolver/helper handle
(credential_resolver.py c8271193...; sanctioned helper 8b1f42e8...),
the -10 Policy A gate-3 contract (gate3_policy_candidate.py
7e44a2e0...; Policy A canonical digest 5d9d82ca...) and the -07 ledger
candidate (79ff4844...), closing the one integration defect the -13
review held open:

LOCK-FIRST. The -13 candidate read the source ledger and computed
original_sha BEFORE acquiring locks and never re-read the bytes under
lock, so a concurrent legitimate reservation between that read and
lock acquisition could be silently overwritten by backup/rollback.
This executor never reads or pins live ledger bytes before BOTH locks
are held:

  1. the one-use marker is created with exclusive-create semantics
     (O_CREAT|O_EXCL) -- an existing marker refuses the transaction
     before any lock or ledger touch;
  2. the owner lease, then the shared-ledger lock, are acquired
     (nonblocking; contention refuses before any ledger read);
  3. ONLY THEN are the ledger bytes read, under lock; the exact
     legacy hash and legacy schema are required against the
     adjudicated pin, and THOSE locked bytes -- never a pre-lock
     snapshot -- are bound into the journal, the backup and any
     rollback. New locked bytes that do not match the adjudicated
     legacy pin produce HOLD; stale bytes are never restored;
  4. target/journal/path bindings are revalidated under lock
     immediately before the adoption mutation;
  5. both locks are held continuously through status evidence
     validation, backup/adoption, the r4 dry-run and the durable
     terminal commit, and released only in a finally block.

Recovery (recover_live) keeps the -13 binding precheck AND revalidates
marker/journal/path/target state again AFTER acquiring locks, closing
the precheck->lock TOCTOU: the journal bytes hashed at precheck must
be byte-identical under lock and a fresh binding precheck under lock
must pass, or recovery is HOLD_MANUAL before any ledger touch.
Recovery accepts NO status/helper callable.

Scope is readiness only: one GET /api_usage status call (Twelve Data
allowed host, Policy A expected schema, the call slot consumed and
journaled BEFORE invocation, no retry/redirect/alternate endpoint),
conditional adoption of the pinned ledger candidate, refreeze and a
12/12 r4 dry-run. Token issuance, armed market-data transport and
time_series exist only as refusals.

Modes. mode="live" requires a distinct one-use readiness clearance
artifact: a JSON file whose sha256 equals the packet pin and whose
fields bind txn id, this executor's source sha256, the r4 gate
sha256, the Policy A digest, the ledger candidate sha256 and the
legacy ledger pin; absent or mismatched clearance refuses BEFORE the
marker, locks or any file touch. Live mode uses actual UTC and the
exact sanctioned helper handle, and refuses all test hooks.
mode="offline" requires injected fixture hooks (stub helper resolved
through the same -08 resolver under the stub pin, an injected
transport spy, an injected clock); the sanctioned helper is never
imported on the offline path and the real network is never touched.
"""
import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.dirname(HERE)

PIN_R3 = "db93f07ee057b731528a231e836e67c791a01ab779c6893fe1bda6c258a5c79a"
PIN_R4_GATE = "b53996454650dafc77e647a8497eba91beb3785fb52c13d70fa81768fd370117"
PIN_R4_RUNNER = "93b911e067eb6ff6bc7e797b08df44eb1ac17a2417ac2102f3fd347087447864"
PIN_RESOLVER = "c8271193c97713f72b59af2377989362750142eda36940fa0be71cf6de8a911c"
PIN_HELPER = "8b1f42e80a76710edf0ff2abf8a51b0cde35b06474af865de108a7ca27d6728d"
PIN_GATE3 = "7e44a2e0d0a3b32dfd6fb7f93f04a224f935310a6e71dfe06ea83008595eb3f9"
PIN_POLICY_A_DIGEST = "5d9d82ca3e1c867e3f38dcb7f50cd7f372c793048d21232608f7835467d26cde"
PIN_POLICY_A_FILE = "728c3defc13d88c27e37d176c560aa708fc93a99730893c9d097c2ca5e9a57e5"
PIN_MANIFEST = "71aade8b"
PIN_SUPPLEMENT = "3cbdbf63"
GO_RECORD_ID = "QF-TD-POLICY-A-52-CREDIT-CEILING-GO-20261017"
GO_COMMENT_ID = 6234434220

STATUS_URL = "https://api.twelvedata.com/api_usage"
STATUS_HOST = "api.twelvedata.com"
ALLOWED_HOSTS = ["api.twelvedata.com"]
CREDENTIAL_NAME = "custom.twelvedata"
CEILING_CREDITS = 52

R3_PATH = os.path.join(
    NOTES, "td_readiness_txn_exception_binding_20261017_13",
    "readiness_transaction_r3.py")
RESOLVER_PATH = os.path.join(
    NOTES, "td_credential_helper_path_binding_20261017_08",
    "credential_resolver.py")
GATE3_PATH = os.path.join(
    NOTES, "td_gate3_attestation_policy_20261017_10",
    "gate3_policy_candidate.py")
POLICY_A_PATH = os.path.join(
    NOTES, "td_gate3_attestation_policy_20261017_10", "policy_A.json")
SANCTIONED_HELPER_PATH = \
    "/opt/hatch/skills/skill-creator/bin/dynamic_credentials.py"


def _sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def _sha256_file(path):
    with open(path, "rb") as f:
        return _sha256_bytes(f.read())


def _load_pinned(path, pin, name):
    digest = _sha256_file(path)
    if digest != pin:
        raise RuntimeError("PIN_MISMATCH:%s:%s" % (name, digest))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RT = _load_pinned(R3_PATH, PIN_R3, "qf14_r3_transaction")
RESOLVER = _load_pinned(RESOLVER_PATH, PIN_RESOLVER, "qf14_resolver")
GATE3 = _load_pinned(GATE3_PATH, PIN_GATE3, "qf14_gate3_policy")

H = RT.H
canon = RT.canon
Refusal = RT.Refusal
Journal = RT.Journal
_atomic_write = RT._atomic_write


def executor_source_sha():
    return _sha256_file(os.path.abspath(__file__))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Refusal("STATUS_REDIRECT_REFUSED", str(code))


def _live_http_get(url):
    """The live status transport: GET only, redirects refused, 30 s
    timeout, 32 MiB cap. Returns (http_status, body_bytes)."""
    req = urllib.request.Request(url, method="GET")
    opener = urllib.request.build_opener(_NoRedirect())
    with opener.open(req, timeout=30) as resp:
        body = resp.read(32 * 1024 * 1024 + 1)
        if len(body) > 32 * 1024 * 1024:
            raise Refusal("STATUS_RESPONSE_TOO_LARGE")
        return resp.status, body


class StatusBoundary:
    """The single pinned status-call slot. The slot is consumed BEFORE
    the transport is invoked; a second call is structurally refused.
    Only GET /api_usage on the Twelve Data allowed host can ever be
    constructed, via the verified helper handle."""

    def __init__(self, helper_handle, http_get):
        self._handle = helper_handle
        self._http_get = http_get
        self.consumed = False
        self.invocations = 0

    def call(self):
        if self.consumed:
            raise Refusal("STATUS_SLOT_ALREADY_CONSUMED")
        self.consumed = True  # consumed BEFORE invocation; no retry
        self._handle.reverify()
        url = self._handle.callable(
            STATUS_URL, CREDENTIAL_NAME, allowed_hosts=list(ALLOWED_HOSTS))
        self.invocations += 1
        return self._http_get(url)


def _legacy_schema_ok(obj):
    """The adjudicated legacy ledger shape (-07): {day, spent, window}
    with window a list of [ts, weight] pairs."""
    if not isinstance(obj, dict):
        return False
    if set(obj.keys()) != {"day", "spent", "window"}:
        return False
    if not isinstance(obj["day"], str) or not isinstance(obj["spent"], int):
        return False
    if not isinstance(obj["window"], list):
        return False
    for e in obj["window"]:
        if not (isinstance(e, list) and len(e) == 2
                and isinstance(e[0], (int, float))
                and isinstance(e[1], (int, float))):
            return False
    return True


def _same_day_reserved(legacy_obj, now_epoch):
    """Conservative same-day reservation count from the LOCKED legacy
    bytes: the day total when the ledger day is today (UTC), else the
    sum of today's window weights, taking the max of the two views."""
    today = datetime.datetime.fromtimestamp(
        now_epoch, datetime.timezone.utc).strftime("%Y-%m-%d")
    reserved = 0
    if legacy_obj.get("day") == today:
        reserved = max(reserved, int(legacy_obj.get("spent", 0)))
    wsum = 0
    for ts, w in legacy_obj.get("window", []):
        d = datetime.datetime.fromtimestamp(
            ts, datetime.timezone.utc).strftime("%Y-%m-%d")
        if d == today:
            wsum += w
    return max(reserved, int(wsum))


class LiveReadinessExecutor:
    def __init__(self, packet, hooks=None):
        self.packet = packet
        self.mode = packet.get("mode")
        if self.mode not in ("live", "offline"):
            raise Refusal("UNKNOWN_MODE")
        hooks = hooks or {}
        if self.mode == "live" and hooks:
            raise Refusal("LIVE_HOOKS_REFUSED")
        if self.mode == "offline" and not hooks.get("fixture"):
            raise Refusal("NON_FIXTURE_HOOKS_REFUSED")
        self.hooks = hooks
        self.txn_id = packet["txn_id"]
        self.workdir = os.path.abspath(packet["workdir"])
        self.target = os.path.abspath(packet["target_path"])
        with open(packet["candidate_path"], "rb") as f:
            self.candidate_bytes = f.read()
        self.candidate_sha = H(self.candidate_bytes)
        self.journal_path = os.path.join(self.workdir, "journal.json")
        self.marker_path = os.path.join(self.workdir, "CONSUMED.marker")
        self.backup_path = os.path.join(self.workdir, "ledger_backup.bin")
        self.evidence_path = os.path.join(self.workdir, "evidence.json")
        self.card_path = os.path.join(self.workdir, "token_card.json")
        self.receipt_path = os.path.join(self.workdir, "dry_run_receipt.json")
        self.terminal_path = os.path.join(self.workdir, "terminal_record.json")
        self.journal = None
        self._lease_fd = None
        self._lock_fd = None
        self.status_calls = 0
        self.boundary = None
        self._status_raw = None
        self._fail_at = hooks.get("fail_at")
        self._crash_at = hooks.get("crash_at")
        self._raise_at = hooks.get("raise_at") or {}
        self._clearance = None

    # -- refusals: outside readiness scope -------------------------------
    def request_token(self, *_a, **_k):
        raise Refusal("NOT_IN_READINESS_SCOPE")

    def arm_transport(self, *_a, **_k):
        raise Refusal("NOT_IN_READINESS_SCOPE")

    def call_time_series(self, *_a, **_k):
        raise Refusal("NOT_IN_READINESS_SCOPE")

    # -- injection points (offline hooks only) ----------------------------
    def _maybe_fail(self, step):
        if self._fail_at == step:
            raise Refusal("INJECTED_FAULT", step)

    def _maybe_crash(self, point):
        if self._crash_at == point:
            os._exit(42)

    def _fault(self, kind, stage):
        exc = self._raise_at.get(kind + ":" + stage)
        if exc is not None:
            raise exc

    def _advance(self, phase, **facts):
        exc = self._raise_at.get("journal:" + phase)
        if exc is not None:
            raise exc
        self.journal.advance(phase, **facts)

    def _now(self):
        if self.mode == "live":
            return time.time()  # actual UTC epoch
        return self.hooks["clock"]()

    # -- clearance (live arming artifact) ---------------------------------
    def _verify_clearance(self):
        path = self.packet.get("clearance_path")
        pin = self.packet.get("clearance_sha256")
        if not path or not pin or not os.path.isfile(path):
            raise Refusal("CLEARANCE_MISSING")
        raw = open(path, "rb").read()
        if _sha256_bytes(raw) != pin:
            raise Refusal("CLEARANCE_PIN_MISMATCH")
        try:
            c = json.loads(raw.decode())
        except Exception:
            raise Refusal("CLEARANCE_MALFORMED")
        expect = {
            "txn_id": self.txn_id,
            "executor_sha256": executor_source_sha(),
            "gate_sha256": PIN_R4_GATE,
            "policy_digest": PIN_POLICY_A_DIGEST,
            "candidate_sha256": self.packet["expected_candidate_sha"],
            "legacy_ledger_sha256": self.packet["expected_original_sha"],
            "ceiling_credits": CEILING_CREDITS,
            "scope": "READINESS_ONLY_ONE_API_USAGE",
        }
        for k, v in expect.items():
            if c.get(k) != v:
                raise Refusal("CLEARANCE_BINDING_MISMATCH", k)
        self._clearance = c

    # -- locks ---------------------------------------------------------------
    def _acquire_locks(self):
        lease = open(self.target + ".dispatch_lease", "a+")
        try:
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lease.close()
            raise Refusal("LOCK_CONTENTION_LEASE")
        self._lease_fd = lease
        lock = open(self.target + ".lock", "a+")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            raise Refusal("LOCK_CONTENTION_LEDGER")
        self._lock_fd = lock

    def _release_locks(self):
        for fd in (self._lock_fd, self._lease_fd):
            if fd is not None:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    fd.close()
                except Exception:
                    pass
        self._lock_fd = self._lease_fd = None

    # -- helper / boundary ---------------------------------------------------
    def _resolve_helper(self):
        if self.mode == "live":
            return RESOLVER.resolve(SANCTIONED_HELPER_PATH, PIN_HELPER)
        hp = self.packet["helper"]
        return RESOLVER.resolve(hp["path"], hp["sha256"])

    def _make_boundary(self, handle):
        if self.mode == "live":
            return StatusBoundary(handle, _live_http_get)
        return StatusBoundary(handle, self.hooks["transport"].http_get)

    # -- pre-mutation binding revalidation (under lock) ----------------------
    def _revalidate_bindings_under_lock(self, locked_sha):
        st = self.journal.state
        if st.get("target_path") != self.target \
                or st.get("workdir") != self.workdir \
                or st.get("backup_path") != self.backup_path:
            raise Refusal("BINDING_REVALIDATION_FAIL", "journal_paths")
        if os.path.islink(self.target) \
                or st.get("target_realpath") != os.path.realpath(self.target):
            raise Refusal("BINDING_REVALIDATION_FAIL", "realpath")
        on_disk = RT.Journal.load(self.journal_path).state
        if canon(on_disk) != canon(st):
            raise Refusal("BINDING_REVALIDATION_FAIL", "journal_drift")
        if H(open(self.target, "rb").read()) != locked_sha:
            raise Refusal("BINDING_REVALIDATION_FAIL", "target_drift")

    # -- main ------------------------------------------------------------------
    def run(self):
        # Packet-static pins are validated in memory only. NOTHING in
        # this section reads the ledger.
        if self.packet["expected_candidate_sha"] != self.candidate_sha:
            raise Refusal("PIN_DRIFT_CANDIDATE")
        pol = json.loads(open(POLICY_A_PATH, "rb").read().decode())
        if _sha256_file(POLICY_A_PATH) != PIN_POLICY_A_FILE \
                or H(canon(pol)) != PIN_POLICY_A_DIGEST:
            raise Refusal("PIN_DRIFT_POLICY")
        go = self.packet.get("go_record") or {}
        if go.get("record_id") != GO_RECORD_ID \
                or go.get("comment_id") != GO_COMMENT_ID:
            raise Refusal("GO_RECORD_MISMATCH")
        if self.mode == "live":
            self._verify_clearance()  # before marker, locks, any touch
        os.makedirs(self.workdir, exist_ok=True)
        # 1. One-use marker, exclusive-create. A pre-existing marker
        # refuses before locks or any ledger touch.
        try:
            fd = os.open(self.marker_path,
                         os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise Refusal("TXN_ALREADY_CONSUMED")
        with os.fdopen(fd, "wb") as f:
            f.write(canon({"txn_id": self.txn_id}))
            f.flush()
            os.fsync(f.fileno())
        RT._fsync_dir(self.workdir)
        self._maybe_crash("after_marker")
        replaced = False
        locked_original = None
        locked_sha = None
        try:
            # 2. Owner lease, then shared-ledger lock -- BEFORE any
            # read of ledger bytes.
            self._acquire_locks()
            self._maybe_crash("after_locks")
            if self.hooks.get("pause_at_locks"):
                self.hooks["pause_at_locks"]()
            # 3. Read the ledger ONLY under lock. The locked bytes are
            # the only bytes ever journaled, backed up or rolled back.
            locked_original = open(self.target, "rb").read()
            locked_sha = H(locked_original)
            self.journal = Journal.create(self.journal_path, {
                "txn_id": self.txn_id,
                "workdir": self.workdir,
                "target_path": self.target,
                "target_realpath": os.path.realpath(self.target),
                "original_sha": locked_sha,
                "candidate_sha": self.candidate_sha,
                "backup_path": self.backup_path,
                "backup_sha": None,
                "phase": "BEGUN",
                "phase_history": ["BEGUN"],
                "status_calls": 0,
                "lock_order": ["owner_lease", "ledger_lock"],
                "ledger_read_under_lock": True,
            })
            if locked_sha != self.packet["expected_original_sha"]:
                self._advance("TERMINAL_HOLD_PRE",
                              reason="LOCKED_LEDGER_PIN_MISMATCH")
                self._write_terminal("HOLD", "LOCKED_LEDGER_PIN_MISMATCH")
                return {"outcome": "HOLD",
                        "reason": "LOCKED_LEDGER_PIN_MISMATCH"}
            try:
                legacy_obj = json.loads(locked_original.decode())
            except Exception:
                legacy_obj = None
            if not _legacy_schema_ok(legacy_obj):
                self._advance("TERMINAL_HOLD_PRE",
                              reason="LOCKED_LEDGER_SCHEMA_MISMATCH")
                self._write_terminal("HOLD", "LOCKED_LEDGER_SCHEMA_MISMATCH")
                return {"outcome": "HOLD",
                        "reason": "LOCKED_LEDGER_SCHEMA_MISMATCH"}
            self._advance("PREFLIGHT_OK")
            self._advance("LOCKS_HELD")
            # 4. Verified helper resolution (never invoked here).
            handle = self._resolve_helper()
            self._advance("HELPER_OK")
            self.boundary = self._make_boundary(handle)
            # 5. The single status slot: consumed + journaled BEFORE
            # the transport is invoked. No retry.
            self.status_calls = 1
            self._advance("STATUS_CONSUMED", status_calls=1)
            http_status, body = self.boundary.call()
            try:
                raw = json.loads(body.decode())
            except Exception:
                raw = None
            self._status_raw = raw
            now = self._now()
            verdict = GATE3.validate_gate3(raw, {
                "policy_id": "A",
                "ceiling_credits": CEILING_CREDITS,
                "ledger_same_day_reserved": _same_day_reserved(
                    legacy_obj, now),
            }, now)
            if verdict[0] != "PASS":
                self._advance("TERMINAL_HOLD_PRE",
                              reason="GATE3_" + verdict[0],
                              gate3_code=verdict[1])
                self._write_terminal("HOLD", "GATE3_" + verdict[1])
                return {"outcome": "HOLD", "reason": "GATE3_" + verdict[1],
                        "http_status": http_status}
            self._advance("GATE3_OK", gate3_code=verdict[1])
            # 6. Backup of the LOCKED bytes, durable + hash journaled
            # BEFORE the replace.
            _atomic_write(self.backup_path, locked_original,
                          fault=self._fault, kind="backup")
            self._advance("BACKED_UP", backup_sha=locked_sha)
            self._maybe_crash("after_backup")
            # 7. Bindings revalidated under lock immediately before
            # the adoption mutation.
            self._revalidate_bindings_under_lock(locked_sha)
            _atomic_write(self.target, self.candidate_bytes,
                          fault=self._fault, kind="target")
            replaced = True
            self._advance("REPLACED")
            self._maybe_crash("after_replace")
            self._maybe_fail("post_write_verify")
            if H(open(self.target, "rb").read()) != self.candidate_sha:
                raise Refusal("POST_WRITE_VERIFY_FAIL")
            self._advance("VERIFIED")
            # 8. Refreeze: status evidence + derived token card.
            facts = {"http_status": http_status, "api_usage": raw,
                     "gate3": verdict[1], "evaluated_at": now}
            self._refreeze(facts)
            self._advance("REFROZEN")
            # 9. r4 dry-run against the post-adoption bytes (12/12).
            receipt = self._dry_run()
            self._maybe_crash("during_dry_run")
            self._maybe_fail("dry_run")
            passed = sum(1 for g in receipt if g == "PASS")
            _atomic_write(self.receipt_path, canon(
                {"txn_id": self.txn_id, "gates": list(receipt),
                 "gates_passed": passed, "gates_total": len(receipt)}),
                fault=self._fault, kind="receipt")
            if passed != 12 or len(receipt) != 12:
                raise Refusal("DRY_RUN_NOT_12_OF_12", "%d/12" % passed)
            self._advance("DRYRUN_OK")
            self._maybe_crash("during_terminal")
            self._maybe_fail("terminal_write")
            self._write_terminal("COMPLETE", "ADOPTED_VERIFIED")
            self._advance("TERMINAL_COMPLETE", outcome="COMPLETE")
            return {"outcome": "COMPLETE", "http_status": http_status}
        except Refusal as e:
            return self._fail(e.code, replaced, locked_original, locked_sha)
        except Exception as e:  # real I/O / runtime failures: same discipline
            return self._fail("UNCAUGHT_" + type(e).__name__,
                              replaced, locked_original, locked_sha)
        finally:
            self._release_locks()

    def _dry_run(self):
        if self.mode == "live":
            if HERE not in sys.path:
                sys.path.insert(0, HERE)
            from r4_dry_run_adapter import make_r4_dry_run_hook
            hook = make_r4_dry_run_hook(self.packet, self.target,
                                        account_raw=self._status_raw)
            return hook(self.evidence_path)
        return self.hooks["dry_run"](self.evidence_path)

    def _fail(self, code, replaced, locked_original, locked_sha):
        """-13 failure discipline, under held locks, over the LOCKED
        bytes only. An unverifiable rollback is HOLD_MANUAL, never
        ROLLED_BACK."""
        if self.journal is None:
            # Failure before the journal existed (e.g. lock contention
            # or crash-adjacent refusal): the marker stays consumed;
            # nothing was read or mutated.
            try:
                self._write_terminal("HOLD", code)
            except Exception:
                pass
            return {"outcome": "HOLD", "reason": code}
        if replaced:
            try:
                self._rollback(locked_original, locked_sha, code)
                return {"outcome": "ROLLED_BACK", "reason": code}
            except Exception:
                try:
                    self._advance("TERMINAL_HOLD_MANUAL", reason=code,
                                  outcome="HOLD_MANUAL")
                except Exception:
                    pass
                try:
                    self._write_terminal("HOLD_MANUAL",
                                         "ROLLBACK_UNVERIFIED:" + code)
                except Exception:
                    pass
                return {"outcome": "HOLD_MANUAL",
                        "reason": "ROLLBACK_UNVERIFIED", "cause": code}
        try:
            if self.journal.state["phase"] not in RT.TERMINAL_PHASES:
                self._advance("TERMINAL_HOLD_PRE", reason=code)
        except Exception:
            pass
        return {"outcome": "HOLD", "reason": code}

    def _refreeze(self, facts):
        evidence = {"txn_id": self.txn_id, "facts": facts,
                    "candidate_sha": self.candidate_sha}
        if self._crash_at == "during_evidence":
            with open(self.evidence_path + ".tmp", "wb") as f:
                f.write(b"{\"partial\":")
                f.flush()
                os.fsync(f.fileno())
            os._exit(42)
        self._maybe_fail("evidence_write")
        _atomic_write(self.evidence_path, canon(evidence),
                      fault=self._fault, kind="evidence")
        card = {"txn_id": self.txn_id,
                "evidence_sha": H(canon(evidence)),
                "candidate_sha": self.candidate_sha}
        if self._crash_at == "during_card":
            with open(self.card_path + ".tmp", "wb") as f:
                f.write(b"{\"partial\":")
                f.flush()
                os.fsync(f.fileno())
            os._exit(42)
        self._maybe_fail("card_write")
        _atomic_write(self.card_path, canon(card),
                      fault=self._fault, kind="card")

    def _rollback(self, locked_original, locked_sha, why):
        _atomic_write(self.target, locked_original,
                      fault=self._fault, kind="rollback")
        if H(open(self.target, "rb").read()) != locked_sha:
            raise Refusal("ROLLBACK_VERIFY_FAIL")
        self.journal.advance("TERMINAL_ROLLED_BACK", reason=why,
                             outcome="RECOVERED_HOLD")
        try:
            self._write_terminal("ROLLED_BACK", why)
        except Exception:
            pass

    def _write_terminal(self, outcome, detail):
        _atomic_write(self.terminal_path, canon({
            "txn_id": self.txn_id, "outcome": outcome, "detail": detail,
            "status_calls": self.status_calls}),
            fault=self._fault, kind="terminal")


def recover_live(workdir, target_path, after_precheck_hook=None):
    """Cold-start recovery for the integrated executor. Accepts NO
    status/helper callable. Binding validation runs at precheck AND
    again under lock (journal bytes must be identical; a fresh
    precheck must pass), closing the precheck->lock TOCTOU, before
    any classification or ledger touch."""
    workdir = os.path.abspath(workdir)
    target_path = os.path.abspath(target_path)
    journal_path = os.path.join(workdir, "journal.json")
    result = {"status_calls_during_recovery": 0}
    st, err = RT._binding_precheck(workdir, target_path)
    if st == "NOT_STARTED":
        result["classification"] = "NOT_STARTED"
        return result
    if err is not None:
        result["classification"] = "HOLD_MANUAL"
        result["reason"] = err
        return result
    with open(journal_path, "rb") as f:
        journal_snapshot_sha = H(f.read())
    result["status_calls_total"] = st.get("status_calls", 0)
    if after_precheck_hook is not None:
        after_precheck_hook()
    lease = open(target_path + ".dispatch_lease", "a+")
    fcntl.flock(lease, fcntl.LOCK_EX)
    lock = open(target_path + ".lock", "a+")
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        # Revalidate EVERYTHING under lock before any ledger touch.
        if H(open(journal_path, "rb").read()) != journal_snapshot_sha:
            result["classification"] = "HOLD_MANUAL"
            result["reason"] = "RECOVERY_JOURNAL_DRIFT_UNDER_LOCK"
            return result
        st2, err2 = RT._binding_precheck(workdir, target_path)
        if err2 is not None or st2 == "NOT_STARTED" \
                or canon(st2) != canon(st):
            result["classification"] = "HOLD_MANUAL"
            result["reason"] = "RECOVERY_BINDING_DRIFT_UNDER_LOCK"
            return result
        journal = Journal.load(journal_path)
        st = journal.state
        target_sha = H(open(target_path, "rb").read())
        phase = st["phase"]
        if phase in RT.TERMINAL_PHASES:
            if phase == "TERMINAL_COMPLETE":
                ok, why = (False, "TARGET_NOT_CANDIDATE") \
                    if target_sha != st["candidate_sha"] \
                    else RT._validate_terminal_complete(workdir, st)
                result["classification"] = ("ADOPTED_VERIFIED" if ok
                                            else "HOLD_MANUAL")
                if not ok:
                    result["reason"] = why
            else:
                result["classification"] = (
                    "ROLLED_BACK" if target_sha == st["original_sha"]
                    else "HOLD_MANUAL")
            return result
        backup_path = st["backup_path"]
        if target_sha == st["original_sha"]:
            result["classification"] = "PRE_REPLACE"
            journal.advance("TERMINAL_RECOVERED_HOLD",
                            recovered_from=phase, restored=False,
                            outcome="RECOVERED_HOLD")
            _atomic_write(os.path.join(workdir, "terminal_record.json"),
                          canon({"txn_id": st["txn_id"],
                                 "outcome": "RECOVERED_HOLD",
                                 "detail": "PRE_REPLACE_FINALIZED",
                                 "status_calls": st.get("status_calls", 0)}))
            result["finalized"] = True
            return result
        if target_sha == st["candidate_sha"]:
            result["classification"] = "POST_REPLACE_UNVERIFIED"
            if not os.path.exists(backup_path):
                result["classification"] = "HOLD_MANUAL"
                result["reason"] = "BACKUP_MISSING"
                return result
            backup = open(backup_path, "rb").read()
            if H(backup) != st["original_sha"] or \
                    st.get("backup_sha") != st["original_sha"]:
                result["classification"] = "HOLD_MANUAL"
                result["reason"] = "BACKUP_VERIFY_FAIL"
                return result
            _atomic_write(target_path, backup)
            if H(open(target_path, "rb").read()) != st["original_sha"]:
                result["classification"] = "HOLD_MANUAL"
                result["reason"] = "RESTORE_VERIFY_FAIL"
                return result
            journal.advance("TERMINAL_RECOVERED_HOLD",
                            recovered_from=phase, restored=True,
                            outcome="RECOVERED_HOLD")
            _atomic_write(os.path.join(workdir, "terminal_record.json"),
                          canon({"txn_id": st["txn_id"],
                                 "outcome": "RECOVERED_HOLD",
                                 "detail": "LEGACY_RESTORED",
                                 "status_calls": st.get("status_calls", 0)}))
            result["restored"] = True
            result["outcome"] = "RECOVERED_HOLD"
            return result
        result["classification"] = "HOLD_MANUAL"
        result["reason"] = "TARGET_UNKNOWN_BYTES"
        return result
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
        fcntl.flock(lease, fcntl.LOCK_UN)
        lease.close()


def main(argv):
    if len(argv) >= 2 and argv[1] == "recover":
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("--workdir", required=True)
        p.add_argument("--target", required=True)
        a = p.parse_args(argv[2:])
        print(json.dumps(recover_live(a.workdir, a.target), sort_keys=True))
        return 0
    if len(argv) >= 3 and argv[1] == "run":
        with open(argv[2], "rb") as f:
            packet = json.loads(f.read().decode())
        ex = LiveReadinessExecutor(packet)
        try:
            out = ex.run()
        except Refusal as e:
            out = {"outcome": "REFUSED", "reason": e.code}
        print(json.dumps(out, sort_keys=True))
        return 0
    print("usage: live_readiness_executor.py run <packet.json> | "
          "recover --workdir W --target T")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
