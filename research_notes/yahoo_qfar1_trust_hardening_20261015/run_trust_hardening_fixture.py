"""QFAR1 trust-hardening fixture driver (-14 r1).

Offline, no sockets. Covers the -14 required items:
  H1 mandatory validation pins (req 1)   H2 framed journal (req 2)
  H3 interprocess intent fencing (req 3) H4 attempt-unique staging (req 4)
  H5 no module-global capture-ID state (req 5, static + behavioral)
  H6 ceiling-size end-to-end publication (req 6, subprocess, RSS in META)
and re-runs the affected design cases A-01/A-07/A-10/A-12/A-14 (req 7).
Usage: run_trust_hardening_fixture.py WORKDIR RESULTS_JSON META_JSON
RESULTS_JSON is deterministic; volatile measurements go to META_JSON.
The suite is run twice from independently materialized trees and the two
RESULTS files must be byte-identical.
"""
import base64
import hashlib
import json
import os
import resource
import shutil
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qfar1_publisher_h14 as qp
from qfar1_publisher_h14 import HoldError, _ApiError, _TransportLost

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


# ------------------------------------------------------------------ synthetic trees
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


# ------------------------------------------------------------------ cases
def main():
    work = sys.argv[1]
    results_path, meta_path = sys.argv[2], sys.argv[3]
    os.makedirs(work, exist_ok=True)
    sizes = default_sizes()
    pins = pins_of(sizes)

    # ============ H1: mandatory validation pins (req 1) ============
    cd = fresh_case_dir(work, "h1")
    tree = materialize(os.path.join(cd, "cap"), sizes)
    remote = FakeGitRemote()

    def omit_pins():
        return qp.publish(tree, CID, remote, os.path.join(cd, "journal.qfj"),
                          os.path.join(cd, "staging"), MANIFEST)
    try:
        omit_pins()
        got_omit = "NO-ERROR"
    except TypeError:
        got_omit = "TypeError"
    except HoldError as e:
        got_omit = e.code
    record("H1", "pins omitted entirely", "refused, 0 writes",
           f"{got_omit}, {remote.writes} writes",
           got_omit in ("TypeError", "HOLD:PINS_INVALID") and remote.writes == 0)

    for name, bad in (
        ("pins=None", None),
        ("one pin missing", {k: v for k, v in list(pins.items())[1:]}),
        ("one extra pin", dict(pins, **{"raw/EXTRA.csv": "0" * 64})),
        ("uppercase hex pin", dict(pins, **{PAYLOAD_RELS[0]: pins[PAYLOAD_RELS[0]].upper()})),
        ("short pin", dict(pins, **{PAYLOAD_RELS[0]: pins[PAYLOAD_RELS[0]][:63]})),
    ):
        cdx = fresh_case_dir(cd, "x_" + name.replace(" ", "_").replace("=", ""))
        rx = FakeGitRemote()
        kind, val = run_hold(lambda: do_publish(tree, CID, rx, cdx, bad))
        record("H1", name, "HOLD:PINS_INVALID, 0 writes", f"{val}, {rx.writes} writes",
               kind == "HOLD" and val == "HOLD:PINS_INVALID" and rx.writes == 0)

    # one-byte current-disk substitution vs correct pins -> MEMBER_DRIFT, 0 writes
    cdsub = fresh_case_dir(cd, "sub")
    tree_sub = materialize(os.path.join(cdsub, "cap"), sizes)
    victim = os.path.join(tree_sub, PAYLOAD_RELS[0])
    with open(victim, "r+b") as f:
        b0 = f.read(1)
        f.seek(0)
        f.write(bytes([b0[0] ^ 1]))
    rsub = FakeGitRemote()
    kind, val = run_hold(lambda: do_publish(tree_sub, CID, rsub, cdsub, pins))
    record("H1", "one-byte disk substitution vs pins", "HOLD:MEMBER_DRIFT, 0 writes",
           f"{val}, {rsub.writes} writes",
           kind == "HOLD" and val == "HOLD:MEMBER_DRIFT" and rsub.writes == 0)

    # baseline: correct pins publish cleanly
    cdb = fresh_case_dir(cd, "base")
    rb = FakeGitRemote()
    kind, val = run_hold(lambda: do_publish(tree, CID, rb, cdb, pins))
    record("H1", "correct pins publish", "PUBLISHED",
           val.get("status") if kind == "OK" else val,
           kind == "OK" and val.get("status") == "PUBLISHED")

    # ============ H5: no module-global capture-ID state (req 5) ============
    src = open(os.path.join(HERE, "qfar1_publisher_h14.py")).read()
    record("H5", "no _MSG_ID global in publisher source", "absent",
           "present" if "_MSG_ID" in src else "absent", "_MSG_ID" not in src)
    # behavioral: verify binds the message to the explicit capture id —
    # a second capture under a different id verifies against its own id.
    kind, val = run_hold(lambda: do_publish(tree, CID2, rb, cdb, pins))
    record("H5", "second capture id verifies independently", "PUBLISHED",
           val.get("status") if kind == "OK" else val,
           kind == "OK" and val.get("status") == "PUBLISHED")

    # ============ A-01 rerun: determinism twin (req 7) ============
    cd1 = fresh_case_dir(work, "a01")
    t1 = materialize(os.path.join(cd1, "cap1"), sizes, order="forward", mtime_base=1_600_000_000)
    t2 = materialize(os.path.join(cd1, "cap2"), sizes, order="reverse", mtime_base=1_700_000_000)
    i1, d1 = build_only(t1, cd1, pins)
    i2, d2 = build_only(t2, cd1, pins)
    record("A-01", "twin builds byte-identical", "identical bytes/blob/sha",
           f"bytes_eq={d1 == d2} blob_eq={i1['blob_id'] == i2['blob_id']}",
           d1 == d2 and i1["blob_id"] == i2["blob_id"]
           and i1["container_sha256"] == i2["container_sha256"])

    # ============ H2: framed journal (req 2) ============
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
    record("H2", "framed round-trip", "4 records, seq 0..3",
           f"{len(frames)} records, seq {[f['seq'] for f in frames]}",
           len(frames) == 4 and [f["seq"] for f in frames] == [0, 1, 2, 3]
           and [f["n"] for f in frames] == [1, 2, 3, 4])
    # frame boundary offsets
    bounds, pos = [0], 0
    while pos < len(data):
        (n,) = struct.unpack(">I", data[pos:pos + 4])
        pos += 4 + n + 32
        bounds.append(pos)
    # byte-cut at EVERY offset: read must return exactly the complete prefix
    cut_ok, cut_detail = True, ""
    for cut in range(len(data) + 1):
        p2 = os.path.join(cdj, "cut.qfj")
        with open(p2, "wb") as f:
            f.write(data[:cut])
        try:
            got = qp._journal_read(p2)
        except HoldError as e:
            cut_ok, cut_detail = False, f"cut {cut} raised {e.code}"
            break
        want = sum(1 for b in bounds[1:] if b <= cut)
        if len(got) != want or [g["seq"] for g in got] != list(range(want)):
            cut_ok, cut_detail = False, f"cut {cut}: want {want} got {len(got)}"
            break
    record("H2", "byte-cut at every offset", "exact complete-frame prefix, never raises",
           cut_detail or f"all {len(data) + 1} cuts ok", cut_ok)
    # interior corruption: payload byte flip in frame 0 (later frames exist)
    bad = bytearray(data)
    bad[bounds[0] + 6] ^= 1
    p3 = os.path.join(cdj, "corrupt1.qfj")
    open(p3, "wb").write(bytes(bad))
    kind, val = run_hold(lambda: qp._journal_read(p3))
    record("H2", "interior payload corruption (frame 0 of 4)", "HOLD:JOURNAL_CORRUPT",
           val, kind == "HOLD" and val == "HOLD:JOURNAL_CORRUPT")
    # interior corruption: tag flip in frame 2
    bad2 = bytearray(data)
    bad2[bounds[2] - 1] ^= 1
    p4 = os.path.join(cdj, "corrupt2.qfj")
    open(p4, "wb").write(bytes(bad2))
    kind, val = run_hold(lambda: qp._journal_read(p4))
    record("H2", "interior tag corruption (frame 2 of 4)", "HOLD:JOURNAL_CORRUPT",
           val, kind == "HOLD" and val == "HOLD:JOURNAL_CORRUPT")
    # sequence forgery: rewrite frame 1 with seq=99 and a VALID checksum
    forged_payload = json.dumps({"type": "note", "n": 2, "seq": 99}, sort_keys=True).encode()
    forged = (data[:bounds[1]] + struct.pack(">I", len(forged_payload)) + forged_payload
              + hashlib.sha256(forged_payload).digest() + data[bounds[2]:])
    p5 = os.path.join(cdj, "corrupt3.qfj")
    open(p5, "wb").write(forged)
    kind, val = run_hold(lambda: qp._journal_read(p5))
    record("H2", "interior sequence forgery (valid checksum)", "HOLD:JOURNAL_CORRUPT",
           val, kind == "HOLD" and val == "HOLD:JOURNAL_CORRUPT")
    # append to a corrupt journal must refuse, not hide
    kind, val = run_hold(lambda: qp._journal_append(p3, {"type": "note", "n": 5}))
    record("H2", "append onto corrupt journal", "HOLD:JOURNAL_CORRUPT",
           val, kind == "HOLD" and val == "HOLD:JOURNAL_CORRUPT")

    # ============ H4: attempt-unique staging (req 4) ============
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
    # stale fixed-name files from the old scheme are ignored
    cds2 = fresh_case_dir(work, "h4b")
    st2 = os.path.join(cds2, "staging")
    os.makedirs(st2)
    open(os.path.join(st2, "spool.tmp"), "wb").write(b"STALE")
    open(os.path.join(st2, "container.tmp"), "wb").write(b"STALE")
    rs2 = FakeGitRemote()
    kind, val = run_hold(lambda: do_publish(tree, CID, rs2, cds2, pins))
    record("H4", "stale fixed-name files ignored", "PUBLISHED",
           val.get("status") if kind == "OK" else val,
           kind == "OK" and val.get("status") == "PUBLISHED")
    # forced name collision -> named HOLD
    orig_name = qp._staging_name
    qp._staging_name = lambda kind: "forced.name.tmp"
    try:
        kind2, val2 = run_hold(lambda: qp.build_container(
            tree, CID, os.path.join(cds2, "staging2"), MANIFEST, validation_pins=pins))
    finally:
        qp._staging_name = orig_name
    record("H4", "staging name collision", "HOLD:STAGING_COLLISION",
           val2, kind2 == "HOLD" and val2 == "HOLD:STAGING_COLLISION")

    # ============ A-07 rerun: crash points + lost response (req 7) ============
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
    assert kind0 == "OK" and val0["status"] == "PUBLISHED", val0  # establishes the ref
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

    # ============ A-12 rerun: encoding traps (req 7) ============
    for idx, (name, faults) in enumerate((("raw returns JSON error body", {"raw_json_error"}),
                                          ("json route encoding lie", {"raw_refused", "encoding_lie"}),
                                          ("json route bad padding", {"raw_refused", "bad_padding"}))):
        cde = fresh_case_dir(work, f"a12_{idx}")
        re_ = FakeGitRemote()
        re_.faults.update(faults)
        kind, val = run_hold(lambda: do_publish(tree, CID, re_, cde, pins))
        record("A-12", name, "HOLD:ENCODING", val,
               kind == "HOLD" and val == "HOLD:ENCODING")

    # ============ A-14 rerun: parent drift / ref race (req 7) ============
    cdw = fresh_case_dir(work, "a14")
    rw = FakeGitRemote()
    kind, val = run_hold(lambda: do_publish(tree, CID, rw, cdw, pins))
    assert kind == "OK" and val["status"] == "PUBLISHED", val
    parent = val["commit"]

    def sibling_hook(at, rw_=rw):
        def h(s, _at=at, _rw=rw_):
            if s == _at:
                cur = _rw.get_ref(qp.REF)
                sib = _rw.make_sibling(cur, f"race-{_at}")
                _rw.update_ref(qp.REF, sib)
        return h
    for name, at, expect in (("W1 move preflight->intent", "preflight", "HOLD:PARENT_DRIFT"),
                             ("W2 move intent->confirm", "intent", "HOLD:PARENT_DRIFT")):
        before = rw.object_ids()
        cdx = fresh_case_dir(cdw, "x_" + at)
        kind, val = run_hold(lambda: do_publish(tree, CID2, rw, cdx, pins,
                                                hook=sibling_hook(at)))
        new_objs = rw.object_ids() - before
        sib_objs = {o for o in new_objs}
        record("A-14", name, f"{expect}, 0 publisher objects",
               f"{val}, new={len(sib_objs)} (sibling only)",
               kind == "HOLD" and val == expect and len(new_objs) <= 3)
    # W3: sibling advances after confirm (at commit step) -> update_ref FF fails
    cdx = fresh_case_dir(cdw, "x_w3")
    kind, val = run_hold(lambda: do_publish(tree, CID2, rw, cdx, pins,
                                            hook=sibling_hook("commit")))
    record("A-14", "W3 move confirm->refupdate", "HOLD:REF_RACE", val,
           kind == "HOLD" and val == "HOLD:REF_RACE")

    # ============ A-10 rerun + H6: ceiling (req 6/7) ============
    # solve payload sizes so sum(158 physical) == CEILING exactly
    ceil_sizes = {rel: 400_000 for rel in PAYLOAD_RELS}
    first_rel = PAYLOAD_RELS[0]
    for _ in range(4):
        cp = pins_of(ceil_sizes)
        files_map = {r: {"length": ceil_sizes[r], "sha256": cp[r]} for r in PAYLOAD_RELS}
        m_len = len(qp._canonical_manifest(CID, files_map))
        total = sum(ceil_sizes.values()) + m_len + CONSTS["sums_bytes"]
        if total == qp.CEILING:
            break
        ceil_sizes[first_rel] += qp.CEILING - total
    total = sum(ceil_sizes.values()) + m_len + CONSTS["sums_bytes"]
    record("A-10", "ceiling fixture solved exactly", f"sum physical == {qp.CEILING}",
           f"sum physical == {total}", total == qp.CEILING)
    cdc = fresh_case_dir(work, "ceiling")
    tree_c = materialize(os.path.join(cdc, "cap"), ceil_sizes)
    ceil_pins = pins_of(ceil_sizes)
    pins_path = os.path.join(cdc, "pins.json")
    with open(pins_path, "w") as f:
        json.dump(ceil_pins, f)
    out = subprocess.run(
        [sys.executable, os.path.join(HERE, "ceiling_worker.py"),
         tree_c, CID, os.path.join(cdc, "journal.qfj"), os.path.join(cdc, "staging"),
         MANIFEST, os.path.join(cdc, "remote"), pins_path],
        text=True, capture_output=True)
    cres = json.loads(out.stdout.strip().splitlines()[-1]) if out.stdout.strip() else {"error": out.stderr[-400:]}
    META["ceiling_publish"] = {k: cres.get(k) for k in ("elapsed_s", "peak_rss_mib")}
    record("H6", "ceiling-size end-to-end publication (subprocess)",
           "PUBLISHED, container_len == 67118605",
           f"{cres.get('status', cres)}, len={cres.get('container_len')}",
           cres.get("status") == "PUBLISHED" and cres.get("container_len") == 67_118_605)
    # ceiling + 1 -> HOLD:CEILING before remote writes
    over_sizes = dict(ceil_sizes)
    over_sizes[first_rel] += 1
    tree_o = materialize(os.path.join(cdc, "cap_over"), over_sizes)
    over_pins = pins_of(over_sizes)
    ro = FakeGitRemote()
    cdo = fresh_case_dir(cdc, "over")
    kind, val = run_hold(lambda: do_publish(tree_o, CID2, ro, cdo, over_pins))
    record("A-10", "ceiling+1", "HOLD:CEILING, 0 writes", f"{val}, {ro.writes} writes",
           kind == "HOLD" and val == "HOLD:CEILING" and ro.writes == 0)

    # ============ H3: two-process intent fencing (req 3) ============
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

    META["suite_peak_rss_mib"] = round(
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2)
    with open(results_path, "w") as f:
        json.dump(RESULTS, f, indent=1, sort_keys=True)
    with open(meta_path, "w") as f:
        json.dump(META, f, indent=1, sort_keys=True)
    bad = [r for r in RESULTS if not r["pass"]]
    print(f"TOTAL {len(RESULTS)} records, {len(RESULTS) - len(bad)} pass, {len(bad)} fail")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
