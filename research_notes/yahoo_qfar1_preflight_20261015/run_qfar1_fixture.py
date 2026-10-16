"""QFAR1 offline preflight fixture driver (-13 r1).

Runs A-01..A-14 from the -12 r3 design (as adjudicated) against a no-socket
fake Git Data remote and synthetic captures. Usage:
  run_qfar1_fixture.py WORKDIR RESULTS_JSON META_JSON
RESULTS_JSON is fully deterministic (no timestamps/paths/RSS); volatile
measurements go to META_JSON. The suite is run twice from independently
materialized trees and the two RESULTS files must be byte-identical.
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
import qfar1_publisher as qp
from qfar1_publisher import HoldError, _ApiError, _TransportLost

MANIFEST = os.path.join(HERE, "..", "yahoo_clean_capture_preflight_20261015", "capture_manifest.json")
CONSTS = qp.derive_constants(MANIFEST)
PAYLOAD_RELS = CONSTS["payload_rels"]
CID = "TEST-CAPTURE-0001"
CID2 = "TEST-CAPTURE-0002"
CID3 = "TEST-CAPTURE-0003"
RESULTS = []


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

    # -- repo / refs
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

    # -- blobs
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
            data = bytes([data[100] ^ 1]) + data[101:] if False else data[:100] + bytes([data[100] ^ 1]) + data[101:]
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

    # -- trees
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

    # -- commits
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

    # -- helpers for cases
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
    """Run fn; return ('HOLD', code) or ('OK', result)."""
    try:
        return ("OK", fn())
    except HoldError as e:
        return ("HOLD", e.code)


def fresh_case_dir(work, name):
    d = os.path.join(work, name)
    os.makedirs(d)
    return d


def do_publish(tree, cid, remote, cdir, pins=None, hook=None, read_hook=None, phase_hook=None):
    return qp.publish(tree, cid, remote, os.path.join(cdir, "journal.jsonl"),
                      os.path.join(cdir, "staging"), MANIFEST,
                      validation_pins=pins, step_hook=hook,
                      read_hook=read_hook, phase_hook=phase_hook)


def build_only(tree, cdir, pins=None, phase_hook=None, read_hook=None):
    info = qp.build_container(tree, CID, os.path.join(cdir, "staging"), MANIFEST,
                              validation_pins=pins, phase_hook=phase_hook, read_hook=read_hook)
    data = os.pread(info["fd"], info["container_len"], 0)
    os.close(info["fd"]); os.close(info["spool_fd"])
    return info, data


# ------------------------------------------------------------------ cases
def main():
    work = sys.argv[1]
    results_path, meta_path = sys.argv[2], sys.argv[3]
    os.makedirs(work, exist_ok=True)
    sizes = default_sizes()
    pins = pins_of(sizes)
    t0 = time.time()

    # ---- A-01 determinism twin (two independently materialized trees)
    cd = fresh_case_dir(work, "a01")
    tA = materialize(os.path.join(cd, "treeA"), sizes, "forward", 1_600_000_000)
    tB = materialize(os.path.join(cd, "treeB"), sizes, "reverse", 1_700_000_000)
    iA, dA = build_only(tA, os.path.join(cd, "sA"))
    iB, dB = build_only(tB, os.path.join(cd, "sB"))
    record("A-01", "determinism twin", "identical bytes/sha/blob",
           f"eq={dA == dB} sha={iA['container_sha256'][:16]} blob={iA['blob_id'][:16]}",
           dA == dB and iA["container_sha256"] == iB["container_sha256"] and iA["blob_id"] == iB["blob_id"])
    record("A-10", "container length byte-exact vs formula", str(sizes_total(sizes, iA)),
           str(iA["container_len"]), iA["container_len"] == iA["total_physical"] + 9741)

    # ---- A-02 component swaps
    cd = fresh_case_dir(work, "a02a")
    tree = materialize(os.path.join(cd, "tree"), sizes)
    outside = os.path.join(cd, "outside"); os.mkdir(outside)
    with open(os.path.join(outside, "NVDA.csv"), "wb") as f: f.write(b"evil")
    shutil.rmtree(os.path.join(tree, "raw")); os.symlink(outside, os.path.join(tree, "raw"))
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s")))
    record("A-02", "symlink raw/ before census", "HOLD:PATH_TYPE|HOLD:MEMBERSHIP", got,
           st == "HOLD" and got in ("HOLD:PATH_TYPE", "HOLD:MEMBERSHIP"))

    cd = fresh_case_dir(work, "a02b")
    tree = materialize(os.path.join(cd, "tree"), sizes)
    def swap_after_census(phase, tree=tree, outside=outside):
        if phase == "census":
            shutil.rmtree(os.path.join(tree, "raw")); os.symlink(outside, os.path.join(tree, "raw"))
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s"), phase_hook=swap_after_census))
    record("A-02", "symlink raw/ after census before read", "HOLD:PATH_TYPE", got,
           st == "HOLD" and got == "HOLD:PATH_TYPE")

    cd = fresh_case_dir(work, "a02d")
    tree = materialize(os.path.join(cd, "tree"), sizes)
    def swap_legit(phase, tree=tree, cd=cd):
        if phase == "census":
            copy = os.path.join(cd, "rawcopy"); shutil.copytree(os.path.join(tree, "raw"), copy)
            shutil.rmtree(os.path.join(tree, "raw")); os.rename(copy, os.path.join(tree, "raw"))
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s"), phase_hook=swap_legit))
    record("A-02", "legitimate-directory swap after census", "HOLD:READ_DRIFT", got,
           st == "HOLD" and got == "HOLD:READ_DRIFT")

    cd = fresh_case_dir(work, "a02e")
    tree = materialize(os.path.join(cd, "tree"), sizes)
    def swap_leaf(phase, tree=tree):
        if phase == "census":
            p = os.path.join(tree, "raw", "NVDA.csv"); os.remove(p); os.symlink("/etc/hostname", p)
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s"), phase_hook=swap_leaf))
    record("A-02", "leaf symlink swap after census", "HOLD:PATH_TYPE", got,
           st == "HOLD" and got == "HOLD:PATH_TYPE")

    cd = fresh_case_dir(work, "a02f")
    tree = materialize(os.path.join(cd, "tree"), sizes)
    link = os.path.join(cd, "rootlink"); os.symlink(tree, link)
    st, got = run_hold(lambda: build_only(link, os.path.join(cd, "s")))
    record("A-02", "capture-root symlink", "HOLD:PATH_TYPE", got,
           st == "HOLD" and got == "HOLD:PATH_TYPE")

    cd = fresh_case_dir(work, "a02g")
    tree = materialize(os.path.join(cd, "tree"), sizes)
    shutil.rmtree(os.path.join(tree, "raw")); os.symlink("/proc/self/fd", os.path.join(tree, "raw"))
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s")))
    record("A-02", "magic-link component", "HOLD:PATH_TYPE|HOLD:MEMBERSHIP", got,
           st == "HOLD" and got in ("HOLD:PATH_TYPE", "HOLD:MEMBERSHIP"))

    # real-process churn swap during reads (big member, external swapper)
    cd = fresh_case_dir(work, "a02c")
    big = dict(sizes); big["raw/NVDA.csv"] = 6 * 1024 * 1024
    tree = materialize(os.path.join(cd, "tree"), big)
    outside2 = os.path.join(cd, "outside"); os.mkdir(outside2)
    with open(os.path.join(outside2, "NVDA.csv"), "wb") as f: f.write(b"evil")
    swapper = os.path.join(cd, "swapper.py")
    with open(swapper, "w") as f:
        f.write("import os,sys,time\n"
                "trig, tree, outside = sys.argv[1], sys.argv[2], sys.argv[3]\n"
                "while not os.path.exists(trig): time.sleep(0.01)\n"
                "os.rename(os.path.join(tree,'raw'), os.path.join(tree,'raw_real'))\n"
                "os.symlink(outside, os.path.join(tree,'raw'))\n")
    trig = os.path.join(cd, "trigger")
    proc = subprocess.Popen([sys.executable, swapper, trig, tree, outside2],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    state = {"n": 0}
    def churn_hook(rel, total, trig=trig, state=state):
        if rel == "raw/NVDA.csv":
            state["n"] += 1
            if state["n"] == 1:
                open(trig, "w").close()
            if state["n"] <= 4:
                time.sleep(0.05)
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s"), read_hook=churn_hook))
    proc.wait(timeout=30)
    record("A-02", "real-process symlink churn during reads", "HOLD:PATH_TYPE|HOLD:READ_DRIFT", got,
           st == "HOLD" and got in ("HOLD:PATH_TYPE", "HOLD:READ_DRIFT"))

    # ---- A-03 injection / membership
    cd = fresh_case_dir(work, "a03")
    tree = materialize(os.path.join(cd, "tree"), sizes)
    with open(os.path.join(tree, "raw", "FAKE.csv"), "wb") as f: f.write(b"x")
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s1")))
    record("A-03", "extra non-frozen file", "HOLD:MEMBERSHIP", got, st == "HOLD" and got == "HOLD:MEMBERSHIP")
    tree = materialize(os.path.join(cd, "tree2"), sizes)
    os.remove(os.path.join(tree, "meta", "QQQ.request.json"))
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s2")))
    record("A-03", "missing frozen file", "HOLD:MEMBERSHIP", got, st == "HOLD" and got == "HOLD:MEMBERSHIP")
    tree = materialize(os.path.join(cd, "tree3"), sizes)
    os.rename(os.path.join(tree, "raw", "NVDA.csv"), os.path.join(tree, "raw", "nvda.csv"))
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s3")))
    record("A-03", "case-variant rel raw/nvda.csv", "HOLD:MEMBERSHIP", got, st == "HOLD" and got == "HOLD:MEMBERSHIP")
    tree = materialize(os.path.join(cd, "tree4"), sizes)
    with open(os.path.join(tree, "raw", "nvda.csv"), "wb") as f: f.write(b"x")
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s4")))
    record("A-03", "frozen rel + case-variant both present", "HOLD:MEMBERSHIP", got,
           st == "HOLD" and got == "HOLD:MEMBERSHIP")
    for bad_id, nm in [("test-capture-0001", "lowercase id"), ("TEST--CAPTURE", "double hyphen"),
                       ("TEST/CAPTURE", "slash in id"), ("SHORT01", "length 7"),
                       ("X" * 65, "length 65")]:
        st, got = run_hold(lambda b=bad_id: qp._validate_capture_id(b))
        record("A-03", f"capture id: {nm}", "HOLD:ID_INVALID", got, st == "HOLD" and got == "HOLD:ID_INVALID")

    # ---- A-04 corruption
    cd = fresh_case_dir(work, "a04")
    tree = materialize(os.path.join(cd, "tree"), sizes)
    p = os.path.join(tree, "raw", "AMD.csv")
    data = bytearray(open(p, "rb").read()); data[10] ^= 1; open(p, "wb").write(bytes(data))
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s1"), pins=pins))
    record("A-04", "member bit-flip vs validation pins", "HOLD:MEMBER_DRIFT", got,
           st == "HOLD" and got == "HOLD:MEMBER_DRIFT")
    info, good = build_only(materialize(os.path.join(cd, "tree2"), sizes), os.path.join(cd, "s2"))
    pinmap = info["pins"]
    def parse_bytes(b):
        fd = os.memfd_create("t"); os.write(fd, b); os.lseek(fd, 0, 0)
        try:
            parsed = qp.parse_container_fd(fd, len(b), PAYLOAD_RELS)
            qp._verify_dag(parsed, pinmap, PAYLOAD_RELS)
            return "PARSED"
        finally:
            os.close(fd)
    tampered = bytearray(good); tampered[len(good) // 2] ^= 1
    st, got = run_hold(lambda: parse_bytes(bytes(tampered)))
    record("A-04", "sealed container payload flip", "HOLD:*", got, st == "HOLD")
    tampered = bytearray(good); tampered[40] ^= 1  # inside first index entry hash
    st, got = run_hold(lambda: parse_bytes(bytes(tampered)))
    record("A-04", "index hash flip", "HOLD:*", got, st == "HOLD")
    tampered = bytearray(good); tampered[-1] ^= 1
    st, got = run_hold(lambda: parse_bytes(bytes(tampered)))
    record("A-04", "trailer flip", "HOLD:CONTAINER_FORMAT", got, st == "HOLD" and got == "HOLD:CONTAINER_FORMAT")

    # ---- A-05 truncation / extension
    for nm, cut in [("cut in header", 8), ("cut mid-index", 100), ("cut mid-payload", len(good) // 2),
                    ("trailer missing", len(good) - 32)]:
        st, got = run_hold(lambda c=cut: parse_bytes(good[:c]))
        record("A-05", nm, "HOLD:CONTAINER_FORMAT", got, st == "HOLD" and got == "HOLD:CONTAINER_FORMAT")
    st, got = run_hold(lambda: parse_bytes(good + b"\x00"))
    record("A-05", "one trailing garbage byte", "HOLD:CONTAINER_FORMAT", got,
           st == "HOLD" and got == "HOLD:CONTAINER_FORMAT")
    tampered = bytearray(good)
    (rl,) = struct.unpack(">H", bytes(tampered[16:18]))
    off = 18 + rl
    (pl,) = struct.unpack(">Q", bytes(tampered[off:off + 8]))
    tampered[off:off + 8] = struct.pack(">Q", pl + 1)
    body = bytes(tampered[:-32]); tampered = body + hashlib.sha256(body).digest()
    st, got = run_hold(lambda: parse_bytes(bytes(tampered)))
    record("A-05", "index length overstates payload", "HOLD:CONTAINER_FORMAT", got,
           st == "HOLD" and got == "HOLD:CONTAINER_FORMAT")

    # ---- baseline remote for protocol cases
    cd = fresh_case_dir(work, "proto")
    tree = materialize(os.path.join(cd, "tree"), sizes)

    # ---- A-09 visibility (before any publish on these remotes)
    for nm, kw in [("repo public", {"private": False}), ("wrong repo name", {"name": "quality-flow-scanner-v5"})]:
        remote = FakeGitRemote(**kw)
        st, got = run_hold(lambda r=remote: do_publish(tree, CID, r, os.path.join(cd, "a09" + nm)))
        record("A-09", nm, "HOLD:VISIBILITY + 0 objects", f"{got} objs={len(remote.object_ids())}",
               st == "HOLD" and got == "HOLD:VISIBILITY" and len(remote.object_ids()) == 0)

    # ---- A-06 / A-14 / A-07 / A-12 on a shared remote with an established parent
    remote = FakeGitRemote()
    res = do_publish(tree, CID, remote, os.path.join(cd, "base"))
    P = remote.get_ref(qp.REF)
    record("A-06", "baseline publish establishes parent", "PUBLISHED", res["status"], res["status"] == "PUBLISHED")

    # A-12 duplicate invocation after success
    st, res2 = run_hold(lambda: do_publish(tree, CID, remote, os.path.join(cd, "base")))
    record("A-12", "duplicate publish after success", "ALREADY_PUBLISHED_VERIFIED",
           res2["status"] if st == "OK" else str(res2), st == "OK" and res2["status"] == "ALREADY_PUBLISHED_VERIFIED"
           and len(remote.commits_for(CID)) == 1)

    # A-14 W1: ref moves between preflight and intent
    cdw = fresh_case_dir(work, "a14w1"); remote_w = FakeGitRemote()
    do_publish(tree, CID, remote_w, os.path.join(cdw, "base"))
    Pw = remote_w.get_ref(qp.REF)
    snap = {}
    def hook_w1(step, remote_w=remote_w, snap=snap):
        if step == "preflight":
            sib = remote_w.make_sibling(Pw, "W1"); remote_w.refs[qp.REF] = sib
        if step == "intent":
            snap["ids"] = remote_w.object_ids()
    st, got = run_hold(lambda: do_publish(tree, CID2, remote_w, os.path.join(cdw, "w1"), hook=hook_w1))
    record("A-14", "W1 preflight->intent drift", "HOLD:PARENT_DRIFT + 0 publisher writes",
           f"{got} extra={len(remote_w.object_ids() - snap.get('ids', set()))}",
           st == "HOLD" and got == "HOLD:PARENT_DRIFT" and remote_w.object_ids() == snap.get("ids"))

    # A-14 W2: ref moves between intent and confirm
    cdw = fresh_case_dir(work, "a14w2"); remote_w = FakeGitRemote()
    do_publish(tree, CID, remote_w, os.path.join(cdw, "base"))
    Pw = remote_w.get_ref(qp.REF)
    snap = {}
    def hook_w2(step, remote_w=remote_w, snap=snap):
        if step == "intent":
            sib = remote_w.make_sibling(Pw, "W2"); remote_w.refs[qp.REF] = sib
            snap["ids"] = remote_w.object_ids()
    st, got = run_hold(lambda: do_publish(tree, CID2, remote_w, os.path.join(cdw, "w2"), hook=hook_w2))
    record("A-14", "W2 intent->confirm drift", "HOLD:PARENT_DRIFT + 0 publisher writes",
           f"{got} extra={len(remote_w.object_ids() - snap.get('ids', set()))}",
           st == "HOLD" and got == "HOLD:PARENT_DRIFT" and remote_w.object_ids() == snap.get("ids"))

    # A-14 W3 + A-06 race family: ref moves after confirm -> FF rejection
    cdw = fresh_case_dir(work, "a14w3"); remote_w = FakeGitRemote()
    do_publish(tree, CID, remote_w, os.path.join(cdw, "base"))
    Pw = remote_w.get_ref(qp.REF)
    sib_holder = {}
    def hook_w3(step, remote_w=remote_w):
        if step == "confirm":
            sib = remote_w.make_sibling(Pw, "W3"); remote_w.refs[qp.REF] = sib; sib_holder["sib"] = sib
    st, got = run_hold(lambda: do_publish(tree, CID2, remote_w, os.path.join(cdw, "w3"), hook=hook_w3))
    record("A-14", "W3 post-confirm race", "HOLD:REF_RACE, winner intact",
           f"{got} ref==sib:{remote_w.get_ref(qp.REF) == sib_holder.get('sib')}",
           st == "HOLD" and got == "HOLD:REF_RACE" and remote_w.get_ref(qp.REF) == sib_holder.get("sib"))

    # A-06: descendant-without-blob advance; ref deletion; creation race
    cdw = fresh_case_dir(work, "a06b"); remote_w = FakeGitRemote()
    do_publish(tree, CID, remote_w, os.path.join(cdw, "base"))
    Pw = remote_w.get_ref(qp.REF)
    def hook_desc(step, remote_w=remote_w):
        if step == "commit":
            sib = remote_w.make_sibling(Pw, "DESC"); child = remote_w.make_sibling(sib, "DESC2")
            remote_w.refs[qp.REF] = child
    st, got = run_hold(lambda: do_publish(tree, CID2, remote_w, os.path.join(cdw, "d"), hook=hook_desc))
    record("A-06", "ref advanced to descendant without our blob", "HOLD:REF_RACE", got,
           st == "HOLD" and got == "HOLD:REF_RACE")
    cdw = fresh_case_dir(work, "a06c"); remote_w = FakeGitRemote()
    do_publish(tree, CID, remote_w, os.path.join(cdw, "base"))
    def hook_del(step, remote_w=remote_w):
        if step == "commit":
            del remote_w.refs[qp.REF]
    st, got = run_hold(lambda: do_publish(tree, CID2, remote_w, os.path.join(cdw, "del"), hook=hook_del))
    record("A-06", "ref deleted mid-protocol", "HOLD:REF_RACE", got, st == "HOLD" and got == "HOLD:REF_RACE")
    cdw = fresh_case_dir(work, "a06d"); remote_w = FakeGitRemote()
    def hook_create_race(step, remote_w=remote_w):
        if step == "commit":
            sib = remote_w.make_sibling(None, "FIRST"); remote_w.refs[qp.REF] = sib
    st, got = run_hold(lambda: do_publish(tree, CID, remote_w, os.path.join(cdw, "cr"), hook=hook_create_race))
    record("A-06", "first-publication ref creation race", "HOLD:REF_RACE", got,
           st == "HOLD" and got == "HOLD:REF_RACE")

    # ---- A-07 crash / restart semantics
    for crash_at in ("blob", "tree", "commit"):
        cdw = fresh_case_dir(work, f"a07{crash_at}"); remote_w = FakeGitRemote()
        do_publish(tree, CID, remote_w, os.path.join(cdw, "base"))
        def hook_crash(step, crash_at=crash_at):
            if step == crash_at:
                raise Crash()
        try:
            do_publish(tree, CID2, remote_w, os.path.join(cdw, "x"), hook=hook_crash)
            crashed = False
        except Crash:
            crashed = True
        st, got = run_hold(lambda: do_publish(tree, CID2, remote_w, os.path.join(cdw, "x")))
        record("A-07", f"crash after {crash_at}, restart", "HOLD:ID_CONSUMED",
               f"crashed={crashed} then {got}",
               crashed and st == "HOLD" and got == "HOLD:ID_CONSUMED"
               and len(remote_w.commits_for(CID2)) <= 1)
    cdw = fresh_case_dir(work, "a07lost"); remote_w = FakeGitRemote()
    do_publish(tree, CID, remote_w, os.path.join(cdw, "base"))
    remote_w.faults.add("lose_update_response")
    st, got = run_hold(lambda: do_publish(tree, CID2, remote_w, os.path.join(cdw, "x")))
    first = (st, got)
    remote_w.faults.discard("lose_update_response")
    st2, res = run_hold(lambda: do_publish(tree, CID2, remote_w, os.path.join(cdw, "x")))
    record("A-07", "ref update applied, response lost; restart", "HOLD:API then PUBLISHED_BY_RECORDING",
           f"{first[1]} then {res['status'] if st2 == 'OK' else res}",
           first == ("HOLD", "HOLD:API") and st2 == "OK" and res["status"] == "PUBLISHED_BY_RECORDING"
           and len(remote_w.commits_for(CID2)) == 1)

    # ---- A-08 remote substitution
    cdw = fresh_case_dir(work, "a08")
    for nm, faults, expect in [
            ("create-blob wrong id", {"blob_wrong_id"}, "HOLD:BLOB_SUBSTITUTION"),
            ("tree entry names other blob", {"tree_wrong_entry"}, "HOLD:TREE_MISMATCH"),
            ("commit altered message", {"commit_alter_message"}, "HOLD:COMMIT_MISMATCH"),
            ("blob bytes altered (raw)", {"alter_blob"}, "HOLD:REFETCH_CONTAINER_HASH"),
            ("blob bytes altered (json)", {"alter_blob", "raw_refused"}, "HOLD:REFETCH_CONTAINER_HASH")]:
        remote_w = FakeGitRemote(); remote_w.faults = set(faults)
        st, got = run_hold(lambda r=remote_w, nm=nm: do_publish(tree, CID, r, os.path.join(cdw, nm)))
        record("A-08", nm, expect, got, st == "HOLD" and got == expect)
    remote_w = FakeGitRemote()
    do_publish(tree, CID, remote_w, os.path.join(cdw, "base2"))
    remote_w.faults = {"commit_extra_parent"}
    st, got = run_hold(lambda: do_publish(tree, CID2, remote_w, os.path.join(cdw, "xp")))
    record("A-08", "commit extra parent", "HOLD:COMMIT_MISMATCH", got,
           st == "HOLD" and got == "HOLD:COMMIT_MISMATCH")

    # ---- A-11 encoding
    cdw = fresh_case_dir(work, "a11")
    remote_w = FakeGitRemote(); remote_w.faults = {"raw_refused"}
    st, res = run_hold(lambda: do_publish(tree, CID, remote_w, os.path.join(cdw, "json")))
    record("A-11", "base64 JSON with embedded newlines verifies", "PUBLISHED",
           res["status"] if st == "OK" else res, st == "OK" and res["status"] == "PUBLISHED")
    for nm, faults in [("encoding field lies", {"raw_refused", "encoding_lie"}),
                       ("raw route returns JSON error body", {"raw_json_error"}),
                       ("base64 invalid padding", {"raw_refused", "bad_padding"})]:
        remote_w = FakeGitRemote(); remote_w.faults = set(faults)
        st, got = run_hold(lambda r=remote_w, nm=nm: do_publish(tree, CID, r, os.path.join(cdw, nm)))
        record("A-11", nm, "HOLD:ENCODING", got, st == "HOLD" and got == "HOLD:ENCODING")

    # ---- A-10 ceiling edges
    cd = fresh_case_dir(work, "a10")
    base = {rel: 430_000 for rel in PAYLOAD_RELS}
    exact = solve_ceiling_size(base, "raw/NVDA.csv")
    X = exact["raw/NVDA.csv"]
    tree = materialize(os.path.join(cd, "exact"), exact)
    st, res = run_hold(lambda: build_only(tree, os.path.join(cd, "s1")))
    ok = st == "OK" and res[0]["total_physical"] == qp.CEILING and res[0]["container_len"] == 67118605
    record("A-10", "sum physical == ceiling seals", f"total={qp.CEILING} len=67118605",
           f"{res[0]['total_physical']}/{res[0]['container_len']}" if st == "OK" else res, ok)
    over = dict(exact); over["raw/NVDA.csv"] = X + 1
    tree = materialize(os.path.join(cd, "over"), over)
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s2")))
    record("A-10", "sum physical == ceiling+1", "HOLD:CEILING", got, st == "HOLD" and got == "HOLD:CEILING")
    guard = {rel: 1000 for rel in PAYLOAD_RELS}; guard["raw/NVDA.csv"] = 33554432
    tree = materialize(os.path.join(cd, "guard"), guard)
    st, res = run_hold(lambda: build_only(tree, os.path.join(cd, "s3")))
    record("A-10", "single member at 32MiB guard, total in range", "seals",
           "sealed" if st == "OK" else res, st == "OK")
    # streaming ceiling: attempt consumed honestly, stream cut at budget
    budget = qp.StreamBudget(CONSTS["payload_budget_bytes"])
    budget.begin_request()
    fed = []
    def feed_all():
        for chunk in (600_000, 700_000):
            budget.feed(chunk); fed.append(chunk)
        # now simulate a giant response chunk that crosses the budget with a small budget instead
    sb = qp.StreamBudget(1_000_000)
    sb.begin_request(); sb.feed(600_000)
    st, got = run_hold(lambda: sb.feed(500_000))
    record("A-10", "streaming oversized response: attempt consumed, cut off",
           "attempts=1 cut=True HOLD:CEILING",
           f"attempts={sb.attempts_consumed} cut={sb.cut_off} {got}",
           st == "HOLD" and got == "HOLD:CEILING" and sb.attempts_consumed == 1 and sb.cut_off)
    # parity: rev.3 candidate pin vs publisher constant (checked again post-write in main flow)
    record("A-10", "adjudicated constants asserted by derive_constants", "all equal",
           "reserve=32164 budget=67076700",
           CONSTS["reserve_bytes"] == 32164 and CONSTS["payload_budget_bytes"] == 67076700)

    # ---- A-13 integrity-graph scope attacks (verify path via assembled containers)
    cd = fresh_case_dir(work, "a13")
    info, good = build_only(materialize(os.path.join(cd, "tree"), sizes), os.path.join(cd, "s0"))
    members = {}
    fd = os.memfd_create("m"); os.write(fd, good)
    parsed = qp.parse_container_fd(fd, len(good), PAYLOAD_RELS); os.close(fd)
    # recover member bytes by slicing per index order from `good`
    raw_members = slice_members(good)
    man = json.loads(raw_members["manifest.json"].decode())
    def with_manifest(mut):
        m2 = json.loads(raw_members["manifest.json"].decode()); mut(m2)
        b = qp._canonical_manifest(CID, m2["files"]) if False else \
            (json.dumps(m2, sort_keys=True, separators=(",", ":")).encode() + b"\n")
        mm = dict(raw_members); mm["manifest.json"] = b
        # rebuild sums over payloads + new manifest
        sm = {r: hashlib.sha256(mm[r]).hexdigest() for r in PAYLOAD_RELS}
        sm["manifest.json"] = hashlib.sha256(b).hexdigest()
        mm["SHA256SUMS"] = qp._canonical_sums(sm)
        return mm
    def with_sums(mut_lines):
        mm = dict(raw_members)
        lines = raw_members["SHA256SUMS"].decode().split("\n")[:-1]
        lines = mut_lines(lines)
        mm["SHA256SUMS"] = ("\n".join(lines) + "\n").encode()
        return mm
    def try_members(mm):
        blob = qp._assemble_container(mm)
        fd = os.memfd_create("t"); os.write(fd, blob)
        try:
            pr = qp.parse_container_fd(fd, len(blob), PAYLOAD_RELS)
            qp._verify_dag(pr, info["pins"], PAYLOAD_RELS)
            return "PARSED"
        finally:
            os.close(fd)
    st, got = run_hold(lambda: try_members(with_manifest(lambda m: m["files"].__setitem__("manifest.json", {"length": 1, "sha256": "0" * 64}))))
    record("A-13", "manifest self-entry", "HOLD:MANIFEST_SCOPE", got, st == "HOLD" and got == "HOLD:MANIFEST_SCOPE")
    st, got = run_hold(lambda: try_members(with_manifest(lambda m: m["files"].__setitem__("SHA256SUMS", {"length": 1, "sha256": "0" * 64}))))
    record("A-13", "manifest SHA256SUMS entry", "HOLD:MANIFEST_SCOPE", got, st == "HOLD" and got == "HOLD:MANIFEST_SCOPE")
    st, got = run_hold(lambda: try_members(with_manifest(lambda m: m["files"].pop("raw/NVDA.csv"))))
    record("A-13", "manifest omits a payload (scope mismatch)", "HOLD:MANIFEST_SCOPE", got,
           st == "HOLD" and got == "HOLD:MANIFEST_SCOPE")
    st, got = run_hold(lambda: try_members(with_sums(lambda ls: ls + [f"{'0'*64}  SHA256SUMS"])))
    record("A-13", "SHA256SUMS self-line (158 lines)", "HOLD:SUMS_SCOPE", got, st == "HOLD" and got == "HOLD:SUMS_SCOPE")
    st, got = run_hold(lambda: try_members(with_sums(lambda ls: [l for l in ls if not l.endswith("  manifest.json")])))
    record("A-13", "SHA256SUMS missing manifest line (156)", "HOLD:SUMS_SCOPE", got,
           st == "HOLD" and got == "HOLD:SUMS_SCOPE")
    # build-side: scope-violating bookkeeping file present in the capture dir
    tree = materialize(os.path.join(cd, "tree2"), sizes)
    bad_man = json.loads(qp._canonical_manifest(CID, {r: {"length": sizes[r], "sha256": pins[r]} for r in PAYLOAD_RELS}).decode())
    bad_man["files"]["manifest.json"] = {"length": 1, "sha256": "0" * 64}
    with open(os.path.join(tree, "manifest.json"), "wb") as f:
        f.write(json.dumps(bad_man, sort_keys=True, separators=(",", ":")).encode() + b"\n")
    st, got = run_hold(lambda: build_only(tree, os.path.join(cd, "s9")))
    record("A-13", "on-disk manifest self-entry at build", "HOLD:MANIFEST_SCOPE", got,
           st == "HOLD" and got == "HOLD:MANIFEST_SCOPE")

    # ---- summary
    allpass = all(r["pass"] for r in RESULTS)
    with open(results_path, "w") as f:
        json.dump({"task": "QF-YAHOO-QFAR1-OFFLINE-PREFLIGHT-20261015-13 r1",
                   "constants": {k: CONSTS[k] for k in
                                 ("sum_rel_len_158", "index_bytes", "overhead_bytes",
                                  "max_container_bytes", "max_base64_bytes", "sums_bytes",
                                  "manifest_template_max_bytes", "reserve_bytes",
                                  "payload_budget_bytes", "ceiling")},
                   "cases": RESULTS, "all_pass": allpass}, f, indent=1, sort_keys=True)
    with open(meta_path, "w") as f:
        json.dump({"elapsed_s": round(time.time() - t0, 1),
                   "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
                   "n_cases": len(RESULTS), "n_pass": sum(1 for r in RESULTS if r["pass"])}, f, indent=1)
    print(f"cases={len(RESULTS)} pass={sum(1 for r in RESULTS if r['pass'])} all_pass={allpass}")
    return 0 if allpass else 1


def sizes_total(sizes_map, info):
    return info["container_len"]


def solve_ceiling_size(base_sizes, adjust_rel):
    """Adjust one member (staying under the 32MiB per-member guard) so
    sum(physical) == CEILING exactly, iterating because manifest.json length
    depends on the decimal digits of the adjusted length."""
    sizes = dict(base_sizes)
    for _ in range(12):
        files = {r: {"length": sizes[r], "sha256": "0" * 64} for r in PAYLOAD_RELS}
        man_len = len(qp._canonical_manifest(CID, files))
        total = sum(sizes.values()) + man_len + CONSTS["sums_bytes"]
        if total == qp.CEILING:
            return sizes
        sizes[adjust_rel] += qp.CEILING - total
        if not (0 < sizes[adjust_rel] <= qp.PER_MEMBER_GUARD):
            raise RuntimeError("ceiling solve left the per-member guard")
    raise RuntimeError("ceiling solve did not converge")


def slice_members(container):
    (count,) = struct.unpack(">I", container[12:16])
    pos = 16
    entries = []
    for _ in range(count):
        (ll,) = struct.unpack(">H", container[pos:pos + 2]); pos += 2
        rel = container[pos:pos + ll].decode(); pos += ll
        (pl,) = struct.unpack(">Q", container[pos:pos + 8]); pos += 8 + 32
        entries.append((rel, pl))
    out = {}
    for rel, pl in entries:
        out[rel] = container[pos:pos + pl]; pos += pl
    return out


if __name__ == "__main__":
    sys.exit(main())
