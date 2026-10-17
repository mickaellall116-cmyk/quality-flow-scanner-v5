#!/usr/bin/env python3
"""QF-TD-READINESS-TXN-EXCEPTION-BINDING-20261017-13 r1 candidate.

Revision of the -12 readiness transaction (readiness_transaction_r2.py,
sha256 167ffe23..., preserved unchanged) closing three reviewed gaps:

1. REAL EXCEPTION CAPTURE. run() catches every Exception (not only
   Refusal) while locks remain held. Any failure after the replace --
   OSError from evidence/card/receipt/terminal persistence, RuntimeError
   from the dry-run hook, failure of the terminal journal advance --
   attempts an exact, hash-verified rollback and a durable
   TERMINAL_ROLLED_BACK journal state BEFORE locks are released. If the
   rollback itself cannot be verified, the journal records
   TERMINAL_HOLD_MANUAL and the outcome is HOLD_MANUAL /
   manual-recovery-required: ROLLED_BACK is never claimed falsely.

2. TERMINAL COMPLETE VALIDATION. Cold-start recovery no longer accepts
   TERMINAL_COMPLETE on file existence. It parses and verifies the
   terminal record (exact txn id, outcome COMPLETE, status-call count
   equal to the journal's), the dry-run receipt (bound txn id, gates
   exactly 12 x PASS, counts 12/12), the evidence and token card
   (cross-digests: card.evidence_sha == sha256 of the evidence bytes;
   candidate_sha bound to the journal), the candidate target hash, and
   journal phase/history consistency. Any tamper -> HOLD_MANUAL, no
   ledger touch.

3. JOURNAL PATH BINDING. The journal binds canonical absolute target
   and backup paths, the target realpath, and the workdir. Recovery
   compares the caller path, marker txn id, journal txn id, path
   bindings, phase/history validity and hash formats BEFORE acquiring
   locks or touching the ledger; symlink substitution, a relocated or
   edited journal, a wrong workdir/target, or an ambiguous second
   journal for the same target all fail closed as HOLD_MANUAL.

Fixture-only, as -12: the constructor refuses any non-fixture mode or
hooks, the real credential helper can never be invoked from this code,
and token / arm / time_series exist only as refusals. Cold-start
recovery (recover()) accepts NO status/helper callable.
"""
import fcntl
import hashlib
import json
import os
import re


def H(b):
    return hashlib.sha256(b).hexdigest()


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_sha(s):
    return isinstance(s, str) and bool(_SHA_RE.match(s))


class Refusal(Exception):
    def __init__(self, code, detail=""):
        super().__init__(code + (": " + detail if detail else ""))
        self.code = code


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write(path, data, fault=None, kind=None):
    """Atomic tmp+replace write. fault(kind, stage), when supplied, is
    invoked at the 'write' and 'fsync' stages and may raise a real
    exception (fault injection); the replace happens only after both
    stages and a real fsync succeed."""
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        if fault is not None:
            fault(kind, "write")
        f.write(data)
        f.flush()
        if fault is not None:
            fault(kind, "fsync")
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_dir(os.path.dirname(path) or ".")


PHASES = ["BEGUN", "PREFLIGHT_OK", "LOCKS_HELD", "HELPER_OK",
          "STATUS_CONSUMED", "GATE3_OK", "BACKED_UP", "REPLACED",
          "VERIFIED", "REFROZEN", "DRYRUN_OK"]
TERMINAL_PHASES = ("TERMINAL_COMPLETE", "TERMINAL_ROLLED_BACK",
                   "TERMINAL_RECOVERED_HOLD", "TERMINAL_HOLD_PRE",
                   "TERMINAL_HOLD_MANUAL")


def valid_history(st):
    """Phase history must be the exact ordered PHASES prefix ending at
    the recorded phase, optionally followed by the single terminal
    phase equal to st['phase']. No gaps, duplicates or reordering."""
    hist = st.get("phase_history")
    phase = st.get("phase")
    if not isinstance(hist, list) or not hist:
        return False
    if phase in TERMINAL_PHASES:
        if hist[-1] != phase:
            return False
        body = hist[:-1]
    else:
        body = hist
        if not body or body[-1] != phase:
            return False
    if len(body) > len(PHASES):
        return False
    return body == PHASES[:len(body)]


