#!/usr/bin/env python3
"""QF-TD-FRESH-LIVE-DRIVER-INTEGRATION-20261016-04 r1 - INTEGRATED live-capable
candidate entrypoint (offline proof round; authorizes no live call).

Closes the four integration gaps of
FRESH_FULL_MANIFEST_PREFLIGHT_R2_TARGETED_GAPS_CLOSED_LIVE_HOLD_INTEGRATION
(Issue #1 comment 6227025232) on top of the accepted r2 preflight machinery
(commit a56c449; fresh manifest 71aade8b..., supplement pin 3cbdbf63...,
account-shared locked limiter ledger outside all run namespaces):

GAP 1 (transport): this entrypoint binds, as immutable constants and
executable code, the exact live HTTPS/vault-proxy transport design of the
-14 pilot harness (research_notes/pilot_harness/pilot_acquire.py,
UrllibTransport): endpoint https://api.twelvedata.com/time_series,
credential reference custom.twelvedata attached ONLY at the last moment
via dynamic_credentials.url_with_surrogate_query_param with
allowed_hosts == [api.twelvedata.com], sanitized exceptions, response
cap. LiveHttpsTransport ships DISARMED: unless constructed armed=True it
refuses TRANSPORT_NOT_ARMED before any namespace/ledger/transport action,
and this package never arms it. Trials inject FakeTransport only, under
kernel network denial.

GAP 2 (supplement schema): the pinned live collector (commit ab254c3)
consumes an already-parsed P2-SPOT/version=v2 supplement keyed by
base_manifest_digest; the fresh supplement uses
TD-FRESH-FM-SUPPLEMENT-NL-20261016 keyed by
base_manifest_canonical_digest with pinned calendar_proofs. The fresh
supplement's canonical BYTES are unchanged and remain the pinned artifact
(SHA-256 checked before parsing/use, as r2). reconcile_supplement() is
the explicit, source-backed reconciliation layer: it validates every
fresh-schema identity/binding field and produces the classifier view the
collector's conjuncts require (entries by exact request digest with
expected_bars == 0; calendar evidence = the digest-verified pinned
calendar_proofs record whose basis is the NL-qualified pinned mechanism,
see supplement.calendar_proofs[*].basis). Any field mismatch refuses
SUPPLEMENT_SCHEMA_MISMATCH pre-dispatch, zero calls/writes.

GAP 3 (closed-response schema): the classifier implements the REAL
vendor closed-response contract from the preserved REQ-SPT-07 observation
(sha 3339c341...): HTTP 400, JSON object with keys exactly
{code, message, status, meta}, code the integer 400, status "error",
message byte-equal to the vendor no-data string, NO values field, and
meta exactly {symbol: <request symbol>, interval: <request interval>,
exchange: ""}. The r1/r2 fake three-key body is removed; FakeTransport
now emits the real four-key schema.

GAP 4 (binding): PINS below bind the collector implementation
(ab254c3 / b683d277...), the NL mechanism module (1b83cdcd...), the NL
environment lock (08b38cfa...), the adapter contract (ec877a04...), and
the pilot transport source files by SHA-256; the integration trial suite
verifies the on-disk sources equal these pins before any lifecycle proof.
"""

import hashlib
import json
import os
import sys

CLOSED_MESSAGE = "No data is available on the specified dates. Try setting different start/end dates."
EXPECTED_MANIFEST_DIGEST = "71aade8bfbb1f94b25d780bdf68f08f7f127740fc745c1755432acc5f74044db"
EXPECTED_SUPPLEMENT_SHA256 = "3cbdbf63fd49b021dc74f63727098551753949f8684967981c65f66101f95a86"

