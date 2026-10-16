"""QFAR1 recovery-atomicity fixture driver (-15 r1).

Offline, no sockets. Covers the -15 required items:
  req 1/2/3  protected journal frame + truncate-at-recovery + exhaustive
             cut->append->reopen and length-corruption evidence
  req 4      real-process partial-frame crash/restart reconciliation
  req 5      all-or-nothing two-file staging allocation
  req 6      re-runs only the affected -14 cases H2/H3/H4/A-07, twice
The FakeGitRemote and synthetic-tree helpers are carried over verbatim from
the -14 driver, re-pointed at the h15 candidate module.
Usage: run_recovery_atomicity_fixture.py WORKDIR RESULTS_JSON META_JSON
RESULTS_JSON is deterministic; the two run outputs must be byte-identical.
"""
import base64
import hashlib
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qfar1_publisher_h15 as qp
from qfar1_publisher_h15 import HoldError, _ApiError, _TransportLost

MANIFEST = os.path.abspath(os.path.join(
    HERE, "..", "yahoo_clean_capture_preflight_20261015", "capture_manifest.json"))
CONSTS = qp.derive_constants(MANIFEST)
PAYLOAD_RELS = CONSTS["payload_rels"]
CID = "TEST-CAPTURE-0001"
CID2 = "TEST-CAPTURE-0002"
RESULTS = []
META = {}


def record(case, name, expect, got, ok):
    RESULTS.append({"case": case, "name": name, "expect": expect, "got": got, "pass": bool(ok)})
    print(f"{'PASS' if ok else 'FAIL'} {case} {name}: expect={expect} got={got}")


def run_hold(fn):
    try:
        return ("OK", fn())
    except HoldError as e:
        return ("HOLD", e.code)


def fresh_case_dir(work, name):
    d = os.path.join(work, name)
    os.makedirs(d)
    return d


def do_publish(tree, cid, remote, cdir, pins, hook=None, read_hook=None, phase_hook=None):
    return qp.publish(tree, cid, remote, os.path.join(cdir, "journal.qfj"),
                      os.path.join(cdir, "staging"), MANIFEST,
                      validation_pins=pins, step_hook=hook,
                      read_hook=read_hook, phase_hook=phase_hook)


def build_only(tree, cdir, pins):
    info = qp.build_container(tree, CID, os.path.join(cdir, "staging"), MANIFEST,
                              validation_pins=pins)
    data = os.pread(info["fd"], info["container_len"], 0)
    os.close(info["fd"])
    os.close(info["spool_fd"])
    return info, data


def fd_count():
    return len(os.listdir("/proc/self/fd"))


# ------------------------------------------------------------------ fake remote
def _git_id(kind, body):
    return hashlib.sha1(b"%s %d\x00" % (kind.encode(), len(body)) + body).hexdigest()


