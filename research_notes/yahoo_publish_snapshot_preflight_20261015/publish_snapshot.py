"""Isolated replacement publisher — QF-YAHOO-PUBLISH-SNAPSHOT-PREFLIGHT-20261015-11 r1.

Implements the accepted design in research_notes/
YAHOO_PUBLISH_SNAPSHOT_DESIGN_20261015.md (SNAPSHOT_DESIGN_READY):

- publish(cap_dir, capture_id, remote) is the ONLY public entry point.
  There is no entries/options/target parameter: the object set is a pure
  function of the internally loaded, hash-pinned frozen capture manifest
  (sha256 634c4541...), exactly 156 objects.
- One immutable in-memory SnapshotBundle (156 objects + SHA256SUMS +
  manifest.json = 158 payloads) is built by a single checked read of the
  archive (lstat path-type discipline, O_NOFOLLOW, fstat before/after
  drift checks). Validation runs against the in-bundle bytes only.
- After the bundle is sealed, the publish phase performs NO filesystem
  reads of payload bytes: upload, post-upload re-assertion (I-2) and
  re-fetch verification all bind to the sealed bundle's digest index.
- Upload order is rel-sorted with SHA256SUMS and manifest.json last;
  158/158 exact re-fetch matches against the pinned validation-time
  hashes are the only path to PUBLISHED. No retries, ever; no
  republication under a consumed capture id.
- Canonical capture-ID grammar is enforced before any local or remote
  path construction.
- Bundle ceiling 64 MiB (frozen capture ceiling is 512 MiB — the
  mismatch is recorded as CEILING_PARITY_REQUIRED by the preflight
  driver; this module does not silently change either ceiling).

Preflight scope guard: only a fake local remote (kind == "FAKE_LOCAL")
is accepted. This module never touches a real remote.
"""

import hashlib
import json
import os
import re
import stat
from types import MappingProxyType

EXPECTED_MANIFEST_SHA256 = \
    "634c4541a8b30ade50e45898e80ee65806fa323c953020edc149530642d9bef3"
EXPECTED_SCHEMA = "qf.yahoo_clean_capture.manifest/1"
EXPECTED_REPO_FULL_NAME = "mickaellall116-cmyk/qf-data-archive"
FROZEN_MANIFEST_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir,
    "yahoo_clean_capture_preflight_20261015", "capture_manifest.json"))

BUNDLE_CEILING_BYTES = 64 * 1024 * 1024          # 67108864
SINGLE_OBJECT_CEILING_BYTES = 32 * 1024 * 1024   # 33554432
FROZEN_CAPTURE_CEILING_BYTES = 512 * 1024 * 1024  # 536870912, manifest pin

JOURNAL_REL = "attempt_journal.jsonl"
LEDGER_REL = "file_ledger.jsonl"
MARKER_REL = "INCOMPLETE_HOLD.json"
SUMS_REL = "SHA256SUMS"
ARCHIVE_MANIFEST_REL = "manifest.json"

_CAPTURE_ID_RE = re.compile(r"[A-Z0-9][A-Z0-9-]*[A-Z0-9]")


