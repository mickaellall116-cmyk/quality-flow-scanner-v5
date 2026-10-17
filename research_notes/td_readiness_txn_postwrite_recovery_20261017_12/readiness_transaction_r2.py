#!/usr/bin/env python3
"""QF-TD-READINESS-TXN-POSTWRITE-RECOVERY-20261017-12 r1 candidate.

Readiness transaction with a durable write-ahead journal and cold-start
recovery. Fixture-only: the constructor refuses any non-fixture mode or
hooks, the real credential helper can never be invoked from this code,
and token / arm / time_series exist only as refusals.

Step order (locks held from LOCKS_HELD through terminal commit):
  begin (one-use marker + journal created, intent bound BEFORE replace)
  -> preflight -> owner lease -> ledger lock -> helper verification
  -> exactly one status call (counter consumed BEFORE the call)
  -> gate 3 -> fsynced backup (hash journaled BEFORE replace)
  -> atomic replace -> post-write verification -> refreeze (evidence+card)
  -> dry-run (must be 12/12) -> durable terminal commit.

Any ordinary failure after replace restores the exact legacy bytes
(atomic replace + fsync + hash verify) and records a terminal
HOLD/ROLLED_BACK journal state before locks are released.

Cold-start recovery (recover()) takes NO status/helper hook: given only
the journal + filesystem it classifies deterministically and either
finalizes a pre-replace transaction, restores legacy bytes for a
nonterminal post-replace transaction, verifies a terminal transaction,
or fails closed HOLD_MANUAL without touching the ledger.
"""
import fcntl
import hashlib
import json
import os


def H(b):
    return hashlib.sha256(b).hexdigest()


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


class Refusal(Exception):
    def __init__(self, code, detail=""):
        super().__init__(code + (": " + detail if detail else ""))
        self.code = code


def _fsync_file(path):
    fd = os.open(path, os.O_RDWR)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_dir(os.path.dirname(path) or ".")


PHASES = ["BEGUN", "PREFLIGHT_OK", "LOCKS_HELD", "HELPER_OK",
          "STATUS_CONSUMED", "GATE3_OK", "BACKED_UP", "REPLACED",
          "VERIFIED", "REFROZEN", "DRYRUN_OK"]
TERMINAL_PHASES = ("TERMINAL_COMPLETE", "TERMINAL_ROLLED_BACK",
                   "TERMINAL_RECOVERED_HOLD", "TERMINAL_HOLD_PRE")


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