class FakeGitRemote:
    """No-socket Git Data API model: blobs/trees/commits/refs, FF-only update."""

    def __init__(self, private=True, owner=qp.DESIGNATED_OWNER, name=qp.DESIGNATED_REPO):
        self.private, self.owner, self.name = private, owner, name
        self.blobs, self.trees, self.commits, self.refs = {}, {}, {}, {}
        self.faults = set()
        self.writes = 0

    def get_repo(self):
        return {"private": self.private, "owner": self.owner, "name": self.name}

    def get_ref(self, ref):
        return self.refs.get(ref)

    def create_ref(self, ref, sha):
        self.writes += 1
        if ref in self.refs:
            raise _ApiError(422, "reference already exists")
        self.refs[ref] = sha
        return {"ref": ref, "sha": sha}

    def update_ref(self, ref, sha, force=False):
        self.writes += 1
        if ref not in self.refs:
            raise _ApiError(422, "reference does not exist")
        cur = self.refs[ref]
        if not force and cur not in self._ancestors(sha):
            raise _ApiError(422, "not fast-forward")
        self.refs[ref] = sha
        if "lose_update_response" in self.faults:
            raise _TransportLost()
        return {"ref": ref, "sha": sha}

    def _ancestors(self, sha):
        seen, stack = set(), [sha]
        while stack:
            c = stack.pop()
            if c in seen or c not in self.commits:
                continue
            seen.add(c)
            stack.extend(self.commits[c]["parents"])
        return seen

    def create_blob(self, content_b64, encoding):
        self.writes += 1
        data = base64.b64decode(content_b64)
        bid = _git_id("blob", data)
        self.blobs[bid] = data
        if "blob_wrong_id" in self.faults:
            return {"sha": _git_id("blob", b"not the blob")}
        return {"sha": bid}

    def get_blob_raw(self, sha):
        if "raw_refused" in self.faults:
            return None
        if "raw_json_error" in self.faults:
            return b'{"message":"Not Found","documentation_url":"https://docs.github.com/rest"}'
        data = self.blobs[sha]
        if "alter_blob" in self.faults:
            data = data[:100] + bytes([data[100] ^ 1]) + data[101:]
        return data

    def get_blob_json(self, sha):
        data = self.blobs[sha]
        if "alter_blob" in self.faults:
            data = data[:100] + bytes([data[100] ^ 1]) + data[101:]
        b64 = base64.b64encode(data).decode()
        wrapped = "\n".join(b64[i:i + 60] for i in range(0, len(b64), 60))
        enc = "utf-8" if "encoding_lie" in self.faults else "base64"
        if "bad_padding" in self.faults:
            wrapped = wrapped.rstrip("=")
        return {"content": wrapped, "encoding": enc, "size": len(data)}

    def create_tree(self, base_tree, entries):
        self.writes += 1
        tree = dict(self.trees.get(base_tree, {})) if base_tree else {}
        for e in entries:
            sha = e["sha"]
            if "tree_wrong_entry" in self.faults:
                sha = _git_id("blob", b"a different blob entirely")
            entry = {"mode": e["mode"], "type": e["type"], "sha": sha}
            if e["type"] == "blob" and sha in self.blobs:
                entry["size"] = len(self.blobs[sha])
            tree[e["path"]] = entry
        tid = _git_id("tree", json.dumps(tree, sort_keys=True).encode())
        self.trees[tid] = tree
        return tid

    def tree_entry(self, tree_id, path):
        if tree_id is None:
            return None
        return self.trees.get(tree_id, {}).get(path)

    def create_commit(self, message, tree, parents):
        self.writes += 1
        parents = list(parents)
        if "commit_extra_parent" in self.faults:
            parents.append(_git_id("commit", b"phantom parent"))
        if "commit_alter_message" in self.faults:
            message = message + " (altered)"
        body = (f"tree {tree}\n" + "".join(f"parent {p}\n" for p in parents)
                + "author QF Publisher <qf@localhost> 1700000000 +0000\n"
                + "committer QF Publisher <qf@localhost> 1700000000 +0000\n\n" + message).encode()
        cid = _git_id("commit", body)
        self.commits[cid] = {"tree": tree, "parents": parents, "message": message}
        return cid

    def get_commit(self, sha):
        return self.commits[sha]

    def object_ids(self):
        return set(self.blobs) | set(self.trees) | set(self.commits)

    def make_sibling(self, parent, note):
        data = f"sibling {note}".encode()
        bid = _git_id("blob", data)
        self.blobs[bid] = data
        base = self.commits[parent]["tree"] if parent else None
        tid = self.create_tree(base, [{"path": f"captures/SIBLING-{note}.qfar",
                                       "mode": "100644", "type": "blob", "sha": bid}])
        return self.create_commit(f"sibling {note}", tid, [parent] if parent else [])

    def commits_for(self, cid):
        return [c for c, v in self.commits.items() if cid in v["message"]]