# --- integration pins (gap 4): collector / NL environment / adapter /
# live transport source, all bound by SHA-256 ---
COLLECTOR_COMMIT = "ab254c3458697dd450356146abcf4ad4f75ecef4"
COLLECTOR_SHA256 = "b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c"
NL_MECHANISM_MODULE_SHA256 = "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58"
NL_ENV_LOCK_SHA256 = "08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068"  # td_nl_env_rebuild_evidence_20261016/lock_copy.txt (NL_ENV_REBUILD_PASS, commit 0923db7)
ADAPTER_CONTRACT_SHA256 = "ec877a04d12e6b0c69378dba245be07ab60279a15c9eb78cc50e8b0c705e166b"
PILOT_ACQUIRE_SHA256 = "acf39bbd98f7174a4205019e754fc714ca420b4a7df43c815ea158a6fad67c59"
PILOT_RATE_LIMITER_SHA256 = "06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64"
# --- live transport binding (gap 1): the -14 pilot UrllibTransport design.
# The credential NAME is an identifier, not material; the key itself is
# never read, stored, logged, or placed in argv by this module - the
# vault surrogate is attached by the platform helper at call time only.
LIVE_ENDPOINT = "https://api.twelvedata.com/time_series"
LIVE_CREDENTIAL_REF = "custom.twelvedata"
LIVE_ALLOWED_HOSTS = ["api.twelvedata.com"]
LIVE_RESPONSE_CAP_BYTES = 33554432
LIVE_TIMEOUT_S = 30


def build_url(req):
    """Deterministic no-key URL for one manifest request (the pilot
    _build_url parameter set). Contains NO credential material; the
    surrogate apikey parameter is attached by the platform helper at
    call time inside LiveHttpsTransport only."""
    import urllib.parse
    params = {
        "symbol": req["symbol"],
        "interval": req["interval"],
        "start_date": req["start_date"],
        "end_date": req["end_date"],
        "timezone": req["timezone"],
        "outputsize": str(req["outputsize"]),
        "order": req["order"],
        "adjust": req["adjust"],
    }
    return LIVE_ENDPOINT + "?" + urllib.parse.urlencode(params)


