#!/usr/bin/env python3
"""Account-preflight adapter — TD probe candidate (task -71 r1,
successor of -70/-68/-67/-66/-65).

TASK -71 (atomic-persistence closure; spec Issue #1 comment
6319460212): the -70 quota semantics below are preserved
EXACTLY. The single change is that DailyUsageSession's outcome
persistence is now a demonstrated transaction: body and receipt
are staged to same-filesystem temp files with a write-all loop
and fsync, the body is published first and made durable (hard
link + parent-directory fsync), and the receipt is published
LAST as the commit point (hard link + directory fsync) — so a
committed receipt never exists unless its exact body is present
and durable. Collisions and ambiguous orphaned final evidence
refuse rather than being silently overwritten; temp files are
cleaned on failure. The -70 writer opened the final paths
directly, wrote each with a single unchecked os.write, and
performed no fsync — fail-closed in ordinary failures, but not
atomic or durable against partial writes/interruption.

USAGE-SEMANTICS REPAIR (task -70; spec Issue #1 comment
6317623205; basis: -69 Day-1 execution, commit c24c545, terminal
TD_PROBE_DAY1_HOLD__G_USE_USAGE_HEADROOM accepted as the correct
fail-closed outcome). The -68 adapter committed two defects:

  DEFECT A (semantics): it treated the /api_usage field
  `plan_limit` as the DAILY budget and required the whole day's
  worst-case attempt budget to fit inside it
  (current_usage + required_headroom <= plan_limit). The live
  Day-1 response returned current_usage=1, plan_limit=8 — the
  Basic plan's published 8-credits-PER-MINUTE bucket — while the
  separate published daily allowance is 800/day, so the adapter
  refused a healthy account. The frozen RollingCreditLimiter
  (8, 800) already separates the two dimensions; this repair
  aligns the preflight with that separation:
    * current_usage / plan_limit are the MINUTE bucket. They are
      schema-checked (integers >= 0) and recorded, but NO
      day-budget headroom is ever required to fit inside them.
      Per-minute spacing is enforced by the pinned rolling
      limiter, not by this gate.
    * The DAILY gate is explicit and fail-closed: daily_usage /
      plan_daily_limit are parsed ONLY when both are present and
      numeric. The Basic-plan path requires plan_daily_limit to
      equal the pinned 800/day and daily_usage +
      required_headroom <= plan_daily_limit, where
      required_headroom is the execution day's remaining
      worst-case call count (Day 1: 10 = 5 legs x 2 attempts).
      Daily fields absent, half-present, malformed, internally
      contradictory (daily_usage > plan_daily_limit), or a
      plan_daily_limit other than the pinned 800 -> HOLD before
      any data transport. Minute fields NEVER satisfy the daily
      gate, and no headroom is ever invented.
    * api-credits-used / api-credits-left response headers are
      captured and reconciled against the body when present and
      integer-parseable (used == current_usage; used + left ==
      plan_limit — the minute bucket of the same response). A
      contradiction refuses. Headers are NEVER used to waive or
      weaken the daily gate.

  DEFECT B (evidence): the -68 session persisted its receipt
  ONLY on PASS — on the -69 refusal the response body was lost
  and the live daily-field schema cannot be reconstructed (and
  must not be guessed). This repair persists EVERY usage
  outcome: before a PASS or a REFUSE is returned, the session
  atomically preserves (a) the exact raw body bytes of the
  terminal attempt in the local evidence store
  (api_usage.<DAY>.body.bin — local store only, never committed
  anywhere else) and (b) a sanitized receipt
  (api_usage.<DAY>.receipt.json) carrying HTTP status, byte
  count, SHA-256 of the exact body bytes, normalized parsed
  fields, the reconciled safe headers, endpoint/params binding,
  execution UTC date/time, attempt count, manifest/store pins,
  verdict, and terminal reason. The receipt is the commit point:
  a receipt whose body file is missing or hash-mismatched is
  invalid on any later verification. A persist failure is itself
  a HOLD (USAGE_RECEIPT_PERSIST_FAILED). A recorded REFUSE is
  sticky for the binding: a later same-day session returns the
  recorded reason without any transport.

Inherited -67/-66 properties, unchanged: injectable transport
(fetch(url_no_key) -> (status, headers, body)); max 2 attempts,
retry only on 429/5xx/timeout; once per execution day via an
O_EXCL receipt; cached PASS reuse re-verifies verdict, day,
manifest SHA-256, store marker, recorded required headroom,
canonical payload digest + field re-derivation, timestamps
(stale > 1 day / future), endpoint params, and the explicit UTC
execution-date binding (cross-midnight reuse refuses) — and now
additionally re-runs the corrected daily gate + header
reconciliation and verifies the persisted body bytes against
the receipt. UNKNOWN, never inferred: the vendor's usage-reset
timezone; the UTC execution date is this candidate's
conservative binding, not a claim about vendor semantics. NO
network and NO credential resolution in this task: synthetic
fakes only.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

USAGE_URL = "https://api.twelvedata.com/api_usage"
USAGE_REQUEST_ID = "API-USAGE-PREFLIGHT"
USAGE_PARAMS = {"endpoint": "/api_usage"}

# Pinned Basic-plan quota dimensions (published plan; also the
# frozen RollingCreditLimiter(8, 800) pair).
PINNED_MINUTE_LIMIT = 8
PINNED_DAILY_LIMIT = 800

# The only response headers this adapter captures: credit
# counters, sanitized by allowlist — never anything else.
SAFE_CREDIT_HEADERS = ("api-credits-used", "api-credits-left")

# Low-level syscall seams for the transactional persistence
# below, bound once at import so the qualification harness can
# deterministically inject short writes and fsync/link failures
# at exactly these points (task -71 failure-injection cases).
_write_once = os.write
_fsync = os.fsync
_link = os.link


def _write_all(fd, data: bytes) -> None:
    """Write ALL of `data` to `fd`, looping over short writes.
    A write that makes no progress (<= 0) is a failure, never a
    spin."""
    view = memoryview(data)
    while len(view) > 0:
        n = _write_once(fd, view)
        if n is None or n <= 0:
            raise OSError(f"short write: os.write returned {n!r}")
        view = view[n:]


def _fsync_dir(path: Path) -> None:
    """fsync a directory so the names published inside it are
    durable."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        _fsync(fd)
    finally:
        os.close(fd)


