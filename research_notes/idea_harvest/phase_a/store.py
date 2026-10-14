#!/usr/bin/env python3
"""Phase A idea-intake store — QF-IDEA-PIPELINE-PHASE-A-20261013-01 r1.

Schema/store ONLY, per PHASE1_DESIGN_PACKAGE_20261013.md as amended by the
Phase A review fixes (Issue #1 comment 6155160682):

- immutable idea cards with `access_basis` (never an inferred `license`),
  canonical-text content hash + extractor version recorded;
- append-only, hash-chained JSONL event log with crash-safe writes
  (single line append + flush + fsync; an unterminated final line is
  terminated before appending, never merged into the new record);
- safe atomic lease (O_CREAT|O_EXCL lockfile; stale break is logged) with a
  fencing token: every mutation re-reads the lockfile and refuses to write
  unless the caller still owns the lease, so a displaced owner whose stale
  lock was broken can no longer write;
- startup reconciliation under the lease, fenced like every other
  mutation (lease verified before any reconciliation write or file move;
  a quarantine is logged before the card is moved, so the order survives
  crashes): a card left orphaned by a crash between its (fsynced) write
  and its INGESTED/MIGRATED event is adopted deterministically (INGESTED
  event marked recovered_orphan) or quarantined;
- UUID-based run/event IDs (unique per attempt without coordination);
  the run association of every event is recorded in its `run_id` field;
- deterministic draft + family-ledger materializers (pure functions of the
  log + a pinned registry read; byte-stable for identical inputs);
- NO automated semantic verdict — dedupe produces matches or ADJACENCY_FLAGs
  for human confirmation, never a semantic same/different judgment;
- separate queue and registry state vocabularies (state_mapping.json).

Hard bounds enforced mechanically: no network code exists in this module;
no registry write path exists (any attempt raises ScopeViolation); the only
terminal success state is SHORTLISTED; transitions to PREREGISTERED /
ELIGIBLE are refused.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

STORE_VERSION = "phase-a-store/1.2.0"
EXTRACTOR_VERSION = "canon-extract/1.0.0"
GENESIS_HASH = "sha256:" + "0" * 64
STALE_LOCK_SECONDS = 2 * 3600

QUEUE_STATES = ["DISCOVERED", "INGESTED", "RANKED", "SHORTLISTED",
                "REJECTED", "BLOCKED-DATA", "PARKED"]
TERMINAL_STATES = {"SHORTLISTED", "REJECTED"}
FORBIDDEN_TARGETS = {"PREREGISTERED", "ELIGIBLE"}

# Legal transitions: (from_state, to_state) -> required event_type.
LEGAL_TRANSITIONS = {
    ("DISCOVERED", "INGESTED"): "INGESTED",
    ("INGESTED", "REJECTED"): "DEDUPE_REJECT",
    ("INGESTED", "RANKED"): "RANKED",
    ("INGESTED", "BLOCKED-DATA"): "BLOCKED",
    ("INGESTED", "PARKED"): "PARKED",
    ("RANKED", "SHORTLISTED"): "SHORTLISTED",
    ("RANKED", "PARKED"): "PARKED",
    ("RANKED", "BLOCKED-DATA"): "BLOCKED",
    ("BLOCKED-DATA", "PARKED"): "PARKED",
    ("BLOCKED-DATA", "INGESTED"): "RECHECKED",
    ("PARKED", "INGESTED"): "RECHECKED",
}
EVENT_TYPES = {
    "RUN_START", "RUN_END", "INGESTED", "DEDUPE_PASS", "DEDUPE_REJECT",
    "RANKED", "SHORTLISTED", "REJECTED", "BLOCKED", "PARKED", "RECHECKED",
    "SOURCE_DOWN", "DUPLICATE_SEEN", "ADJACENCY_FLAG", "LOCK_BROKEN",
    "MIGRATED", "ERROR",
}


class StoreError(Exception):
    pass


class CardValidationError(StoreError):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("card validation failed: " + "; ".join(self.errors))


class IllegalTransitionError(StoreError):
    pass


class ScopeViolation(StoreError):
    pass


class LeaseHeldError(StoreError):
    pass


class FencingError(StoreError):
    """A mutation was attempted without currently owning the lease."""


class ChainVerificationError(StoreError):
    pass


# --------------------------------------------------------------------------
# Canonical text + hashes
# --------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def canonical_text(raw: str) -> str:
    """Canonical text for content hashing (canon-extract/1.0.0).

    Deterministic and fetch-stable: strip markup tags, NFC-normalize,
    casefold, collapse all whitespace runs to single spaces, trim. Raw HTML
    bytes are never hashed (ads/timestamps would break idempotency).
    """
    if raw is None:
        return ""
    text = _TAG_RE.sub(" ", str(raw))
    text = unicodedata.normalize("NFC", text).casefold()
    return _WS_RE.sub(" ", text).strip()


def content_hash(title: str, body: str) -> str:
    canon = canonical_text(title) + "\n" + canonical_text(body)
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


def normalize_claim(claim: str) -> str:
    text = unicodedata.normalize("NFC", claim or "").casefold()
    text = re.sub(r"[^\w\s]", " ", text)
    return _WS_RE.sub(" ", text).strip()


def primary_source_key(source: dict) -> str:
    doi = (source.get("doi") or "").strip()
    if doi:
        return "doi:" + doi.casefold()
    url = (source.get("url") or "").strip()
    return "url:" + url.rstrip("/").casefold()


def dedup_key(claim_normalized: str, source: dict) -> str:
    payload = claim_normalized + "|" + primary_source_key(source)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_event_json(core: dict) -> str:
    return json.dumps(core, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def _event_hash(prev_hash: str, core: dict) -> str:
    payload = prev_hash + "|" + _canonical_event_json(core)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _pid_alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


# --------------------------------------------------------------------------
# Seed / sources / mapping loaders
# --------------------------------------------------------------------------

def _load_json(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def killed_seed_index(seed: dict) -> dict:
    """family -> seed entry (mechanical lookup only)."""
    idx = {}
    for entry in seed.get("entries", []):
        for fam in entry.get("families", []):
            idx[fam] = entry
    return idx


def source_class_index(sources: dict) -> dict:
    return {s["id"]: s for s in sources.get("sources", [])}


# --------------------------------------------------------------------------
# Card validation
# --------------------------------------------------------------------------

REQUIRED_CARD_FIELDS = [
    "idea_id", "dedup_key", "claim", "claim_normalized", "hypothesis",
    "strategy_family", "timeframe", "mechanically_definable", "pit_data",
    "source", "limitations", "lane_fit", "created_at", "created_by",
]
REQUIRED_SOURCE_FIELDS = [
    "authors", "title", "venue", "url", "accessed_at", "access_basis",
    "evidence", "content_hash", "extractor_version", "is_primary",
    "source_class",
]


def validate_card(card: dict, sources_idx: dict, *, new_intake: bool) -> list:
    """Return a list of validation errors (empty = valid).

    new_intake=True enforces the Phase A review fixes for fresh cards:
    access_basis mandatory, `license` key forbidden, canonical content hash
    present with extractor version, PARKED-SOURCE primaries refused,
    secondary classes may not be primary, non-empty limitations.
    Migrated historical cards (new_intake=False) may carry the documented
    nulls (content_hash_note / source.url_note) but never a `license` key.
    """
    errors = []
    for field in REQUIRED_CARD_FIELDS:
        if field not in card or card[field] in (None, ""):
            errors.append(f"missing required field: {field}")
    src = card.get("source") or {}
    if "license" in src:
        errors.append("source.license is forbidden: record access_basis, "
                      "never an inferred license")
    for field in REQUIRED_SOURCE_FIELDS:
        if field not in src:
            errors.append(f"missing required source field: {field}")
    if not card.get("limitations"):
        errors.append("limitations must be a non-empty list")
    tf = (card.get("timeframe") or "").strip().casefold()
    if tf in ("", "unspecified"):
        errors.append("timeframe must be named (v1 intake rule)")
    if card.get("pit_data") == "yes" and not card.get("pit_inputs"):
        errors.append("pit_data=yes requires pit_inputs")
    if new_intake:
        if not src.get("access_basis"):
            errors.append("source.access_basis is required for new intake")
        if src.get("is_primary") is not True:
            errors.append("source.is_primary must be true for new intake: "
                          "a claim not verifiable from a primary source is "
                          "dropped at intake, not carded")
        if not src.get("content_hash"):
            errors.append("source.content_hash (canonical text) is required "
                          "for new intake")
        if src.get("extractor_version") != EXTRACTOR_VERSION:
            errors.append("source.extractor_version must record the "
                          f"extractor used ({EXTRACTOR_VERSION})")
        if not src.get("url"):
            errors.append("source.url is required for new intake")
        cls = sources_idx.get(src.get("source_class", ""))
        if cls is None:
            errors.append(f"unknown source_class: {src.get('source_class')}")
        else:
            if cls.get("status") == "PARKED-SOURCE":
                errors.append(
                    f"SOURCE_PARKED: {cls['id']} is PARKED-SOURCE until a "
                    "primary source replaces the summary/mirror")
            if cls.get("role") == "secondary-only" and src.get("is_primary"):
                errors.append("secondary source classes may support a card "
                              "but never serve as its primary")
        # dedup key must recompute exactly (no hand-written keys)
        want = dedup_key(card.get("claim_normalized", ""), src)
        if card.get("dedup_key") != want:
            errors.append("dedup_key does not recompute from "
                          "claim_normalized + primary source key")
    return errors


# --------------------------------------------------------------------------
# The store
# --------------------------------------------------------------------------

class Store:
    """Single-writer, append-only idea store rooted at a directory.

    Layout:
        ideas/IDEA-*.json            immutable cards (write-once)
        queue/queue_log.jsonl        hash-chained event log (system of record)
        drafts/intake_draft_*.json   materialized drafts (regenerable)
        ledger/family_ledger.json    materialized family ledger (regenerable)
        pipeline.lock                lease file (present only during a run)
    """

    def __init__(self, root, phase_a_dir=None, clock=None):
        self.root = Path(root)
        self.phase_a_dir = Path(phase_a_dir) if phase_a_dir else Path(__file__).parent
        self.clock = clock or utc_now_iso
        self._lease = None  # (run_id, lock_path, fence_token)
        seed_path = self.phase_a_dir / "killed_ideas_seed.json"
        src_path = self.phase_a_dir / "sources.json"
        self.seed = _load_json(seed_path) if seed_path.exists() else {"entries": []}
        self.sources = _load_json(src_path) if src_path.exists() else {"sources": []}
        self.seed_idx = killed_seed_index(self.seed)
        self.sources_idx = source_class_index(self.sources)

    # -- layout ------------------------------------------------------------
    @property
    def ideas_dir(self):
        return self.root / "ideas"

    @property
    def queue_dir(self):
        return self.root / "queue"

    @property
    def log_path(self):
        return self.queue_dir / "queue_log.jsonl"

    @property
    def drafts_dir(self):
        return self.root / "drafts"

    @property
    def ledger_dir(self):
        return self.root / "ledger"

    @property
    def lock_path(self):
        return self.root / "pipeline.lock"

    def init_layout(self):
        for d in (self.ideas_dir, self.queue_dir, self.drafts_dir,
                  self.ledger_dir):
            d.mkdir(parents=True, exist_ok=True)
        # Create-if-absent, NEVER truncating: O_CREAT without O_TRUNC is
        # a no-op when the log already exists, so concurrent init_layout
        # calls (which run pre-lease, in every process) adopt the existing
        # log instead of racing a check-then-create that could reset it —
        # including the interleave where one process checks while another
        # has already created the log and begun appending.
        fd = os.open(self.log_path,
                     os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o644)
        os.close(fd)

    # -- log reading / chain ------------------------------------------------
    def read_events(self):
        if not self.log_path.exists():
            return []
        events = []
        with open(self.log_path, "r", encoding="utf-8") as fh:
            for n, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ChainVerificationError(
                        f"queue log line {n}: unparsable JSON ({exc}); "
                        "the log is corrupt (e.g. a torn write) and is "
                        "never silently repaired")
        return events

    def verify_chain(self, events=None):
        """Recompute the whole hash chain. Raises ChainVerificationError."""
        events = self.read_events() if events is None else events
        prev = GENESIS_HASH
        for i, ev in enumerate(events):
            if ev.get("prev_event_hash") != prev:
                raise ChainVerificationError(
                    f"event {ev.get('event_id')} (line {i + 1}): "
                    "prev_event_hash mismatch")
            core = {k: v for k, v in ev.items()
                    if k not in ("prev_event_hash", "event_hash")}
            want = _event_hash(prev, core)
            if ev.get("event_hash") != want:
                raise ChainVerificationError(
                    f"event {ev.get('event_id')} (line {i + 1}): "
                    "event_hash mismatch (log tampered or corrupt)")
            prev = ev["event_hash"]
        return prev

    def _tail(self, events):
        if not events:
            return GENESIS_HASH, 0
        return events[-1]["event_hash"], len(events)

    # -- lease ---------------------------------------------------------------
    def _create_lock(self, payload):
        fd = os.open(self.lock_path,
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
            fh.flush()
            os.fsync(fh.fileno())

    def acquire_lease(self, run_id, *, break_stale=True):
        """Take the single-writer lease atomically (O_CREAT|O_EXCL).

        The lock payload carries a random fencing token. Every mutation
        re-reads the lockfile and writes only while the token still matches
        (see _require_lease), so when a stale lease is broken and replaced,
        the displaced owner is fenced out of all further writes.

        Returns ("fresh", info) or ("broke-stale", info); info records any
        orphan cards reconciled at startup (see reconcile_orphans) — the
        caller must still log LOCK_BROKEN as the new run's first own event
        when a stale lease was broken. Raises LeaseHeldError if a live
        lease exists. Staleness rule (r2): a lock whose recorded PID is
        ALIVE is never displaced, however old it is — age alone never
        breaks a lease. A lock is breakable only when its recorded PID is
        dead/gone, or, when no usable PID is recorded, when the lockfile
        itself is older than STALE_LOCK_SECONDS (mtime — the non-PID
        abandonment test).
        """
        self.init_layout()
        payload = {"pid": os.getpid(), "run_id": run_id,
                   "acquired_at": self.clock(),
                   "fence_token": uuid.uuid4().hex,
                   "store_version": STORE_VERSION}
        broken = None
        try:
            self._create_lock(payload)
        except FileExistsError:
            raw_before = self.lock_path.read_bytes()
            try:
                existing = json.loads(raw_before.decode("utf-8"))
            except Exception:
                existing = {}
            age = None
            try:
                t0 = datetime.fromisoformat(existing["acquired_at"])
                t1 = datetime.fromisoformat(self.clock())
                age = (t1 - t0).total_seconds()
            except Exception:
                age = None
            # Staleness (r2): the recorded PID decides. A LIVE pid means a
            # live owner — never stale, regardless of lock age (the r1 rule
            # let age alone break a live owner's lease). A dead/gone pid
            # means abandoned. Only a lock with no usable pid falls back to
            # the non-PID abandonment test: lockfile mtime older than
            # STALE_LOCK_SECONDS.
            raw_pid = existing.get("pid")
            pid_known = False
            if raw_pid is not None:
                try:
                    int(raw_pid)
                    pid_known = True
                except (TypeError, ValueError):
                    pid_known = False
            if pid_known:
                stale = not _pid_alive(raw_pid)
            else:
                try:
                    mtime_age = time.time() - \
                        self.lock_path.stat().st_mtime
                except OSError:
                    mtime_age = None
                stale = mtime_age is not None and \
                    mtime_age > STALE_LOCK_SECONDS
            if not (break_stale and stale):
                raise LeaseHeldError(
                    f"pipeline.lock held by pid={existing.get('pid')} "
                    f"run={existing.get('run_id')} age={age}")
            # Takeover race guard: break only the exact lock observed —
            # if it changed since the read, someone else got there first.
            if self.lock_path.read_bytes() != raw_before:
                raise LeaseHeldError(
                    "pipeline.lock changed during stale-break attempt; "
                    "refusing to displace a lock that was not observed")
            aside = self.root / f"pipeline.lock.stale-{run_id}"
            os.replace(self.lock_path, aside)
            if aside.read_bytes() != raw_before:
                # The move displaced a lock that was NOT the one observed
                # (a fresh owner slipped in between the check and the
                # move). Put it back and refuse — a takeover must never
                # displace an unobserved lock.
                if not self.lock_path.exists():
                    os.replace(aside, self.lock_path)
                raise LeaseHeldError(
                    "stale-break displaced an unobserved lock; restored "
                    "it and refusing to take over")
            self._create_lock(payload)
            broken = {"broken": existing, "moved_aside": aside.name}
        self._lease = (run_id, self.lock_path, payload["fence_token"])
        reconciled = self.reconcile_orphans(run_id)
        info = {"reconciled": reconciled}
        if broken is not None:
            info.update(broken)
            return "broke-stale", info
        return "fresh", info

    def release_lease(self):
        if self._lease is None:
            return
        run_id, path, token = self._lease
        try:
            current = _load_json(path)
            if current.get("run_id") == run_id and \
                    current.get("fence_token") == token:
                path.unlink()
        except FileNotFoundError:
            pass
        self._lease = None

    def _require_lease(self):
        """Fencing check, run before EVERY store mutation.

        The caller must hold the lease AND the lockfile on disk must still
        carry this instance's fencing token. A displaced owner (its stale
        lock broken and replaced, or its lock released/taken over) fails
        here and cannot write.
        """
        if self._lease is None:
            raise FencingError(
                "mutation attempted without holding the pipeline lease")
        run_id, path, token = self._lease
        try:
            current = _load_json(path)
        except FileNotFoundError:
            raise FencingError(
                f"lease lockfile missing for run {run_id}: this writer "
                "has been displaced and is fenced out")
        except Exception as exc:
            raise FencingError(f"lease lockfile unreadable: {exc}")
        if current.get("run_id") != run_id or \
                current.get("fence_token") != token:
            raise FencingError(
                f"lease now owned by run={current.get('run_id')}; "
                f"run {run_id} has been displaced and is fenced out")

    # -- orphan reconciliation -------------------------------------------------
    def reconcile_orphans(self, run_id):
        """Resolve cards orphaned by a crash mid-ingest. Runs under the
        caller's lease (invoked automatically by acquire_lease).

        FENCED (r2): the lease is verified before ANY mutation and again
        immediately before each filesystem move, under the same discipline
        as every other store mutation — an unfenced or displaced caller is
        refused before touching anything.

        Write ordering makes this recoverable: a card file is fsynced and
        atomically renamed BEFORE its INGESTED/MIGRATED event is appended,
        so the only crash window leaves a durable card with no event.
        Deterministic resolution, in idea_id order: a card that still
        re-validates and whose dedup_key recomputes is ADOPTED — the lost
        INGESTED event is appended now, marked recovered_orphan with the
        card's sha256. A card that fails re-validation is QUARANTINED to
        ideas/orphaned/: its ERROR event is appended FIRST and the file
        moved only after, so the log always records the quarantine before
        the card leaves ideas/ — if a crash lands between the event and
        the move, the next reconciliation completes the pending move
        without appending a duplicate event. Leftover write_card temp
        files are removed (they are never valid cards).
        Returns the list of actions taken.
        """
        self._require_lease()  # fence before ANY mutation
        actions = []
        if self.ideas_dir.exists():
            for tmp in sorted(self.ideas_dir.glob("IDEA-*.json.tmp")):
                tmp.unlink()
                actions.append({"action": "removed-temp",
                                "path": tmp.name})
        events = self.read_events()
        known = {ev.get("idea_id") for ev in events
                 if ev.get("event_type") in ("INGESTED", "MIGRATED")
                 and ev.get("idea_id")}
        quarantine_recorded = {ev.get("idea_id") for ev in events
                               if ev.get("event_type") == "ERROR"
                               and ev.get("quarantined_orphan")
                               and ev.get("idea_id")}
        for idea_id in sorted(self.all_cards()):
            if idea_id in known:
                continue
            card = self.read_card(idea_id)
            raw = self.card_path(idea_id).read_bytes()
            digest = "sha256:" + hashlib.sha256(raw).hexdigest()
            if idea_id in quarantine_recorded:
                # A previous reconciliation recorded the quarantine in the
                # log but crashed before moving the file. Complete the
                # pending move — no duplicate event.
                self._require_lease()
                orphan_dir = self.ideas_dir / "orphaned"
                orphan_dir.mkdir(parents=True, exist_ok=True)
                os.replace(self.card_path(idea_id),
                           orphan_dir / self.card_path(idea_id).name)
                actions.append({"action": "quarantine-completed",
                                "idea_id": idea_id, "card_sha256": digest})
                continue
            recomputed = dedup_key(card.get("claim_normalized", ""),
                                   card.get("source") or {})
            errors = validate_card(card, self.sources_idx,
                                   new_intake=False)
            if not errors and recomputed == card.get("dedup_key"):
                self.append_event(
                    "INGESTED", run_id, idea_id=idea_id,
                    from_state="DISCOVERED", to_state="INGESTED",
                    reason="startup reconciliation: card was durable but "
                           "its INGESTED event was lost to a crash; "
                           "adopted deterministically",
                    extra={"recovered_orphan": True, "card_sha256": digest})
                actions.append({"action": "adopted", "idea_id": idea_id,
                                "card_sha256": digest})
            else:
                detail = "; ".join(errors) if errors else \
                    "dedup_key does not recompute"
                # Log FIRST, move SECOND: the quarantine is recorded in
                # the chain before the card leaves ideas/, so the order
                # survives a crash in between (see docstring).
                self.append_event(
                    "ERROR", run_id, idea_id=idea_id,
                    reason="startup reconciliation: orphan card failed "
                           f"re-validation ({detail}) and was quarantined "
                           f"to ideas/orphaned/ (card {digest})",
                    extra={"quarantined_orphan": True,
                           "card_sha256": digest})
                self._require_lease()
                orphan_dir = self.ideas_dir / "orphaned"
                orphan_dir.mkdir(parents=True, exist_ok=True)
                os.replace(self.card_path(idea_id),
                           orphan_dir / self.card_path(idea_id).name)
                actions.append({"action": "quarantined",
                                "idea_id": idea_id, "card_sha256": digest})
        return actions

    # -- appending events ------------------------------------------------------
    def _terminate_tail_if_needed(self):
        """If the log's final line lacks a trailing newline, terminate it
        before appending. Without this, the next record would merge into
        the unterminated line and corrupt both. Called only AFTER the
        chain verifies, so the unterminated line is known to be a complete
        valid event that is merely missing its newline; a torn (invalid)
        tail aborts in read_events/verify_chain before any write."""
        if not self.log_path.exists():
            return
        with open(self.log_path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            if fh.tell() == 0:
                return
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) == b"\n":
                return
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())

    def append_event(self, event_type, run_id, *, idea_id=None,
                     from_state=None, to_state=None, reason=None, rank=None,
                     score_breakdown=None, actor="idea-harvest-weekly",
                     extra=None, at=None):
        """Append one hash-chained event. Crash-safe: one line, fsync.

        Requires the lease (fencing-checked against the lockfile on disk).
        Verifies the chain tail before appending — a corrupt log aborts
        the run; it is never silently repaired. Event IDs are UUIDs
        (unique per attempt without coordination); the event's run
        association is recorded in its run_id field.
        """
        self._require_lease()
        if event_type not in EVENT_TYPES:
            raise StoreError(f"unknown event_type: {event_type}")
        events = self.read_events()
        prev_hash, _count = self._tail(events)
        self.verify_chain(events)  # abort on corruption, never repair
        self._terminate_tail_if_needed()
        stamp = at or self.clock()
        core = {
            "event_id": "EVT-" + uuid.uuid4().hex,
            "run_id": run_id,
            "event_type": event_type,
            "idea_id": idea_id,
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "rank": rank,
            "score_breakdown": score_breakdown,
            "actor": actor,
            "at": stamp,
        }
        if extra:
            core.update(extra)
        ev = dict(core)
        ev["prev_event_hash"] = prev_hash
        ev["event_hash"] = _event_hash(prev_hash, core)
        line = json.dumps(ev, ensure_ascii=False) + "\n"
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        return ev

    # -- state reconstruction ---------------------------------------------------
    def current_states(self, events=None):
        """idea_id -> current queue state, replayed from the log."""
        events = self.read_events() if events is None else events
        states = {}
        for ev in events:
            if ev.get("idea_id") and ev.get("to_state"):
                states[ev["idea_id"]] = ev["to_state"]
        return states

    def next_idea_seq(self, events=None):
        events = self.read_events() if events is None else events
        seqs = []
        for ev in events:
            if ev.get("event_type") in ("INGESTED", "MIGRATED") and ev.get("idea_id"):
                m = re.search(r"-(\d{4})$", ev["idea_id"])
                if m:
                    seqs.append(int(m.group(1)))
        return (max(seqs) + 1) if seqs else 1

    def new_run_id(self, events=None):
        """Unique per-attempt run ID. UUID-based: two attempts starting
        from the same log state can never collide (the r1 sequenced form
        could). The UTC date prefix is retained for readability and for
        _run_date(); uniqueness comes from the UUID fragment."""
        date = self.clock()[:10].replace("-", "")
        return f"RUN-{date}-{uuid.uuid4().hex[:12]}"

    # -- cards -------------------------------------------------------------------
    def card_path(self, idea_id):
        return self.ideas_dir / f"{idea_id}.json"

    def read_card(self, idea_id):
        path = self.card_path(idea_id)
        if not path.exists():
            return None
        return _load_json(path)

    def all_cards(self):
        cards = {}
        if self.ideas_dir.exists():
            for path in sorted(self.ideas_dir.glob("IDEA-*.json")):
                card = _load_json(path)
                cards[card["idea_id"]] = card
        return cards

    def write_card(self, card):
        """Write a card exactly once. Immutable: any second write raises.
        Requires the lease (fencing-checked). The card is fsynced and
        atomically renamed into place BEFORE its log event is appended —
        that ordering is what makes a mid-ingest crash recoverable by
        reconcile_orphans."""
        self._require_lease()
        self.init_layout()
        path = self.card_path(card["idea_id"])
        if path.exists():
            raise StoreError(f"immutable card already exists: {card['idea_id']}")
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(card, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        return path

    # -- scope guard ----------------------------------------------------------------
    def guard_registry_write(self, target_path):
        """Phase A has NO registry write path. Any attempt raises."""
        raise ScopeViolation(
            f"Phase A store refuses registry writes (attempted: {target_path})."
            " Registry merges are a separate human-approved step.")

    # -- transitions ------------------------------------------------------------------
    def transition(self, idea_id, to_state, run_id, *, reason=None, rank=None,
                   score_breakdown=None, actor="idea-harvest-weekly"):
        """Move one idea along a legal transition, or refuse + log ERROR."""
        events = self.read_events()
        states = self.current_states(events)
        if idea_id not in states:
            raise IllegalTransitionError(f"unknown idea: {idea_id}")
        from_state = states[idea_id]
        try:
            if to_state in FORBIDDEN_TARGETS:
                raise IllegalTransitionError(
                    f"transition to {to_state} is outside Phase 1 scope "
                    "(human process only)")
            if from_state in TERMINAL_STATES:
                raise IllegalTransitionError(
                    f"{idea_id} is in terminal state {from_state}")
            event_type = LEGAL_TRANSITIONS.get((from_state, to_state))
            if event_type is None:
                raise IllegalTransitionError(
                    f"illegal transition: {from_state} -> {to_state}")
            if event_type in ("DEDUPE_REJECT", "BLOCKED", "REJECTED") \
                    and not reason:
                raise IllegalTransitionError(
                    f"{event_type} requires a recorded reason")
        except IllegalTransitionError as exc:
            self.append_event("ERROR", run_id, idea_id=idea_id,
                              from_state=from_state, to_state=None,
                              reason=f"refused transition {from_state} -> "
                                     f"{to_state}: {exc}")
            raise
        return self.append_event(event_type, run_id, idea_id=idea_id,
                                 from_state=from_state, to_state=to_state,
                                 reason=reason, rank=rank,
                                 score_breakdown=score_breakdown, actor=actor)

    # -- ingestion ----------------------------------------------------------------------
    def ingest(self, card_fields, run_id, *, actor="idea-harvest-weekly",
               known_families=None, closed_families=None):
        """Ingest one candidate. Returns a result dict.

        Mechanical only — outcomes: ingested | duplicate | rejected.
        Adjacency (known/open or justified family match) is FLAGGED on the
        event record, never verdicted.
        """
        events = self.read_events()
        cards = self.all_cards()
        src = card_fields.get("source") or {}
        claim_norm = normalize_claim(card_fields.get("claim", ""))
        key = dedup_key(claim_norm, src)

        # 1) Exact-duplicate idempotency (DUPLICATE_SEEN semantics):
        #    no new card, no new ID, disposition cites the existing record.
        for existing in cards.values():
            if existing.get("dedup_key") == key:
                state = self.current_states(events).get(existing["idea_id"])
                self.append_event(
                    "DUPLICATE_SEEN", run_id, idea_id=existing["idea_id"],
                    reason=f"duplicate ingestion of {existing['idea_id']} "
                           f"(dedup_key match); existing state: {state}; "
                           "no new card, no new ID allocated",
                    actor=actor)
                return {"outcome": "duplicate",
                        "idea_id": existing["idea_id"], "state": state}

        # 2) Build the card and validate as new intake.
        seq = self.next_idea_seq(events)
        year = (card_fields.get("created_at") or self.clock())[:4]
        card = dict(card_fields)
        card["idea_id"] = f"IDEA-{year}-{seq:04d}"
        card["claim_normalized"] = claim_norm
        card["dedup_key"] = key
        errors = validate_card(card, self.sources_idx, new_intake=True)
        if errors:
            raise CardValidationError(errors)
        self.write_card(card)
        self.append_event("INGESTED", run_id, idea_id=card["idea_id"],
                          from_state="DISCOVERED", to_state="INGESTED",
                          actor=actor)

        family = card.get("strategy_family")
        justification = card.get("materially_different_mechanism")
        seed_hit = self.seed_idx.get(family)
        closed = closed_families or {}
        known = known_families or {}

        # 3) Killed-seed / closed-family mechanical match.
        reject_reason = None
        if seed_hit:
            reject_reason = (
                f"killed-seed match {seed_hit['seed_id']} "
                f"(family {family}): {seed_hit['record_ref']}")
        elif family in closed:
            reject_reason = f"closed family {family}: {closed[family]}"
        if reject_reason:
            if justification:
                self.append_event(
                    "ADJACENCY_FLAG", run_id, idea_id=card["idea_id"],
                    reason=f"{reject_reason} — materially-different-mechanism "
                           f"justification recorded; human confirmation "
                           f"required, no automated verdict: {justification}",
                    actor=actor)
                self.append_event("DEDUPE_PASS", run_id,
                                  idea_id=card["idea_id"], actor=actor)
                return {"outcome": "ingested", "idea_id": card["idea_id"],
                        "adjacency_flag": True}
            self.transition(card["idea_id"], "REJECTED", run_id,
                            reason=reject_reason, actor=actor)
            return {"outcome": "rejected", "idea_id": card["idea_id"],
                    "reason": reject_reason}

        # 4) Known-but-open family: adjacency flag only, no verdict.
        if family in known:
            self.append_event(
                "ADJACENCY_FLAG", run_id, idea_id=card["idea_id"],
                reason=f"family adjacency: {family} already present in the "
                       f"record ({known[family]}); mechanism difference is "
                       "a human call, not automated",
                actor=actor)
            self.append_event("DEDUPE_PASS", run_id, idea_id=card["idea_id"],
                              actor=actor)
            return {"outcome": "ingested", "idea_id": card["idea_id"],
                    "adjacency_flag": True}

        self.append_event("DEDUPE_PASS", run_id, idea_id=card["idea_id"],
                          actor=actor)
        return {"outcome": "ingested", "idea_id": card["idea_id"],
                "adjacency_flag": False}


# --------------------------------------------------------------------------
# Deterministic materializers (pure functions of log + pinned registry read)
# --------------------------------------------------------------------------

def _write_deterministic(path: Path, obj) -> bytes:
    data = (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return data


def _run_date(run_id: str) -> str:
    m = re.search(r"(\d{4})(\d{2})(\d{2})", run_id or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return "1970-01-01"


def materialize_drafts(store: Store, run_id: str, out_path=None):
    """Materialize the registry-shaped DRAFT for one run's shortlist.

    Only ideas whose SHORTLISTED transition happened in `run_id` appear.
    Byte-stable for the same log: every value derives from cards + events.
    Writing the draft is a store mutation: the caller must hold the lease.
    """
    store._require_lease()
    events = store.read_events()
    store.verify_chain(events)
    cards = store.all_cards()
    ranks = {}
    shortlisted = []
    for ev in events:
        if ev.get("event_type") == "RANKED" and ev.get("idea_id"):
            ranks[ev["idea_id"]] = ev.get("rank")
        if ev.get("event_type") == "SHORTLISTED" \
                and ev.get("run_id") == run_id and ev.get("idea_id"):
            shortlisted.append(ev["idea_id"])
    date = _run_date(run_id)
    entries = []
    for idea_id in sorted(shortlisted, key=lambda i: (ranks.get(i) or 99, i)):
        card = cards[idea_id]
        src = card["source"]
        fam_slug = card["strategy_family"].upper().replace("_", "-")
        seq = idea_id.rsplit("-", 1)[-1]
        entries.append({
            "draft": True,
            "experiment_id": f"DRAFT-{date.replace('-', '')}-PA{seq}-{fam_slug}",
            "title": card.get("short_title") or card["claim"],
            "owner": "Muse (idea harvest intake)",
            "created_at": date,
            "state": "DRAFT-INTAKE-NOT-MERGED",
            "hypothesis": card["hypothesis"],
            "primary_sources": [src.get("url")] if src.get("url") else [],
            "literature_intake": {
                "source": f"{src.get('authors', '')}, {src.get('venue', '')}",
                "finding": src.get("evidence", ""),
                "hypothesis_derived": card["hypothesis"],
            },
            "rule_spec_version": "IDEA_HARVEST_SPEC_v1 intake; no rule spec yet",
            "code_pin": "NONE — no code written",
            "dataset_pin": "NONE — no data pulled",
            "output_pin": f"phase_a queue_log (idea_id {idea_id})",
            "dependencies": card.get("pit_inputs") or [],
            "next_action": "Awaiting Mike selection; if picked, next step is "
                           "a preregistration with a frozen gate (separate "
                           "approval).",
            "attempted_variations": [],
            "trial_budget": {"allocated": "NONE", "used": "0",
                             "unit": "no test authorized"},
            "repair_budget": {"allocated_rounds": 0, "used_rounds": 0},
            "baseline_design": "TBD at preregistration",
            "costs": "TBD at preregistration (standing bar: 25 bps)",
            "validation_split": "TBD at preregistration",
            "acceptance_criteria": "TBD — frozen gate to be written before "
                                   "any run",
            "robustness_diagnostics": [],
            "limitations": card.get("limitations") or [],
            "verdict": "NOT TESTED — intake draft only",
            "decision_refs": [run_id],
            "failure_reason": None,
            "failure_market": None,
            "failure_timeframe": card.get("timeframe"),
            "failure_data_source": f"PIT: {card.get('pit_data')}",
            "failure_strategy_family": card.get("strategy_family"),
            "task_revision": run_id,
            "evidence_pin": src.get("url"),
            "authorization": "Intake authorized under the approved idea "
                             "pipeline. NO test execution authorized.",
            "idea_id": idea_id,
            "queue_run_id": run_id,
        })
    doc = {
        "draft": True,
        "status": "DRAFT — NOT MERGED INTO registry.json",
        "generated_from": f"phase_a queue log, run {run_id}",
        "generator": STORE_VERSION,
        "source_report": "phase_a/queue/queue_log.jsonl",
        "merge_instruction": "Do NOT merge automatically. A draft becomes a "
                             "registry experiment only after Mike selects it "
                             "and a preregistration is approved; merge then "
                             "via python json (indent=2, ensure_ascii=False) "
                             "in a separate approved bookkeeping step.",
        "experiments": entries,
    }
    out = Path(out_path) if out_path else \
        store.drafts_dir / f"intake_draft_{date.replace('-', '')}.json"
    _write_deterministic(out, doc)
    return out


def _registry_test_counts(experiments, attributions):
    """family -> {tests_run, tests_failed, tests_passed, last_test_ref}.

    Counting rules (documented in registry_backfill.json): family is the
    registry `failure_strategy_family` when populated and not 'N/A', else an
    explicit backfill attribution, else uncounted. FAILED if the state field
    contains 'FAIL' or the verdict starts with 'FAIL'. PASSED if the state
    contains 'PASS' and not 'FAIL'. Anything else is neither.
    """
    counts = {}
    for exp in experiments:
        fam = exp.get("failure_strategy_family")
        if fam in (None, "", "N/A"):
            att = attributions.get(exp.get("experiment_id") or "")
            fam = att.get("family") if att else None
        if not fam:
            continue
        c = counts.setdefault(fam, {"tests_run": 0, "tests_failed": 0,
                                    "tests_passed": 0, "last_test_ref": None,
                                    "closed": False})
        c["tests_run"] += 1
        state = str(exp.get("state") or "")
        verdict = str(exp.get("verdict") or "")
        failed = ("FAIL" in state) or verdict.startswith("FAIL")
        passed = ("PASS" in state) and not failed
        if failed:
            c["tests_failed"] += 1
            if "CLOSED" in state:
                c["closed"] = True
        elif passed:
            c["tests_passed"] += 1
        if exp.get("experiment_id"):
            prev = c.get("_last_created") or ""
            if str(exp.get("created_at") or "") >= prev:
                c["_last_created"] = str(exp.get("created_at") or "")
                c["last_test_ref"] = exp["experiment_id"]
    for c in counts.values():
        c.pop("_last_created", None)
    return counts


def materialize_ledger(store: Store, registry_path, attributions=None,
                       out_path=None):
    """Materialize the family-level multiple-testing ledger.

    Counters are DERIVED from (queue log + pinned registry read) — never
    hand-incremented. `updated_at` is the last queue event's timestamp, so
    the output is byte-stable for identical inputs. Writing the ledger is
    a store mutation: the caller must hold the lease.
    """
    store._require_lease()
    events = store.read_events()
    store.verify_chain(events)
    cards = store.all_cards()
    registry_path = Path(registry_path)
    raw = registry_path.read_bytes()  # READ-ONLY. This module has no
    # registry write path anywhere (see Store.guard_registry_write).
    blob_sha = "sha256:" + hashlib.sha256(raw).hexdigest()
    registry = json.loads(raw.decode("utf-8"))
    experiments = registry["experiments"] if isinstance(registry, dict) \
        else registry
    test_counts = _registry_test_counts(experiments, attributions or {})

    intake, dedupe_rejects, shortlisted = {}, {}, {}
    for ev in events:
        card = cards.get(ev.get("idea_id") or "")
        if not card:
            continue
        fam = card.get("strategy_family")
        if ev["event_type"] in ("INGESTED", "MIGRATED"):
            intake[fam] = intake.get(fam, 0) + 1
        elif ev["event_type"] == "DEDUPE_REJECT":
            dedupe_rejects[fam] = dedupe_rejects.get(fam, 0) + 1
        elif ev["event_type"] == "SHORTLISTED":
            shortlisted[fam] = shortlisted.get(fam, 0) + 1

    families = sorted(set(intake) | set(test_counts))
    last_at = events[-1]["at"] if events else None
    records = []
    for fam in families:
        tc = test_counts.get(fam, {"tests_run": 0, "tests_failed": 0,
                                   "tests_passed": 0, "last_test_ref": None,
                                   "closed": False})
        if tc.get("closed"):
            fam_state = "closed"
        elif tc["tests_failed"] > 0:
            fam_state = "caution"
        else:
            fam_state = "open"
        records.append({
            "strategy_family": fam,
            "intake_count": intake.get(fam, 0),
            "dedupe_reject_count": dedupe_rejects.get(fam, 0),
            "shortlisted_count": shortlisted.get(fam, 0),
            "tests_run": tc["tests_run"],
            "tests_failed": tc["tests_failed"],
            "tests_passed": tc["tests_passed"],
            "last_test_ref": tc["last_test_ref"],
            "family_state": fam_state,
            "updated_at": last_at,
        })
    doc = {
        "ledger_version": "family-ledger/1.0.0",
        "generated_from": {
            "queue_log_events": len(events),
            "registry_blob_sha256": blob_sha,
            "registry_experiments": len(experiments),
            "generator": STORE_VERSION,
        },
        "families": records,
    }
    out = Path(out_path) if out_path else \
        store.ledger_dir / "family_ledger.json"
    _write_deterministic(out, doc)
    return out


def closed_families_from_ledger(ledger_doc):
    """{family: reason} for families whose derived state is closed."""
    out = {}
    for rec in ledger_doc.get("families", []):
        if rec.get("family_state") == "closed":
            out[rec["strategy_family"]] = (
                f"family ledger state=closed "
                f"(last_test_ref={rec.get('last_test_ref')}, "
                f"tests_failed={rec.get('tests_failed')})")
    return out