class LiveHttpsTransport:
    """Candidate live transport (pilot UrllibTransport semantics).
    DISARMED by default and in every trial: __call__ refuses
    TRANSPORT_NOT_ARMED unless constructed armed=True. The armed path
    mirrors pilot_acquire.UrllibTransport: surrogate attached at the
    last moment via dynamic_credentials, sanitized exceptions, capped
    body read. It is provided as candidate source only; nothing in this
    package arms or connects it."""

    def __init__(self, armed=False):
        self.armed = armed
        self.calls = []

    def __call__(self, req):
        if not self.armed:
            raise Refusal("TRANSPORT_NOT_ARMED")
        self.calls.append(req["request_id"])
        try:
            from dynamic_credentials import url_with_surrogate_query_param
        except Exception:
            raise Refusal("CREDENTIAL_HELPER_UNAVAILABLE")
        import urllib.error
        import urllib.request
        url = url_with_surrogate_query_param(
            build_url(req), LIVE_CREDENTIAL_REF, allowed_hosts=LIVE_ALLOWED_HOSTS)
        request = urllib.request.Request(
            url, headers={"User-Agent": "qf-live-driver/04-r1",
                          "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=LIVE_TIMEOUT_S) as resp:
                return resp.status, resp.read(LIVE_RESPONSE_CAP_BYTES)
        except urllib.error.HTTPError as e:
            try:
                body = e.read(LIVE_RESPONSE_CAP_BYTES)
            except Exception:
                body = b""
            return e.code, body
        except Exception:
            raise TransportTimeout("live transport failure (sanitized)")



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


def build_closed_body(req):
    """The REAL vendor closed-session body (preserved REQ-SPT-07
    observation, sha 3339c341...): keys exactly {code, message, status,
    meta}; meta exactly {symbol, interval, exchange: ""}; no values."""
    return json.dumps(
        {"code": 400, "status": "error", "message": CLOSED_MESSAGE,
         "meta": {"symbol": req["symbol"], "interval": req["interval"],
                  "exchange": ""}},
        sort_keys=True).encode()


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
                return (400, build_closed_body(req))
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



def reconcile_supplement(supp, manifest_digest, request_digest):
    """Gap-2 reconciliation layer. The pinned collector (ab254c3)
    requires, semantically: a supplement of the EXPECTED_EMPTY_CLOSED_SESSION
    class, bound to THIS manifest digest, preregistering requests by exact
    request digest with expected_bars == 0, with digest-verified calendar
    evidence that the window date is exchange-closed. The fresh
    supplement carries exactly those semantics under its own schema
    (TD-FRESH-FM-SUPPLEMENT-NL-20261016 / base_manifest_canonical_digest /
    pinned calendar_proofs from the NL-qualified mechanism). This
    function validates the fresh schema field-by-field and returns the
    classifier view {entries, calendar_proofs}; it never mutates the
    pinned bytes and any anomaly raises Refusal before namespace/ledger
    access."""
    if supp.get("supplement_id") != "TD-FRESH-FM-SUPPLEMENT-NL-20261016":
        raise Refusal("SUPPLEMENT_SCHEMA_MISMATCH")
    if supp.get("class") != "EXPECTED_EMPTY_CLOSED_SESSION":
        raise Refusal("SUPPLEMENT_SCHEMA_MISMATCH")
    if supp.get("lifecycle_event") != "CLOSED_DAY_EVIDENCED":
        raise Refusal("SUPPLEMENT_SCHEMA_MISMATCH")
    if supp.get("status") != "OFFLINE_CANDIDATE_NOT_ADOPTED":
        raise Refusal("SUPPLEMENT_SCHEMA_MISMATCH")
    if supp.get("base_manifest_canonical_digest") != manifest_digest:
        raise Refusal("SUPPLEMENT_BINDING_MISMATCH")
    pins = supp.get("classifier_pins") or {}
    if pins.get("collector_sha256") != COLLECTOR_SHA256 or \
            pins.get("collector_commit") != COLLECTOR_COMMIT:
        raise Refusal("SUPPLEMENT_SCHEMA_MISMATCH")
    safety = supp.get("safety_design_binding") or {}
    if safety.get("adapter_contract_sha256") != ADAPTER_CONTRACT_SHA256:
        raise Refusal("SUPPLEMENT_SCHEMA_MISMATCH")
    cal = supp.get("calendar") or {}
    if not isinstance(cal.get("environment_binding"), dict):
        raise Refusal("SUPPLEMENT_SCHEMA_MISMATCH")
    entries = supp.get("entries")
    proofs = supp.get("calendar_proofs")
    if not isinstance(entries, dict) or not isinstance(proofs, dict) or not entries:
        raise Refusal("SUPPLEMENT_SCHEMA_MISMATCH")
    for rid, entry in entries.items():
        if entry.get("expected_bars") != 0:
            raise Refusal("SUPPLEMENT_ENTRY_NOT_ZERO_BARS")
        if entry.get("request_digest") != request_digest.get(rid):
            raise Refusal("SUPPLEMENT_ENTRY_DIGEST_MISMATCH")
        pd = entry.get("calendar_proof_digest")
        proof = proofs.get(pd)
        if proof is None or H(canon(proof)) != pd:
            raise Refusal("CALENDAR_PROOF_DIGEST_MISMATCH")
        if proof.get("closed") is not True or proof.get("date") not in entry.get("window_dates", []):
            raise Refusal("SUPPLEMENT_SCHEMA_MISMATCH")
        if set(entry.get("window_dates", [])) != {proof.get("date")}:
            raise Refusal("SUPPLEMENT_SCHEMA_MISMATCH")
    return {"entries": entries, "calendar_proofs": proofs}


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
        # --- transport binding: an unarmed live transport can never be
        # dispatched by this entrypoint (gap 1); refuse before any
        # namespace or ledger access. ---
        if isinstance(transport, LiveHttpsTransport) and not transport.armed:
            raise Refusal("TRANSPORT_NOT_ARMED")
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
        # --- schema reconciliation (gap 2): the fresh supplement is
        # NOT the collector's P2-SPOT/v2 object. Validate every
        # fresh-schema identity/binding field explicitly and build the
        # classifier view; any mismatch refuses pre-dispatch. ---
        self.supp = reconcile_supplement(supp, digest, self.request_digest)
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
        if not isinstance(obj, dict) or set(obj.keys()) != {"code", "message", "status", "meta"}:
            return None
        if type(obj["code"]) is not int or obj["code"] != 400 or obj["status"] != "error":
            return None
        if obj["message"] != CLOSED_MESSAGE:
            return None
        meta = obj["meta"]
        if not isinstance(meta, dict) or set(meta.keys()) != {"symbol", "interval", "exchange"}:
            return None
        if (meta["symbol"] != req["symbol"] or meta["interval"] != req["interval"]
                or meta["exchange"] != ""):
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