class Journal:
    """Write-ahead journal: every advance is an atomic write + fsync."""

    def __init__(self, path, state=None):
        self.path = path
        self.state = state

    @classmethod
    def create(cls, path, initial):
        j = cls(path, dict(initial))
        j._flush()
        return j

    @classmethod
    def load(cls, path):
        with open(path, "rb") as f:
            state = json.loads(f.read().decode())
        if not isinstance(state, dict) or "phase" not in state:
            raise Refusal("JOURNAL_MALFORMED")
        return cls(path, state)

    def _flush(self):
        _atomic_write(self.path, canon(self.state))

    def advance(self, phase, **facts):
        self.state["phase"] = phase
        self.state.update(facts)
        self.state["phase_history"] = self.state.get("phase_history", []) + [phase]
        self._flush()


class ReadinessTransactionR3:
    def __init__(self, workdir, packet, hooks):
        if packet.get("mode") != "fixture":
            raise Refusal("LIVE_MODE_REFUSED")
        if not hooks.get("fixture"):
            raise Refusal("NON_FIXTURE_HOOKS_REFUSED")
        self.workdir = os.path.abspath(workdir)
        self.packet = packet
        self.hooks = hooks
        self.txn_id = packet["txn_id"]
        self.target = os.path.abspath(packet["target_path"])
        self.candidate_bytes = packet["candidate_bytes"]
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
        self._fail_at = hooks.get("fail_at")        # Refusal injection (-12)
        self._crash_at = hooks.get("crash_at")      # os._exit injection
        self._raise_at = hooks.get("raise_at") or {}  # real-exception inj.
        self.status_calls = 0

    # -- refusals: outside readiness scope -------------------------------
    def request_token(self, *_a, **_k):
        raise Refusal("NOT_IN_READINESS_SCOPE")

    def arm_transport(self, *_a, **_k):
        raise Refusal("NOT_IN_READINESS_SCOPE")

    def call_time_series(self, *_a, **_k):
        raise Refusal("NOT_IN_READINESS_SCOPE")

    # -- injection points --------------------------------------------------
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

    # -- locks ---------------------------------------------------------------
    def _acquire_locks(self):
        lease = open(self.target + ".dispatch_lease", "a+")
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self._lease_fd = lease
        lock = open(self.target + ".lock", "a+")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
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

    # -- steps ---------------------------------------------------------------
    def run(self):
        os.makedirs(self.workdir, exist_ok=True)
        if os.path.exists(self.marker_path):
            raise Refusal("TXN_ALREADY_CONSUMED")
        original = open(self.target, "rb").read()
        original_sha = H(original)
        # One-use marker + journal intent BEFORE anything else durable.
        # The journal binds canonical absolute paths from this moment.
        _atomic_write(self.marker_path, canon({"txn_id": self.txn_id}))
        self.journal = Journal.create(self.journal_path, {
            "txn_id": self.txn_id,
            "workdir": self.workdir,
            "target_path": self.target,
            "target_realpath": os.path.realpath(self.target),
            "original_sha": original_sha,
            "candidate_sha": self.candidate_sha,
            "backup_path": self.backup_path,
            "backup_sha": None,
            "phase": "BEGUN",
            "phase_history": ["BEGUN"],
            "status_calls": 0,
        })
        replaced = False
        try:
            self._preflight(original_sha)
            self._advance("PREFLIGHT_OK")
            self._acquire_locks()
            self._advance("LOCKS_HELD")
            self.hooks["verify_helper"]()
            self._advance("HELPER_OK")
            # Counter consumed BEFORE the single status call; journaled.
            self.status_calls = 1
            self._advance("STATUS_CONSUMED", status_calls=1)
            facts = self.hooks["status_call"]()
            self._maybe_fail("status_eval")
            if not self.hooks["gate3"](facts):
                self._advance("TERMINAL_HOLD_PRE", reason="GATE3_FAIL")
                self._write_terminal("HOLD", "GATE3_FAIL")
                return {"outcome": "HOLD", "reason": "GATE3_FAIL"}
            self._advance("GATE3_OK")
            # Backup durable + hash journaled BEFORE replace.
            _atomic_write(self.backup_path, original,
                          fault=self._fault, kind="backup")
            self._advance("BACKED_UP", backup_sha=original_sha)
            self._maybe_crash("after_backup")
            _atomic_write(self.target, self.candidate_bytes,
                          fault=self._fault, kind="target")
            replaced = True
            self._advance("REPLACED")
            self._maybe_crash("after_replace")
            self._maybe_fail("post_write_verify")
            if H(open(self.target, "rb").read()) != self.candidate_sha:
                raise Refusal("POST_WRITE_VERIFY_FAIL")
            self._advance("VERIFIED")
            self._refreeze(facts)
            self._advance("REFROZEN")
            receipt = self.hooks["dry_run"](self.evidence_path)
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
            return {"outcome": "COMPLETE"}
        except Refusal as e:
            return self._fail(e.code, replaced, original, original_sha)
        except Exception as e:  # real I/O / runtime failures: same discipline
            return self._fail("UNCAUGHT_" + type(e).__name__,
                              replaced, original, original_sha)
        finally:
            self._release_locks()

    def _fail(self, code, replaced, original, original_sha):
        """Failure discipline, executed while locks are still held.
        Post-replace: exact rollback first, durable journal second.
        An unverifiable rollback is HOLD_MANUAL, never ROLLED_BACK."""
        if replaced:
            try:
                self._rollback(original, original_sha, code)
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
            if self.journal.state["phase"] not in TERMINAL_PHASES:
                self._advance("TERMINAL_HOLD_PRE", reason=code)
        except Exception:
            pass
        return {"outcome": "HOLD", "reason": code}

    def _preflight(self, original_sha):
        if self.packet["expected_original_sha"] != original_sha:
            raise Refusal("PIN_DRIFT_ORIGINAL")
        if self.packet["expected_candidate_sha"] != self.candidate_sha:
            raise Refusal("PIN_DRIFT_CANDIDATE")

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

    def _rollback(self, original, original_sha, why):
        # Atomic restore + fsync + exact-hash verification, journaled.
        _atomic_write(self.target, original,
                      fault=self._fault, kind="rollback")
        if H(open(self.target, "rb").read()) != original_sha:
            raise Refusal("ROLLBACK_VERIFY_FAIL")
        self.journal.advance("TERMINAL_ROLLED_BACK", reason=why,
                             outcome="RECOVERED_HOLD")
        # The terminal record is a derived artifact; the ROLLED_BACK
        # claim rests on the verified ledger bytes + the durable
        # journal above, so its write is best-effort (a fault here --
        # e.g. the same fsync failure that triggered the rollback --
        # must not convert a verified rollback into HOLD_MANUAL).
        try:
            self._write_terminal("ROLLED_BACK", why)
        except Exception:
            pass

    def _write_terminal(self, outcome, detail):
        _atomic_write(self.terminal_path, canon({
            "txn_id": self.txn_id, "outcome": outcome, "detail": detail,
            "status_calls": self.status_calls}),
            fault=self._fault, kind="terminal")


