"""Atomicity-corrected clean capture executor for
QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-ATOMICITY-20261016-19 r4.

Minimal delta over the r3 executor (SHA-256 10e6c07f...; r1/r2/r3 packages
preserved unchanged), closing the defects adjudicated in Issue #1 comment
6217441495:

A. Stable coordination fence: in addition to the journal-fd flock, the
   pinned per-capture CONTROL-DIRECTORY fd is flocked nonblocking BEFORE
   the journal is opened/read and held through run end. Before every
   ATTEMPT append, transport call and COMPLETE append, the control path
   and the journal pathname must still resolve (no-follow) to the pinned
   control-dir identity and the locked journal fd's (dev, ino) identity;
   an empty, copied or symlinked journal-path replacement therefore can
   never create a second transport owner, and the live owner detects the
   split (HOLD:JOURNAL_SPLIT / HOLD:PATH_RACE) before its next call. No
   lock file and no third control artifact is added.
B. Executor temp identity retained through publication: the temp fd
   created O_EXCL stays OPEN from creation through final publication.
   Its (dev, ino) is pinned; immediately before publication the temp
   pathname must still name that inode. Publication is a same-directory
   hard link with follow_symlinks=False; afterwards the final path must
   name the pinned inode (a raced/substituted link is removed — it is a
   dirent this call created — and yields HOLD:FINAL_COLLISION), the
   directory is fsynced, and only the still-verified same-run temp is
   unlinked, followed by a second directory fsync. A substituted temp
   (regular file or symlink) is retained untouched and durably HOLDs.
C. No durable-handling bypass: ordinary OSError from payload write/fsync/
   link/unlink/finalization/path-recheck after ATTEMPT is routed through
   the durable fail() path as HOLD:FILESYSTEM (or the more specific named
   cause). ATTEMPT and COMPLETE append failures are centralized: no
   transport call follows a failed ATTEMPT append, and the run returns
   HOLD:JOURNAL_DURABILITY without claiming any cause was recorded.

Retained from r3 (adjudication comment 6215975805):

1. Stable journal-fd ownership: the acquisition journal is opened ONCE
   (O_NOFOLLOW, fd-relative to the pinned control dirfd), verified a
   regular file, and flocked nonblocking on that very fd BEFORE any read.
   The same fd is held for every read/append/fsync through run end. There
   is NO capture_owner.lock and no third control artifact; the journal is
   never reopened by pathname. Every record binds the journal fd's
   (dev, ino) identity ("journal" key); a journal whose records carry a
   different identity is HOLD:JOURNAL_SPLIT, so a journal-path replacement
   cannot produce a second owner or split records.
2. Explicit base trust boundary: the base directory is reached from the
   documented trusted parent "/" by component-wise no-follow traversal
   (each component opened O_DIRECTORY|O_NOFOLLOW, fd-relative); the final
   component is created by mkdirat only if absent. Root/control/subdirs
   are pinned dirfds exactly as in r2. A symlinked/swapped base, root or
   control component fails before transport or stays confined to the
   pinned dirfds.
3. Atomic no-replace finalization: each executor-owned temp is published
   with renameat2(RENAME_NOREPLACE) (link()+unlink-of-own-temp fallback).
   A destination appearing after the absence check is retained
   byte-identical and yields HOLD:FINAL_COLLISION. Removal targets only
   the identity-verified same-run temp after a successful no-replace
   link, never a pre-existing artifact.
4. Durable post-ATTEMPT failures: after ATTEMPT, EVERY handled
   serialization/ceiling/filesystem/finalization/path-race failure is
   routed through one durable HOLD append+fsync on the still-locked
   journal fd; restart reproduces the exact original code/detail with
   zero calls. If the durable append/fsync itself fails, the run returns
   HOLD:JOURNAL_DURABILITY and does NOT claim the cause was recorded.
5. Exact-key-strict schemas + recorded-truth binding: ATTEMPT/COMPLETE/
   HOLD records validate their EXACT key sets and legal transition
   binding (a consumed HOLD must bind the currently pending ATTEMPT).
   On restart each COMPLETE record's bytes AND hashes are recomputed
   from the files and must EQUAL the record; a false byte total or hash
   is HOLD:JOURNAL_CONFLICT, zero calls — never silently corrected.

Retained from r2: wall re-check after limiter.wait() before ATTEMPT;
pre-existing temp/final retained byte-identical; component identity
re-verification before COMPLETE; separation of authority (stages ONLY
the 156 payloads; no bookkeeping, no pins, no qualification, no
publishing). Transport and clock are injected; no network I/O;
standard library only.
"""
import ctypes
import errno
import fcntl
import hashlib
import json
import os
import re
import stat as _stat
import struct

CANDIDATE_SHA256 = "3d3d4ef51e54f9e6d9bce6119673ddd7e41825049d13c58bead3b19bf4021248"
TASK_ID = "QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-ATOMICITY-20261016-19 r4"
R3_EXECUTOR_SHA256 = "10e6c07f2b850bc10d7b9d852ce1fc13fd9eec87ae8017e4e69fd6be7f01c242"

_libc = ctypes.CDLL(None, use_errno=True)
_SYS_RENAMEAT2 = 316          # Linux x86_64 renameat2
_RENAME_NOREPLACE = 1

SPEC_BYTES_PER_SYMBOL = 33554432          # 32 MiB
SPEC_PAYLOAD_BUDGET = 67076700
SPEC_ROWS_PER_SYMBOL = 20000
SPEC_WALL_SECONDS = 1800
SPEC_MIN_START_GAP = 1.0

