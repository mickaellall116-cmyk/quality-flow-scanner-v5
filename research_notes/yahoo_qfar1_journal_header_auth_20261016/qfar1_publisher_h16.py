"""QFAR1 single-blob archive publisher — -15 RECOVERY-ATOMICITY CANDIDATE (isolated offline).

Derived from the pinned -14 trust-hardening source (package cf929e0,
qfar1_publisher_h14.py sha256 074ade29…); the -13/-14 packages are immutable
evidence and are not modified. Recovery-atomicity fixes per Issue #1 -15 spec
(comment 6207508054): the journal frame boundary itself is protected (fixed
magic/version, bounded length cross-checked against its complement, checksum
over framing + payload); journal recovery truncates a torn tail to the exact
verified end under the per-capture fence before any append, so no record is
ever appended behind unvalidated bytes; the two-file staging allocation is
all-or-nothing (a second-create failure closes and unlinks the first;
cleanup failure is HOLD:STAGING_CLEANUP).

Implements QF-YAHOO-SINGLE-BLOB-ARCHIVE-DESIGN-20261015-12 r3 as corrected by
the final adjudication (Issue #1 comment 6205968339): all derived constants are
computed from the internally pinned frozen rel set and asserted against the
adjudicated values; hardcoding a total without deriving it is a drift failure.

Public surface: exactly `publish` and `HoldError` (plus underscored internals
used by the preflight fixture driver). No network code exists in this module;
the `remote` argument is any object implementing the Git Data surface used
here (the preflight supplies a no-socket fake).
"""
import base64
import fcntl
import hashlib
import itertools
import json
import os
import re
import struct

# ---------------------------------------------------------------- constants
CEILING = 67_108_864                    # QF_SHARED_TOTAL_CEILING_BYTES (sum of 158 physical members)
PER_MEMBER_GUARD = 33_554_432           # 32 MiB member-level guard
MAGIC = b"QFAR0001"
VERSION = 1
HEADER_BYTES = 16                       # 8 magic + 4 version + 4 count
TRAILER_BYTES = 32
INDEX_FIXED_PER_ENTRY = 42              # 2 (u16 rel len) + 8 (u64 len) + 32 (sha256)
FROZEN_MANIFEST_SHA256 = "634c4541a8b30ade50e45898e80ee65806fa323c953020edc149530642d9bef3"
DESIGNATED_OWNER = "mickaellall116-cmyk"
DESIGNATED_REPO = "qf-data-archive"
REF = "refs/heads/qf-archive"
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
_CAPTURE_ID_RE = re.compile(r"[A-Z0-9][A-Z0-9-]*[A-Z0-9]\Z")
_PIN_RE = re.compile(r"[0-9a-f]{64}")


def _require_pins(validation_pins, payload_rels):
    """Independently supplied validation pins are MANDATORY (-14 req 1):
    exactly the 156 payload rels, each a 64-lowercase-hex sha256. There is
    no default, no None and no current-disk fallback."""
    if not isinstance(validation_pins, dict):
        raise HoldError("HOLD:PINS_INVALID", "validation pins missing or not a mapping")
    if set(validation_pins.keys()) != set(payload_rels):
        raise HoldError("HOLD:PINS_INVALID",
                        "pin key set != exactly the 156 payload rels")
    for rel, hx in validation_pins.items():
        if not isinstance(hx, str) or _PIN_RE.fullmatch(hx) is None:
            raise HoldError("HOLD:PINS_INVALID", f"pin for {rel} is not 64 lowercase hex")
_CHUNK = 1 << 20

# Adjudicated values (comment 6205968339). Derived programmatically below and
# asserted equal; any drift is a hard failure, never silently accepted.
ADJUDICATED = {
    "sum_rel_len_158": 3057,
    "index_bytes": 9693,
    "overhead_bytes": 9741,
    "max_container_bytes": 67118605,
    "max_base64_bytes": 89491476,
    "sums_bytes": 13566,
    "manifest_template_max_bytes": 18598,
    "reserve_bytes": 32164,
    "payload_budget_bytes": 67076700,
}


class HoldError(Exception):
    def __init__(self, code, detail=""):
        self.code = code
        super().__init__(code + ((" " + detail) if detail else ""))


class _ApiError(Exception):
    """Raised by remotes for HTTP-style failures (status carried)."""
    def __init__(self, status, msg=""):
        self.status = status
        super().__init__(f"api {status} {msg}")


class _TransportLost(Exception):
    """The request was applied but its response was lost."""


# ---------------------------------------------------------------- membership
def _load_membership(manifest_path):
    raw = open(manifest_path, "rb").read()
    if hashlib.sha256(raw).hexdigest() != FROZEN_MANIFEST_SHA256:
        raise HoldError("HOLD:MANIFEST_PIN", "frozen capture manifest hash drift")
    doc = json.loads(raw.decode("utf-8"))
    symbols = [e["symbol"] for e in doc["request_order"]]
    if len(symbols) != 52 or len(set(symbols)) != 52:
        raise HoldError("HOLD:MANIFEST_PIN", "frozen symbol set is not 52 unique")
    payload_rels = sorted(
        [f"raw/{s}.csv" for s in symbols]
        + [f"actions/{s}.actions.csv" for s in symbols]
        + [f"meta/{s}.request.json" for s in symbols]
    )
    all_rels = sorted(payload_rels + ["manifest.json", "SHA256SUMS"])
    return symbols, payload_rels, all_rels


def _canonical_manifest(capture_id, files):
    obj = {"capture_id": capture_id, "files": files, "format": "QFAR1-MANIFEST/1"}
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")


def _canonical_sums(entries):
    # entries: {rel: sha256hex} over exactly the 156 payloads + manifest.json
    lines = [f"{entries[r]}  {r}\n" for r in sorted(entries)]
    return "".join(lines).encode("ascii")


