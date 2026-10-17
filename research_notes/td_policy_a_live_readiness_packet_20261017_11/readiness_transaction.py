#!/usr/bin/env python3
"""QF-TD-POLICY-A-LIVE-READINESS-PACKET-20261017-11 r1 - OFFLINE CANDIDATE.

Executable one-use readiness transaction implementing the accepted
ordering for the future live readiness step:

  begin (one-use marker) -> preflight pins/GO/policy/manifest ->
  acquire owner lease THEN ledger lock -> verify helper via resolver ->
  exactly ONE status call -> Policy A gate-3 evaluation -> only on PASS:
  fsynced exact backup -> atomic candidate adoption -> post-write
  consumer verification (rollback atomically on any failure) ->
  refreeze canonical evidence/card -> 12/12 dry-run -> terminal record.
  STOP before token issuance and before any market-data request.

This candidate ships FIXTURE MODE ONLY. The constructor refuses any
mode other than "offline_fixture", refuses non-fixture hooks, and
refuses a ledger target outside the fixture root (the real pilot ledger
path is refused by construction). The real credential helper is never
invoked: the helper slot accepts only an injected fixture resolver.
Token issuance, transport arming and time_series calls exist only as
guarded refusals (NOT_IN_READINESS_SCOPE), so the no-data boundary is
executable, not just documented.
"""
import fcntl
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.abspath(os.path.join(HERE, ".."))
REAL_LEDGER = os.path.join(NOTES, "pilot_harness", "credit_ledger.json")
PIN_POLICY_A = "5d9d82ca3e1c867e3f38dcb7f50cd7f372c793048d21232608f7835467d26cde"
GO_RECORD_ID = "QF-TD-POLICY-A-52-CREDIT-CEILING-GO-20261017"
GO_COMMENT_ID = 6234434220

import importlib.util as _ilu
_G3_PATH = os.path.join(NOTES, "td_gate3_attestation_policy_20261017_10",
                        "gate3_policy_candidate.py")
assert hashlib.sha256(open(_G3_PATH, "rb").read()).hexdigest() == \
    "7e44a2e0d0a3b32dfd6fb7f93f04a224f935310a6e71dfe06ea83008595eb3f9"
_g3s = _ilu.spec_from_file_location("qf_gate3_policy_txn", _G3_PATH)
GATE3_POLICY = _ilu.module_from_spec(_g3s)
_g3s.loader.exec_module(GATE3_POLICY)


def H(b):
    return hashlib.sha256(b).hexdigest()


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


class Refusal(Exception):
    def __init__(self, code, detail=""):
        super().__init__(code)
        self.code = code
        self.detail = detail


def _fsync_file(path):
    fd = os.open(path, os.O_RDONLY)
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
    _fsync_dir(os.path.dirname(os.path.abspath(path)))