_CAPTURE_ID_RE = re.compile(r"\A[A-Z0-9]+(?:-[A-Z0-9]+)*\Z")
_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")

_FRAME_MAGIC = b"QFJ2"
_FRAME_VERSION = 2
_FRAME_CORE = 21
_FRAME_HEADER = 53
_FRAME_TAG = 32
_MAX_FRAME_PAYLOAD = 1048576

JOURNAL_NAME = "acquisition_attempt_journal.qfj2"


class HoldError(Exception):
    def __init__(self, code, detail=""):
        super().__init__(code + (": " + detail if detail else ""))
        self.code = code
        self.detail = detail


class TransportFailure(Exception):
    """Raised by the injected transport. status: int HTTP-like code or None."""

    def __init__(self, status=None, message=""):
        super().__init__(message or f"transport failure status={status}")
        self.status = status


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _sha256(b):
    return hashlib.sha256(b).hexdigest()


def validate_capture_id(capture_id):
    if (not isinstance(capture_id, str) or not (8 <= len(capture_id) <= 64)
            or not _CAPTURE_ID_RE.match(capture_id)):
        raise HoldError("HOLD:CAPTURE_ID_INVALID", repr(capture_id))


# ---------------------------------------------------------------- journal
def _frame_bytes(record, seq):
    rec = dict(record)
    rec["seq"] = seq
    payload = _canonical(rec)
    if len(payload) > _MAX_FRAME_PAYLOAD:
        raise HoldError("HOLD:JOURNAL_CORRUPT", "frame payload over bound")
    core = (_FRAME_MAGIC + bytes([_FRAME_VERSION]) + struct.pack(">Q", seq)
            + struct.pack(">I", len(payload))
            + struct.pack(">I", (~len(payload)) & 0xFFFFFFFF))
    header = core + hashlib.sha256(core).digest()
    return header + payload + hashlib.sha256(header + payload).digest()


def _journal_parse(data):
    """Strict parse. Torn tail -> HOLD:JOURNAL_TORN; any authenticated-framing
    violation -> HOLD:JOURNAL_CORRUPT. (Unchanged from r1.)"""
    records = []
    off = 0
    seq = 0
    n = len(data)
    while off < n:
        if n - off < _FRAME_HEADER:
            raise HoldError("HOLD:JOURNAL_TORN", f"partial header at frame {seq}")
        header = data[off:off + _FRAME_HEADER]
        core = header[:_FRAME_CORE]
        if core[:4] != _FRAME_MAGIC or core[4] != _FRAME_VERSION:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"bad magic/version frame {seq}")
        fseq, length, comp = struct.unpack(">QII", core[5:21])
        if fseq != seq:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"seq gap frame {seq}")
        if hashlib.sha256(core).digest() != header[_FRAME_CORE:]:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"header digest frame {seq}")
        if length > _MAX_FRAME_PAYLOAD or comp != (~length) & 0xFFFFFFFF:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"length/complement frame {seq}")
        end = off + _FRAME_HEADER + length + _FRAME_TAG
        if end > n:
            raise HoldError("HOLD:JOURNAL_TORN", f"partial frame {seq}")
        payload = data[off + _FRAME_HEADER:off + _FRAME_HEADER + length]
        tag = data[off + _FRAME_HEADER + length:end]
        if hashlib.sha256(header + payload).digest() != tag:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"frame tag frame {seq}")
        try:
            rec = json.loads(payload.decode())
        except Exception:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"frame JSON {seq}")
        if not isinstance(rec, dict) or rec.get("seq") != seq:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"frame body seq {seq}")
        records.append(rec)
        off = end
        seq += 1
    return records


def _read_all(fd):
    chunks = []
    while True:
        b = os.read(fd, 1 << 20)
        if not b:
            return b"".join(chunks)
        chunks.append(b)


class JournalSession:
    """One stable journal fd for the whole run (spec item 1).

    Opened once, fd-relative to the pinned control dirfd with O_NOFOLLOW;
    verified a regular file; flocked nonblocking BEFORE any read. Every
    read/append/fsync uses this fd — the journal path is never reopened.
    Records bind this fd's (dev, ino) identity via the "journal" key.
    """

    def __init__(self, control_fd):
        created = False
        try:
            self.fd = os.open(JOURNAL_NAME,
                              os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                              0o600, dir_fd=control_fd)
            created = True
        except FileExistsError:
            pass
        if not created:
            try:
                self.fd = os.open(JOURNAL_NAME, os.O_RDWR | os.O_NOFOLLOW,
                                  dir_fd=control_fd)
            except FileNotFoundError:
                self.fd = os.open(JOURNAL_NAME,
                                  os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
                                  0o600, dir_fd=control_fd)
                created = True
            except OSError as e:
                if e.errno == errno.ELOOP:
                    raise HoldError("HOLD:PATH_TYPE", "journal is a symlink")
                raise
        try:
            st = os.fstat(self.fd)
            if not _stat.S_ISREG(st.st_mode):
                raise HoldError("HOLD:PATH_TYPE", "journal is not a regular file")
            self.identity = f"{st.st_dev}:{st.st_ino}"
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise HoldError("HOLD:OWNER_BUSY",
                                "a live owner holds the acquisition journal")
            if created:
                os.fsync(control_fd)   # durable dirent for the new journal
        except BaseException:
            os.close(self.fd)
            raise
        self.seq = 0

    def read_records(self):
        os.lseek(self.fd, 0, os.SEEK_SET)
        records = _journal_parse(_read_all(self.fd))
        self.seq = len(records)
        return records

    def append(self, record):
        """Append one framed record on the locked fd + fsync. Raises
        OSError on failure (caller turns that into HOLD:JOURNAL_DURABILITY
        where a durable record was required)."""
        rec = dict(record)
        rec["journal"] = self.identity
        frame = _frame_bytes(rec, self.seq)
        os.lseek(self.fd, 0, os.SEEK_END)
        view = memoryview(frame)
        while view:
            w = os.write(self.fd, view)
            view = view[w:]
        os.fsync(self.fd)
        self.seq += 1

    def close(self):
        os.close(self.fd)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


