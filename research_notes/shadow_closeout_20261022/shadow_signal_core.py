"""Shadow SIGNAL-ONLY observer core — successor to the task -80 design.

WHY THIS MODULE EXISTS (ChatGPT expedite review of -80, Issue #1
comment 6353427339): the -80 package's synthetic safety suite passed
6/6 but its runner was not deployable. Four blockers, and how this
successor closes each BY CONSTRUCTION:

  B1  -80's runner main() unconditionally raised "design-stage
      module" — no operational entrypoint existed.
      HERE: shadow_signal_runner.main() is a real entrypoint. It
      runs a dry-run mode on synthetic fixtures with no network, and
      its live mode is gated by a launch-authorization artifact
      (Mike's GO) instead of a blanket raise. The gate is an
      authorization check, not a missing entrypoint.

  B2  -80's observe_once() set health["market_ok"] = True
      unconditionally; build_frames() swallowed a market-frame
      failure and still labeled the cycle healthy — a blind cycle
      could read HEALTHY / no-signal.
      HERE: the core DEFAULTS market_ok to False when the binding
      does not positively supply it, and the runner derives
      market_ok from an actual market-frame fetch result. A blind
      or incomplete cycle is recorded DEGRADED with named reasons
      and records NO signals.

  B3  -80 never compared signal_bar_close_at to a frozen
      prospective launch instant: stale signals could be accepted
      on first launch (prohibited backfill) and a lifecycle could
      be simulated retrospectively.
      HERE: the launch watermark T0 is frozen into a launch
      manifest inside the shadow root at first initialization and
      can never move (reopening with a different T0 refuses). A
      signal is recorded only if its bar CLOSED strictly after T0
      and at or before the cycle instant (a bar that has not
      closed yet is a partial bar and is refused). Refusals are
      themselves appended as evidence records. Stage 1 simulates
      NOTHING, so there is no retrospective-fill surface at all.

  B4  -80's crash seam: a crash between the log append and the
      state save could mark a signal seen while its lifecycle was
      lost (state and log were separate artifacts).
      HERE: there is no state file. The append-only log is the
      ONLY record; the seen-set is rebuilt from the log at every
      startup, so a committed record can never be lost and can
      never be duplicated by a restart. A torn final line (an
      append interrupted mid-write) is detected at startup and
      truncated — it was never a committed record — and the
      recovery is itself logged.

SCOPE (stage 1, per the assignment): record the frozen strategy's
qualified signals, prospectively, as timestamped SHADOW_OBSERVATION
records with counts_as_trade = False. NO hypothetical entries, NO
exit simulation, NO fills of any kind. The pinned Mode B exit
tracker is deliberately NOT imported: there is nothing to simulate
at this gate. Lifecycle/hypothetical mode, if ever wanted, is a
separate later candidate with its own catch-up and crash-seam
tests.

ISOLATION: this module imports only the Python standard library.
Every write is rooted at the caller-supplied shadow root: the
launch manifest and the append-only log, nothing else. It opens
no production path and imports no production module.

Nothing in this file launches anything. Launch requires Mike's
explicit GO naming a prospective start instant (see
LAUNCH_READINESS.md).

REPAIR 2026-10-22 (V8, shadow_successor_repair_20261022 — candidate
copy; the 798de18 successor is untouched): the parity verification
(d5a4fe6, check V8) found 0/7 log records carrying any hash /
prev-hash field, and ChatGPT's source review (Issue #1 comment
6356126182) confirmed two further defects: _append() wrote no
chain fields at all, and _load_log() truncated from the FIRST
malformed line anywhere — so mid-log tampering could silently
erase later intact evidence. THIS COPY (schema shadow-signal-v2):

  * every record carries prev_hash + hash. The hash is sha256
    over (prev_hash + canonical JSON of the record without the
    two chain fields). The genesis prev-hash is sha256 over a
    domain string plus the launch-manifest bytes, binding the
    chain to the frozen T0 manifest.
  * startup verifies the ENTIRE chain before anything is
    appended. A hash/prev-hash mismatch anywhere, or an
    unparseable line anywhere except as the final line, refuses
    with ShadowError and alters NO bytes. Only a torn FINAL line
    (an append interrupted mid-write) is truncated, as before.
  * verify_chain() is the external first-cycle anchor procedure:
    it recomputes the chain from the manifest bytes and returns
    (records, genesis, tail_hash); check_anchor() compares a
    report against an externally recorded anchor. A hash chain
    alone cannot detect suffix truncation (deleting whole tail
    records leaves a self-consistent prefix) — the external
    anchor comparison is the control for that, and it is stated
    here rather than implied.
  * a v1 (unchained) log fails chain verification and refuses:
    this candidate has never launched, so no v1 log exists to
    migrate; refusing is the fail-closed reading.

CLOSEOUT 2026-10-22 (shadow_closeout_20261022 — candidate copy;
4130e74 repair and 798de18 successor untouched): ChatGPT's
independent verdict on the repair (Issue #1 comment 6356610693)
passed V5/V8 at source level and held launch on data/parity
items 3-4. THIS COPY (schema shadow-signal-v3) closes the two
code/test items, offline only:

  * MANIFEST PIN BINDING (verdict item 4): the launch manifest
    now carries the full frozen pin set from
    shadow_closeout_pins.EXPECTED_PINS — candidate commit,
    live-stack pins, candidate module hashes, ordered-universe
    digest + count, calendar version + session-table hash +
    session count, frozen rule version, and the authorization
    artifact slot (digest null, state NOT_AUTHORIZED — no
    authorization artifact exists or is created by this
    package). The manifest carries a manifest_digest (sha256
    over the canonical manifest without the digest field);
    startup recomputes it, requires the manifest pins to equal
    EXPECTED_PINS exactly, and requires the on-disk candidate
    module files to hash to the pinned module hashes — a
    swapped pin, an altered manifest byte, or a swapped module
    refuses fail-closed before any append. Every record
    appended carries manifest_digest, and the hash chain's
    genesis remains bound to the raw manifest bytes, so the
    digest is verified alongside the genesis binding.
  * SESSION-TABLE ADMISSION (verdict item 3): _validate_candidate
    no longer admits on bar-start wall + duration assumptions.
    Symbol class comes from the pinned universe artifact
    (universe.json, digest-verified at import). EQUITY bars are
    admitted iff (start, close) is exactly a bar of the pinned
    adopted session table (session_table.json — the 751-session
    XNYS union adopted 2026-10-21, hash-verified at import):
    ordinary sessions admit 09:30->13:30 and 13:30->16:00;
    13:00 early-close sessions admit exactly one bar,
    09:30->13:00; a non-session date refuses. CRYPTO bars never
    touch the equity table: admission is by the adopted
    S-C1..S-C6 continuous calendar — session [D 09:30 ET,
    D+1 09:30 ET), six wall-anchored 4H bins (09:30/13:30/
    17:30/21:30/01:30/05:30 ET, fold=0), the overnight 01:30
    bin absorbing DST (3 elapsed hours across spring-forward,
    5 across fall-back; session spans of 23/24/25 elapsed
    hours). Exact start AND end must match a bin.
  * EXTERNAL ANCHOR AT STARTUP: SignalObserver accepts
    anchor_path; when supplied, the anchor file must exist and
    equal the live chain anchor exactly or startup refuses —
    a missing anchor is a fail-closed refusal, not a warning.

Nothing here launches anything, wires a new adapter path, or
creates an authorization artifact. Launch remains HOLD (see
LAUNCH_READINESS.md).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, time, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shadow_closeout_pins as _pins  # noqa: E402

COHORT_LABEL = "SHADOW_OBSERVATION"
SCHEMA_VERSION = "shadow-signal-v3"
LOG_FILENAME = "shadow_log.jsonl"
MANIFEST_FILENAME = "launch_manifest.json"
GENESIS_DOMAIN = "shadow-chain-genesis-v3"

ET = ZoneInfo("America/New_York")
# The frozen V5.4 4H grid: bar opens at 09:30 and 13:30 ET.
GRID_OPEN_WALL = {(9, 30), (13, 30)}

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))


class ShadowError(RuntimeError):
    """Fail-closed error: the observer refuses to proceed."""


def _load_pinned_json(filename: str, expected_sha256: str) -> Any:
    """Load a package data artifact, refusing if its bytes do
    not hash to the pinned digest (fail-closed at import)."""
    path = os.path.join(_PKG_DIR, filename)
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except Exception as exc:
        raise ShadowError(f"pinned artifact unreadable: "
                          f"{filename}: {exc}")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise ShadowError(
            f"pinned artifact hash mismatch: {filename}: "
            f"{digest} != {expected_sha256}")
    return json.loads(raw.decode("utf-8"))


# Pinned session table (adopted 751-session XNYS union) and the
# pinned ordered universe + symbol classes, both digest-bound
# by shadow_closeout_pins.EXPECTED_PINS.
_SESSION_TABLE_DOC = _load_pinned_json(
    _pins.SESSION_TABLE_FILENAME,
    _pins.EXPECTED_PINS["calendar"]["session_table_sha256"])
SESSION_TABLE: Dict[str, str] = {
    s["date"]: s["close"] for s in _SESSION_TABLE_DOC["sessions"]}
if len(SESSION_TABLE) != _pins.EXPECTED_PINS["calendar"]["sessions"]:
    raise ShadowError("session table session-count mismatch vs pin")

_UNIVERSE_DOC = _load_pinned_json(
    _pins.UNIVERSE_FILENAME,
    _pins.EXPECTED_PINS["universe"]["file_sha256"])
ORDERED_UNIVERSE: List[str] = list(_UNIVERSE_DOC["ordered_universe"])
SYMBOL_CLASS: Dict[str, str] = dict(_UNIVERSE_DOC["symbol_class"])


def universe_digest(symbols: List[str]) -> str:
    """Canonical ordered-universe digest: sha256 over the
    LF-joined ordered symbols plus a trailing LF, UTF-8."""
    canon = ("\n".join(symbols) + "\n").encode("utf-8")
    return hashlib.sha256(canon).hexdigest()


def verify_universe_digest(symbols: List[str]) -> None:
    """Refuse unless a binding-supplied universe is exactly the
    pinned ordered universe (order matters: a reordered cohort
    is a different cohort)."""
    expected = _pins.EXPECTED_PINS["universe"]
    if len(symbols) != expected["count"] or \
            universe_digest(list(symbols)) != \
            expected["ordered_digest"]:
        raise ShadowError(
            "universe mismatch vs pinned ordered digest/count "
            "(changed membership or changed order) — refusing")


if universe_digest(ORDERED_UNIVERSE) != \
        _pins.EXPECTED_PINS["universe"]["ordered_digest"]:
    raise ShadowError("pinned universe artifact digest mismatch")


# -- session-table admission geometry -------------------------------

def _equity_session_bars(date_str: str):
    """The session's exact 4H bars [(start, close), ...] as UTC
    instants, from the pinned table; None if the date is not a
    session. Ordinary (16:00 close): 09:30->13:30 and
    13:30->16:00. Early close (13:00): exactly one bar,
    09:30->13:00 — admission is by table lookup, never by bar
    duration. Bars are returned in UTC because cross-tzinfo
    datetime equality is not instant equality in this runtime
    (see crypto_session_bins); all admission comparisons are
    made on UTC instants."""
    close_wall = SESSION_TABLE.get(date_str)
    if close_wall is None:
        return None
    y, m, d = (int(x) for x in date_str.split("-"))

    def at(hh, mm):
        return datetime(y, m, d, hh, mm, tzinfo=ET) \
            .astimezone(timezone.utc)

    if close_wall == "16:00":
        return [(at(9, 30), at(13, 30)), (at(13, 30), at(16, 0))]
    if close_wall == "13:00":
        return [(at(9, 30), at(13, 0))]
    raise ShadowError(
        f"session table malformed for {date_str}: "
        f"close {close_wall!r}")


_CRYPTO_BIN_WALLS = [(9, 30), (13, 30), (17, 30), (21, 30),
                     (1, 30), (5, 30)]


def _crypto_session_date(dt_et: datetime):
    """Session date owning an instant (S-C3, ET wall time):
    wall >= 09:30 -> same date, else the previous date."""
    if dt_et.time() >= time(9, 30):
        return dt_et.date()
    return dt_et.date() - timedelta(days=1)


def crypto_session_span_hours(session_date) -> float:
    """Elapsed hours of the [D 09:30 ET, D+1 09:30 ET) span:
    23 across spring-forward, 25 across fall-back, else 24.
    Computed on UTC instants — subtracting two datetimes that
    share one tzinfo object is wall-clock arithmetic in Python
    and would read 24.0 across a transition."""
    start = datetime.combine(session_date, time(9, 30),
                             tzinfo=ET).astimezone(timezone.utc)
    end = datetime.combine(session_date + timedelta(days=1),
                           time(9, 30), tzinfo=ET) \
        .astimezone(timezone.utc)
    return (end - start).total_seconds() / 3600.0


def crypto_session_bins(session_date):
    """The session's six 4H bins [(start, close), ...] as UTC
    instants: wall-anchored ET starts 09:30/13:30/17:30/
    21:30/01:30/05:30 (fold=0), each bin closing at the next
    bin's start, the last at the next session's 09:30. The
    01:30 overnight bin absorbs DST: 3 elapsed hours on the
    spring session, 5 on the fall session (S-C1..S-C6).

    Bins are UTC instants, not ET datetimes, because of a
    measured runtime behavior: across the fall-back repeated
    hour, an ET datetime and a fixed-offset datetime for the
    SAME instant (equal timestamps, equal hashes, zero
    difference) compare UNEQUAL with == in CPython — the
    first draft of this function returned ET datetimes and
    its own DST fixtures refused every fall-session bin.
    All admission comparisons therefore run on UTC instants
    (the same discipline as the -94 session model)."""
    starts = []
    for i, (hh, mm) in enumerate(_CRYPTO_BIN_WALLS):
        day = session_date + timedelta(days=1) if i >= 4 \
            else session_date
        starts.append(datetime.combine(day, time(hh, mm),
                                       tzinfo=ET)
                      .astimezone(timezone.utc))
    end = datetime.combine(session_date + timedelta(days=1),
                           time(9, 30), tzinfo=ET) \
        .astimezone(timezone.utc)
    return [(starts[i], starts[i + 1] if i < 5 else end)
            for i in range(6)]


def _parse_ts(value: Any) -> Optional[datetime]:
    """Parse an ISO timestamp; None unless it is tz-aware."""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        return None
    return dt


def _canonical(record: Dict[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"),
                      default=str)


def _record_hash(prev_hash: str, body: Dict[str, Any]) -> str:
    """sha256 over prev_hash + canonical JSON of the record body
    (the record WITHOUT its two chain fields)."""
    return hashlib.sha256(
        (prev_hash + "\n" + _canonical(body)).encode("utf-8")
    ).hexdigest()


def _genesis_seed(manifest_bytes: bytes) -> str:
    """The chain's genesis prev-hash: binds the chain to the exact
    launch-manifest bytes (and therefore to the frozen T0)."""
    return hashlib.sha256(
        GENESIS_DOMAIN.encode("utf-8") + b"\n" + manifest_bytes
    ).hexdigest()


def _manifest_digest(manifest: Dict[str, Any]) -> str:
    """sha256 over the canonical JSON of the manifest WITHOUT
    its manifest_digest field. Any altered value in the
    manifest — a swapped pin, a moved T0, a changed timestamp —
    changes this digest."""
    body = {k: v for k, v in manifest.items()
            if k != "manifest_digest"}
    return hashlib.sha256(
        _canonical(body).encode("utf-8")).hexdigest()


def _module_file_hashes() -> Dict[str, str]:
    """sha256 of the candidate module files as they lie on disk
    next to this module (the files the manifest pins)."""
    out = {}
    for name in _pins.EXPECTED_PINS["module_hashes"]:
        path = os.path.join(_PKG_DIR, name)
        try:
            with open(path, "rb") as fh:
                out[name] = hashlib.sha256(fh.read()).hexdigest()
        except Exception as exc:
            raise ShadowError(
                f"candidate module unreadable: {name}: {exc}")
    return out


def _verify_manifest(manifest: Dict[str, Any]) -> None:
    """Fail-closed manifest verification, run at every startup
    alongside the hash-chain genesis binding: (1) the stored
    manifest_digest recomputes exactly; (2) the manifest's pin
    set equals shadow_closeout_pins.EXPECTED_PINS exactly —
    any swapped, added, or dropped pin refuses; (3) the
    candidate module files on disk hash to the pinned module
    hashes — a swapped module refuses even with an intact
    manifest."""
    stored = manifest.get("manifest_digest")
    if not stored or _manifest_digest(manifest) != stored:
        raise ShadowError(
            "launch manifest digest mismatch — a manifest byte "
            "or value was altered after creation; refusing")
    if manifest.get("pins") != _pins.EXPECTED_PINS:
        raise ShadowError(
            "launch manifest pin set does not equal the frozen "
            "EXPECTED_PINS — a pin was swapped, added, or "
            "dropped; refusing")
    if _module_file_hashes() != \
            _pins.EXPECTED_PINS["module_hashes"]:
        raise ShadowError(
            "candidate module files on disk do not hash to the "
            "pinned module hashes — a module was swapped; "
            "refusing")


def load_anchor_file(anchor_path: str) -> Dict[str, Any]:
    """Load an externally recorded chain anchor. A missing or
    malformed anchor is a fail-closed refusal, never a
    warning: without the anchor, suffix truncation of the log
    is undetectable."""
    if not os.path.exists(anchor_path):
        raise ShadowError(
            f"external anchor missing at {anchor_path} — "
            "refusing (the anchor is the suffix-truncation "
            "control)")
    try:
        with open(anchor_path, encoding="utf-8") as fh:
            anchor = json.load(fh)
    except Exception as exc:
        raise ShadowError(f"external anchor unreadable: {exc}")
    if not all(k in anchor for k in
               ("genesis", "records", "tail_hash")):
        raise ShadowError(
            "external anchor malformed: needs genesis, records, "
            "tail_hash")
    return anchor


def verify_chain(log_path: str, manifest_path: str) -> Dict[str, Any]:
    """External anchor procedure (no observer state required).

    Recomputes the hash chain from the genesis seed derived from
    the launch-manifest bytes and verifies every record's
    prev_hash linkage and record hash. Returns a report:
    {ok, records, genesis, tail_hash, failures}. Compare the
    report against an externally recorded anchor with
    check_anchor(): the chain alone cannot detect suffix
    truncation, so (records, tail_hash) must be pinned outside
    the log after cycles whose evidence matters.
    """
    report: Dict[str, Any] = {"ok": False, "records": 0,
                              "genesis": None, "tail_hash": None,
                              "failures": []}
    try:
        with open(manifest_path, "rb") as fh:
            genesis = _genesis_seed(fh.read())
    except Exception as exc:
        report["failures"].append(f"manifest unreadable: {exc}")
        return report
    report["genesis"] = genesis
    if not os.path.exists(log_path):
        report["failures"].append("log missing")
        return report
    prev = genesis
    count = 0
    with open(log_path, "rb") as fh:
        lines = fh.read().split(b"\n")
    if lines and lines[-1] == b"":
        lines = lines[:-1]
    for i, line in enumerate(lines):
        try:
            rec = json.loads(line.decode("utf-8"))
        except Exception:
            report["failures"].append(f"record {i}: unparseable")
            break
        if rec.get("prev_hash") != prev:
            report["failures"].append(
                f"record {i}: prev_hash mismatch")
            break
        body = {k: v for k, v in rec.items()
                if k not in ("hash", "prev_hash")}
        if _record_hash(prev, body) != rec.get("hash"):
            report["failures"].append(f"record {i}: hash mismatch")
            break
        prev = rec["hash"]
        count += 1
    report["records"] = count
    report["tail_hash"] = prev if count else None
    report["ok"] = not report["failures"] and count == len(lines)
    return report


def check_anchor(report: Dict[str, Any],
                 anchor: Dict[str, Any]) -> bool:
    """True iff a verify_chain report matches an externally
    recorded anchor {genesis, records, tail_hash} exactly. This
    is the suffix-truncation control: deleting whole tail records
    leaves a self-consistent shorter chain whose (records,
    tail_hash) no longer matches the anchor."""
    return bool(report.get("ok")) and \
        report.get("genesis") == anchor.get("genesis") and \
        report.get("records") == anchor.get("records") and \
        report.get("tail_hash") == anchor.get("tail_hash")


class SignalObserver:
    """Append-only prospective signal recorder (one shadow root).

    root: the shadow namespace directory — the ONLY directory this
    object writes to. launch_t0: the frozen prospective watermark
    (tz-aware). A signal is recordable only if its bar closed
    strictly after launch_t0. clock: injectable for tests.
    """

    def __init__(self, root: str, launch_t0: datetime,
                 clock: Optional[Callable[[], datetime]] = None,
                 anchor_path: Optional[str] = None):
        if launch_t0.tzinfo is None or launch_t0.utcoffset() is None:
            raise ShadowError("launch T0 must be tz-aware")
        self.root = os.path.abspath(root)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.log_path = os.path.join(self.root, LOG_FILENAME)
        self.manifest_path = os.path.join(self.root, MANIFEST_FILENAME)
        os.makedirs(self.root, exist_ok=True)
        self.t0 = self._init_manifest(launch_t0)
        with open(self.manifest_path, "rb") as fh:
            self._genesis = _genesis_seed(fh.read())
        with open(self.manifest_path, encoding="utf-8") as fh:
            self._manifest_digest = \
                json.load(fh)["manifest_digest"]
        self._last_hash = self._genesis
        self._record_count = 0
        self.seen_signal_ids: set = set()
        self.signal_count = 0
        self._load_log()
        if anchor_path is not None:
            anchor = load_anchor_file(anchor_path)
            if anchor != self.chain_anchor:
                raise ShadowError(
                    "external anchor does not match the live "
                    "chain anchor — the log's tail may have "
                    "been truncated or the anchor is stale; "
                    "refusing")

    @property
    def chain_anchor(self) -> Dict[str, Any]:
        """The external anchor for the log as it stands now:
        record it outside the log to make suffix truncation
        detectable (see verify_chain / check_anchor)."""
        return {"genesis": self._genesis,
                "records": self._record_count,
                "tail_hash": self._last_hash}

    # -- launch manifest: the frozen watermark ----------------------

    def _init_manifest(self, launch_t0: datetime) -> datetime:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, encoding="utf-8") as fh:
                    manifest = json.load(fh)
            except Exception as exc:
                raise ShadowError(f"launch manifest unreadable: {exc}")
            if manifest.get("cohort") != COHORT_LABEL:
                raise ShadowError("launch manifest cohort mismatch")
            recorded = _parse_ts(manifest.get("launch_t0_utc"))
            if recorded is None:
                raise ShadowError("launch manifest T0 unparseable")
            if recorded != launch_t0:
                raise ShadowError(
                    "launch T0 is frozen at first initialization "
                    f"({recorded.isoformat()}); refusing a different "
                    f"T0 ({launch_t0.isoformat()}) — a moved watermark "
                    "would admit backfill")
            _verify_manifest(manifest)
            return recorded
        # Creation: the candidate's own module files must hash
        # to the frozen pins before any manifest is written —
        # a candidate whose code moved after pinning cannot
        # initialize a root at all.
        if _module_file_hashes() != \
                _pins.EXPECTED_PINS["module_hashes"]:
            raise ShadowError(
                "candidate module files do not hash to the "
                "frozen module pins — refusing to create a "
                "launch manifest")
        manifest = {
            "schema": SCHEMA_VERSION,
            "cohort": COHORT_LABEL,
            "counts_as_trade": False,
            "launch_t0_utc": launch_t0.astimezone(timezone.utc).isoformat(),
            "created_at_utc": self.clock().isoformat(),
            "mode": "signal_only",
            "simulated_fills": False,
            "pins": json.loads(json.dumps(_pins.EXPECTED_PINS)),
        }
        manifest["manifest_digest"] = _manifest_digest(manifest)
        tmp = self.manifest_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.manifest_path)
        return launch_t0

    # -- the log is the only state -----------------------------------

    def _load_log(self) -> None:
        """Rebuild the seen-set from the log; verify the hash
        chain; repair ONLY a torn tail.

        Fail-closed startup tamper check (V8 repair): every
        complete record's prev_hash linkage and record hash are
        recomputed from the genesis seed before anything is
        appended. A mismatch anywhere — or an unparseable line
        anywhere except as the FINAL line — raises ShadowError
        and alters no bytes: mid-log corruption is tamper
        evidence, not a torn write, and truncating from the first
        bad line (the v1 behavior) would silently erase later
        intact records. A final line that does not parse is the
        tail of an append interrupted mid-write: it was never a
        committed record, so the file is truncated back to the
        last complete record and the recovery is itself logged
        as a chained record.
        """
        if not os.path.exists(self.log_path):
            return
        with open(self.log_path, "rb") as fh:
            lines = fh.read().split(b"\n")
        if lines and lines[-1] == b"":
            lines = lines[:-1]
        parsed: List[Dict[str, Any]] = []
        offsets: List[int] = []
        offset = 0
        torn_index: Optional[int] = None
        for i, line in enumerate(lines):
            offset += len(line) + 1
            offsets.append(offset)
            try:
                parsed.append(json.loads(line.decode("utf-8")))
            except Exception:
                torn_index = i
                break
        if torn_index is not None and torn_index != len(lines) - 1:
            raise ShadowError(
                f"shadow log corrupt at record {torn_index} with "
                f"{len(lines) - torn_index - 1} further line(s) "
                "after it — mid-log corruption is not a torn tail; "
                "refusing and altering no bytes (possible tamper)")
        prev = self._genesis
        for i, rec in enumerate(parsed):
            if rec.get("prev_hash") != prev or not rec.get("hash"):
                raise ShadowError(
                    f"shadow log hash-chain verification failed at "
                    f"record {i}: prev_hash missing or mismatched "
                    "(tampered record, or a legacy unchained v1 "
                    "log) — refusing")
            body = {k: v for k, v in rec.items()
                    if k not in ("hash", "prev_hash")}
            if _record_hash(prev, body) != rec["hash"]:
                raise ShadowError(
                    f"shadow log hash-chain verification failed at "
                    f"record {i}: record hash mismatch (tampered "
                    "record) — refusing")
            prev = rec["hash"]
            if rec.get("record_kind") == "shadow_signal":
                sid = rec.get("shadow_id")
                if sid:
                    self.seen_signal_ids.add(sid)
                    self.signal_count += 1
        self._last_hash = prev
        self._record_count = len(parsed)
        if torn_index is not None:
            good_offset = offsets[torn_index - 1] if torn_index else 0
            with open(self.log_path, "r+b") as fh:
                fh.truncate(good_offset)
            self._append({
                "event": "torn_tail_recovered",
                "detail": "an interrupted append left an incomplete "
                          "final line; it was truncated because it "
                          "was never a committed record",
            }, "shadow_recovery", self.clock())

    def _append(self, record: Dict[str, Any], kind: str,
                now: datetime) -> Dict[str, Any]:
        rec = dict(record)
        rec["record_kind"] = kind
        rec["schema"] = SCHEMA_VERSION
        rec["cohort"] = COHORT_LABEL
        rec["counts_as_trade"] = False
        rec["manifest_digest"] = self._manifest_digest
        rec["logged_at"] = now.isoformat()
        if rec.get("cohort") != COHORT_LABEL or \
                rec.get("counts_as_trade") is not False:
            raise ShadowError("refusing to write an unlabeled record")
        rec["prev_hash"] = self._last_hash
        body = {k: v for k, v in rec.items() if k != "prev_hash"}
        rec["hash"] = _record_hash(self._last_hash, body)
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._last_hash = rec["hash"]
        self._record_count += 1
        return rec

    # -- signal validation (the B3 gate) ------------------------------

    def _validate_candidate(self, row: Dict[str, Any],
                            now: datetime) -> Optional[str]:
        """None if recordable, else the named refusal reason."""
        if not row.get("signal_id") or not row.get("symbol"):
            return "MALFORMED_SIGNAL_ROW"
        start = _parse_ts(row.get("signal_bar_start_at"))
        close = _parse_ts(row.get("signal_bar_close_at"))
        if start is None or close is None:
            return "TZ_NAIVE_OR_UNPARSEABLE_STAMPS"
        if close <= start:
            return "BAR_CLOSE_NOT_AFTER_START"
        reason = self._session_admission(row.get("symbol"),
                                         start, close)
        if reason is not None:
            return reason
        if close <= self.t0:
            return "PRELAUNCH_SIGNAL"
        if close > now:
            return "PARTIAL_BAR_NOT_CLOSED"
        return None

    @staticmethod
    def _session_admission(symbol: Any, start: datetime,
                           close: datetime) -> Optional[str]:
        """Exact symbol-class start/end admission (closeout).

        EQUITY: (start, close) must be exactly a bar of the
        pinned session table for the bar's ET date — ordinary
        sessions 09:30->13:30 / 13:30->16:00, 13:00 early-close
        sessions the single 09:30->13:00 bar. Admission is by
        table lookup, never by duration: a 09:30->13:30 bar on
        an early-close day refuses (SESSION_TABLE_CLOSE_MISMATCH)
        even though its duration matches an ordinary first bar.
        CRYPTO: the equity table is never consulted; (start,
        close) must be exactly one of the six S-C bins of the
        continuous [09:30 ET, +09:30 ET) session owning the
        bar's start."""
        cls = SYMBOL_CLASS.get(symbol)
        if cls is None:
            return "SYMBOL_CLASS_UNKNOWN"
        # All comparisons on UTC instants (see crypto_session_bins
        # for the measured cross-tzinfo equality failure).
        start_utc = start.astimezone(timezone.utc)
        close_utc = close.astimezone(timezone.utc)
        if cls == "crypto":
            session_date = _crypto_session_date(
                start.astimezone(ET))
            bins = crypto_session_bins(session_date)
            if (start_utc, close_utc) in bins:
                return None
            if any(start_utc == b[0] for b in bins):
                return "CRYPTO_BIN_CLOSE_MISMATCH"
            return "CRYPTO_BIN_START_MISMATCH"
        bars = _equity_session_bars(
            start.astimezone(ET).date().isoformat())
        if bars is None:
            return "NON_SESSION_DATE"
        if (start_utc, close_utc) in bars:
            return None
        if any(start_utc == b[0] for b in bars):
            return "SESSION_TABLE_CLOSE_MISMATCH"
        return "OFF_GRID_BAR_START"

    # -- one cycle ------------------------------------------------------

    def run_cycle(self, candidates: List[Dict[str, Any]],
                  health: Optional[Dict[str, Any]] = None,
                  now: Optional[datetime] = None) -> Dict[str, Any]:
        """Run one observation cycle.

        health (binding-supplied, defaults are fail-closed):
          market_ok: must be positively True — the market frame was
            actually fetched this cycle. Absent/False = blind.
          scan_complete: the frozen scan covered the full cohort.
          degraded_symbols: symbols the binding could not serve.
        A blind or incomplete cycle is recorded DEGRADED with named
        reasons and records NO signals and NO refusals — degraded
        data is never reinterpreted.
        """
        now = now or self.clock()
        health = health or {}
        market_ok = health.get("market_ok") is True
        scan_complete = health.get("scan_complete") is True
        degraded_symbols = sorted(health.get("degraded_symbols") or [])
        reasons = []
        if not market_ok:
            reasons.append("MARKET_FRAME_NOT_OK")
        if not scan_complete:
            reasons.append("SCAN_INCOMPLETE")
        if degraded_symbols:
            reasons.append("DEGRADED_SYMBOLS")
        healthy = not reasons

        recorded, refused, duplicates = 0, [], 0
        if healthy:
            for row in candidates:
                sid = "shadow:" + str(row.get("signal_id"))
                if sid in self.seen_signal_ids:
                    duplicates += 1
                    continue
                reason = self._validate_candidate(row, now)
                if reason is not None:
                    refused.append({"signal_id": row.get("signal_id"),
                                    "symbol": row.get("symbol"),
                                    "reason": reason})
                    self._append({
                        "shadow_id": sid,
                        "source_signal_id": row.get("signal_id"),
                        "symbol": row.get("symbol"),
                        "reason": reason,
                        "signal_bar_start_at":
                            row.get("signal_bar_start_at"),
                        "signal_bar_close_at":
                            row.get("signal_bar_close_at"),
                        "launch_t0_utc": self.t0.isoformat(),
                    }, "shadow_refusal", now)
                    continue
                self._append({
                    "shadow_id": sid,
                    "source_signal_id": row["signal_id"],
                    "symbol": row["symbol"],
                    "grade": row.get("v54_grade"),
                    "signal_bar_start_at":
                        row["signal_bar_start_at"],
                    "signal_bar_close_at":
                        row["signal_bar_close_at"],
                    "detected_at_utc": now.isoformat(),
                    "launch_t0_utc": self.t0.isoformat(),
                    "stop": row.get("stop"),
                    "tp1": row.get("tp1"),
                    "market_gate": row.get("market_gate"),
                    "snapshot": {
                        k: row.get(k) for k in (
                            "symbol", "theme", "timeframe",
                            "signal_bar_start_at", "signal_bar_close_at",
                            "state", "entry", "price", "stop", "tp1",
                            "risk_reward", "market_gate",
                            "market_regime", "daily_trend",
                            "weekly_trend", "rel_vol", "adx",
                            "v54_grade", "v54_rule_version")
                    },
                }, "shadow_signal", now)
                self.seen_signal_ids.add(sid)
                self.signal_count += 1
                recorded += 1

        summary = {
            "status": "HEALTHY" if healthy else "DEGRADED",
            "degraded_reasons": reasons,
            "market_ok": market_ok,
            "scan_complete": scan_complete,
            "degraded_symbols": degraded_symbols,
            "candidates_seen": len(candidates),
            "new_signals_recorded": recorded,
            "signals_refused": refused,
            "duplicates_skipped": duplicates,
            "total_signals_recorded": self.signal_count,
            "launch_t0_utc": self.t0.isoformat(),
            "at_utc": now.isoformat(),
        }
        self._append(summary, "shadow_cycle", now)
        return summary