def utc_date_string(ms: int) -> str:
    """UTC calendar date (YYYY-MM-DD) of an epoch-ms instant,
    derived deterministically — the execution-date binding unit."""
    return datetime.datetime.fromtimestamp(
        ms / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d")


MAX_ATTEMPTS = 2
RETRYABLE_STATUS = {429, 502, 503, 504}
DAY_MS = 86_400_000
FUTURE_SKEW_MS = 300_000


class PreflightRefusal(Exception):
    """A fail-closed preflight refusal. Carries the outcome
    receipt (`.receipt`, verdict REFUSE) when one was built, so
    the session can persist it before returning the refusal."""

    def __init__(self, tag: str, detail: str = "",
                 receipt: dict | None = None):
        super().__init__(f"{tag}: {detail}" if detail else tag)
        self.tag = tag
        self.receipt = receipt


def _is_count(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def parse_usage_body(body: bytes) -> dict:
    """Parse a /api_usage body into normalized fields:

      {current_usage, plan_limit,            <- minute bucket
       daily_usage, plan_daily_limit,        <- daily pair or None
       daily_present: bool}

    The minute pair is required (integers >= 0) — any deviation
    is USAGE_SCHEMA. The daily pair is parsed ONLY when both
    fields are present; exactly one present, or a present field
    that is not an integer >= 0, is USAGE_DAILY_SCHEMA. Both
    absent yields daily_present=False (the gate, not the parser,
    refuses that). Unknown extra fields are ignored: the gate
    keys only on the four named fields, and a schema that cannot
    be established under those names fails at the gate.
    """
    try:
        payload = json.loads(body)
    except Exception as e:
        raise PreflightRefusal("USAGE_SCHEMA", f"bad JSON: {e}") from e
    if not isinstance(payload, dict):
        raise PreflightRefusal("USAGE_SCHEMA", "not a JSON object")
    cur = payload.get("current_usage")
    lim = payload.get("plan_limit")
    for name, v in (("current_usage", cur), ("plan_limit", lim)):
        if not _is_count(v):
            raise PreflightRefusal(
                "USAGE_SCHEMA", f"{name} (minute bucket) not int>=0")
    has_du = "daily_usage" in payload
    has_dl = "plan_daily_limit" in payload
    if has_du != has_dl:
        raise PreflightRefusal(
            "USAGE_DAILY_SCHEMA",
            "exactly one of daily_usage/plan_daily_limit present")
    if not has_du:
        return {"current_usage": cur, "plan_limit": lim,
                "daily_usage": None, "plan_daily_limit": None,
                "daily_present": False}
    du, dl = payload["daily_usage"], payload["plan_daily_limit"]
    for name, v in (("daily_usage", du), ("plan_daily_limit", dl)):
        if not _is_count(v):
            raise PreflightRefusal(
                "USAGE_DAILY_SCHEMA", f"{name} not int>=0")
    return {"current_usage": cur, "plan_limit": lim,
            "daily_usage": du, "plan_daily_limit": dl,
            "daily_present": True}


def canonical_usage_payload(fields: dict) -> str:
    """Canonical sanitized payload of an established usage
    reading: the four quota fields, deterministic key
    order/encoding. Only defined when the daily pair is
    established (a PASS can never be written without it)."""
    return json.dumps(
        {"current_usage": fields["current_usage"],
         "daily_usage": fields["daily_usage"],
         "plan_daily_limit": fields["plan_daily_limit"],
         "plan_limit": fields["plan_limit"]},
        sort_keys=True, separators=(",", ":"))


def capture_credit_headers(headers) -> dict:
    """Capture ONLY the two safe credit headers (case-insensitive
    names), values as strings. Anything else in the header block
    is dropped, never stored."""
    out = {}
    if isinstance(headers, dict):
        lowered = {str(k).lower(): v for k, v in headers.items()}
        for name in SAFE_CREDIT_HEADERS:
            if name in lowered:
                out[name] = str(lowered[name])
    return out


def _header_int(headers: dict, name: str) -> int | None:
    """Integer value of a captured header, or None when absent or
    not integer-parseable (unparseable headers are recorded but
    never interpreted)."""
    raw = headers.get(name)
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def reconcile_credit_headers(fields: dict, headers: dict) -> None:
    """Reconcile captured credit headers against the body of the
    SAME response (the minute bucket): used must equal
    current_usage, and used + left must equal plan_limit, when
    the values are present and integer-parseable. A contradiction
    refuses. Headers never waive the daily gate — this check can
    only refuse, never pass anything the body did not establish.
    """
    used = _header_int(headers, "api-credits-used")
    left = _header_int(headers, "api-credits-left")
    if used is not None and used != fields["current_usage"]:
        raise PreflightRefusal(
            "USAGE_HEADER_MISMATCH",
            f"api-credits-used {used} != body current_usage "
            f"{fields['current_usage']}")
    if used is not None and left is not None and \
            used + left != fields["plan_limit"]:
        raise PreflightRefusal(
            "USAGE_HEADER_MISMATCH",
            f"api-credits-used {used} + api-credits-left {left} "
            f"!= body plan_limit {fields['plan_limit']}")


def evaluate_daily_gate(fields: dict, required_headroom: int) -> None:
    """The explicit, fail-closed daily gate. `required_headroom`
    is the execution day's remaining worst-case call count; it is
    charged ONLY against the daily allowance — never against the
    minute bucket (defect-A repair)."""
    if not fields["daily_present"]:
        raise PreflightRefusal(
            "USAGE_DAILY_SCHEMA",
            "daily_usage/plan_daily_limit absent — the daily "
            "schema cannot be established; minute fields are not "
            "a daily budget and no headroom is invented")
    du, dl = fields["daily_usage"], fields["plan_daily_limit"]
    if dl != PINNED_DAILY_LIMIT:
        raise PreflightRefusal(
            "USAGE_DAILY_PLAN",
            f"plan_daily_limit {dl} != pinned Basic-plan daily "
            f"allowance {PINNED_DAILY_LIMIT}")
    if du > dl:
        raise PreflightRefusal(
            "USAGE_DAILY_SCHEMA",
            f"daily_usage {du} > plan_daily_limit {dl} "
            "(contradictory daily fields)")
    if du + required_headroom > dl:
        raise PreflightRefusal(
            "USAGE_DAILY_HEADROOM",
            f"daily {du} + headroom {required_headroom} > "
            f"daily limit {dl}")


class AccountPreflight:
    """Injectable /api_usage preflight with corrected quota
    semantics. `required_headroom` is the execution day's
    remaining worst-case call count, charged only against the
    explicitly established daily allowance. check() returns the
    PASS outcome receipt, or raises PreflightRefusal carrying the
    REFUSE outcome receipt (`.receipt`); the transient exact body
    bytes ride in the receipt under `_body_bytes` for the
    session's evidence persistence and are never serialized into
    the receipt file."""

    def __init__(self, transport, clock=None, sleeper=None,
                 required_headroom: int = 0):
        self.transport = transport
        self.clock = clock or time.time
        self.sleeper = sleeper or (lambda s: None)
        self.required_headroom = required_headroom
        self.attempts_made = 0

    def _outcome_receipt(self, attempt_statuses, request_ts_ms,
                         receipt_ts_ms, status, body, headers):
        return {
            "request_id": USAGE_REQUEST_ID,
            "attempt": len(attempt_statuses),
            "attempts": len(attempt_statuses),
            "attempt_statuses": list(attempt_statuses),
            "request_ts_ms": request_ts_ms,
            "receipt_ts_ms": receipt_ts_ms,
            "http_status": status,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "params": dict(USAGE_PARAMS),
            "execution_date_utc": utc_date_string(request_ts_ms),
            "credits_headers": capture_credit_headers(headers),
            "_body_bytes": body,
        }

    def check(self) -> dict:
        attempt_statuses: list[int] = []
        first_t0 = None
        last_status = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            t0 = self.clock()
            try:
                status, headers, body = self.transport.fetch(USAGE_URL)
            except TimeoutError:
                status, headers, body = 0, {}, b""
            t1 = self.clock()
            self.attempts_made = attempt
            last_status = status
            attempt_statuses.append(status)
            if first_t0 is None:
                first_t0 = t0
            receipt = self._outcome_receipt(
                attempt_statuses, int(first_t0 * 1000),
                int(t1 * 1000), status, body, headers)
            if status == 200:
                try:
                    fields = parse_usage_body(body)
                    evaluate_daily_gate(fields,
                                        self.required_headroom)
                    reconcile_credit_headers(
                        fields, receipt["credits_headers"])
                except PreflightRefusal as e:
                    receipt["verdict"] = "REFUSE"
                    receipt["terminal_reason"] = str(e)
                    raise PreflightRefusal(
                        e.tag, str(e), receipt=receipt) from e
                payload = canonical_usage_payload(fields)
                receipt["current_usage"] = fields["current_usage"]
                receipt["plan_limit"] = fields["plan_limit"]
                receipt["daily_usage"] = fields["daily_usage"]
                receipt["plan_daily_limit"] = \
                    fields["plan_daily_limit"]
                receipt["response_payload"] = payload
                receipt["response_sha256"] = hashlib.sha256(
                    payload.encode()).hexdigest()
                receipt["verdict"] = "PASS"
                receipt["terminal_reason"] = None
                return receipt
            if status in RETRYABLE_STATUS or status == 0:
                if attempt < MAX_ATTEMPTS:
                    self.sleeper(0)
                    continue
                receipt["verdict"] = "REFUSE"
                receipt["terminal_reason"] = (
                    f"USAGE_RETRIES_EXHAUSTED: status {status}")
                raise PreflightRefusal(
                    "USAGE_RETRIES_EXHAUSTED", f"status {status}",
                    receipt=receipt)
            receipt["verdict"] = "REFUSE"
            receipt["terminal_reason"] = (
                f"USAGE_TERMINAL_STATUS: status {status}")
            raise PreflightRefusal(
                "USAGE_TERMINAL_STATUS", f"status {status}",
                receipt=receipt)
        raise PreflightRefusal("USAGE_RETRIES_EXHAUSTED",
                               f"status {last_status}")


def store_marker_sha256(store_marker: str) -> str:
    return hashlib.sha256(store_marker.encode()).hexdigest()


class DailyUsageSession:
    """Once-per-execution-day binding used as the ManifestDriver
    preflight callable.

    EVERY outcome is persisted before it is returned (defect-B
    repair): the terminal attempt's exact body bytes go to
    api_usage.<DAY>.body.bin in the local evidence store, and the
    sanitized, binding-stamped receipt to
    api_usage.<DAY>.receipt.json (the commit point). A persist
    failure is itself a HOLD (USAGE_RECEIPT_PERSIST_FAILED) and
    no data transport is reached. Returns [] on pass,
    [reason] on failure — which the wrapper turns into a
    fail-closed abort BEFORE any data request is fetched.

    Later same-day invocations never re-call: a stored PASS is
    re-verified (integrity bindings, body-byte hash, payload
    digest + field re-derivation, the corrected daily gate and
    header reconciliation re-run at the session's required
    headroom, timestamps, UTC execution-date equality) and
    reused; a stored REFUSE returns its recorded terminal reason
    (sticky refusal). Any defect refuses before data transport.
    """

    def __init__(self, store_dir: Path, day: str,
                 preflight: AccountPreflight,
                 manifest_sha256: str, store_marker: str,
                 required_headroom: int, clock=None):
        self.store_dir = Path(store_dir)
        self.day = day
        self.preflight = preflight
        self.manifest_sha256 = manifest_sha256
        self.store_marker = store_marker
        self.required_headroom = required_headroom
        self.clock = clock or time.time
        self.receipt_path = self.store_dir / \
            f"api_usage.{day}.receipt.json"
        self.body_path = self.store_dir / \
            f"api_usage.{day}.body.bin"
        self.receipt: dict | None = None

    # -- persistence -------------------------------------------------

    def _stage_temp(self, data: bytes, tag: str,
                    temps: list) -> Path:
        """Write `data` to a same-directory temporary file with
        restrictive permissions (write-all loop + fsync) and
        return its path. The temp is registered in `temps` so
        the caller cleans it up on any failure."""
        fd, name = tempfile.mkstemp(
            dir=str(self.store_dir), prefix=f".usage-{tag}-",
            suffix=".tmp")
        tmp = Path(name)
        temps.append(tmp)
        try:
            os.fchmod(fd, 0o600)
            _write_all(fd, data)
            _fsync(fd)
        finally:
            os.close(fd)
        return tmp

    def _persist_outcome(self, receipt: dict) -> None:
        """Transactionally preserve body bytes + receipt
        (task -71). Both artifacts are staged to
        same-filesystem temp files (write-all + fsync); the
        body is then published first and made durable (hard
        link + parent-directory fsync), and the receipt is
        published LAST as the commit point (hard link +
        directory fsync) — a committed receipt never exists
        unless its exact body is present and durable.
        Publishing by hard link refuses (FileExistsError)
        rather than overwriting a colliding final name, and
        any pre-existing final body/receipt — including an
        orphaned body left by an interrupted earlier
        transaction — refuses the persist as ambiguous
        evidence. Temp files are cleaned on failure; a final
        already published is left in place (it is evidence,
        and any later session refuses on the collision).
        Raises OSError on any failure — the caller turns that
        into HOLD."""
        body = receipt.pop("_body_bytes", b"")
        receipt_bytes = json.dumps(receipt, indent=2).encode()
        self.store_dir.mkdir(parents=True, exist_ok=True)
        for final in (self.body_path, self.receipt_path):
            if os.path.lexists(final):
                raise OSError(
                    "USAGE_PERSIST_COLLISION: final evidence "
                    f"{final.name} already present — refusing "
                    "to overwrite ambiguous state")
        temps: list = []
        try:
            body_tmp = self._stage_temp(body, "body", temps)
            receipt_tmp = self._stage_temp(
                receipt_bytes, "receipt", temps)
            _link(body_tmp, self.body_path)
            os.unlink(body_tmp)
            temps.remove(body_tmp)
            _fsync_dir(self.store_dir)
            _link(receipt_tmp, self.receipt_path)
            os.unlink(receipt_tmp)
            temps.remove(receipt_tmp)
            _fsync_dir(self.store_dir)
        finally:
            for tmp in temps:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def _verify_body_file(self, stored) -> str | None:
        """The stored receipt's exact-body evidence must exist and
        hash-match; otherwise the receipt proves nothing."""
        if not self.body_path.exists():
            return "USAGE_RECEIPT_BODY_MISSING: body evidence absent"
        body = self.body_path.read_bytes()
        if len(body) != stored.get("bytes") or \
                hashlib.sha256(body).hexdigest() != \
                stored.get("sha256"):
            return ("USAGE_RECEIPT_BODY_MISMATCH: persisted body "
                    "bytes do not match the receipt hash/count")
        return None

    # -- cached-outcome verification ---------------------------------

    def _verify_cached(self, stored) -> str | None:
        """Return None if a cached PASS receipt may be reused,
        else a refusal reason string. (A stored REFUSE is handled
        by the caller before this runs.)"""
        if not isinstance(stored, dict):
            return "USAGE_CACHE_MALFORMED: not an object"
        if stored.get("verdict") != "PASS" or \
                stored.get("day") != self.day:
            return "USAGE_RECEIPT_INVALID"
        if stored.get("request_id") != USAGE_REQUEST_ID or \
                stored.get("http_status") != 200:
            return "USAGE_CACHE_IDENTITY"
        attempt = stored.get("attempt")
        if not isinstance(attempt, int) or isinstance(attempt, bool) \
                or not 1 <= attempt <= MAX_ATTEMPTS:
            return "USAGE_CACHE_IDENTITY: attempt out of range"
        if stored.get("params") != USAGE_PARAMS:
            return ("USAGE_CACHE_PARAMS: endpoint params "
                    f"{stored.get('params')!r} != {USAGE_PARAMS!r}")
        if stored.get("manifest_sha256") != self.manifest_sha256:
            return "USAGE_CACHE_BINDING: manifest_sha256 mismatch"
        if stored.get("store_marker_sha256") != \
                store_marker_sha256(self.store_marker):
            return "USAGE_CACHE_BINDING: store marker mismatch"
        if stored.get("required_headroom") != self.required_headroom:
            return ("USAGE_CACHE_BINDING: required_headroom "
                    f"{stored.get('required_headroom')!r} != "
                    f"{self.required_headroom!r} (weaker cached "
                    "headroom is never reusable)")
        payload = stored.get("response_payload")
        digest = stored.get("response_sha256")
        if not isinstance(payload, str) or not isinstance(digest, str):
            return "USAGE_CACHE_BODY_MISSING"
        if hashlib.sha256(payload.encode()).hexdigest() != digest:
            return "USAGE_CACHE_BODY_ALTERED: payload digest mismatch"
        try:
            fields = parse_usage_body(payload.encode())
        except PreflightRefusal as e:
            return f"USAGE_CACHE_BODY_ALTERED: {e}"
        for name in ("current_usage", "plan_limit", "daily_usage",
                     "plan_daily_limit"):
            if fields[name] != stored.get(name):
                return ("USAGE_CACHE_BODY_ALTERED: payload fields "
                        "!= stored fields")
        if not fields["daily_present"]:
            return ("USAGE_CACHE_BODY_ALTERED: cached PASS lacks "
                    "the established daily pair")
        try:
            evaluate_daily_gate(fields, self.required_headroom)
            stored_headers = stored.get("credits_headers")
            reconcile_credit_headers(
                fields, stored_headers
                if isinstance(stored_headers, dict) else {})
        except PreflightRefusal as e:
            return str(e)
        req_ts = stored.get("request_ts_ms")
        rcpt_ts = stored.get("receipt_ts_ms")
        for v in (req_ts, rcpt_ts):
            if not isinstance(v, int) or isinstance(v, bool):
                return "USAGE_CACHE_TIMESTAMP: non-integer ts"
        if req_ts <= 0 or rcpt_ts < req_ts:
            return "USAGE_CACHE_TIMESTAMP: insane ts order"
        now_ms = int(self.clock() * 1000)
        if rcpt_ts > now_ms + FUTURE_SKEW_MS:
            return "USAGE_CACHE_TIMESTAMP: future-dated receipt"
        if now_ms - rcpt_ts > DAY_MS:
            return "USAGE_CACHE_TIMESTAMP: stale receipt (>1 day)"
        # -67 closure, retained: explicit UTC execution-date
        # binding. Age is not a date: reuse requires the stored
        # execution date to equal the UTC dates of the receipt's
        # own timestamps AND today's UTC date per the session
        # clock. Cross-midnight reuse (age < 24h) refuses here,
        # before any transport.
        exp_date = stored.get("execution_date_utc")
        if not isinstance(exp_date, str) or not exp_date:
            return "USAGE_CACHE_DATE: execution date missing"
        if exp_date != utc_date_string(req_ts) or \
                exp_date != utc_date_string(rcpt_ts):
            return ("USAGE_CACHE_DATE: execution date != receipt "
                    "timestamp dates")
        today = utc_date_string(now_ms)
        if exp_date != today:
            return (f"USAGE_CACHE_DATE: execution date {exp_date} "
                    f"!= today {today} (cross-day reuse refused; "
                    "vendor reset-zone semantics are an "
                    "execution-day unknown)")
        return None

    def __call__(self) -> list[str]:
        if self.receipt_path.exists():
            try:
                stored = json.loads(self.receipt_path.read_text())
            except Exception as e:
                return [f"USAGE_CACHE_MALFORMED: {e}"]
            if not isinstance(stored, dict):
                return ["USAGE_CACHE_MALFORMED: not an object"]
            reason = self._verify_body_file(stored)
            if reason is not None:
                return [reason]
            if stored.get("verdict") == "REFUSE":
                # Sticky refusal: bindings must still match this
                # session before the recorded reason is honored;
                # either way, no transport is used.
                if stored.get("manifest_sha256") != \
                        self.manifest_sha256 or \
                        stored.get("store_marker_sha256") != \
                        store_marker_sha256(self.store_marker) or \
                        stored.get("day") != self.day:
                    return ["USAGE_CACHE_BINDING: recorded refusal "
                            "bound to another manifest/store/day"]
                return [stored.get("terminal_reason")
                        or "USAGE_RECEIPT_INVALID"]
            reason = self._verify_cached(stored)
            if reason is not None:
                return [reason]
            self.receipt = stored
            return []
        try:
            receipt = self.preflight.check()
        except PreflightRefusal as e:
            if e.receipt is None:
                return [str(e)]
            receipt = e.receipt
        receipt = dict(receipt)
        receipt["day"] = self.day
        receipt["manifest_sha256"] = self.manifest_sha256
        receipt["store_marker_sha256"] = store_marker_sha256(
            self.store_marker)
        receipt["required_headroom"] = self.required_headroom
        try:
            self._persist_outcome(receipt)
        except OSError as e:
            return [f"USAGE_RECEIPT_PERSIST_FAILED: {e}"]
        self.receipt = receipt
        if receipt.get("verdict") == "PASS":
            return []
        return [receipt.get("terminal_reason")
                or "USAGE_RECEIPT_INVALID"]