_KEYSET_BASE = {"seq", "type", "capture_id", "symbol", "clock", "journal"}
_ATTEMPT_KEYS = _KEYSET_BASE | {"rels"}
_COMPLETE_KEYS = _KEYSET_BASE | {"files", "bytes"}
_HOLD_KEYS = _KEYSET_BASE | {"code", "detail", "attempt_consumed"}


def _validate_records(records, plan, capture_id, journal_identity):
    """Exact-key-strict schema/order validation (spec items 1+5). Returns
    (attempts, completes, hold_record_or_None). Extra or missing keys on
    ANY record -> HOLD:JOURNAL_CONFLICT. Records bound to a different
    journal identity -> HOLD:JOURNAL_SPLIT. A HOLD claiming a consumed
    attempt must bind the currently pending ATTEMPT exactly."""
    by_sym = {p["symbol"]: p for p in plan}
    attempts, completes = {}, {}
    hold = None
    pending = None          # symbol with ATTEMPT but no COMPLETE yet
    last_idx = -1
    order_idx = {p["symbol"]: i for i, p in enumerate(plan)}

    def conflict(msg):
        raise HoldError("HOLD:JOURNAL_CONFLICT", msg)

    for pos, rec in enumerate(records):
        kind = rec.get("type")
        if hold is not None:
            conflict(f"record after terminal HOLD at {pos}")
        if kind not in ("ATTEMPT", "COMPLETE", "HOLD"):
            conflict(f"unknown record {kind!r} at {pos}")
        if rec.get("journal") != journal_identity:
            raise HoldError("HOLD:JOURNAL_SPLIT",
                            f"record at {pos} bound to another journal identity")
        want = {"ATTEMPT": _ATTEMPT_KEYS, "COMPLETE": _COMPLETE_KEYS,
                "HOLD": _HOLD_KEYS}[kind]
        if set(rec.keys()) != want:
            conflict(f"{kind} key set {sorted(rec.keys())} != exact schema at {pos}")
        if rec.get("capture_id") != capture_id:
            conflict(f"record capture_id mismatch at {pos}")
        if not _is_num(rec.get("clock")):
            conflict(f"record clock invalid at {pos}")
        sym = rec.get("symbol")
        if kind == "ATTEMPT":
            if sym not in by_sym:
                conflict(f"ATTEMPT unknown symbol {sym!r}")
            if pending is not None:
                conflict(f"ATTEMPT {sym} while {pending} unresolved")
            if sym in attempts or sym in completes:
                conflict(f"duplicate ATTEMPT {sym}")
            if order_idx[sym] <= last_idx:
                conflict(f"ATTEMPT out of plan order {sym}")
            if rec.get("rels") != by_sym[sym]["rels"]:
                conflict(f"ATTEMPT rel set mismatch {sym}")
            attempts[sym] = rec
            pending = sym
            last_idx = order_idx[sym]
        elif kind == "COMPLETE":
            if sym not in by_sym or sym not in attempts or sym in completes:
                conflict(f"COMPLETE without pending ATTEMPT {sym!r}")
            if pending != sym:
                conflict(f"COMPLETE {sym} does not close pending {pending}")
            files = rec.get("files")
            if not isinstance(files, dict) or set(files) != set(by_sym[sym]["rels"]):
                conflict(f"COMPLETE rel set mismatch {sym}")
            if any(not (isinstance(v, str) and _HEX64.match(v))
                   for v in files.values()):
                conflict(f"COMPLETE hash not 64-hex {sym}")
            b = rec.get("bytes")
            if not isinstance(b, int) or isinstance(b, bool) or b < 0:
                conflict(f"COMPLETE bytes invalid {sym}")
            completes[sym] = rec
            pending = None
        else:  # HOLD
            if sym is not None and sym not in by_sym:
                conflict(f"HOLD unknown symbol {sym!r}")
            if sym is not None and sym in completes:
                conflict(f"HOLD after COMPLETE for {sym}")
            code = rec.get("code")
            if not isinstance(code, str) or not code.startswith("HOLD:"):
                conflict("HOLD code invalid")
            if not isinstance(rec.get("detail"), str):
                conflict("HOLD detail invalid")
            if not isinstance(rec.get("attempt_consumed"), bool):
                conflict("HOLD attempt_consumed invalid")
            if rec["attempt_consumed"]:
                # exact transition binding: the consumed attempt must be
                # the currently pending one
                if pending is None or sym != pending:
                    conflict("HOLD consumed flag does not bind pending ATTEMPT")
            else:
                if pending is not None:
                    conflict("unconsumed HOLD while an ATTEMPT is pending")
                if sym is not None and order_idx[sym] <= last_idx:
                    conflict("unconsumed HOLD binds a settled symbol")
            hold = rec
    return attempts, completes, hold


