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
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

COHORT_LABEL = "SHADOW_OBSERVATION"
SCHEMA_VERSION = "shadow-signal-v2"
LOG_FILENAME = "shadow_log.jsonl"
MANIFEST_FILENAME = "launch_manifest.json"
GENESIS_DOMAIN = "shadow-chain-genesis-v2"

ET = ZoneInfo("America/New_York")
# The frozen V5.4 4H grid: bar opens at 09:30 and 13:30 ET.
GRID_OPEN_WALL = {(9, 30), (13, 30)}


class ShadowError(RuntimeError):
    """Fail-closed error: the observer refuses to proceed."""


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
                 clock: Optional[Callable[[], datetime]] = None):
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
        self._last_hash = self._genesis
        self._record_count = 0
        self.seen_signal_ids: set = set()
        self.signal_count = 0
        self._load_log()

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
            return recorded
        manifest = {
            "schema": SCHEMA_VERSION,
            "cohort": COHORT_LABEL,
            "counts_as_trade": False,
            "launch_t0_utc": launch_t0.astimezone(timezone.utc).isoformat(),
            "created_at_utc": self.clock().isoformat(),
            "mode": "signal_only",
            "simulated_fills": False,
        }
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
        start_et = start.astimezone(ET)
        if (start_et.hour, start_et.minute) not in GRID_OPEN_WALL:
            return "OFF_GRID_BAR_START"
        if close <= self.t0:
            return "PRELAUNCH_SIGNAL"
        if close > now:
            return "PARTIAL_BAR_NOT_CLOSED"
        return None

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