class ReadinessTransactionR2:
    def __init__(self, workdir, packet, hooks):
        if packet.get("mode") != "fixture":
            raise Refusal("LIVE_MODE_REFUSED")
        if not hooks.get("fixture"):
            raise Refusal("NON_FIXTURE_HOOKS_REFUSED")
        self.workdir = workdir
        self.packet = packet
        self.hooks = hooks
        self.txn_id = packet["txn_id"]
        self.target = packet["target_path"]
        self.candidate_bytes = packet["candidate_bytes"]
        self.candidate_sha = H(self.candidate_bytes)
        self.journal_path = os.path.join(workdir, "journal.json")
        self.marker_path = os.path.join(workdir, "CONSUMED.marker")
        self.backup_path = os.path.join(workdir, "ledger_backup.bin")
        self.evidence_path = os.path.join(workdir, "evidence.json")
        self.card_path = os.path.join(workdir, "token_card.json")
        self.receipt_path = os.path.join(workdir, "dry_run_receipt.json")
        self.terminal_path = os.path.join(workdir, "terminal_record.json")
        self.journal = None
        self._lease_fd = None
        self._lock_fd = None
        self._fail_at = hooks.get("fail_at")        # ordinary fault injection
        self._crash_at = hooks.get("crash_at")      # os._exit injection
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
        _atomic_write(self.marker_path, canon({"txn_id": self.txn_id}))
        self.journal = Journal.create(self.journal_path, {
            "txn_id": self.txn_id,
            "target_path": os.path.basename(self.target),
            "original_sha": original_sha,
            "candidate_sha": self.candidate_sha,
            "backup_path": os.path.basename(self.backup_path),
            "backup_sha": None,
            "phase": "BEGUN",
            "phase_history": ["BEGUN"],
            "status_calls": 0,
        })
        replaced = False
        try:
            self._preflight(original_sha)
            self.journal.advance("PREFLIGHT_OK")
            self._acquire_locks()
            self.journal.advance("LOCKS_HELD")
            self.hooks["verify_helper"]()
            self.journal.advance("HELPER_OK")
            # Counter consumed BEFORE the single status call; journaled.
            self.status_calls = 1
            self.journal.advance("STATUS_CONSUMED", status_calls=1)
            facts = self.hooks["status_call"]()
            self._maybe_fail("status_eval")
            if not self.hooks["gate3"](facts):
                self.journal.advance("TERMINAL_HOLD_PRE",
                                     reason="GATE3_FAIL")
                self._write_terminal("HOLD", "GATE3_FAIL")
                return {"outcome": "HOLD", "reason": "GATE3_FAIL"}
            self.journal.advance("GATE3_OK")
            # Backup durable + hash journaled BEFORE replace.
            _atomic_write(self.backup_path, original)
            self.journal.advance("BACKED_UP", backup_sha=original_sha)
            self._maybe_crash("after_backup")
            _atomic_write(self.target, self.candidate_bytes)
            replaced = True
            self.journal.advance("REPLACED")
            self._maybe_crash("after_replace")
            self._maybe_fail("post_write_verify")
            if H(open(self.target, "rb").read()) != self.candidate_sha:
                raise Refusal("POST_WRITE_VERIFY_FAIL")
            self.journal.advance("VERIFIED")
            self._refreeze(facts)
            self.journal.advance("REFROZEN")
            receipt = self.hooks["dry_run"](self.evidence_path)
            self._maybe_crash("during_dry_run")
            self._maybe_fail("dry_run")
            passed = sum(1 for g in receipt if g == "PASS")
            _atomic_write(self.receipt_path, canon(
                {"gates_passed": passed, "gates_total": len(receipt)}))
            if passed != 12 or len(receipt) != 12:
                raise Refusal("DRY_RUN_NOT_12_OF_12", "%d/12" % passed)
            self.journal.advance("DRYRUN_OK")
            self._maybe_crash("during_terminal")
            self._maybe_fail("terminal_write")
            self._write_terminal("COMPLETE", "ADOPTED_VERIFIED")
            self.journal.advance("TERMINAL_COMPLETE",
                                 outcome="COMPLETE")
            return {"outcome": "COMPLETE"}
        except Refusal as e:
            if replaced:
                self._rollback(original, original_sha, e.code)
                return {"outcome": "ROLLED_BACK", "reason": e.code}
            if self.journal.state["phase"] not in TERMINAL_PHASES:
                self.journal.advance("TERMINAL_HOLD_PRE", reason=e.code)
            return {"outcome": "HOLD", "reason": e.code}
        finally:
            self._release_locks()

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
        _atomic_write(self.evidence_path, canon(evidence))
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
        _atomic_write(self.card_path, canon(card))

    def _rollback(self, original, original_sha, why):
        # Atomic restore + fsync + exact-hash verification, journaled.
        _atomic_write(self.target, original)
        if H(open(self.target, "rb").read()) != original_sha:
            raise Refusal("ROLLBACK_VERIFY_FAIL")
        self.journal.advance("TERMINAL_ROLLED_BACK", reason=why,
                             outcome="RECOVERED_HOLD")
        self._write_terminal("ROLLED_BACK", why)

    def _write_terminal(self, outcome, detail):
        _atomic_write(self.terminal_path, canon({
            "txn_id": self.txn_id, "outcome": outcome, "detail": detail,
            "status_calls": self.status_calls}))


def recover(workdir, target_path):
    """Cold-start recovery. Accepts NO status/helper callable: recovery
    can never place a status call. Returns a classification dict."""
    journal_path = os.path.join(workdir, "journal.json")
    marker_path = os.path.join(workdir, "CONSUMED.marker")
    backup_path = os.path.join(workdir, "ledger_backup.bin")
    result = {"status_calls_during_recovery": 0}
    if not os.path.exists(marker_path) and not os.path.exists(journal_path):
        result["classification"] = "NOT_STARTED"
        return result
    # Same lock order as the transaction: owner lease, then ledger lock.
    lease = open(target_path + ".dispatch_lease", "a+")
    fcntl.flock(lease, fcntl.LOCK_EX)
    lock = open(target_path + ".lock", "a+")
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        try:
            journal = Journal.load(journal_path)
        except Exception:
            result["classification"] = "HOLD_MANUAL"
            result["reason"] = "JOURNAL_UNREADABLE"
            return result
        st = journal.state
        result["status_calls_total"] = st.get("status_calls", 0)
        target_bytes = open(target_path, "rb").read()
        target_sha = H(target_bytes)
        phase = st["phase"]
        if phase in TERMINAL_PHASES:
            if phase == "TERMINAL_COMPLETE":
                ok = (target_sha == st["candidate_sha"]
                      and os.path.exists(os.path.join(
                          workdir, "terminal_record.json"))
                      and os.path.exists(os.path.join(
                          workdir, "dry_run_receipt.json")))
                result["classification"] = ("ADOPTED_VERIFIED" if ok
                                             else "HOLD_MANUAL")
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