# ---------------------------------------------------------------- plan
def load_plan(candidate_path):
    with open(candidate_path, "rb") as f:
        raw = f.read()
    if _sha256(raw) != CANDIDATE_SHA256:
        raise HoldError("HOLD:CANDIDATE_PIN", "candidate SHA-256 mismatch")
    cand = json.loads(raw.decode())
    order = cand["request_order"]
    if len(order) != 52 or cand["call_budget"]["max_requests_total"] != 52:
        raise HoldError("HOLD:CONSTANT_DRIFT", "request count != 52")
    ceil = cand["call_budget"]["ceilings"]
    got = (ceil["bytes_per_symbol"], ceil["payload_budget_bytes"],
           ceil["rows_per_symbol"], ceil["wall_seconds_total"])
    want = (SPEC_BYTES_PER_SYMBOL, SPEC_PAYLOAD_BUDGET,
            SPEC_ROWS_PER_SYMBOL, SPEC_WALL_SECONDS)
    if got != want:
        raise HoldError("HOLD:CONSTANT_DRIFT", f"ceilings {got} != spec {want}")
    symbols = [e["symbol"] for e in order]
    if len(set(symbols)) != 52:
        raise HoldError("HOLD:CONSTANT_DRIFT", "duplicate symbol in order")
    params = cand["request_params"]
    plan = []
    for e in order:
        sym = e["symbol"]
        plan.append({
            "symbol": sym, "class": e["class"], "session": e["session"],
            "interval": params["interval"], "auto_adjust": params["auto_adjust"],
            "prepost": params["prepost"], "actions": params["actions"],
            "required_fields": list(params["required_fields"]),
            "date_policy": params["date_policy"]["form"],
            "start_rule": params["date_policy"]["start"],
            "end_rule": params["date_policy"]["end"],
            "rels": [f"raw/{sym}.csv", f"actions/{sym}.actions.csv",
                     f"meta/{sym}.request.json"],
        })
    return plan


# ---------------------------------------------------------------- fs (dirfd)
def _identity(fd):
    st = os.fstat(fd)
    return (st.st_dev, st.st_ino)


def _ensure_dir(parent_fd, name):
    """Open (creating if needed) a trusted subdirectory dirfd. A pre-existing
    symlink or non-directory component is HOLD:PATH_TYPE."""
    try:
        st = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        st = None
    if st is not None:
        if _stat.S_ISLNK(st.st_mode) or not _stat.S_ISDIR(st.st_mode):
            raise HoldError("HOLD:PATH_TYPE", f"non-directory component {name!r}")
    else:
        os.mkdir(name, 0o755, dir_fd=parent_fd)
        os.fsync(parent_fd)
    try:
        return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                       dir_fd=parent_fd)
    except OSError as e:
        if e.errno in (errno.ELOOP, errno.ENOTDIR):
            raise HoldError("HOLD:PATH_TYPE", f"non-directory component {name!r}")
        raise


def _recheck_dir(parent_fd, name, ident):
    """Post-write identity re-verification of a pinned component."""
    try:
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                     dir_fd=parent_fd)
    except OSError:
        raise HoldError("HOLD:PATH_RACE", f"component {name!r} swapped/vanished")
    try:
        if _identity(fd) != ident:
            raise HoldError("HOLD:PATH_RACE", f"component {name!r} identity changed")
    finally:
        os.close(fd)


def _open_trusted_base(base_dir):
    """Open the base directory through component-wise no-follow traversal
    from the documented trusted parent "/" (spec item 2). Returns the
    pinned base dirfd. The final component is created by mkdirat only if
    absent; any symlink / non-directory component is HOLD:PATH_TYPE."""
    ap = os.path.abspath(base_dir)
    parts = [p for p in ap.split(os.sep) if p]
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for i, part in enumerate(parts):
            last = i == len(parts) - 1
            try:
                st = os.stat(part, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                st = None
            if st is not None and (_stat.S_ISLNK(st.st_mode)
                                   or not _stat.S_ISDIR(st.st_mode)):
                raise HoldError("HOLD:PATH_TYPE",
                                f"base component {part!r} is not a plain directory")
            if st is None:
                if not last:
                    raise HoldError("HOLD:PATH_TYPE",
                                    f"base component {part!r} missing mid-path")
                os.mkdir(part, 0o755, dir_fd=fd)
                os.fsync(fd)
            try:
                nfd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=fd)
            except OSError as e:
                if e.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise HoldError("HOLD:PATH_TYPE",
                                    f"base component {part!r} is not a plain directory")
                raise
            os.close(fd)
            fd = nfd
    except BaseException:
        os.close(fd)
        raise
    return fd


def _is_temp_name(name):
    return name.startswith(".") and name.endswith(".tmp")


def _rename_noreplace(src_fd, src, dst_fd, dst):
    """Atomic no-replace rename (spec item 3). Returns True on success.
    Raises FileExistsError if the destination exists; falls back to a
    link()+unlink protocol when renameat2 is unavailable (ENOSYS/EINVAL)."""
    rc = _libc.syscall(_SYS_RENAMEAT2, ctypes.c_int(src_fd),
                       os.fsencode(src), ctypes.c_int(dst_fd),
                       os.fsencode(dst), ctypes.c_uint(_RENAME_NOREPLACE))
    if rc == 0:
        return True
    e = ctypes.get_errno()
    if e in (errno.EEXIST, errno.ENOTEMPTY):
        raise FileExistsError(e, os.strerror(e), dst)
    if e in (errno.ENOSYS, errno.EINVAL):
        # fallback: hardlink no-replace, then remove ONLY our own temp
        try:
            os.link(src, dst, src_dir_fd=src_fd, dst_dir_fd=dst_fd)
        except FileExistsError:
            raise
        os.unlink(src, dir_fd=src_fd)
        return True
    raise OSError(e, os.strerror(e))