def derive_constants(manifest_path):
    """Compute every derived quantity from the pinned rel set; assert adjudicated."""
    symbols, payload_rels, all_rels = _load_membership(manifest_path)
    sum_len_158 = sum(len(r) for r in all_rels)
    sum_len_157 = sum(len(r) for r in payload_rels + ["manifest.json"])
    index_bytes = 158 * INDEX_FIXED_PER_ENTRY + sum_len_158
    overhead = HEADER_BYTES + index_bytes + TRAILER_BYTES
    max_container = CEILING + overhead
    max_b64 = 4 * ((max_container + 2) // 3)
    sums_bytes = 157 * 67 + sum_len_157
    template_files = {r: {"length": 99999999, "sha256": "0" * 64} for r in payload_rels}
    manifest_template_max = len(_canonical_manifest("X" * 64, template_files))
    reserve = manifest_template_max + sums_bytes
    got = {
        "sum_rel_len_158": sum_len_158,
        "index_bytes": index_bytes,
        "overhead_bytes": overhead,
        "max_container_bytes": max_container,
        "max_base64_bytes": max_b64,
        "sums_bytes": sums_bytes,
        "manifest_template_max_bytes": manifest_template_max,
        "reserve_bytes": reserve,
        "payload_budget_bytes": CEILING - reserve,
    }
    for k, v in ADJUDICATED.items():
        if got[k] != v:
            raise HoldError("HOLD:CONSTANT_DRIFT", f"{k}: derived {got[k]} != adjudicated {v}")
    got.update({"ceiling": CEILING, "symbols": symbols, "payload_rels": payload_rels,
                "all_rels": all_rels, "n_payloads": 156, "n_members": 158})
    return got


# ---------------------------------------------------------------- capture-ID
def _validate_capture_id(capture_id):
    if (not isinstance(capture_id, str) or not (8 <= len(capture_id) <= 64)
            or "--" in capture_id or not _CAPTURE_ID_RE.match(capture_id)):
        raise HoldError("HOLD:ID_INVALID", repr(capture_id))


# ---------------------------------------------------------------- fd-walk reads (R-3)
def _open_root(path):
    try:
        return os.open(path, _DIR_FLAGS)
    except OSError as e:
        raise HoldError("HOLD:PATH_TYPE", f"capture root: {e.strerror}")


def _stat_at(dir_fd, name):
    return os.stat(name, dir_fd=dir_fd, follow_symlinks=False)


def _census(root_fd, payload_rels):
    """fd-relative census: {rel: (dev, ino, size)} for payloads; dir inodes pinned.
    Any non-regular file, symlink, missing or extra entry -> HOLD before reads."""
    import stat as _stat
    census = {}
    dir_inodes = {}
    expected_dirs = {"raw": set(), "actions": set(), "meta": set()}
    for rel in payload_rels:
        d, name = rel.split("/", 1)
        expected_dirs[d].add(name)
    root_st = os.fstat(root_fd)
    dir_inodes[""] = (root_st.st_dev, root_st.st_ino)
    found = set()
    top = set(os.listdir(root_fd))
    if not top.issubset({"raw", "actions", "meta", "manifest.json", "SHA256SUMS"}):
        raise HoldError("HOLD:MEMBERSHIP", f"unexpected top-level entries: {sorted(top - {'raw','actions','meta','manifest.json','SHA256SUMS'})}")
    for d, names in expected_dirs.items():
        if d not in top:
            raise HoldError("HOLD:MEMBERSHIP", f"missing directory {d}")
        st = _stat_at(root_fd, d)
        if not _stat.S_ISDIR(st.st_mode) or _stat.S_ISLNK(st.st_mode):
            raise HoldError("HOLD:PATH_TYPE", f"{d} is not a real directory")
        dir_inodes[d] = (st.st_dev, st.st_ino)
        dfd = os.open(d, _DIR_FLAGS, dir_fd=root_fd)
        try:
            present = set(os.listdir(dfd))
            if present != names:
                raise HoldError("HOLD:MEMBERSHIP",
                                f"{d}: missing={sorted(names - present)} extra={sorted(present - names)}")
            for name in names:
                fst = _stat_at(dfd, name)
                if not _stat.S_ISREG(fst.st_mode):
                    raise HoldError("HOLD:PATH_TYPE", f"{d}/{name} not a regular file")
                census[f"{d}/{name}"] = (fst.st_dev, fst.st_ino, fst.st_size)
                found.add(f"{d}/{name}")
        finally:
            os.close(dfd)
    for bk in ("manifest.json", "SHA256SUMS"):
        if bk in top:
            bst = _stat_at(root_fd, bk)
            import stat as _s2
            if not _s2.S_ISREG(bst.st_mode):
                raise HoldError("HOLD:PATH_TYPE", f"{bk} not a regular file")
            census[bk] = (bst.st_dev, bst.st_ino, bst.st_size)
    if found != set(payload_rels):
        raise HoldError("HOLD:MEMBERSHIP", "payload set mismatch")
    return census, dir_inodes


def _walk_open(root_fd, rel, dir_inodes):
    """Open rel component-wise with O_NOFOLLOW on EVERY component, starting at
    the pinned root fd. Returns (fd, fstat). Directory identity is re-checked
    against the census pins during the walk (legitimate-directory swap)."""
    parts = rel.split("/")
    cur = root_fd
    owned = []
    try:
        for i, comp in enumerate(parts):
            last = i == len(parts) - 1
            fd = os.open(comp, _DIR_FLAGS if not last else _FILE_FLAGS, dir_fd=cur)
            owned.append(fd)
            st = os.fstat(fd)
            if not last:
                drel = "/".join(parts[: i + 1])
                pin = dir_inodes.get(drel)
                if pin is not None and (st.st_dev, st.st_ino) != pin:
                    raise HoldError("HOLD:READ_DRIFT", f"directory {drel} identity changed")
            cur = fd
        return cur, st
    except HoldError:
        for fd in owned:
            os.close(fd)
        raise
    except OSError as e:
        for fd in owned:
            try:
                os.close(fd)
            except OSError:
                pass
        raise HoldError("HOLD:PATH_TYPE", f"open {rel}: {e.strerror}")


def _close_walk(root_fd, fd):
    # _walk_open returns the leaf fd; intermediate fds were tracked by caller
    # pattern: we re-walk per member and close only the leaf + intermediates
    # recorded on the fd chain is not tracked; instead _walk_open keeps them
    # open intentionally is wrong — see _read_member which uses _walk_chain.
    os.close(fd)


def _walk_chain(root_fd, rel, dir_inodes):
    """Like _walk_open but returns (leaf_fd, [all fds]) for clean closing."""
    parts = rel.split("/")
    fds = []
    cur = root_fd
    try:
        for i, comp in enumerate(parts):
            last = i == len(parts) - 1
            fd = os.open(comp, _DIR_FLAGS if not last else _FILE_FLAGS, dir_fd=cur)
            fds.append(fd)
            st = os.fstat(fd)
            if not last:
                drel = "/".join(parts[: i + 1])
                pin = dir_inodes.get(drel)
                if pin is not None and (st.st_dev, st.st_ino) != pin:
                    raise HoldError("HOLD:READ_DRIFT", f"directory {drel} identity changed")
            cur = fd
        return cur, os.fstat(cur), fds
    except HoldError:
        for fd in fds:
            os.close(fd)
        raise
    except OSError as e:
        for fd in fds:
            try:
                os.close(fd)
            except OSError:
                pass
        raise HoldError("HOLD:PATH_TYPE", f"open {rel}: {e.strerror}")


def _read_member(root_fd, rel, census, dir_inodes, spool, read_hook=None):
    """Read one member via its walked fd into `spool` (a writable file object),
    hashing incrementally. Census (dev, ino, size) verified before and after."""
    pin = census[rel]
    fd, st, chain = _walk_chain(root_fd, rel, dir_inodes)
    try:
        if (st.st_dev, st.st_ino, st.st_size) != pin:
            raise HoldError("HOLD:READ_DRIFT", f"{rel} identity/size drift at open")
        h = hashlib.sha256()
        total = 0
        while True:
            chunk = os.pread(fd, _CHUNK, total)
            if not chunk:
                break
            h.update(chunk)
            spool.write(chunk)
            total += len(chunk)
            if read_hook is not None:
                read_hook(rel, total)
        st2 = os.fstat(fd)
        if (st2.st_dev, st2.st_ino, st2.st_size) != pin or total != pin[2]:
            raise HoldError("HOLD:READ_DRIFT", f"{rel} drift during/after read")
        return total, h.hexdigest()
    finally:
        for f in chain:
            os.close(f)


# ---------------------------------------------------------------- bookkeeping scope checks
def _check_manifest_scope(manifest_bytes, payload_rels):
    try:
        doc = json.loads(manifest_bytes.decode("utf-8"))
        files = doc["files"]
    except Exception:
        raise HoldError("HOLD:MANIFEST_SCOPE", "manifest unparsable")
    if set(files.keys()) != set(payload_rels) or doc.get("format") != "QFAR1-MANIFEST/1":
        raise HoldError("HOLD:MANIFEST_SCOPE", "manifest files map != 156 payloads")
    return doc


def _check_sums_scope(sums_bytes, payload_rels):
    try:
        text = sums_bytes.decode("ascii")
    except Exception:
        raise HoldError("HOLD:SUMS_SCOPE", "SHA256SUMS not ascii")
    lines = text.split("\n")
    if lines[-1] != "":
        raise HoldError("HOLD:SUMS_SCOPE", "SHA256SUMS must end with LF")
    lines = lines[:-1]
    if len(lines) != 157:
        raise HoldError("HOLD:SUMS_SCOPE", f"SHA256SUMS has {len(lines)} lines, need 157")
    rels = []
    for ln in lines:
        if len(ln) < 67 or ln[64] != " " or ln[65] != " ":
            raise HoldError("HOLD:SUMS_SCOPE", "SHA256SUMS line shape")
        rels.append(ln[66:])
    if rels != sorted(rels) or set(rels) != set(payload_rels) | {"manifest.json"}:
        raise HoldError("HOLD:SUMS_SCOPE", "SHA256SUMS rel set != 156 payloads + manifest.json")
    return {ln[66:]: ln[:64] for ln in lines}


# ---------------------------------------------------------------- container build (streaming, sealed fd)
def build_container(cap_dir, capture_id, staging_dir, manifest_path,
                    validation_pins, phase_hook=None, read_hook=None):
    """Seal the capture at cap_dir into a QFAR1 container temp file under
    staging_dir. Returns info dict incl. an OPEN fd positioned at 0 (caller
    owns it), container length, CONTAINER_SHA256 (trailer value), blob id and
    the member pin set {rel: (length, sha256)}."""
    _validate_capture_id(capture_id)
    consts = derive_constants(manifest_path)
    payload_rels, all_rels = consts["payload_rels"], consts["all_rels"]
    _require_pins(validation_pins, payload_rels)
    root_fd = _open_root(cap_dir)
    try:
        census, dir_inodes = _census(root_fd, payload_rels)
        if phase_hook:
            phase_hook("census")
        os.makedirs(staging_dir, exist_ok=True)
        stage_fd = os.open(staging_dir, _DIR_FLAGS)
        spool_name = _staging_name("spool")
        cont_name = _staging_name("container")
        spool_fd = None
        cont_fd = None
        try:
            try:
                spool_fd = os.open(spool_name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                   0o600, dir_fd=stage_fd)
                cont_fd = os.open(cont_name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                  0o600, dir_fd=stage_fd)
            except BaseException as alloc_err:
                # all-or-nothing (-15 req 5): whatever this attempt created is
                # closed and unlinked before the failure surfaces. A rollback
                # failure is its own named HOLD, never silently masked.
                cleanup_err = None
                for _fd, _nm in ((cont_fd, cont_name), (spool_fd, spool_name)):
                    if _fd is None:
                        continue
                    try:
                        os.close(_fd)
                    except OSError as e:
                        cleanup_err = cleanup_err or e
                    try:
                        os.unlink(_nm, dir_fd=stage_fd)
                    except FileNotFoundError:
                        pass
                    except OSError as e:
                        cleanup_err = cleanup_err or e
                if cleanup_err is not None:
                    raise HoldError("HOLD:STAGING_CLEANUP",
                                    f"staging rollback failed: {cleanup_err.strerror}")
                if isinstance(alloc_err, FileExistsError):
                    raise HoldError("HOLD:STAGING_COLLISION",
                                    "attempt-unique staging name collided")
                raise
        finally:
            os.close(stage_fd)
        spool = os.fdopen(os.dup(spool_fd), "wb")
        pins = {}
        try:
            # payloads -> spool, hashing; census re-verified per member
            for rel in payload_rels:
                if census[rel][2] > PER_MEMBER_GUARD:
                    raise HoldError("HOLD:CEILING", f"{rel} exceeds per-member guard")
                n, hx = _read_member(root_fd, rel, census, dir_inodes, spool, read_hook)
                if validation_pins[rel] != hx:
                    raise HoldError("HOLD:MEMBER_DRIFT", f"{rel} != validation pin")
                pins[rel] = (n, hx)
            spool.flush()
            # bookkeeping members (rebuilt canonically; if present on disk they
            # must match the rebuild byte-for-byte after scope checks)
            files_map = {r: {"length": pins[r][0], "sha256": pins[r][1]} for r in payload_rels}
            manifest_bytes = _canonical_manifest(capture_id, files_map)
            sums_map = {r: pins[r][1] for r in payload_rels}
            sums_map["manifest.json"] = hashlib.sha256(manifest_bytes).hexdigest()
            sums_bytes = _canonical_sums(sums_map)
            _check_manifest_scope(manifest_bytes, payload_rels)
            _check_sums_scope(sums_bytes, payload_rels)
            for bk, want in (("manifest.json", manifest_bytes), ("SHA256SUMS", sums_bytes)):
                if bk in census:
                    tmp = _TmpBuf()
                    n, hx = _read_member(root_fd, bk, census, dir_inodes, tmp, None)
                    got = tmp.data
                    if bk == "manifest.json":
                        _check_manifest_scope(got, payload_rels)
                    else:
                        _check_sums_scope(got, payload_rels)
                    if got != want:
                        raise HoldError("HOLD:MEMBER_DRIFT", f"on-disk {bk} != canonical rebuild")
                pins[bk] = (len(want), hashlib.sha256(want).hexdigest())
            total_physical = sum(pins[r][0] for r in all_rels)
            if total_physical > CEILING:
                raise HoldError("HOLD:CEILING", f"sum physical {total_physical} > {CEILING}")
            if phase_hook:
                phase_hook("prescribed")
            # assemble: header + index, then spool payloads in index order + bookkeeping
            index = bytearray()
            for rel in all_rels:
                rb = rel.encode("ascii")
                index += struct.pack(">H", len(rb)) + rb + struct.pack(">Q", pins[rel][0]) \
                    + bytes.fromhex(pins[rel][1])
            header = MAGIC + struct.pack(">I", VERSION) + struct.pack(">I", len(all_rels))
            trailer_h = hashlib.sha256()
            w = os.fdopen(os.dup(cont_fd), "wb")
            try:
                for part in (header, bytes(index)):
                    w.write(part)
                    trailer_h.update(part)
                os.lseek(spool_fd, 0, os.SEEK_SET)
                spool_map = {}
                off = 0
                for rel in payload_rels:
                    spool_map[rel] = off
                    off += pins[rel][0]
                for rel in all_rels:
                    if rel == "manifest.json":
                        w.write(manifest_bytes); trailer_h.update(manifest_bytes)
                    elif rel == "SHA256SUMS":
                        w.write(sums_bytes); trailer_h.update(sums_bytes)
                    else:
                        left = pins[rel][0]
                        pos = spool_map[rel]
                        while left:
                            chunk = os.pread(spool_fd, min(_CHUNK, left), pos)
                            if not chunk:
                                raise HoldError("HOLD:CONTAINER_FORMAT", "spool short")
                            w.write(chunk); trailer_h.update(chunk)
                            pos += len(chunk); left -= len(chunk)
                trailer = trailer_h.digest()
                w.write(trailer)
                w.flush()
                os.fsync(cont_fd)
            finally:
                w.close()
            container_len = HEADER_BYTES + len(index) + total_physical + TRAILER_BYTES
            expect = total_physical + consts["overhead_bytes"]
            if container_len != expect:
                raise HoldError("HOLD:CONTAINER_FORMAT", "container length != formula")
            os.lseek(cont_fd, 0, os.SEEK_SET)
            # self-check: parse back from the sealed fd and verify the DAG
            parsed = parse_container_fd(cont_fd, container_len, payload_rels)
            _verify_dag(parsed, {r: {"length": pins[r][0], "sha256": pins[r][1]} for r in all_rels},
                        payload_rels)
            os.lseek(cont_fd, 0, os.SEEK_SET)
            blob_id = _git_blob_id(cont_fd, container_len)
            os.lseek(cont_fd, 0, os.SEEK_SET)
            # final re-census: any drift anywhere during the build is fatal
            census2, _ = _census(root_fd, payload_rels)
            if census2 != census:
                raise HoldError("HOLD:READ_DRIFT", "tree changed during build")
            _unlink_stage(staging_dir, spool_name)
            _unlink_stage(staging_dir, cont_name)
            return {
                "fd": cont_fd, "spool_fd": spool_fd, "container_len": container_len,
                "container_sha256": parsed["trailer_hex"], "blob_id": blob_id,
                "pins": {r: {"length": pins[r][0], "sha256": pins[r][1]} for r in all_rels},
                "payload_pins": {r: pins[r][1] for r in payload_rels},
                "total_physical": total_physical, "consts": consts,
                "staging_dir": staging_dir,
            }
        except BaseException:
            os.close(spool_fd); os.close(cont_fd)
            spool.close()
            _unlink_stage_quiet(staging_dir, spool_name)
            _unlink_stage_quiet(staging_dir, cont_name)
            raise
    finally:
        os.close(root_fd)


class _TmpBuf:
    def __init__(self):
        self.data = b""
    def write(self, b):
        self.data += b


def _git_blob_id(fd, length):
    h = hashlib.sha1()
    h.update(b"blob %d\x00" % length)
    pos = 0
    while pos < length:
        chunk = os.pread(fd, min(_CHUNK, length - pos), pos)
        if not chunk:
            raise HoldError("HOLD:CONTAINER_FORMAT", "short sealed fd")
        h.update(chunk)
        pos += len(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- container parse + DAG verify (streaming)
def parse_container_fd(fd, length, payload_rels):
    """Parse a QFAR1 container from fd. Returns {trailer_hex, members:{rel:(len,sha)}}.
    Raises the design's HOLD codes on any format/scope problem. Hash-level DAG
    edges are checked by _verify_dag."""
    def read_at(pos, n):
        out = b""
        while len(out) < n:
            c = os.pread(fd, n - len(out), pos + len(out))
            if not c:
                raise HoldError("HOLD:CONTAINER_FORMAT", "unexpected EOF")
            out += c
        return out
    if length < HEADER_BYTES + TRAILER_BYTES:
        raise HoldError("HOLD:CONTAINER_FORMAT", "container too short")
    head = read_at(0, HEADER_BYTES)
    if head[:8] != MAGIC:
        raise HoldError("HOLD:CONTAINER_FORMAT", "bad magic")
    version, count = struct.unpack(">II", head[8:16])
    if version != VERSION or count != 158:
        raise HoldError("HOLD:CONTAINER_FORMAT", f"version/count {version}/{count}")
    pos = HEADER_BYTES
    entries = []
    prev = None
    for _ in range(count):
        (llen,) = struct.unpack(">H", read_at(pos, 2)); pos += 2
        if not (1 <= llen <= 1024):
            raise HoldError("HOLD:CONTAINER_FORMAT", "rel length out of range")
        rel = read_at(pos, llen); pos += llen
        (plen,) = struct.unpack(">Q", read_at(pos, 8)); pos += 8
        ph = read_at(pos, 32); pos += 32
        try:
            rel_s = rel.decode("ascii")
        except Exception:
            raise HoldError("HOLD:CONTAINER_FORMAT", "rel not ascii")
        if prev is not None and rel <= prev:
            raise HoldError("HOLD:CONTAINER_FORMAT", "index not strictly increasing")
        prev = rel
        entries.append((rel_s, plen, ph.hex()))
    payload_start = pos
    total = sum(e[1] for e in entries)
    if payload_start + total + TRAILER_BYTES != length:
        raise HoldError("HOLD:CONTAINER_FORMAT", "length fields inconsistent with container length")
    trailer_stored = read_at(length - TRAILER_BYTES, TRAILER_BYTES)
    h = hashlib.sha256()
    pos = 0
    end = length - TRAILER_BYTES
    while pos < end:
        c = os.pread(fd, min(_CHUNK, end - pos), pos)
        if not c:
            raise HoldError("HOLD:CONTAINER_FORMAT", "unexpected EOF hashing")
        h.update(c); pos += len(c)
    if h.digest() != trailer_stored:
        raise HoldError("HOLD:CONTAINER_FORMAT", "trailer mismatch")
    members = {}
    off = payload_start
    member_bytes = {}
    for rel_s, plen, ph in entries:
        mh = hashlib.sha256()
        p = off
        left = plen
        buf = bytearray() if rel_s in ("manifest.json", "SHA256SUMS") else None
        while left:
            c = os.pread(fd, min(_CHUNK, left), p)
            if not c:
                raise HoldError("HOLD:CONTAINER_FORMAT", "payload EOF")
            mh.update(c)
            if buf is not None:
                buf += c
            p += len(c); left -= len(c)
        if mh.hexdigest() != ph:
            raise HoldError("HOLD:MEMBER_DRIFT", f"{rel_s} != index hash")
        members[rel_s] = (plen, ph)
        if buf is not None:
            member_bytes[rel_s] = bytes(buf)
        off += plen
    return {"trailer_hex": trailer_stored.hex(), "members": members, "bookkeeping": member_bytes}


def _verify_dag(parsed, pins, payload_rels):
    """pins: {rel: {'length','sha256'}} validation-time pins (all 158)."""
    members = parsed["members"]
    bk = parsed["bookkeeping"]
    # sec.7 step 6: scope first, then hashes
    man = _check_manifest_scope(bk["manifest.json"], payload_rels)
    sums = _check_sums_scope(bk["SHA256SUMS"], payload_rels)
    if set(members) != set(pins):
        raise HoldError("HOLD:MEMBERSHIP", "container member set != pin set")
    for rel, (ln, hx) in members.items():
        if pins[rel]["length"] != ln or pins[rel]["sha256"] != hx:
            raise HoldError("HOLD:MEMBER_DRIFT", f"{rel} != validation pin")
    for rel in payload_rels:
        e = man["files"][rel]
        if e["length"] != members[rel][0] or e["sha256"] != members[rel][1]:
            raise HoldError("HOLD:MEMBER_DRIFT", f"{rel} != manifest entry")
        if sums[rel] != members[rel][1]:
            raise HoldError("HOLD:MEMBER_DRIFT", f"{rel} != SHA256SUMS line")
    if sums["manifest.json"] != members["manifest.json"][1]:
        raise HoldError("HOLD:MEMBER_DRIFT", "manifest.json != SHA256SUMS line")


def _assemble_container(members):
    """Fixture helper: assemble a container from {rel: bytes} verbatim (used to
    craft scope/format attacks). Returns bytes."""
    rels = sorted(members)
    index = bytearray()
    for rel in rels:
        rb = rel.encode("ascii")
        index += struct.pack(">H", len(rb)) + rb + struct.pack(">Q", len(members[rel])) \
            + hashlib.sha256(members[rel]).digest()
    header = MAGIC + struct.pack(">I", VERSION) + struct.pack(">I", len(rels))
    body = header + bytes(index) + b"".join(members[r] for r in rels)
    return body + hashlib.sha256(body).digest()


_STAGE_COUNTER = itertools.count()


def _staging_name(kind):
    """Attempt-unique staging name (-14 req 4): pid + process counter + random.
    Never a fixed name, so a stale file from a crashed attempt is never reused."""
    return f"{kind}.{os.getpid()}.{next(_STAGE_COUNTER)}.{os.urandom(6).hex()}.tmp"


def _unlink_stage(staging_dir, name):
    dfd = os.open(staging_dir, _DIR_FLAGS)
    try:
        os.unlink(name, dir_fd=dfd)
    except FileNotFoundError:
        pass
    except OSError as e:
        raise HoldError("HOLD:STAGING_CLEANUP", f"unlink {name}: {e.strerror}")
    finally:
        os.close(dfd)


def _unlink_stage_quiet(staging_dir, name):
    try:
        dfd = os.open(staging_dir, _DIR_FLAGS)
        try:
            os.unlink(name, dir_fd=dfd)
        finally:
            os.close(dfd)
    except OSError:
        pass


# ---------------------------------------------------------------- journal
# -16 r1 frame: the boundary metadata is authenticated BEFORE the declared
# length may classify a tail as "torn". Frame layout:
#   header(53) || payload || tag(32)
#   header = magic b"QFJ2" (4) || version u8 (1) || seq u64be (8)
#            || length u32be (4) || length complement u32be (4)
#            || header digest (32) = SHA-256(header bytes [0:21])
#   tag    = SHA-256(header || payload)   -- whole-frame digest
# Parse order is the fix (-16 req 1): with a full header available, magic,
# version, seq, complement, the 1 MiB bound AND the header digest are all
# verified before the length is used to size the frame or to decide the
# tail is torn. A coherent in-bound length+complement forgery (the -15
# blocker) now fails the header digest and raises HOLD:JOURNAL_CORRUPT; it
# can never stride past a frame end and reclassify later frames as a tear.
# A short tail (< one header) is checked against the KNOWN fixed fields
# (magic/version/expected seq) for every byte present: a malformed
# available header is corruption, a genuine byte-prefix tear recovers.
# Threat model, stated honestly (-16 req 1): this defends the
# non-adversarial crash/corruption model -- torn writes, bit rot, partial
# flushes, accidental field damage. The digests are UNKEYED: an actor who
# can rewrite the entire journal can recompute every digest and forge a
# fully self-consistent journal. No claim is made against that actor.
FRAME_MAGIC = b"QFJ2"
FRAME_VERSION = 2
FRAME_HEADER_BYTES = 53
FRAME_HEADER_CORE_BYTES = 21  # magic||version||seq||length||complement
FRAME_TAG_BYTES = 32
MAX_FRAME_PAYLOAD = 1_048_576  # 1 MiB hard bound; journal records are small JSON


def _frame_bytes(record):
    payload = json.dumps(record, sort_keys=True).encode()
    if len(payload) > MAX_FRAME_PAYLOAD:
        raise HoldError("HOLD:JOURNAL_WRITE", "record exceeds frame payload bound")
    n = len(payload)
    core = FRAME_MAGIC + bytes([FRAME_VERSION]) \
        + struct.pack(">Q", int(record["seq"])) \
        + struct.pack(">I", n) + struct.pack(">I", (~n) & 0xFFFFFFFF)
    header = core + hashlib.sha256(core).digest()
    return header + payload + hashlib.sha256(header + payload).digest()


def _parse_frames(data):
    """Parse framed journal bytes -> (records, verified_end).

    verified_end is the exact offset one past the last fully verified
    frame. A torn tail -- a byte-prefix of a well-formed frame, cut inside
    its header, payload or tag -- ends the parse at verified_end WITHOUT
    error, but ONLY once the available boundary metadata is authenticated:
    a full header must pass magic/version/seq/complement/bound and its
    independent header digest before its length may classify the tail as
    torn, and a partial header must match the known fixed fields for every
    byte present. Anything else malformed raises HOLD:JOURNAL_CORRUPT
    wherever it occurs: corruption is never silently treated as a torn
    tail, and a corrupt length can never hide later complete frames."""
    out = []
    pos = 0
    total = len(data)
    while pos < total:
        remaining = total - pos
        expected_seq = len(out)
        if remaining < FRAME_HEADER_BYTES:
            # Partial header: torn tail ONLY if every available byte is
            # consistent with the fixed fields of the next genuine frame.
            tail = data[pos:]
            known = FRAME_MAGIC + bytes([FRAME_VERSION]) \
                + struct.pack(">Q", expected_seq)
            k = min(len(tail), len(known))
            if tail[:k] != known[:k]:
                raise HoldError("HOLD:JOURNAL_CORRUPT",
                                "partial header contradicts fixed fields")
            break  # byte-prefix tear inside the header
        header = data[pos:pos + FRAME_HEADER_BYTES]
        core = header[:FRAME_HEADER_CORE_BYTES]
        if header[:4] != FRAME_MAGIC or header[4] != FRAME_VERSION:
            raise HoldError("HOLD:JOURNAL_CORRUPT", "frame magic/version mismatch")
        (seq,) = struct.unpack(">Q", header[5:13])
        (n,) = struct.unpack(">I", header[13:17])
        (comp,) = struct.unpack(">I", header[17:21])
        if seq != expected_seq:
            raise HoldError("HOLD:JOURNAL_CORRUPT", "frame sequence mismatch")
        if comp != (~n) & 0xFFFFFFFF or n < 1 or n > MAX_FRAME_PAYLOAD:
            raise HoldError("HOLD:JOURNAL_CORRUPT",
                            "frame length fails complement/bound check")
        if hashlib.sha256(core).digest() != header[FRAME_HEADER_CORE_BYTES:]:
            raise HoldError("HOLD:JOURNAL_CORRUPT",
                            "frame header digest mismatch")
        # Boundary authenticated: only NOW may the length classify a tear.
        frame_len = FRAME_HEADER_BYTES + n + FRAME_TAG_BYTES
        if remaining < frame_len:
            break  # torn tail inside payload/tag
        payload = data[pos + FRAME_HEADER_BYTES:pos + FRAME_HEADER_BYTES + n]
        tag = data[pos + FRAME_HEADER_BYTES + n:pos + frame_len]
        if hashlib.sha256(header + payload).digest() != tag:
            raise HoldError("HOLD:JOURNAL_CORRUPT", "frame checksum mismatch")
        try:
            rec = json.loads(payload.decode())
        except Exception:
            raise HoldError("HOLD:JOURNAL_CORRUPT", "frame payload is not valid JSON")
        if not isinstance(rec, dict) or rec.get("seq") != expected_seq:
            raise HoldError("HOLD:JOURNAL_CORRUPT", "frame payload sequence mismatch")
        out.append(rec)
        pos += frame_len
    return out, pos


def _journal_read(journal_path):
    """Verified-prefix records of the journal. Corruption raises; a torn tail
    is tolerated at read time (prefix returned). The durable repair --
    truncation to the verified end -- is journal recovery, performed by
    _journal_append under the per-capture fence before any append."""
    if not os.path.exists(journal_path):
        return []
    with open(journal_path, "rb") as f:
        return _parse_frames(f.read())[0]


def _write_all(fd, data):
    view = memoryview(data)
    while view:
        n = os.write(fd, view)
        if n <= 0:
            raise HoldError("HOLD:JOURNAL_WRITE", "short write made no progress")
        view = view[n:]


def _journal_recover_fd(fd):
    """Truncate an open journal fd to its exact verified end and fsync, so no
    subsequent write can land behind torn bytes (-15 req 2). Returns the
    verified-prefix records. Corruption raises HOLD:JOURNAL_CORRUPT before
    any truncation; a failed truncate/fsync is HOLD:JOURNAL_RECOVERY."""
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(fd, 1 << 16)
        if not chunk:
            break
        chunks.append(chunk)
    data = b"".join(chunks)
    recs, verified_end = _parse_frames(data)
    if verified_end < len(data):
        try:
            os.ftruncate(fd, verified_end)
            os.fsync(fd)
        except OSError as e:
            raise HoldError("HOLD:JOURNAL_RECOVERY",
                            f"truncate to verified end failed: {e.strerror}")
    os.lseek(fd, verified_end, os.SEEK_SET)
    return recs


def _journal_append(journal_path, record):
    """Recover, then append exactly one framed record at the verified end.

    Recovery (truncate any torn tail to the verified end + fsync) and the
    append are one unit and MUST run under the per-capture fence -- publish()
    holds it for every call. An append therefore never lands behind
    unvalidated bytes, and a torn intent/published frame can never hide its
    durable replacement."""
    existed = os.path.exists(journal_path)
    fd = os.open(journal_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        recs = _journal_recover_fd(fd)
        rec = dict(record)
        rec["seq"] = len(recs)
        _write_all(fd, _frame_bytes(rec))
        os.fsync(fd)
    finally:
        os.close(fd)
    if not existed:
        dfd = os.open(os.path.dirname(os.path.abspath(journal_path)), _DIR_FLAGS)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)


class _Fence:
    """Per-journal interprocess intent fence (-14 req 3): an flock on
    <journal>.lock serializes publishers. Two processes cannot both create
    first intents; the second reconciles from the framed journal. The lock
    is released by the OS if the holder dies."""
    def __init__(self, journal_path):
        self.fd = os.open(journal_path + ".lock", os.O_RDWR | os.O_CREAT, 0o600)

    def __enter__(self):
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
        return False



# ---------------------------------------------------------------- capture-side streaming budget (design sec.4 + adjudication)
class StreamBudget:
    """Capture-side payload budget. The adjudicated semantics: the reserve
    guarantees a COMPLETED capture cannot overflow; an oversized streaming
    response still CONSUMES its attempt — begin_request() records that honestly
    and feed() cuts the stream off at the budget."""
    def __init__(self, payload_budget):
        self.budget = payload_budget
        self.running = 0
        self.attempts_consumed = 0
        self.cut_off = False

    def begin_request(self):
        self.attempts_consumed += 1

    def feed(self, chunk_len):
        if self.running + chunk_len > self.budget:
            self.cut_off = True
            raise HoldError("HOLD:CEILING",
                            f"stream cut at {self.running}+{chunk_len} > budget {self.budget}")
        self.running += chunk_len


# ---------------------------------------------------------------- publish protocol (design sec.6)
def _tree_contains(remote, tree_id, path):
    if tree_id is None:
        return None
    return remote.tree_entry(tree_id, path)


def _verify_remote(remote, commit_id, parent, path, info, payload_rels, capture_id):
    """Design sec.7 verification against the final commit. Returns transcript hash."""
    repo_path = path
    tip = remote.get_ref(REF)
    if tip != commit_id:
        raise HoldError("HOLD:REF_RACE", "ref tip != published commit at verify")
    commit = remote.get_commit(commit_id)
    parents = commit["parents"]
    if parents != ([parent] if parent else []):
        raise HoldError("HOLD:COMMIT_MISMATCH", "commit parents != [P]")
    want_msg = f"QF archive {capture_id} {info['container_sha256']}"
    if commit["message"] != want_msg:
        raise HoldError("HOLD:COMMIT_MISMATCH", "commit message != frozen template")
    entry = remote.tree_entry(commit["tree"], repo_path)
    expected_len = sum(p["length"] for p in info["pins"].values()) + 9741
    if entry is None or entry.get("mode") != "100644" or entry.get("type") != "blob" \
            or entry.get("sha") != info["blob_id"] or entry.get("size") != expected_len:
        raise HoldError("HOLD:TREE_MISMATCH", "tree entry != sealed blob")
    raw = remote.get_blob_raw(info["blob_id"])
    if raw is not None:
        if raw[:1] == b"{" and b'"message"' in raw[:256]:
            raise HoldError("HOLD:ENCODING", "raw route returned a JSON error body")
        data = raw
    else:
        doc = remote.get_blob_json(info["blob_id"])
        data = _strict_b64_decode(doc)
    # sec.7 step 5: CONTAINER_SHA256 is the trailer (SHA-256 over all preceding
    # bytes); the re-fetched bytes must reproduce it exactly.
    if len(data) != expected_len \
            or hashlib.sha256(data[:-TRAILER_BYTES]).digest() != bytes.fromhex(info["container_sha256"]):
        raise HoldError("HOLD:REFETCH_CONTAINER_HASH", "re-fetched container hash mismatch")
    import io as _io
    fd = os.memfd_create("qfar1-verify")
    try:
        os.write(fd, data)
        parsed = parse_container_fd(fd, len(data), payload_rels)
    finally:
        os.close(fd)
    _verify_dag(parsed, info["pins"], payload_rels)
    transcript = hashlib.sha256(
        json.dumps({"c": commit_id, "t": commit["tree"], "b": info["blob_id"],
                    "h": info["container_sha256"]}, sort_keys=True).encode()).hexdigest()
    return transcript


def _strict_b64_decode(doc):
    """Strict GitHub JSON blob decoding: encoding must say base64; the API's
    line wrapping is stripped, then alphabet + padding are validated."""
    import binascii
    if not isinstance(doc, dict) or doc.get("encoding") != "base64" \
            or not isinstance(doc.get("content"), str):
        raise HoldError("HOLD:ENCODING", "blob JSON shape/encoding not as specified")
    compact = "".join(doc["content"].split())
    try:
        return base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError):
        raise HoldError("HOLD:ENCODING", "base64 failed strict decode")


def publish(cap_dir, capture_id, remote, journal_path, staging_dir, manifest_path,
            validation_pins, step_hook=None, read_hook=None, phase_hook=None):
    """Run the sec.6 protocol against `remote` under the per-journal
    interprocess fence. Returns a result dict. Restart with an existing
    journal intent reconciles per sec.6.4 and never republishes.
    validation_pins is mandatory (-14 req 1)."""
    _validate_capture_id(capture_id)
    consts = derive_constants(manifest_path)
    _require_pins(validation_pins, consts["payload_rels"])
    with _Fence(journal_path):
        return _publish_inner(cap_dir, capture_id, remote, journal_path, staging_dir,
                              manifest_path, validation_pins, step_hook, read_hook,
                              phase_hook)


def _publish_inner(cap_dir, capture_id, remote, journal_path, staging_dir, manifest_path,
                   validation_pins, step_hook=None, read_hook=None, phase_hook=None):
    consts = derive_constants(manifest_path)
    payload_rels = consts["payload_rels"]
    path = f"captures/{capture_id}.qfar"
    journal = _journal_read(journal_path)
    intent = next((r for r in journal if r.get("type") == "intent" and r.get("capture_id") == capture_id), None)
    published_rec = next((r for r in journal if r.get("type") == "published" and r.get("capture_id") == capture_id), None)

    if intent is not None:
        # ---- restart reconciliation (sec.6.4) ----
        info = {"container_sha256": intent["container_sha256"], "blob_id": intent["blob_id"],
                "pins": intent["pins"]}
        if published_rec is not None:
            _verify_remote(remote, published_rec["commit"], intent["parent"], path, info, payload_rels, capture_id)
            return {"status": "ALREADY_PUBLISHED_VERIFIED", "commit": published_rec["commit"]}
        tip = remote.get_ref(REF)
        if tip is not None:
            commit = remote.get_commit(tip)
            entry = remote.tree_entry(commit["tree"], path)
            if entry is not None and entry.get("sha") == intent["blob_id"]:
                transcript = _verify_remote(remote, tip, intent["parent"], path, info, payload_rels, capture_id)
                _journal_append(journal_path, {"type": "published", "capture_id": capture_id,
                                               "commit": tip, "transcript": transcript})
                return {"status": "PUBLISHED_BY_RECORDING", "commit": tip}
        raise HoldError("HOLD:ID_CONSUMED", "intent exists; ref does not carry this capture")

    # ---- step 0: local seal ----
    info = build_container(cap_dir, capture_id, staging_dir, manifest_path,
                           validation_pins, phase_hook, read_hook)
    if step_hook:
        step_hook("sealed")
    try:
        # ---- step 1: read-only preflight ----
        repo = remote.get_repo()
        if repo.get("private") is not True or repo.get("owner") != DESIGNATED_OWNER \
                or repo.get("name") != DESIGNATED_REPO:
            raise HoldError("HOLD:VISIBILITY", "designated private repo check failed")
        P = remote.get_ref(REF)
        T_P = remote.get_commit(P)["tree"] if P else None
        if P is not None:
            existing = remote.tree_entry(T_P, path)
            if existing is not None:
                raise HoldError("HOLD:ID_CONSUMED", "path already present without our intent")
        if step_hook:
            step_hook("preflight")
        # ---- step 2: intent journal (fsync) ----
        _journal_append(journal_path, {
            "type": "intent", "capture_id": capture_id,
            "container_sha256": info["container_sha256"], "blob_id": info["blob_id"],
            "pins": info["pins"], "parent": P, "tree": T_P,
            "manifest_pin": FROZEN_MANIFEST_SHA256})
        if step_hook:
            step_hook("intent")
        # ---- step 3: confirm exact parent ----
        cur = remote.get_ref(REF)
        if cur != P:
            raise HoldError("HOLD:PARENT_DRIFT", "ref moved between preflight and confirm")
        if step_hook:
            step_hook("confirm")
        # ---- step 4: create blob from the sealed fd ----
        os.lseek(info["fd"], 0, os.SEEK_SET)
        parts = []
        pos = 0
        while pos < info["container_len"]:
            chunk = os.pread(info["fd"], min(_CHUNK, info["container_len"] - pos), pos)
            parts.append(chunk); pos += len(chunk)
        blob_resp = remote.create_blob(base64.b64encode(b"".join(parts)).decode("ascii"), "base64")
        if blob_resp.get("sha") != info["blob_id"]:
            raise HoldError("HOLD:BLOB_SUBSTITUTION", "create-blob returned a different id")
        if step_hook:
            step_hook("blob")
        # ---- step 5: create tree ----
        T = remote.create_tree(T_P, [{"path": path, "mode": "100644", "type": "blob",
                                      "sha": info["blob_id"]}])
        if step_hook:
            step_hook("tree")
        # ---- step 6: create commit ----
        msg = f"QF archive {capture_id} {info['container_sha256']}"
        C = remote.create_commit(msg, T, [P] if P else [])
        if step_hook:
            step_hook("commit")
        # ---- step 7: the single visibility event ----
        try:
            if P is not None:
                remote.update_ref(REF, C, force=False)
            else:
                remote.create_ref(REF, C)
        except _TransportLost:
            raise HoldError("HOLD:API", "ref update response lost; restart reconciles")
        except _ApiError as e:
            if e.status in (409, 422):
                raise HoldError("HOLD:REF_RACE", f"ref update rejected ({e.status})")
            raise HoldError("HOLD:API", f"ref update failed ({e.status})")
        if step_hook:
            step_hook("refupdate")
        # ---- step 8: verify, then record ----
        transcript = _verify_remote(remote, C, P, path, info, payload_rels, capture_id)
        _journal_append(journal_path, {"type": "published", "capture_id": capture_id,
                                       "commit": C, "transcript": transcript})
        return {"status": "PUBLISHED", "commit": C, "tree": T,
                "container_sha256": info["container_sha256"], "blob_id": info["blob_id"],
                "container_len": info["container_len"]}
    finally:
        os.close(info["fd"])
        os.close(info["spool_fd"])
