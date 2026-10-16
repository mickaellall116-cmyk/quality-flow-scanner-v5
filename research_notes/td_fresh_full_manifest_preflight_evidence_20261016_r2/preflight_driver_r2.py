#!/usr/bin/env python3
"""QF-TD-FRESH-FULL-MANIFEST-PREFLIGHT-20261016-03 r2 - offline preflight driver.

Targeted repair of the r1 driver (preserved unchanged alongside) closing
the two source gaps of FRESH_FULL_MANIFEST_PREFLIGHT_HOLD_SOURCE_GAPS
(Issue #1 comment 6225948851):

GAP 1 - the credit limiter ledger is no longer namespace-local. There is
exactly ONE limiter ledger per account, at an operator-pinned path
OUTSIDE every run namespace (the driver refuses a ledger path inside the
run namespace). The complete load/check/reserve/atomic-replace
transaction runs under an interprocess flock on the shared ledger's own
lock file, and the ledger is re-read from disk inside that lock on every
transaction, so distinct runs/processes share the same 8/min and 800/day
budgets and no race can lose or duplicate a reservation. A corrupt or
unreadable shared ledger raises Refusal and is never reset.

GAP 2 - the supplement is received as canonical BYTES. Before any
namespace creation or limiter access the driver requires the bytes to be
the canonical encoding and to hash exactly to
EXPECTED_SUPPLEMENT_SHA256; only then is the supplement parsed and the
r1 semantic checks run. Mutations to any field - including metadata the
r1 driver never examined - refuse pre-dispatch with zero calls/writes.

Otherwise implements the r1 design unchanged: the accepted -04 safety
design re-scoped to the FRESH manifest identity
TD-ACQUISITION-MANIFEST-V2-FRESH-20261016 with the adjudicated
EXPECTED_EMPTY_CLOSED_SESSION semantics bound via the fresh supplement.

FAKE TRANSPORT ONLY. This module contains no network code; the trial
suite is additionally executed under `unshare -n` by the harness.
Every trial runs in its own fresh namespace directory; trials that model
one account share one account ledger directory outside the namespaces.
"""
import hashlib
import json
import os
import sys

CLOSED_MESSAGE = "No data is available on the specified dates. Try setting different start/end dates."
EXPECTED_MANIFEST_DIGEST = "71aade8bfbb1f94b25d780bdf68f08f7f127740fc745c1755432acc5f74044db"
EXPECTED_SUPPLEMENT_SHA256 = "3cbdbf63fd49b021dc74f63727098551753949f8684967981c65f66101f95a86"


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def H(b):
    return hashlib.sha256(b).hexdigest()


class Refusal(Exception):
    """Pre-dispatch refusal (fail-closed before any transport call)."""


class SimulatedCrash(BaseException):
    pass


class TransportTimeout(Exception):
    pass