def _write_once_fd(dirfd, name, data):
    """Write-once via temp + hard-link NO-REPLACE publication, fd-relative
    (r4 delta B). The executor-created temp fd stays OPEN from O_EXCL
    creation through final publication and its (dev, ino) is pinned:
    immediately before publication the temp pathname must still name the
    pinned inode (a substituted regular file or symlink is retained
    untouched and yields HOLD:TEMP_COLLISION). Publication is a
    same-directory hard link with follow_symlinks=False; the new final
    path must name the pinned inode — a raced link naming any other inode
    is removed (it is a dirent this call created) and yields
    HOLD:FINAL_COLLISION. Only then is the directory fsynced, the
    still-verified same-run temp unlinked, and the directory fsynced
    again. A destination already present — or appearing after the absence
    check — is retained byte-identical (HOLD:FINAL_COLLISION). Ordinary
    OSError propagates to the caller's durable fail() path."""
    tmp = "." + name + ".tmp"
    try:
        os.stat(name, dir_fd=dirfd, follow_symlinks=False)
        raise HoldError("HOLD:FINAL_COLLISION", f"final path exists: {name}")
    except FileNotFoundError:
        pass
    try:
        os.stat(tmp, dir_fd=dirfd, follow_symlinks=False)
        raise HoldError("HOLD:TEMP_COLLISION", f"pre-existing temp retained: {tmp}")
    except FileNotFoundError:
        pass
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=dirfd)
    try:
        fst = os.fstat(fd)
        tmp_id = (fst.st_dev, fst.st_ino)
        view = memoryview(data)
        while view:
            w = os.write(fd, view)
            view = view[w:]
        os.fsync(fd)
        # temp fd still open; the pathname must still name the pinned inode
        st = os.stat(tmp, dir_fd=dirfd, follow_symlinks=False)
        if _stat.S_ISLNK(st.st_mode) or (st.st_dev, st.st_ino) != tmp_id:
            raise HoldError("HOLD:TEMP_COLLISION",
                            f"temp substituted before publication: {tmp}")
        try:
            os.link(tmp, name, src_dir_fd=dirfd, dst_dir_fd=dirfd,
                    follow_symlinks=False)
        except FileExistsError:
            # destination raced in after our absence check — retained
            raise HoldError("HOLD:FINAL_COLLISION",
                            f"destination appeared during finalization: {name}")
        fst2 = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
        if _stat.S_ISLNK(fst2.st_mode) or (fst2.st_dev, fst2.st_ino) != tmp_id:
            # the link we just created names a substituted inode; remove
            # ONLY that dirent — the foreign file itself is untouched.
            os.unlink(name, dir_fd=dirfd)
            raise HoldError("HOLD:FINAL_COLLISION",
                            f"final path does not name the pinned temp inode: {name}")
        os.fsync(dirfd)
        st2 = os.stat(tmp, dir_fd=dirfd, follow_symlinks=False)
        if _stat.S_ISLNK(st2.st_mode) or (st2.st_dev, st2.st_ino) != tmp_id:
            raise HoldError("HOLD:PATH_RACE",
                            f"temp pathname substituted after link: {tmp}")
        os.unlink(tmp, dir_fd=dirfd)
        os.fsync(dirfd)
    finally:
        os.close(fd)


def _read_file_fd(dirfd, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dirfd)
    try:
        return _read_all(fd)
    finally:
        os.close(fd)


def _census_root(root_fd, sub_fds, plan):
    """Root may contain only the raw/actions/meta pinned dirs and journaled
    payload files; no symlinks/non-regular entries. A stray temp artifact
    is HOLD:TEMP_COLLISION (retained, never deleted)."""
    allowed_dirs = {"raw", "actions", "meta"}
    expected = {rel for p in plan for rel in p["rels"]}
    seen = set()
    for entry in sorted(os.listdir(root_fd)):
        if entry not in allowed_dirs:
            raise HoldError("HOLD:MEMBERSHIP", f"stray capture-root entry {entry!r}")
        st = os.stat(entry, dir_fd=root_fd, follow_symlinks=False)
        if _stat.S_ISLNK(st.st_mode) or not _stat.S_ISDIR(st.st_mode):
            raise HoldError("HOLD:MEMBERSHIP", f"stray capture-root entry {entry!r}")
        sub_fd = sub_fds[entry]
        for name in sorted(os.listdir(sub_fd)):
            st2 = os.stat(name, dir_fd=sub_fd, follow_symlinks=False)
            if _stat.S_ISLNK(st2.st_mode) or not _stat.S_ISREG(st2.st_mode):
                if _is_temp_name(name):
                    raise HoldError("HOLD:TEMP_COLLISION",
                                    f"pre-existing temp retained: {entry}/{name}")
                raise HoldError("HOLD:PATH_TYPE", f"non-regular file {entry}/{name}")
            seen.add(f"{entry}/{name}")
    extra = seen - expected
    for rel in sorted(extra):
        if _is_temp_name(rel.split("/", 1)[1]):
            raise HoldError("HOLD:TEMP_COLLISION", f"pre-existing temp retained: {rel}")
    if extra:
        raise HoldError("HOLD:MEMBERSHIP", f"unjournaled/extra files {sorted(extra)}")
    return seen