class HoldError(Exception):
    """Fail-closed refusal; .code is the exact HOLD:* verdict string."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _validate_capture_id(capture_id):
    """Canonical ASCII capture-ID grammar, enforced before ANY local or
    remote path/prefix construction. Charset [A-Z0-9-], length 8..64,
    alphanumeric at both ends, no consecutive hyphens. This rejects path
    separators, dot segments, percent-encoding, Unicode lookalikes
    (non-ASCII never matches the ASCII charset), control characters,
    whitespace and all lowercase (case-collision ambiguity)."""
    if not isinstance(capture_id, str):
        raise HoldError("HOLD:CAPTURE_ID_INVALID")
    if not 8 <= len(capture_id) <= 64:
        raise HoldError("HOLD:CAPTURE_ID_INVALID")
    if "--" in capture_id:
        raise HoldError("HOLD:CAPTURE_ID_INVALID")
    if _CAPTURE_ID_RE.fullmatch(capture_id) is None:
        raise HoldError("HOLD:CAPTURE_ID_INVALID")


# ---------------------------------------------------------------------------
# Frozen manifest — loaded internally, hash-pinned; the only entry source
# ---------------------------------------------------------------------------

def _load_frozen_manifest():
    with open(FROZEN_MANIFEST_PATH, "rb") as fh:
        raw = fh.read()
    if _sha256(raw) != EXPECTED_MANIFEST_SHA256:
        raise HoldError("HOLD:MANIFEST_DRIFT")
    try:
        man = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HoldError("HOLD:MANIFEST_DRIFT")
    if man.get("schema") != EXPECTED_SCHEMA:
        raise HoldError("HOLD:MANIFEST_DRIFT")
    try:
        entries = sorted(man["request_order"], key=lambda e: e["i"])
        idx = [e["i"] for e in entries]
        symbols = [e["symbol"] for e in entries]
        max_total = int(man["call_budget"]["max_requests_total"])
    except (KeyError, TypeError, ValueError):
        raise HoldError("HOLD:MANIFEST_DRIFT")
    if idx != list(range(1, len(entries) + 1)):
        raise HoldError("HOLD:ORDER_DRIFT")
    if len(entries) != max_total:
        raise HoldError("HOLD:ORDER_DRIFT")
    if len(set(symbols)) != len(symbols):
        raise HoldError("HOLD:ORDER_DRIFT")
    return man, entries


def _expected_object_rels(entries):
    out = set()
    for e in entries:
        s = e["symbol"]
        out.add(f"raw/{s}.csv")
        out.add(f"actions/{s}.actions.csv")
        out.add(f"meta/{s}.request.json")
    return out


# ---------------------------------------------------------------------------
# Publication journal — append-only local evidence, fsync'd per event.
# Lives OUTSIDE cap_dir (sibling directory); never an input to byte decisions.
# ---------------------------------------------------------------------------

class _Journal:
    def __init__(self, path):
        self._path = path

    def append(self, event):
        line = json.dumps(event, sort_keys=True) + "\n"
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())


def _journal_for(cap_dir, capture_id):
    parent = os.path.dirname(os.path.abspath(cap_dir))
    jdir = os.path.join(parent, ".publication_journals")
    os.makedirs(jdir, exist_ok=True)
    return _Journal(os.path.join(jdir, capture_id + ".jsonl"))


# ---------------------------------------------------------------------------
# Snapshot builder — the ONLY component that reads payload bytes from disk
# ---------------------------------------------------------------------------

def _lstat_regular(path, dir_ok=False):
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode):
        raise HoldError("HOLD:PATH_TYPE_DRIFT")
    if dir_ok and stat.S_ISDIR(st.st_mode):
        return st
    if not stat.S_ISREG(st.st_mode):
        raise HoldError("HOLD:PATH_TYPE_DRIFT")
    return st


def _census(cap_dir, expected_objects):
    """Strict membership: walk without following symlinks. Any symlink or
    non-regular entry is PATH_TYPE_DRIFT; any set difference is OBJECT_SET."""
    _lstat_regular(cap_dir, dir_ok=True)
    actual = {}
    stack = [""]
    while stack:
        rel_dir = stack.pop()
        abs_dir = os.path.join(cap_dir, rel_dir) if rel_dir else cap_dir
        for name in os.listdir(abs_dir):
            rel = f"{rel_dir}/{name}" if rel_dir else name
            st = os.lstat(os.path.join(cap_dir, rel))
            if stat.S_ISLNK(st.st_mode):
                raise HoldError("HOLD:PATH_TYPE_DRIFT")
            if stat.S_ISDIR(st.st_mode):
                stack.append(rel)
            elif stat.S_ISREG(st.st_mode):
                actual[rel] = st
            else:
                raise HoldError("HOLD:PATH_TYPE_DRIFT")
    allowed = expected_objects | {JOURNAL_REL, LEDGER_REL,
                                   SUMS_REL, ARCHIVE_MANIFEST_REL}
    if set(actual) != allowed:
        raise HoldError("HOLD:OBJECT_SET")
    return actual


def _read_once(path):
    """Single checked read: lstat type discipline, O_NOFOLLOW open, fstat
    before/after on the open handle (dev, ino, size, mtime_ns must be
    identical), bytes read must equal st_size, per-object ceiling checked
    against fstat size BEFORE reading."""
    lst = _lstat_regular(path)
    if lst.st_size > SINGLE_OBJECT_CEILING_BYTES:
        raise HoldError("HOLD:CEILING")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if (before.st_dev, before.st_ino) != (lst.st_dev, lst.st_ino):
            raise HoldError("HOLD:READ_DRIFT")
        chunks = []
        total = 0
        while True:
            block = os.read(fd, 1 << 20)
            if not block:
                break
            chunks.append(block)
            total += len(block)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    if (before.st_dev, before.st_ino, before.st_size,
            before.st_mtime_ns) != (after.st_dev, after.st_ino,
                                    after.st_size, after.st_mtime_ns):
        raise HoldError("HOLD:READ_DRIFT")
    if total != before.st_size:
        raise HoldError("HOLD:READ_DRIFT")
    return b"".join(chunks)


def _parse_sums(text_bytes):
    try:
        text = text_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HoldError("HOLD:SUMS_INVALID")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    sums = {}
    for line in lines:
        if len(line) < 67 or line[64:66] != "  ":
            raise HoldError("HOLD:SUMS_INVALID")
        h, rel = line[:64], line[66:]
        if any(c not in "0123456789abcdef" for c in h):
            raise HoldError("HOLD:SUMS_INVALID")
        if rel in sums:
            raise HoldError("HOLD:SUMS_INVALID")
        sums[rel] = h
    return sums


class _SnapshotBundle:
    """Sealed immutable bundle: payload bytes + digest index + bundle
    digest. No method mutates payloads; mappings are read-only views."""

    __slots__ = ("_payloads", "_index", "bundle_sha256", "upload_order")

    def __init__(self, payloads, index, bundle_sha256, upload_order):
        self._payloads = MappingProxyType(dict(payloads))
        self._index = MappingProxyType(dict(index))
        self.bundle_sha256 = bundle_sha256
        self.upload_order = tuple(upload_order)

    def __len__(self):
        return len(self._payloads)

    def payload(self, rel):
        return self._payloads[rel]

    def digest(self, rel):
        return self._index[rel]

    def assert_integrity(self):
        """I-2: every payload still hashes to its pinned digest."""
        for rel, h in self._index.items():
            if _sha256(self._payloads[rel]) != h:
                raise HoldError("HOLD:BUNDLE_MUTATED")


def _build_bundle(cap_dir, capture_id, entries):
    if os.path.lexists(os.path.join(cap_dir, MARKER_REL)):
        raise HoldError("HOLD:INCOMPLETE_MARKER")
    expected = _expected_object_rels(entries)
    _census(cap_dir, expected)
    load_order = sorted(expected) + [SUMS_REL, ARCHIVE_MANIFEST_REL]
    payloads = {}
    total = 0
    for rel in load_order:
        data = _read_once(os.path.join(cap_dir, rel))
        total += len(data)
        if total > BUNDLE_CEILING_BYTES:
            raise HoldError("HOLD:CEILING")
        payloads[rel] = data
    # In-bundle validation — against memory only, never disk.
    sums = _parse_sums(payloads[SUMS_REL])
    if len(sums) != len(expected):
        raise HoldError("HOLD:SUMS_INVALID")
    object_index = {rel: _sha256(payloads[rel]) for rel in expected}
    if sums != object_index:
        raise HoldError("HOLD:SUMS_INVALID")
    try:
        doc = json.loads(payloads[ARCHIVE_MANIFEST_REL].decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HoldError("HOLD:ARCHIVE_MANIFEST_INVALID")
    if (doc.get("status") != "COMPLETE"
            or doc.get("capture_id") != capture_id
            or doc.get("symbols") != len(entries)
            or doc.get("capture_manifest_sha256") != EXPECTED_MANIFEST_SHA256
            or doc.get("files") != sums):
        raise HoldError("HOLD:ARCHIVE_MANIFEST_INVALID")
    index = dict(object_index)
    index[SUMS_REL] = _sha256(payloads[SUMS_REL])
    index[ARCHIVE_MANIFEST_REL] = _sha256(payloads[ARCHIVE_MANIFEST_REL])
    canonical = "".join(f"{index[rel]}  {rel}\n" for rel in sorted(index))
    bundle_sha = _sha256(canonical.encode("utf-8"))
    upload_order = sorted(expected) + [SUMS_REL, ARCHIVE_MANIFEST_REL]
    bundle = _SnapshotBundle(payloads, index, bundle_sha, upload_order)
    assert len(bundle) == 158
    bundle.assert_integrity()
    return bundle


# ===== publish phase (no payload filesystem access below this line) =====
# The functions below receive only the sealed bundle, the capture id, the
# remote and the journal. They never see cap_dir and never open a payload
# path; the journal (outside cap_dir) is their only filesystem touch.

def _publish_bundle(bundle, capture_id, remote, journal):
    if remote.full_name() != EXPECTED_REPO_FULL_NAME:
        raise HoldError("HOLD:TARGET_NAME_DRIFT")
    if remote.visibility() != "private":
        raise HoldError("HOLD:VISIBILITY_REFUSAL")
    base = f"captures/{capture_id}"
    if remote.has_prefix(base):
        raise HoldError("HOLD:CAPTURE_EXISTS")
    for existing in remote.list_capture_prefixes():
        if existing != base and existing.casefold() == base.casefold():
            raise HoldError("HOLD:CAPTURE_EXISTS")
    puts = 0
    for rel in bundle.upload_order:
        try:
            remote.put_file(f"{base}/{rel}", bundle.payload(rel))
        except Exception:
            journal.append({"event": "PARTIAL_UPLOAD", "rel": rel,
                            "puts_completed": puts,
                            "bundle_sha256": bundle.bundle_sha256})
            raise HoldError("HOLD:PARTIAL_UPLOAD")
        puts += 1
        journal.append({"event": "PUT", "rel": rel,
                        "head_sha": remote.head_sha()})
    bundle.assert_integrity()
    verified = 0
    for rel in bundle.upload_order:
        got = remote.get_file(f"{base}/{rel}")
        if got is None or _sha256(got) != bundle.digest(rel):
            journal.append({"event": "REFETCH_MISMATCH", "rel": rel,
                            "bundle_sha256": bundle.bundle_sha256})
            raise HoldError("HOLD:REFETCH_MISMATCH")
        verified += 1
    journal.append({"event": "PUBLISHED", "objects": len(bundle),
                    "verified": verified,
                    "bundle_sha256": bundle.bundle_sha256,
                    "commit_sha": remote.head_sha()})
    return {"status": "PUBLISHED", "objects": len(bundle),
            "verified": verified, "bundle_sha256": bundle.bundle_sha256,
            "commit_sha": remote.head_sha()}


def publish(cap_dir, capture_id, remote):
    """Publish the completed capture archive in cap_dir under capture_id
    to the (fake local) remote. The object set is derived exclusively
    from the internal hash-pinned frozen manifest — this signature
    accepts no entries, options or target overrides."""
    _validate_capture_id(capture_id)
    if getattr(remote, "kind", None) != "FAKE_LOCAL":
        raise HoldError("HOLD:REAL_REMOTE_FORBIDDEN")
    _man, entries = _load_frozen_manifest()
    journal = _journal_for(cap_dir, capture_id)
    journal.append({"event": "PUBLISH_START", "capture_id": capture_id})
    bundle = _build_bundle(cap_dir, capture_id, entries)
    journal.append({"event": "BUNDLE_SEALED",
                    "bundle_sha256": bundle.bundle_sha256})
    try:
        return _publish_bundle(bundle, capture_id, remote, journal)
    except HoldError as exc:
        journal.append({"event": "HOLD", "code": exc.code,
                        "bundle_sha256": bundle.bundle_sha256})
        raise