class FakeClock:
    def __init__(self, start=1792132800):  # 2026-10-16T14:00:00Z, fixed for determinism
        self.t = start

    def now(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def iso(ts):
    import datetime
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def day_of(ts):
    return iso(ts)[:10]


class Limiter:
    """Account-shared persistent credit limiter (8/min, 800/day per the
    pinned rate_limiter design). ONE ledger per account, at a pinned path
    outside all run namespaces. Every transaction (load -> check ->
    reserve -> atomic replace) is serialized by an interprocess flock on
    the ledger's own lock file, and the ledger is re-read from disk
    inside the lock, so concurrent runs/processes cannot lose, duplicate,
    or over-spend a reservation, and reservations survive process death.
    A corrupt/unreadable ledger raises Refusal and is never reset."""

    def __init__(self, path, minute_cap=8, day_cap=800):
        self.path = path
        self.lock_path = path + ".lock"
        self.minute_cap = minute_cap
        self.day_cap = day_cap
        self.ledger = {"reservations": []}
        # Validate (or create) the shared ledger under its lock before
        # any caller can reserve against it: a missing ledger is created
        # empty inside the same locked transaction.
        self._transact(lambda: (None, not self._loaded_existed))

    # -- locked transaction machinery --
    def _load_locked(self):
        """Read the ledger from disk. Caller must hold the flock.
        Missing file -> empty ledger (created by the paired _save).
        Corrupt/unreadable -> Refusal; the file is never reset."""
        self._loaded_existed = os.path.exists(self.path)
        if self._loaded_existed:
            try:
                with open(self.path, "rb") as f:
                    ledger = json.loads(f.read())
                assert isinstance(ledger, dict)
                assert isinstance(ledger.get("reservations"), list)
                for r in ledger["reservations"]:
                    assert isinstance(r["rid"], str) and isinstance(r["ts"], (int, float)) \
                        and isinstance(r["day"], str) and isinstance(r["weight"], (int, float))
            except Refusal:
                raise
            except Exception:
                raise Refusal("LIMITER_LEDGER_CORRUPT")
            return ledger
        return {"reservations": []}

    def _save_locked(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            f.write(json.dumps(self.ledger, sort_keys=True))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    def _transact(self, body):
        """Run body() with the shared-ledger flock held and the ledger
        freshly loaded from disk. body returns (result, dirty)."""
        import fcntl
        parent = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(parent, exist_ok=True)
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            self.ledger = self._load_locked()
            result, dirty = body()
            if dirty:
                self._save_locked()
            return result
        finally:
            os.close(fd)  # closing releases the flock, incl. on death

    def reserve(self, rid, weight, clock):
        def body():
            now = clock.now()
            day = day_of(now)
            day_used = sum(r["weight"] for r in self.ledger["reservations"] if r["day"] == day)
            if day_used + weight > self.day_cap:
                return (("REFUSED_DAY", None), False)
            minute = [r for r in self.ledger["reservations"] if r["ts"] > now - 60]
            if len(minute) + weight > self.minute_cap:
                release = min(r["ts"] for r in minute) + 60
                return (("WAIT", release), False)
            self.ledger["reservations"].append(
                {"rid": rid, "ts": now, "day": day, "weight": weight})
            return (("OK", None), True)
        return self._transact(body)

    def count(self):
        return self._transact(lambda: (len(self.ledger["reservations"]), False))


def build_ok_body(req, rows):
    meta = {
        "symbol": req["symbol"],
        "interval": req["interval"],
        "currency": req["venue_identity"]["currency"],
        "exchange_timezone": req["timezone"],
        "exchange": req["venue_identity"]["exchange"],
        "mic_code": req["venue_identity"]["mic_code"],
        "type": "Common Stock",
    }
    date = req["start_date"][:10]
    values = [
        {"datetime": "%s %02d:30:00" % (date, 9 + i), "open": "100.0", "high": "101.0",
         "low": "99.0", "close": "100.5", "volume": "1000"}
        for i in range(rows)
    ]
    return json.dumps({"meta": meta, "values": values, "status": "ok"}, sort_keys=True).encode()


CLOSED_BODY = json.dumps(
    {"code": 400, "status": "error", "message": CLOSED_MESSAGE}, sort_keys=True
).encode()


class FakeTransport:
    """Scripted transport. script: rid -> action tuple.
    Default: valid 200 with a small row count; REQ-SPT-07/08 -> closed 400."""

    def __init__(self, script=None):
        self.script = script or {}
        self.calls = []

    def __call__(self, req):
        rid = req["request_id"]
        self.calls.append(rid)
        action = self.script.get(rid)
        if action is None:
            if rid in ("REQ-SPT-07", "REQ-SPT-08"):
                return (400, CLOSED_BODY)
            rows = 4 if rid in ("REQ-SPT-05", "REQ-SPT-06") else 3
            return (200, build_ok_body(req, rows))
        kind = action[0]
        if kind == "ok":
            return (200, build_ok_body(req, action[1]))
        if kind == "raw":
            return (action[1], action[2])
        if kind == "timeout":
            raise TransportTimeout("simulated timeout")
        if kind == "crash":
            raise SimulatedCrash("simulated process death after STARTED")
        raise AssertionError("unknown action " + kind)


class Runner:
    KNOWN_FILES = {"manifest_binding.json", "owner.lock",
                   "lifecycle.jsonl", "pilot_state.json"}

    def __init__(self, ns, manifest_bytes, supplement_bytes, transport, clock,
                 shared_ledger_path=None,
                 expected_digest=EXPECTED_MANIFEST_DIGEST, account_mode="known"):
        self.ns = ns
        self.transport = transport
        self.clock = clock
        self.account_mode = account_mode
        # --- account-shared ledger path: required, pinned, and OUTSIDE
        # this run namespace (checked before anything is created) ---
        if not shared_ledger_path:
            raise Refusal("SHARED_LEDGER_PATH_REQUIRED")
        ns_abs = os.path.abspath(ns)
        ledger_abs = os.path.abspath(shared_ledger_path)
        if ledger_abs == ns_abs or ledger_abs.startswith(ns_abs + os.sep):
            raise Refusal("SHARED_LEDGER_INSIDE_NAMESPACE")
        self.shared_ledger_path = shared_ledger_path
        # --- manifest integrity (any failure = refusal, zero calls) ---
        try:
            manifest = json.loads(manifest_bytes)
        except Exception:
            raise Refusal("MANIFEST_UNPARSEABLE")
        if canon(manifest) != manifest_bytes:
            raise Refusal("MANIFEST_NOT_CANONICAL_BYTES")
        digest = H(manifest_bytes)
        if digest != expected_digest:
            raise Refusal("MANIFEST_DIGEST_MISMATCH")
        self.manifest = manifest
        self.digest = digest
        reqs = manifest["requests"]
        if len(reqs) != 51 or len({r["symbol"] for r in reqs}) != 20:
            raise Refusal("MANIFEST_SHAPE_MISMATCH")
        if manifest["budget"]["max_credits"] != 51 or manifest["budget"]["expected_credits"] != 51:
            raise Refusal("BUDGET_MISMATCH")
        for r in reqs:
            if r["max_attempts"] != 1 or r["credit_weight"] != 1 or r["expected_credits"] != 1:
                raise Refusal("REQUEST_TERMS_MISMATCH")
        self.request_digest = {r["request_id"]: H(canon(r)) for r in reqs}
        # --- supplement: canonical BYTES, exact pin enforced BEFORE any
        # namespace creation or limiter access (r2 gap 2). Only after the
        # exact-hash check passes is the supplement parsed and the r1
        # semantic binding checks run. ---
        try:
            supp = json.loads(supplement_bytes)
        except Exception:
            raise Refusal("SUPPLEMENT_UNPARSEABLE")
        if canon(supp) != supplement_bytes:
            raise Refusal("SUPPLEMENT_NOT_CANONICAL_BYTES")
        if H(supplement_bytes) != EXPECTED_SUPPLEMENT_SHA256:
            raise Refusal("SUPPLEMENT_SHA_MISMATCH")
        # --- supplement semantic binding (as r1) ---
        if supp["base_manifest_canonical_digest"] != digest:
            raise Refusal("SUPPLEMENT_BINDING_MISMATCH")
        for rid, entry in supp["entries"].items():
            if entry["expected_bars"] != 0:
                raise Refusal("SUPPLEMENT_ENTRY_NOT_ZERO_BARS")
            if entry["request_digest"] != self.request_digest.get(rid):
                raise Refusal("SUPPLEMENT_ENTRY_DIGEST_MISMATCH")
            proof = supp["calendar_proofs"].get(entry["calendar_proof_digest"])
            if proof is not None and H(canon(proof)) != entry["calendar_proof_digest"]:
                raise Refusal("CALENDAR_PROOF_DIGEST_MISMATCH")
        self.supp = supp
        # --- namespace: fresh, or resumable state of THIS run identity only ---
        os.makedirs(ns, exist_ok=True)
        existing = set(os.listdir(ns))
        if existing:
            binding_path = os.path.join(ns, "manifest_binding.json")
            if "manifest_binding.json" not in existing or not existing.issubset(
                    self.KNOWN_FILES | {"receipts"}):
                raise Refusal("NAMESPACE_NOT_CLEAN")
            binding = json.load(open(binding_path))
            if binding.get("run_id") != manifest["run_id"] or binding.get("manifest_digest") != digest:
                raise Refusal("NAMESPACE_BOUND_TO_OTHER_IDENTITY")
        else:
            binding = {"run_id": manifest["run_id"], "manifest_digest": digest}
            with open(os.path.join(ns, "manifest_binding.json"), "x") as f:
                f.write(json.dumps(binding, sort_keys=True))
        # --- sole owner: flock held for the runner's lifetime; the OS
        # releases it on process death, so a crash-restart can proceed
        # while a second LIVE owner is refused ---
        import fcntl
        self.lock_path = os.path.join(ns, "owner.lock")
        self._lock_fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(self._lock_fd)
            raise Refusal("DUPLICATE_OWNER")
        self.limiter = Limiter(self.shared_ledger_path)
        self.state_path = os.path.join(ns, "pilot_state.json")
        if os.path.exists(self.state_path):
            self.state = json.load(open(self.state_path))
        else:
            self.state = {"run_id": manifest["run_id"], "manifest_digest": digest, "requests": {}}
            self._save_state()
        self.events = []
        self.pacing_waits = 0

    # -- durable state helpers --
    def _save_state(self):
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            f.write(json.dumps(self.state, sort_keys=True))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.state_path)

    def _emit(self, event, rid, **kw):
        rec = {"event": event, "request_id": rid, "at": iso(self.clock.now())}
        rec.update(kw)
        with open(os.path.join(self.ns, "lifecycle.jsonl"), "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self.events.append(rec)

    def _set_status(self, rid, status, **kw):
        self.state["requests"].setdefault(rid, {}).update({"status": status}, **kw)
        self._save_state()

    def _write_once(self, rel, data):
        path = os.path.join(self.ns, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            with open(path, "rb") as f:
                if f.read() != data:
                    raise Refusal("WRITE_ONCE_COLLISION_FOREIGN_BYTES")
            return path
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        return path

    def close(self):
        try:
            os.close(self._lock_fd)  # releases the flock
        except Exception:
            pass

    # -- closed-session classification (-15 sec.5 conjuncts) --
    def classify_closed(self, req, raw):
        rid = req["request_id"]
        entry = self.supp["entries"].get(rid)
        if entry is None or entry["expected_bars"] != 0:
            return None
        if entry["request_digest"] != self.request_digest[rid]:
            return None
        proof = self.supp["calendar_proofs"].get(entry["calendar_proof_digest"])
        if proof is None or H(canon(proof)) != entry["calendar_proof_digest"]:
            return None  # calendar proof unavailable -> classification disabled
        if proof.get("closed") is not True or proof.get("date") not in entry["window_dates"]:
            return None
        if set(entry["window_dates"]) != {proof["date"]}:
            return None
        try:
            obj = json.loads(raw)
        except Exception:
            return None
        if not isinstance(obj, dict) or set(obj.keys()) != {"code", "status", "message"}:
            return None
        if obj["code"] != 400 or isinstance(obj["code"], bool) or obj["status"] != "error":
            return None
        if obj["message"] != CLOSED_MESSAGE:
            return None
        return entry["calendar_proof_digest"]

    def validate_ok(self, req, raw):
        try:
            obj = json.loads(raw)
        except Exception:
            return "UNPARSEABLE_200"
        if obj.get("status") != "ok":
            return "API_STATUS_NOT_OK"
        values = obj.get("values")
        if not isinstance(values, list) or len(values) == 0:
            return "MISSING_EMPTY_VALUES"
        if len(values) > req["one_response_bound_bars"]:
            return "OVER_ONE_RESPONSE_BOUND"
        meta = obj.get("meta") or {}
        venue = req["venue_identity"]
        if (meta.get("symbol") != req["symbol"] or meta.get("interval") != req["interval"]
                or meta.get("exchange") != venue["exchange"]
                or meta.get("mic_code") != venue["mic_code"]
                or meta.get("currency") != venue["currency"]):
            return "META_VENUE_MISMATCH"
        return None

    # -- main loop --
    def run(self):
        outcome = "COMPLETE"
        for req in self.manifest["requests"]:
            rid = req["request_id"]
            st = self.state["requests"].get(rid, {}).get("status")
            if st == "COMPLETED":
                rec = self.state["requests"][rid]
                path = os.path.join(self.ns, "receipts", rid + ".json")
                with open(path, "rb") as f:
                    if H(f.read()) != rec["receipt_sha256"]:
                        return self._finish("HOLD_RECEIPT_REVALIDATION_FAILED")
                continue
            if st == "CLOSED_DAY_EVIDENCED":
                continue
            if st in ("STARTED", "RESERVED"):
                self._set_status(rid, "AMBIGUOUS")
                self._emit("AMBIGUOUS_NO_REDISPATCH", rid)
                return self._finish("HOLD_AMBIGUOUS_STARTED")
            if self.account_mode == "unknown":
                self._emit("HOLD_UNKNOWN_CREDIT_STATE", rid)
                return self._finish("HOLD_UNKNOWN_CREDIT_STATE")
            # credit reservation lifecycle (durable, before dispatch)
            while True:
                res, release = self.limiter.reserve(rid, 1, self.clock)
                if res == "OK":
                    break
                if res == "REFUSED_DAY":
                    self._emit("LIMITER_REFUSED", rid)
                    return self._finish("REFUSED_LIMITER_DAY_CAP")
                self.pacing_waits += 1
                self.clock.advance(release - self.clock.now())
            self._set_status(rid, "STARTED")
            self._emit("CREDIT_RESERVED", rid)
            self._emit("STARTED", rid)
            try:
                status, raw = self.transport(req)
            except TransportTimeout:
                self._write_once(os.path.join("receipts", rid + ".rejected.bin"),
                                 b"TRANSPORT_TIMEOUT")
                self._emit("ERROR_EVIDENCE", rid, kind="TRANSPORT_TIMEOUT")
                self._set_status(rid, "ERROR_EVIDENCED")
                return self._finish("HOLD_TRANSPORT_TIMEOUT")
            if status == 400:
                proof_digest = self.classify_closed(req, raw)
                if proof_digest is not None:
                    self._write_once(os.path.join("receipts", rid + ".closed_day.bin"), raw)
                    self._set_status(rid, "CLOSED_DAY_EVIDENCED",
                                     calendar_proof_digest=proof_digest,
                                     body_sha256=H(raw))
                    self._emit("CLOSED_DAY_EVIDENCED", rid,
                               calendar_proof_digest=proof_digest, body_sha256=H(raw))
                    continue
                self._write_once(os.path.join("receipts", rid + ".rejected.bin"), raw)
                self._emit("ERROR_EVIDENCE", rid, kind="HTTP_400_UNCLASSIFIED")
                self._set_status(rid, "ERROR_EVIDENCED")
                return self._finish("HOLD_HTTP_400")
            if status != 200:
                self._write_once(os.path.join("receipts", rid + ".rejected.bin"), raw)
                self._emit("ERROR_EVIDENCE", rid, kind="HTTP_%d" % status)
                self._set_status(rid, "ERROR_EVIDENCED")
                return self._finish("HOLD_HTTP_%d" % status)
            problem = self.validate_ok(req, raw)
            if problem is not None:
                self._write_once(os.path.join("receipts", rid + ".rejected.bin"), raw)
                self._emit("ERROR_EVIDENCE", rid, kind=problem)
                self._set_status(rid, "ERROR_EVIDENCED")
                return self._finish("HOLD_" + problem)
            self._write_once(os.path.join("receipts", rid + ".json"), raw)
            self._emit("RECEIVED", rid, receipt_sha256=H(raw))
            self._set_status(rid, "COMPLETED", receipt_sha256=H(raw),
                             request_digest=self.request_digest[rid],
                             manifest_digest=self.digest)
            self._emit("COMPLETED", rid, receipt_sha256=H(raw))
        return self._finish(outcome)

    def _finish(self, outcome):
        return {
            "outcome": outcome,
            "transport_calls": list(self.transport.calls),
            "reservations": self.limiter.count(),
            "pacing_waits": self.pacing_waits,
            "states": {rid: v.get("status") for rid, v in sorted(self.state["requests"].items())},
        }