# ---------------------------------------------------------------- serialization
def _fmt_num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise HoldError("HOLD:SCHEMA_DRIFT", f"non-numeric bar value {v!r}")
    return repr(v)


def _serialize(req, resp, clock_now_iso):
    """Validate the injected response; return (raw_csv, actions_csv, meta_json).
    Unchanged from r1."""
    if not isinstance(resp, dict):
        raise HoldError("HOLD:SHAPE_DRIFT", "response not an object")
    if resp.get("symbol") != req["symbol"]:
        raise HoldError("HOLD:META_DRIFT", "symbol echo mismatch (unknown symbol)")
    meta_in = resp.get("meta")
    if not isinstance(meta_in, dict) or meta_in.get("session") != req["session"] \
            or meta_in.get("class") != req["class"]:
        raise HoldError("HOLD:META_DRIFT", "session/class echo mismatch")
    for k in ("exchange", "timezone", "currency", "source"):
        if not isinstance(meta_in.get(k), str) or not meta_in[k]:
            raise HoldError("HOLD:META_DRIFT", f"meta missing {k}")
    bars = resp.get("bars")
    if not isinstance(bars, list) or not bars:
        raise HoldError("HOLD:SHAPE_DRIFT", "bars missing/empty")
    fields = req["required_fields"]
    raw_lines = ["Datetime,Open,High,Low,Close,Volume"]
    act_lines = ["Datetime,Dividends,Stock Splits"]
    for row in bars:
        if not isinstance(row, dict) or set(row.keys()) != set(fields) | {"Datetime"}:
            raise HoldError("HOLD:SCHEMA_DRIFT",
                            f"row fields {sorted(row.keys()) if isinstance(row, dict) else row!r}")
        ts = row["Datetime"]
        if not isinstance(ts, str) or not ts:
            raise HoldError("HOLD:SCHEMA_DRIFT", "bad Datetime")
        raw_lines.append(",".join([ts] + [_fmt_num(row[f]) for f in
                                          ("Open", "High", "Low", "Close", "Volume")]))
        act_lines.append(",".join([ts, _fmt_num(row["Dividends"]),
                                   _fmt_num(row["Stock Splits"])]))
    if resp.get("end_covered") is not True:
        raise HoldError("HOLD:PARTIAL_RESPONSE", "end-of-window not covered")
    rows = len(bars)
    if rows > SPEC_ROWS_PER_SYMBOL:
        raise HoldError("HOLD:ROW_CEILING", f"{rows} rows > {SPEC_ROWS_PER_SYMBOL}")
    meta = {
        "symbol": req["symbol"], "class": req["class"], "session": req["session"],
        "interval": req["interval"], "auto_adjust": req["auto_adjust"],
        "prepost": req["prepost"], "actions": req["actions"],
        "required_fields": req["required_fields"],
        "date_policy": req["date_policy"], "start_rule": req["start_rule"],
        "end_rule": req["end_rule"], "rows": rows,
        "exchange": meta_in["exchange"], "timezone": meta_in["timezone"],
        "currency": meta_in["currency"], "source": meta_in["source"],
        "acquisition_utc": clock_now_iso,
    }
    return ("\n".join(raw_lines) + "\n").encode(), \
           ("\n".join(act_lines) + "\n").encode(), \
           _canonical(meta) + b"\n"


# ---------------------------------------------------------------- limiter
class Limiter:
    """One process-wide limiter: >= gap seconds between request starts.
    Unchanged from r1."""

    def __init__(self, clock, gap=SPEC_MIN_START_GAP):
        self.clock = clock
        self.gap = gap
        self._last_start = None

    def wait(self):
        now = self.clock.now()
        if self._last_start is not None:
            delta = now - self._last_start
            if delta < self.gap:
                self.clock.sleep(self.gap - delta)
                now = self.clock.now()
        self._last_start = now
        return now