class ReadinessTransaction:
    """One-use readiness transaction. `packet` binds every pin; `hooks`
    supplies fixture-only callables: resolve_helper(), status_call(),
    consumer_verify(path)->bool, dry_run(evidence_bytes)->dict, and
    fail_at (a set of step names for fault injection in tests)."""

    def __init__(self, workdir, packet, hooks):
        if packet.get("mode") != "offline_fixture":
            raise Refusal("LIVE_NOT_AUTHORIZED_IN_CANDIDATE",
                          "this candidate executes fixture mode only")
        for name in ("resolve_helper", "status_call"):
            if getattr(getattr(hooks, name, None), "is_fixture", None) is not True:
                raise Refusal("FIXTURE_HOOK_REQUIRED", name)
        self.workdir = workdir
        self.packet = packet
        self.hooks = hooks
        self.fail_at = set(getattr(hooks, "fail_at", ()) or ())
        self.state = "NEW"
        self.steps = []
        self.status_calls = 0
        self.raw_account = None
        self.gate3 = None
        self.evidence = None
        self.evidence_digest = None
        self.card = None
        self._fds = []
        os.makedirs(workdir, exist_ok=True)

    # -- internal helpers -------------------------------------------------
    def _log(self, step, **facts):
        self.steps.append({"step": step, **facts})

    def _maybe_fail(self, step):
        if step in self.fail_at:
            raise Refusal("INJECTED_FAILURE", step)

    def _release_locks(self):
        for fd in reversed(self._fds):
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
            except Exception:
                pass
        self._fds = []

    # -- scope boundary: executable refusals ------------------------------
    def request_token(self):
        raise Refusal("NOT_IN_READINESS_SCOPE", "token issuance excluded")

    def arm_transport(self):
        raise Refusal("NOT_IN_READINESS_SCOPE", "transport arming excluded")

    def call_time_series(self, *_a, **_k):
        raise Refusal("NOT_IN_READINESS_SCOPE", "market data excluded")

    # -- steps -------------------------------------------------------------
    def begin(self):
        marker = os.path.join(self.workdir, "CONSUMED.marker")
        if os.path.exists(marker):
            raise Refusal("TRANSACTION_ALREADY_CONSUMED",
                          "one-use transaction id already begun")
        _atomic_write(marker, canon({"txn_id": self.packet["txn_id"]}))
        self.state = "BEGUN"
        self._log("begin", txn_id=self.packet["txn_id"])

    def preflight(self):
        pk = self.packet
        target = os.path.abspath(pk["ledger_target"])
        if target == os.path.abspath(REAL_LEDGER):
            raise Refusal("REAL_LEDGER_TARGET_FORBIDDEN",
                          "adoption is fixture-copy only in this candidate")
        root = os.path.abspath(pk["fixture_root"])
        if not (target == root or target.startswith(root + os.sep)):
            raise Refusal("TARGET_OUTSIDE_FIXTURE_ROOT", target)
        for name, pin in pk["pins"].items():
            path = pk["pin_paths"][name]
            if H(open(path, "rb").read()) != pin:
                raise Refusal("PIN_DRIFT", name)
        go = pk.get("go_record")
        if not isinstance(go, dict) or not go:
            raise Refusal("GO_RECORD_MISSING")
        if not (go.get("record_id") == GO_RECORD_ID
                and go.get("comment_id") == GO_COMMENT_ID
                and go.get("ceiling_credits") == 52
                and go.get("status_credits") == 1
                and go.get("manifest_credits") == 51
                and go.get("spend_usd") == 0):
            raise Refusal("GO_RECORD_MALFORMED")
        if pk.get("policy_digest") != PIN_POLICY_A:
            raise Refusal("POLICY_DIGEST_MISMATCH")
        if pk.get("ceiling_credits") != 52:
            raise Refusal("POLICY_CEILING_MISMATCH")
        man_bytes = open(pk["pin_paths"]["manifest"], "rb").read()
        reqs = json.loads(man_bytes)["requests"]
        if len(reqs) != 51:
            raise Refusal("MANIFEST_COUNT_MISMATCH", str(len(reqs)))
        seq = H(canon([r["request_id"] for r in reqs]))
        if seq != pk["manifest_sequence_sha256"]:
            raise Refusal("MANIFEST_SEQUENCE_MISMATCH",
                          "ordered request identity drift (reorder/drop)")
        if H(open(pk["ledger_target"], "rb").read()) != pk["source_ledger_sha256"]:
            raise Refusal("SOURCE_LEDGER_DRIFT")
        self.state = "PREFLIGHT_OK"
        self._log("preflight", pins=len(pk["pins"]), sequence=seq[:12])

    def acquire_locks(self):
        if self.state != "PREFLIGHT_OK":
            raise Refusal("ORDER_VIOLATION", "locks require preflight")
        target = self.packet["ledger_target"]
        order = []
        for suffix, label in ((".owner_lease", "owner_lease"),
                              (".lock", "ledger_lock")):
            fd = os.open(target + suffix, os.O_RDWR | os.O_CREAT, 0o644)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                os.close(fd)
                self._release_locks()
                raise Refusal("LOCK_HELD", label)
            self._fds.append(fd)
            order.append(label)
        self.state = "LOCKS_HELD"
        self._log("locks", order=order)

    def verify_helper(self):
        if self.state != "LOCKS_HELD":
            raise Refusal("ORDER_VIOLATION", "helper verify requires locks")
        handle = self.hooks.resolve_helper()
        if not isinstance(handle, dict) or handle.get("fixture") is not True:
            raise Refusal("HELPER_HANDLE_NOT_FIXTURE")
        self.state = "HELPER_VERIFIED"
        self._log("helper_verified", origin=handle.get("origin"))

    def call_status(self):
        if self.status_calls >= 1:
            raise Refusal("STATUS_CALL_ALREADY_MADE", "one-call ceiling")
        if self.state != "HELPER_VERIFIED":
            raise Refusal("ORDER_VIOLATION",
                          "status call requires locks + verified helper")
        self.status_calls += 1  # consumed even if the call fails: no retry
        self.raw_account = self.hooks.status_call()
        self.state = "STATUS_CALLED"
        self._log("status_call", n=self.status_calls)
        return self.raw_account

    def evaluate_gate3(self):
        if self.state != "STATUS_CALLED":
            raise Refusal("ORDER_VIOLATION", "gate3 requires the status call")
        target = self.packet["ledger_target"]
        led = json.loads(open(target, "rb").read())
        reserved = 0
        if led.get("day") == self.packet["run_day"]:
            reserved = int(led.get("spent", 0))
        st, code, detail = GATE3_POLICY.validate_gate3(
            self.raw_account,
            {"policy_id": "A", "ceiling_credits": 52,
             "ledger_same_day_reserved": reserved},
            self.packet["now"])
        self.gate3 = {"status": st, "code": code, "detail": detail}
        self._log("gate3", status=st, code=code)
        if st != "PASS":
            self.state = "GATE3_NOT_PASS"
            raise Refusal("GATE3_NOT_PASS", code)
        self.state = "GATE3_PASS"

    def adopt(self):
        if self.state != "GATE3_PASS":
            raise Refusal("ADOPTION_NOT_REACHED",
                          "adoption requires a gate-3 PASS first")
        pk = self.packet
        target = pk["ledger_target"]
        cand = open(pk["pin_paths"]["ledger_candidate"], "rb").read()
        if H(cand) != pk["pins"]["ledger_candidate"]:
            raise Refusal("CANDIDATE_PIN_DRIFT")
        original = open(target, "rb").read()
        # 1) fsynced exact backup of the legacy bytes
        self._maybe_fail("backup")
        with open(pk["backup_path"], "wb") as f:
            f.write(original)
            f.flush()
            os.fsync(f.fileno())
        _fsync_dir(os.path.dirname(os.path.abspath(pk["backup_path"])))
        if H(open(pk["backup_path"], "rb").read()) != H(original):
            raise Refusal("BACKUP_VERIFY_FAILED")
        self._log("backup", sha256=H(original))
        # 2) atomic adoption
        self._maybe_fail("replace")
        _atomic_write(target, cand)
        if H(open(target, "rb").read()) != pk["pins"]["ledger_candidate"]:
            self._rollback(original, "POST_WRITE_HASH_MISMATCH")
            raise Refusal("POST_WRITE_HASH_MISMATCH")
        self.state = "ADOPTED"
        self._log("adopted", sha256=pk["pins"]["ledger_candidate"])
        # 3) post-write consumer verification; rollback on any failure
        try:
            self._maybe_fail("post_verify")
            ok = self.hooks.consumer_verify(target)
        except Refusal:
            self._rollback(original, "POST_WRITE_CONSUMER_FAILURE")
            raise
        except Exception:
            self._rollback(original, "POST_WRITE_CONSUMER_FAILURE")
            raise Refusal("POST_WRITE_CONSUMER_FAILURE")
        if not ok:
            self._rollback(original, "POST_WRITE_CONSUMER_FAILURE")
            raise Refusal("POST_WRITE_CONSUMER_FAILURE")
        self._log("post_write_verified")

    def _rollback(self, original, why):
        _atomic_write(self.packet["ledger_target"], original)
        assert H(open(self.packet["ledger_target"], "rb").read()) == H(original)
        self.state = "ROLLED_BACK"
        self._log("rollback", why=why, restored=H(original))

    def refreeze(self):
        if self.state != "ADOPTED":
            raise Refusal("ORDER_VIOLATION", "refreeze requires adoption")
        pk = self.packet
        self.evidence = {
            "txn_id": pk["txn_id"],
            "policy_digest": pk["policy_digest"],
            "ceiling_credits": 52,
            "manifest_digest": pk["pins"]["manifest"],
            "manifest_sequence_sha256": pk["manifest_sequence_sha256"],
            "account_api_usage": self.raw_account,
            "adopted_ledger_sha256": pk["pins"]["ledger_candidate"],
            "gate3": self.gate3,
            "window": pk["window"],
        }
        self.evidence_digest = H(canon(self.evidence))
        self.card = {
            "evidence_digest": self.evidence_digest,
            "run_id": pk["run_id"],
            "manifest_digest": pk["pins"]["manifest"],
            "ledger_path": pk["ledger_target"],
            "window": pk["window"],
        }
        self.card["card_digest"] = H(canon(self.card))
        _atomic_write(pk["evidence_path"], canon(self.evidence))
        _atomic_write(pk["card_path"], canon(self.card))
        self.state = "REFROZEN"
        self._log("refreeze", evidence_digest=self.evidence_digest)

    @staticmethod
    def verify_card(card_path, evidence_path):
        card = json.loads(open(card_path, "rb").read())
        ev = json.loads(open(evidence_path, "rb").read())
        body = {k: v for k, v in card.items() if k != "card_digest"}
        if H(canon(body)) != card.get("card_digest"):
            raise Refusal("CARD_DRIFT")
        if card.get("evidence_digest") != H(canon(ev)):
            raise Refusal("EVIDENCE_DRIFT")
        return True

    def dry_run(self):
        if self.state != "REFROZEN":
            raise Refusal("ORDER_VIOLATION", "dry-run requires refreeze")
        result = self.hooks.dry_run(canon(self.evidence))
        self._log("dry_run", decision=result.get("decision"))
        if result.get("decision") != "PASS_DRY_RUN" or result.get("gates_passed") != 12:
            raise Refusal("DRY_RUN_NOT_12_OF_12", json.dumps(result)[:200])
        self.state = "DRYRUN_OK"
        return result

    def run(self):
        """Execute the full sequence; never raises Refusal - returns the
        terminal record. Locks are always released at the end."""
        outcome = {"txn_id": self.packet["txn_id"]}
        try:
            self.begin()
            self.preflight()
            self.acquire_locks()
            self.verify_helper()
            self.call_status()
            self.evaluate_gate3()
            self.adopt()
            self.refreeze()
            self.dry_run()
            self.state = "COMPLETE"
            outcome["outcome"] = "COMPLETE"
        except Refusal as r:
            outcome["outcome"] = "ROLLED_BACK" if self.state == "ROLLED_BACK" else "HOLD"
            outcome["refusal"] = r.code
            outcome["refusal_detail"] = r.detail
            if self.state not in ("ROLLED_BACK",):
                self.state = "ABORTED"
        except Exception as e:  # recorded, not hidden
            outcome["outcome"] = "HOLD"
            outcome["refusal"] = "ERROR:%s" % type(e).__name__
            outcome["refusal_detail"] = str(e)[:200]
            self.state = "ABORTED"
        finally:
            self._release_locks()
        outcome["final_state"] = self.state
        outcome["status_calls"] = self.status_calls
        outcome["steps"] = self.steps
        outcome["gate3"] = self.gate3
        outcome["evidence_digest"] = self.evidence_digest
        rec = os.path.join(self.workdir, "terminal_record.json")
        _atomic_write(rec, canon(outcome))
        return outcome