def _load_json(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode())


def _validate_terminal_complete(workdir, st):
    """Strict TERMINAL_COMPLETE validation. Returns (ok, reason).
    Existence of artifacts is never sufficient."""
    try:
        term = _load_json(os.path.join(workdir, "terminal_record.json"))
    except Exception:
        return False, "TERMINAL_RECORD_UNREADABLE"
    if not isinstance(term, dict) \
            or term.get("txn_id") != st["txn_id"] \
            or term.get("outcome") != "COMPLETE" \
            or term.get("status_calls") != st.get("status_calls"):
        return False, "TERMINAL_RECORD_MISMATCH"
    try:
        receipt = _load_json(os.path.join(workdir, "dry_run_receipt.json"))
    except Exception:
        return False, "RECEIPT_UNREADABLE"
    if not isinstance(receipt, dict) \
            or receipt.get("txn_id") != st["txn_id"] \
            or receipt.get("gates") != ["PASS"] * 12 \
            or receipt.get("gates_passed") != 12 \
            or receipt.get("gates_total") != 12:
        return False, "RECEIPT_NOT_12_OF_12_BOUND"
    try:
        evidence_bytes = open(os.path.join(workdir, "evidence.json"),
                              "rb").read()
        evidence = json.loads(evidence_bytes.decode())
        card = _load_json(os.path.join(workdir, "token_card.json"))
    except Exception:
        return False, "EVIDENCE_OR_CARD_UNREADABLE"
    if not isinstance(evidence, dict) \
            or evidence.get("txn_id") != st["txn_id"] \
            or evidence.get("candidate_sha") != st["candidate_sha"]:
        return False, "EVIDENCE_MISMATCH"
    if not isinstance(card, dict) \
            or card.get("txn_id") != st["txn_id"] \
            or card.get("candidate_sha") != st["candidate_sha"] \
            or card.get("evidence_sha") != H(evidence_bytes):
        return False, "CARD_CROSS_DIGEST_MISMATCH"
    return True, "OK"