# ---------------------------------------------------------------- executor
def run_capture(candidate_path, base_dir, capture_id, transport, clock, limiter):
    """Stage the 156 payloads under the journal-fd owner fence. Returns a
    result dict; raises HoldError for named HOLD states. Every handled
    post-journal failure also appends a durable HOLD record to the
    acquisition journal before returning INCOMPLETE_HOLD (spec item 4)."""
    plan = load_plan(candidate_path)
    validate_capture_id(capture_id)
    root_name = capture_id
    control_name = capture_id + ".control"
    # (2) base trust boundary: component-wise no-follow from "/"
    base_fd = _open_trusted_base(base_dir)
    fds = [base_fd]
    journal = None
    # case-collision: a sibling differing only by case is an alias risk
    for entry in os.listdir(base_fd):
        if entry != capture_id and entry.lower() == capture_id.lower():
            raise HoldError("HOLD:CAPTURE_ID_INVALID", f"case collision {entry!r}")
        if entry != control_name and entry.lower() == control_name.lower():
            raise HoldError("HOLD:CAPTURE_ID_INVALID", f"case collision {entry!r}")
    try:
        control_fd = _ensure_dir(base_fd, control_name)
        fds.append(control_fd)
        control_id = _identity(control_fd)

        # (r4-A) coordination fence: flock the pinned control-directory fd
        # nonblocking BEFORE the journal is opened/read, held through run
        # end. A contender is excluded even if the journal pathname is
        # later replaced (empty/copied/symlink) — the fence is on the
        # directory identity, not on any pathname or lock file.
        try:
            fcntl.flock(control_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise HoldError("HOLD:OWNER_BUSY",
                            "a live owner holds the capture control directory")

        # (1) journal fd opened once; flock on it BEFORE any read; the fd
        # is held for every read/append/fsync through run end. No lock file.
        journal = JournalSession(control_fd)
        _jdev, _jino = journal.identity.split(":")
        journal_id = (int(_jdev), int(_jino))

        def _assert_fences():
            """Before every ATTEMPT append / transport call / COMPLETE
            append: the control path and the journal pathname must still
            resolve (no-follow) to the pinned identities. Any replacement
            — empty, copied or symlink — fails closed here."""
            try:
                st = os.stat(control_name, dir_fd=base_fd, follow_symlinks=False)
            except OSError:
                raise HoldError("HOLD:PATH_RACE", "control path vanished")
            if _stat.S_ISLNK(st.st_mode) or (st.st_dev, st.st_ino) != control_id:
                raise HoldError("HOLD:PATH_RACE",
                                "control path no longer names the pinned control dir")
            try:
                st = os.stat(JOURNAL_NAME, dir_fd=control_fd,
                             follow_symlinks=False)
            except OSError:
                raise HoldError("HOLD:JOURNAL_SPLIT", "journal pathname vanished")
            if _stat.S_ISLNK(st.st_mode) or not _stat.S_ISREG(st.st_mode) \
                    or (st.st_dev, st.st_ino) != journal_id:
                raise HoldError(
                    "HOLD:JOURNAL_SPLIT",
                    "journal pathname no longer names the locked journal inode")

        _assert_fences()

        records = journal.read_records()
        attempts, completes, hold = _validate_records(
            records, plan, capture_id, journal.identity)
        if hold is not None:
            # (4) a durable terminal HOLD is reproduced BEFORE the capture
            # tree is touched, so it stays reproducible even when the tree
            # itself was damaged by the failure that produced the HOLD.
            raise HoldError(hold["code"],
                            hold["detail"] + " [durable HOLD record]")

        root_fd = _ensure_dir(base_fd, root_name)
        fds.append(root_fd)
        sub_fds = {}
        for d in ("raw", "actions", "meta"):
            sub_fds[d] = _ensure_dir(root_fd, d)
            fds.append(sub_fds[d])
        identities = {"root": _identity(root_fd),
                      "control": _identity(control_fd),
                      **{d: _identity(sub_fds[d]) for d in sub_fds}}

        def recheck_all():
            _recheck_dir(base_fd, root_name, identities["root"])
            _recheck_dir(base_fd, control_name, identities["control"])
            for d in ("raw", "actions", "meta"):
                _recheck_dir(root_fd, d, identities[d])

        on_disk = _census_root(root_fd, sub_fds, plan)

        result = {"task": TASK_ID, "capture_id": capture_id, "status": None,
                  "code": None, "calls_this_run": 0, "states": {},
                  "payload_bytes": 0}
        t0 = clock.now()

        def durability_result(cause):
            """(r4-C) centralized journal-append failure outcome: the run
            returns HOLD:JOURNAL_DURABILITY and no cause is claimed to
            have been recorded durably."""
            result.update(status="INCOMPLETE_HOLD",
                          code="HOLD:JOURNAL_DURABILITY",
                          detail=f"journal append failed ({cause}); "
                                 f"no cause recorded durably")
            return result

        def fail(code, detail, sym, consumed):
            """(4) one durable HOLD append on the locked journal fd, then
            INCOMPLETE_HOLD. If the durable append/fsync itself fails, the
            result is HOLD:JOURNAL_DURABILITY and the original cause is
            NOT claimed as recorded."""
            try:
                journal.append({
                    "type": "HOLD", "capture_id": capture_id, "symbol": sym,
                    "code": code, "detail": detail,
                    "attempt_consumed": consumed, "clock": clock.now()})
            except Exception as e:
                result.update(status="INCOMPLETE_HOLD",
                              code="HOLD:JOURNAL_DURABILITY",
                              detail=f"durable HOLD append failed ({type(e).__name__}); "
                                     f"original cause {code} NOT recorded")
                return result
            result.update(status="INCOMPLETE_HOLD", code=code)
            if sym is not None and consumed:
                result["states"][sym] = "ATTEMPT_CONSUMED"
            return result

        # ---- restart reconciliation before any new attempt ----
        for p in plan:
            sym = p["symbol"]
            if sym in completes:
                rec = completes[sym]
                actual = 0
                actual_hashes = {}
                missing = False
                for rel in p["rels"]:
                    d, name = rel.split("/", 1)
                    if rel not in on_disk:
                        missing = True
                        break
                    data = _read_file_fd(sub_fds[d], name)
                    actual_hashes[rel] = _sha256(data)
                    actual += len(data)
                if missing:
                    raise HoldError("HOLD:FINAL_MISMATCH",
                                    f"completed triplet missing: {sym}")
                # (5) the record must EQUAL the recomputed truth; a false
                # bytes total or hash is corruption, never corrected away
                if actual != rec["bytes"] or actual_hashes != rec["files"]:
                    raise HoldError("HOLD:JOURNAL_CONFLICT",
                                    f"COMPLETE record disagrees with files: {sym} "
                                    f"(record bytes={rec['bytes']} actual={actual})")
                result["states"][sym] = "SKIP_VERIFIED"
                result["payload_bytes"] += actual
            elif sym in attempts:
                raise HoldError("HOLD:ATTEMPT_CONSUMED_AMBIGUOUS",
                                f"attempt without COMPLETE: {sym}")
            else:
                stray = [r for r in p["rels"] if r in on_disk]
                if stray:
                    raise HoldError("HOLD:FINAL_MISMATCH",
                                    f"files without journal records: {sym} {stray}")
                result["states"][sym] = "ELIGIBLE"

        # ---- acquisition loop ----
        for p in plan:
            sym = p["symbol"]
            if result["states"][sym] != "ELIGIBLE":
                continue
            if clock.now() - t0 > SPEC_WALL_SECONDS:
                return fail("HOLD:WALL_CEILING", "wall ceiling before attempt",
                            None, False)
            limiter.wait()
            # (4) wall re-check AFTER the limiter sleep, before ATTEMPT/call;
            # the forbidden start consumes no attempt.
            if clock.now() - t0 >= SPEC_WALL_SECONDS:
                return fail("HOLD:WALL_CEILING",
                            "wall ceiling reached during limiter wait",
                            sym, False)
            # (r4-A) fence re-verification before the ATTEMPT append and
            # the transport call it authorizes; raises a run-level
            # HOLD:JOURNAL_SPLIT / HOLD:PATH_RACE with zero further calls.
            _assert_fences()
            # (r4-C) a failed ATTEMPT append is terminal durability
            # failure: no transport call may follow it.
            try:
                journal.append({
                    "type": "ATTEMPT", "capture_id": capture_id, "symbol": sym,
                    "rels": p["rels"], "clock": clock.now()})
            except Exception as e:
                return durability_result(
                    f"ATTEMPT append: {type(e).__name__}")
            result["calls_this_run"] += 1
            req = {k: p[k] for k in ("symbol", "class", "session", "interval",
                                     "auto_adjust", "prepost", "actions",
                                     "required_fields")}
            try:
                resp = transport(req)
            except TransportFailure as e:
                code = "HOLD:THROTTLE_429" if e.status == 429 else "HOLD:TRANSPORT"
                return fail(code, f"transport failure status={e.status}",
                            sym, True)
            except Exception as e:
                return fail("HOLD:TRANSPORT", f"transport raised {type(e).__name__}",
                            sym, True)
            if isinstance(resp, dict) and resp.get("status") not in (None, 200):
                code = "HOLD:THROTTLE_429" if resp.get("status") == 429 else "HOLD:TRANSPORT"
                return fail(code, f"transport status {resp.get('status')}",
                            sym, True)
            # (r4-A) the owner detects a journal/control split before any
            # further work on this attempt; the detection itself is the
            # durable record via fail() on the still-pinned journal fd.
            try:
                _assert_fences()
            except HoldError as e:
                return fail(e.code, e.detail, sym, True)
            try:
                raw_b, act_b, meta_b = _serialize(p, resp, clock.iso())
                triplet = {p["rels"][0]: raw_b, p["rels"][1]: act_b,
                           p["rels"][2]: meta_b}
                sym_bytes = sum(len(b) for b in triplet.values())
                if sym_bytes > SPEC_BYTES_PER_SYMBOL:
                    raise HoldError("HOLD:SYMBOL_CEILING",
                                    f"{sym} {sym_bytes} > {SPEC_BYTES_PER_SYMBOL}")
                if result["payload_bytes"] + sym_bytes > SPEC_PAYLOAD_BUDGET:
                    raise HoldError("HOLD:TOTAL_CEILING",
                                    f"payload budget {SPEC_PAYLOAD_BUDGET} would breach")
                if clock.now() - t0 > SPEC_WALL_SECONDS:
                    raise HoldError("HOLD:WALL_CEILING", "wall limit before COMPLETE")
            except HoldError as e:
                return fail(e.code, e.detail, sym, True)
            # (4)+(r4-C) ALL post-ATTEMPT filesystem/finalization/
            # path-race failures are routed through the durable fail()
            # path; ordinary OSError (write/fsync/link/unlink/recheck)
            # becomes HOLD:FILESYSTEM, never an escaping exception.
            hashes = {}
            try:
                for rel in p["rels"]:
                    d, name = rel.split("/", 1)
                    _write_once_fd(sub_fds[d], name, triplet[rel])
                    hashes[rel] = _sha256(triplet[rel])
                recheck_all()   # component identity verified before COMPLETE
                _assert_fences()
            except HoldError as e:
                return fail(e.code, e.detail, sym, True)
            except OSError as e:
                return fail("HOLD:FILESYSTEM",
                            f"{type(e).__name__}: {e}", sym, True)
            # (r4-C) a failed COMPLETE append is terminal durability
            # failure; nothing is claimed recorded.
            try:
                journal.append({
                    "type": "COMPLETE", "capture_id": capture_id, "symbol": sym,
                    "files": hashes, "bytes": sym_bytes, "clock": clock.now()})
            except Exception as e:
                return durability_result(
                    f"COMPLETE append: {type(e).__name__}")
            result["payload_bytes"] += sym_bytes
            result["states"][sym] = "COMPLETE"

        recheck_all()
        done = all(result["states"][p["symbol"]] in ("COMPLETE", "SKIP_VERIFIED")
                   for p in plan)
        result["status"] = "COMPLETE" if done else "INCOMPLETE_HOLD"
        if done:
            result["code"] = "OK"
        return result
    finally:
        if journal is not None:
            journal.close()
        for fd in reversed(fds):
            os.close(fd)