def payload_bytes(rel, size):
    block = bytearray()
    b = hashlib.sha256(("QFAR1-FIXTURE|" + rel).encode()).digest()
    while len(block) < 8192:
        block += b
        b = hashlib.sha256(b).digest()
    reps = (size // 8192) + 1
    return (bytes(block) * reps)[:size]


def default_sizes():
    return {rel: 800 + (int(hashlib.sha256(rel.encode()).hexdigest()[:4], 16) % 2400)
            for rel in PAYLOAD_RELS}


def materialize(base, sizes, order="forward", mtime_base=1_600_000_000):
    os.makedirs(base)
    for d in ("raw", "actions", "meta"):
        os.mkdir(os.path.join(base, d))
    rels = list(PAYLOAD_RELS)
    if order == "reverse":
        rels = rels[::-1]
    for i, rel in enumerate(rels):
        p = os.path.join(base, rel)
        with open(p, "wb") as f:
            f.write(payload_bytes(rel, sizes[rel]))
        t = mtime_base + i * 137
        os.utime(p, (t, t))
    return base


def pins_of(sizes):
    return {rel: hashlib.sha256(payload_bytes(rel, sizes[rel])).hexdigest() for rel in PAYLOAD_RELS}



class Crash(BaseException):
    pass


# ------------------------------------------------------------------ cases
def main():
    work = sys.argv[1]
    results_path, meta_path = sys.argv[2], sys.argv[3]
    os.makedirs(work, exist_ok=True)
    sizes = default_sizes()
    tree = materialize(os.path.join(work, "cap"), sizes)
    pins = pins_of(sizes)

    # ============ H2 (rerun, req 6) + req 1/3: protected frame ============
    cdj = fresh_case_dir(work, "h2")
    jpath = os.path.join(cdj, "journal.qfj")
    recs_in = [{"type": "intent", "capture_id": CID, "n": 1},
               {"type": "note", "n": 2},
               {"type": "note", "n": 3},
               {"type": "published", "capture_id": CID, "n": 4}]
    for r in recs_in:
        qp._journal_append(jpath, r)
    data = open(jpath, "rb").read()
    frames = qp._journal_read(jpath)
    record("H2", "protected-frame round-trip", "4 records, seq 0..3",
           f"{len(frames)} records, seq {[f['seq'] for f in frames]}",
           len(frames) == 4 and [f["seq"] for f in frames] == [0, 1, 2, 3]
           and [f["n"] for f in frames] == [1, 2, 3, 4])
    # frame boundary offsets under the -15 format
    bounds, pos = [0], 0
    while pos < len(data):
        hdr = data[pos:pos + qp.FRAME_HEADER_BYTES]
        (n,) = struct.unpack(">I", hdr[5:9])
        pos += qp.FRAME_HEADER_BYTES + n + qp.FRAME_TAG_BYTES
        bounds.append(pos)
    assert pos == len(data)

    # req 3: exhaustive cut -> append -> reopen at EVERY byte offset.
    # After recovery+append the journal must read back as exactly the
    # verified prefix plus the one new record, and end at the verified end.
    cut_ok, cut_detail = True, ""
    new_rec = {"type": "note", "n": 99}
    for cut in range(len(data) + 1):
        p2 = os.path.join(cdj, "cut.qfj")
        with open(p2, "wb") as f:
            f.write(data[:cut])
        want_recs, vend = qp._parse_frames(data[:cut])
        try:
            qp._journal_append(p2, new_rec)
            got = qp._journal_read(p2)
            raw = open(p2, "rb").read()
            _, vend2 = qp._parse_frames(raw)
        except HoldError as e:
            cut_ok, cut_detail = False, f"cut {cut} raised {e.code}"
            break
        expect = want_recs + [dict(new_rec, seq=len(want_recs))]
        expect_len = vend + len(qp._frame_bytes(expect[-1]))
        if got != expect or vend2 != len(raw) or len(raw) != expect_len:
            cut_ok, cut_detail = False, (
                f"cut {cut}: want {len(expect)} records end {expect_len}, "
                f"got {len(got)} records len {len(raw)}")
            break
    record("H2", "cut-append-reopen at every byte offset",
           "verified prefix + exactly one new record, file ends at verified end",
           cut_detail or f"all {len(data) + 1} cuts ok", cut_ok)

    # req 1/3: length-field bit corruptions (first + interior frame), every
    # byte of the length and complement fields, low and high bit. Later
    # valid frames exist in all variants. All must be JOURNAL_CORRUPT --
    # a corrupt length is never an ordinary torn tail.
    len_ok, len_detail, n_var = True, "", 0
    for fidx in (0, 2):
        base = bounds[fidx]
        for byte_off in range(5, 13):  # length (5..8) + complement (9..12)
            for bit in (0x01, 0x80):
                bad = bytearray(data)
                bad[base + byte_off] ^= bit
                p3 = os.path.join(cdj, "lencorrupt.qfj")
                open(p3, "wb").write(bytes(bad))
                kind, val = run_hold(lambda: qp._journal_read(p3))
                n_var += 1
                if not (kind == "HOLD" and val == "HOLD:JOURNAL_CORRUPT"):
                    len_ok, len_detail = False, f"frame {fidx} byte {byte_off} bit {bit:#x}: {kind}:{val}"
                    break
            if not len_ok:
                break
        if not len_ok:
            break
    record("H2", "length/complement bit corruptions (frames 0 and 2)",
           "HOLD:JOURNAL_CORRUPT for every variant",
           len_detail or f"all {n_var} variants corrupt", len_ok)

    # req 1: a fully self-consistent forged length ABOVE the bound, with a
    # valid complement AND a valid tag, is still corruption (bound fires),
    # as first frame and as an interior frame hiding later valid records.
    big_n = qp.MAX_FRAME_PAYLOAD + 1
    big_payload = b"x" * big_n
    big_hdr = (qp.FRAME_MAGIC + bytes([qp.FRAME_VERSION])
               + struct.pack(">I", big_n) + struct.pack(">I", (~big_n) & 0xFFFFFFFF))
    big_frame = big_hdr + big_payload + hashlib.sha256(big_hdr + big_payload).digest()
    for name, blob in (("oversized length, sole frame", big_frame),
                       ("oversized length, interior frame", data[:bounds[1]] + big_frame + data[bounds[1]:])):
        p4 = os.path.join(cdj, "biglen.qfj")
        open(p4, "wb").write(blob)
        kind, val = run_hold(lambda: qp._journal_read(p4))
        record("H2", name, "HOLD:JOURNAL_CORRUPT", val,
               kind == "HOLD" and val == "HOLD:JOURNAL_CORRUPT")

    # retained -14 H2 coverage under the new frame: interior payload flip,
    # tag flip, sequence forgery with valid tag, append onto corrupt.
    bad = bytearray(data)
    bad[bounds[0] + qp.FRAME_HEADER_BYTES + 2] ^= 1
    p5 = os.path.join(cdj, "corrupt1.qfj")
    open(p5, "wb").write(bytes(bad))
    kind, val = run_hold(lambda: qp._journal_read(p5))
    record("H2", "interior payload corruption (frame 0 of 4)", "HOLD:JOURNAL_CORRUPT",
           val, kind == "HOLD" and val == "HOLD:JOURNAL_CORRUPT")
    bad2 = bytearray(data)
    bad2[bounds[2] - 1] ^= 1
    p6 = os.path.join(cdj, "corrupt2.qfj")
    open(p6, "wb").write(bytes(bad2))
    kind, val = run_hold(lambda: qp._journal_read(p6))
    record("H2", "interior tag corruption (frame 2 of 4)", "HOLD:JOURNAL_CORRUPT",
           val, kind == "HOLD" and val == "HOLD:JOURNAL_CORRUPT")
    forged = b"".join([
        qp._frame_bytes({"type": "intent", "capture_id": CID, "n": 1, "seq": 0}),
        qp._frame_bytes({"type": "note", "n": 2, "seq": 99}),
        qp._frame_bytes({"type": "note", "n": 3, "seq": 2}),
        qp._frame_bytes({"type": "published", "capture_id": CID, "n": 4, "seq": 3})])
    p7 = os.path.join(cdj, "corrupt3.qfj")
    open(p7, "wb").write(forged)
    kind, val = run_hold(lambda: qp._journal_read(p7))
    record("H2", "interior sequence forgery (valid tag)", "HOLD:JOURNAL_CORRUPT",
           val, kind == "HOLD" and val == "HOLD:JOURNAL_CORRUPT")
    kind, val = run_hold(lambda: qp._journal_append(p5, {"type": "note", "n": 5}))
    record("H2", "append onto corrupt journal", "HOLD:JOURNAL_CORRUPT",
           val, kind == "HOLD" and val == "HOLD:JOURNAL_CORRUPT")

    # ============ H4 (rerun, req 6) + req 5: all-or-nothing staging =======
    cds = fresh_case_dir(work, "h4")
    stage = os.path.join(cds, "staging")
    crash = {"armed": True}

    def crash_at_prescribed(phase):
        if phase == "prescribed" and crash["armed"]:
            crash["armed"] = False
            raise Crash()
    rs = FakeGitRemote()
    try:
        do_publish(tree, CID, rs, cds, pins, phase_hook=crash_at_prescribed)
        crash_got = "NO-CRASH"
    except Crash:
        crash_got = "Crash"
    leftovers = sorted(os.listdir(stage)) if os.path.isdir(stage) else ["<missing>"]
    record("H4", "pre-intent crash leaves no staging files", "Crash, staging empty",
           f"{crash_got}, leftovers={leftovers}", crash_got == "Crash" and leftovers == [])
    kind, val = run_hold(lambda: do_publish(tree, CID, rs, cds, pins))
    fresh_info, _ = build_only(tree, cds, pins)
    record("H4", "clean retry after crash (no stale bytes)", "PUBLISHED, hash == fresh build",
           f"{val.get('status') if kind == 'OK' else val}, "
           f"eq={kind == 'OK' and val.get('container_sha256') == fresh_info['container_sha256']}",
           kind == "OK" and val.get("status") == "PUBLISHED"
           and val.get("container_sha256") == fresh_info["container_sha256"])

    # req 5: force a SECOND-name collision. The spool create succeeds; the
    # container create collides with a pre-existing file. Rollback must close
    # + unlink ONLY the spool it created: staging keeps just the pre-existing
    # file, the process fd count is stable, and a clean retry succeeds.
    cds5 = fresh_case_dir(work, "h4_collision")
    st5 = os.path.join(cds5, "staging")
    os.makedirs(st5)
    open(os.path.join(st5, "container.forced.tmp"), "wb").write(b"PREEXISTING")
    orig_name = qp._staging_name
    qp._staging_name = lambda kind: f"{kind}.forced.tmp"
    try:
        fds_before = fd_count()
        kind, val = run_hold(lambda: qp.build_container(
            tree, CID, st5, MANIFEST, validation_pins=pins))
        fds_after = fd_count()
    finally:
        qp._staging_name = orig_name
    left5 = sorted(os.listdir(st5))
    record("H4", "second-name collision rolls back first file",
           "HOLD:STAGING_COLLISION, staging == [pre-existing file], fd delta 0",
           f"{val}, left={left5}, fd_delta={fds_after - fds_before}",
           kind == "HOLD" and val == "HOLD:STAGING_COLLISION"
           and left5 == ["container.forced.tmp"] and fds_after == fds_before)
    os.unlink(os.path.join(st5, "container.forced.tmp"))
    kind, val = run_hold(lambda: qp.build_container(
        tree, CID, st5, MANIFEST, validation_pins=pins))
    if kind == "OK":
        os.close(val["fd"])
        os.close(val["spool_fd"])
    record("H4", "clean retry after collision", "build ok, hash == fresh build",
           f"{'ok' if kind == 'OK' else val}, "
           f"eq={kind == 'OK' and val['container_sha256'] == fresh_info['container_sha256']}",
           kind == "OK" and val["container_sha256"] == fresh_info["container_sha256"])

    # req 5: both names forced to the same value (spool collides with itself
    # as the container): rollback leaves staging EMPTY and fds stable.
    cds6 = fresh_case_dir(work, "h4_samename")
    st6 = os.path.join(cds6, "staging")
    qp._staging_name = lambda kind: "same.tmp"
    try:
        fds_before = fd_count()
        kind, val = run_hold(lambda: qp.build_container(
            tree, CID, st6, MANIFEST, validation_pins=pins))
        fds_after = fd_count()
    finally:
        qp._staging_name = orig_name
    left6 = sorted(os.listdir(st6)) if os.path.isdir(st6) else ["<missing>"]
    record("H4", "same-name collision (spool == container)",
           "HOLD:STAGING_COLLISION, staging empty, fd delta 0",
           f"{val}, left={left6}, fd_delta={fds_after - fds_before}",
           kind == "HOLD" and val == "HOLD:STAGING_COLLISION"
           and left6 == [] and fds_after == fds_before)

    # req 5: rollback unlink failure is a named HOLD, and the leftover is
    # visible (not silently masked). Force os.unlink to fail on the spool.
    cds7 = fresh_case_dir(work, "h4_cleanup")
    st7 = os.path.join(cds7, "staging")
    os.makedirs(st7)
    open(os.path.join(st7, "container.forced.tmp"), "wb").write(b"PREEXISTING")
    qp._staging_name = lambda kind: f"{kind}.forced.tmp"
    real_unlink = os.unlink

    def flaky_unlink(path, *a, **kw):
        if isinstance(path, str) and path.endswith("spool.forced.tmp"):
            raise OSError(13, "forced unlink failure")
        return real_unlink(path, *a, **kw)
    os.unlink = flaky_unlink
    try:
        fds_before = fd_count()
        kind, val = run_hold(lambda: qp.build_container(
            tree, CID, st7, MANIFEST, validation_pins=pins))
        fds_after = fd_count()
    finally:
        os.unlink = real_unlink
        qp._staging_name = orig_name
    left7 = sorted(os.listdir(st7))
    record("H4", "rollback cleanup failure", "HOLD:STAGING_CLEANUP, leftover visible, fd delta 0",
           f"{val}, left={left7}, fd_delta={fds_after - fds_before}",
           kind == "HOLD" and val == "HOLD:STAGING_CLEANUP"
           and left7 == ["container.forced.tmp", "spool.forced.tmp"]
           and fds_after == fds_before)

    # ============ A-07 (rerun, req 6): crash points + lost response ========
    for step in ("blob", "tree", "commit"):
        cda = fresh_case_dir(work, f"a07_{step}")
        ra = FakeGitRemote()
        state = {"armed": True}

        def hook(step_name, _s=step, _st=state):
            if step_name == _s and _st["armed"]:
                _st["armed"] = False
                raise Crash()
        try:
            do_publish(tree, CID, ra, cda, pins, hook=hook)
            g1 = "NO-CRASH"
        except Crash:
            g1 = "Crash"
        kind, val = run_hold(lambda: do_publish(tree, CID, ra, cda, pins))
        record("A-07", f"crash after {step}, restart", "Crash then HOLD:ID_CONSUMED",
               f"{g1} then {val}",
               g1 == "Crash" and kind == "HOLD" and val == "HOLD:ID_CONSUMED")
    cdl = fresh_case_dir(work, "a07_lost")
    rl = FakeGitRemote()
    kind0, val0 = run_hold(lambda: do_publish(tree, CID, rl, cdl, pins))
    assert kind0 == "OK" and val0["status"] == "PUBLISHED", val0
    rl.faults.add("lose_update_response")
    kind, val = run_hold(lambda: do_publish(tree, CID2, rl, cdl, pins))
    first = f"{kind}:{val if kind == 'HOLD' else val.get('status')}"
    rl.faults.clear()
    kind2, val2 = run_hold(lambda: do_publish(tree, CID2, rl, cdl, pins))
    record("A-07", "lost ref-update response, restart records",
           "HOLD:API then PUBLISHED_BY_RECORDING, exactly 1 commit",
           f"{first} then {val2.get('status') if kind2 == 'OK' else val2}, "
           f"commits={len(rl.commits_for(CID2))}",
           first == "HOLD:HOLD:API" and kind2 == "OK"
           and val2.get("status") == "PUBLISHED_BY_RECORDING"
           and len(rl.commits_for(CID2)) == 1)

    # ============ H3 (rerun, req 6): two-process intent fencing ===========
    cdf = fresh_case_dir(work, "h3")
    tree_f = materialize(os.path.join(cdf, "cap"), sizes)
    pins_f = os.path.join(cdf, "pins.json")
    with open(pins_f, "w") as f:
        json.dump(pins, f)
    journal_f = os.path.join(cdf, "journal.qfj")
    args = [sys.executable, os.path.join(HERE, "fence_worker.py"),
            tree_f, CID, journal_f, os.path.join(cdf, "staging"),
            MANIFEST, os.path.join(cdf, "remote"), pins_f]
    p1 = subprocess.Popen(args, stdout=subprocess.PIPE, text=True)
    p2 = subprocess.Popen(args, stdout=subprocess.PIPE, text=True)
    o1, _ = p1.communicate()
    o2, _ = p2.communicate()
    statuses = sorted(json.loads(o.strip().splitlines()[-1]).get("status", "?")
                      for o in (o1, o2))
    frames = qp._journal_read(journal_f)
    n_intent = sum(1 for r in frames if r.get("type") == "intent")
    n_published = sum(1 for r in frames if r.get("type") == "published")
    remote_dir = os.path.join(cdf, "remote", "commits")
    n_commits = len(os.listdir(remote_dir)) if os.path.isdir(remote_dir) else -1
    record("H3", "two-process duplicate invocation",
           "statuses [ALREADY_PUBLISHED_VERIFIED, PUBLISHED], 1 intent, 1 commit",
           f"{statuses}, intents={n_intent}, published={n_published}, commits={n_commits}",
           statuses == ["ALREADY_PUBLISHED_VERIFIED", "PUBLISHED"]
           and n_intent == 1 and n_published == 1 and n_commits == 1)

    # ============ req 4: real-process partial-frame crash/restart =========
    cdt = fresh_case_dir(work, "h7_tear")
    tree_t = materialize(os.path.join(cdt, "cap"), sizes)
    pins_t = os.path.join(cdt, "pins.json")
    with open(pins_t, "w") as f:
        json.dump(pins, f)
    journal_t = os.path.join(cdt, "journal.qfj")
    worker = os.path.join(HERE, "crash_worker.py")
    tear = subprocess.run([sys.executable, worker, "tear", journal_t, CID],
                          text=True, capture_output=True)
    torn_frame = qp._frame_bytes({"type": "intent", "capture_id": CID,
                                  "torn_marker": True, "seq": 0})
    torn_size = os.path.getsize(journal_t) if os.path.exists(journal_t) else -1
    prefix = qp._journal_read(journal_t)
    record("H7", "real-process crash mid-append leaves torn final frame",
           "exit 3, file == half the frame, read returns empty verified prefix",
           f"rc={tear.returncode}, size={torn_size}/{len(torn_frame) // 2}, prefix={len(prefix)}",
           tear.returncode == 3 and torn_size == len(torn_frame) // 2 and prefix == [])
    pub_args = [sys.executable, worker, "publish", tree_t, CID, journal_t,
                os.path.join(cdt, "staging"), MANIFEST,
                os.path.join(cdt, "remote"), pins_t]
    out1 = subprocess.run(pub_args, text=True, capture_output=True)
    st1 = json.loads(out1.stdout.strip().splitlines()[-1]).get("status", "?")
    raw = open(journal_t, "rb").read()
    jrecs, vend = qp._parse_frames(raw)
    types = [r.get("type") for r in jrecs]
    commits_t = os.listdir(os.path.join(cdt, "remote", "commits"))
    record("H7", "restart after torn intent reconciles",
           "PUBLISHED, journal == [intent, published] with no torn bytes, 1 commit",
           f"{st1}, types={types}, torn_marker={'torn_marker' in jrecs[0] if jrecs else '?'}, "
           f"end={vend}/{len(raw)}, commits={len(commits_t)}",
           st1 == "PUBLISHED" and types == ["intent", "published"]
           and "torn_marker" not in jrecs[0] and vend == len(raw)
           and len(commits_t) == 1)
    out2 = subprocess.run(pub_args, text=True, capture_output=True)
    st2 = json.loads(out2.stdout.strip().splitlines()[-1]).get("status", "?")
    jrecs2 = qp._journal_read(journal_t)
    commits_t2 = os.listdir(os.path.join(cdt, "remote", "commits"))
    record("H7", "second restart is a no-op verification",
           "ALREADY_PUBLISHED_VERIFIED, still 1 intent / 1 published / 1 commit",
           f"{st2}, records={len(jrecs2)}, commits={len(commits_t2)}",
           st2 == "ALREADY_PUBLISHED_VERIFIED" and len(jrecs2) == 2
           and len(commits_t2) == 1)

    with open(results_path, "w") as f:
        json.dump(RESULTS, f, indent=1, sort_keys=True)
    with open(meta_path, "w") as f:
        json.dump(META, f, indent=1, sort_keys=True)
    bad = [r for r in RESULTS if not r["pass"]]
    print(f"TOTAL {len(RESULTS)} records, {len(RESULTS) - len(bad)} pass, {len(bad)} fail")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