def _binding_precheck(workdir, target_path):
    """Validate marker/journal identity, canonical path bindings, hash
    formats and phase/history BEFORE locks or any ledger touch.
    Returns (state, None) or (None, reason)."""
    journal_path = os.path.join(workdir, "journal.json")
    marker_path = os.path.join(workdir, "CONSUMED.marker")
    has_journal = os.path.exists(journal_path)
    has_marker = os.path.exists(marker_path)
    if not has_journal and not has_marker:
        return "NOT_STARTED", None
    if has_journal != has_marker:
        return None, "MARKER_JOURNAL_INCOMPLETE"
    try:
        marker = _load_json(marker_path)
        journal = Journal.load(journal_path)
    except Exception:
        return None, "JOURNAL_UNREADABLE"
    st = journal.state
    if not isinstance(marker, dict) \
            or marker.get("txn_id") != st.get("txn_id"):
        return None, "MARKER_JOURNAL_TXN_MISMATCH"
    if st.get("workdir") != workdir:
        return None, "JOURNAL_WORKDIR_BINDING"
    if st.get("target_path") != target_path:
        return None, "JOURNAL_TARGET_BINDING"
    if os.path.islink(target_path) \
            or st.get("target_realpath") != os.path.realpath(target_path):
        return None, "TARGET_SYMLINK_OR_REALPATH_MISMATCH"
    if st.get("backup_path") != os.path.join(workdir, "ledger_backup.bin"):
        return None, "JOURNAL_BACKUP_BINDING"
    if not _is_sha(st.get("original_sha")) \
            or not _is_sha(st.get("candidate_sha")) \
            or (st.get("backup_sha") is not None
                and not _is_sha(st.get("backup_sha"))):
        return None, "JOURNAL_HASH_FORMAT"
    if st.get("phase") not in PHASES + list(TERMINAL_PHASES) \
            or not valid_history(st):
        return None, "JOURNAL_PHASE_HISTORY_INVALID"
    if not isinstance(st.get("status_calls"), int) \
            or st.get("status_calls") not in (0, 1):
        return None, "JOURNAL_STATUS_CALLS_INVALID"
    # Ambiguity: a second journal artifact in this workdir binding the
    # same target is a fail-closed condition.
    for name in os.listdir(workdir):
        if name.startswith("journal") and name.endswith(".json") \
                and name != "journal.json":
            try:
                other = _load_json(os.path.join(workdir, name))
            except Exception:
                continue
            if isinstance(other, dict) \
                    and other.get("target_path") == st.get("target_path"):
                return None, "AMBIGUOUS_SECOND_JOURNAL"
    return st, None


def recover(workdir, target_path):
    """Cold-start recovery. Accepts NO status/helper callable: recovery
    can never place a status call. All binding validation happens
    before locks are acquired or the ledger is touched."""
    workdir = os.path.abspath(workdir)
    target_path = os.path.abspath(target_path)
    journal_path = os.path.join(workdir, "journal.json")
    result = {"status_calls_during_recovery": 0}
    st, err = _binding_precheck(workdir, target_path)
    if st == "NOT_STARTED":
        result["classification"] = "NOT_STARTED"
        return result
    if err is not None:
        result["classification"] = "HOLD_MANUAL"
        result["reason"] = err
        return result
    backup_path = st["backup_path"]
    result["status_calls_total"] = st.get("status_calls", 0)
    # Same lock order as the transaction: owner lease, then ledger lock.
    lease = open(target_path + ".dispatch_lease", "a+")
    fcntl.flock(lease, fcntl.LOCK_EX)
    lock = open(target_path + ".lock", "a+")
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        journal = Journal.load(journal_path)
        st = journal.state
        target_bytes = open(target_path, "rb").read()
        target_sha = H(target_bytes)
        phase = st["phase"]
        if phase in TERMINAL_PHASES:
            if phase == "TERMINAL_COMPLETE":
                ok, why = (False, "TARGET_NOT_CANDIDATE") \
                    if target_sha != st["candidate_sha"] \
                    else _validate_terminal_complete(workdir, st)
                result["classification"] = ("ADOPTED_VERIFIED" if ok
                                             else "HOLD_MANUAL")
                if not ok:
                    result["reason"] = why
            else:
                result["classification"] = (
                    "ROLLED_BACK" if target_sha == st["original_sha"]
                    else "HOLD_MANUAL")
            return result
        # Nonterminal, consumed transaction: never a second status call.
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
            # Exact backup must verify before any ledger touch.
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
