"""No-socket fixture for QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-OFFLINE-20261016-19 r1.

Sockets are denied BEFORE the executor is imported. All transport is injected
and deterministic; all clocks are virtual. The fixture-side validator (never
the executor) computes the 156 payload hashes for the publisher-compatibility
case. Output: one deterministic results JSON (no volatile paths/timestamps).
"""
import ast
import hashlib
import importlib.util
import json
import os
import resource
import socket
import sys
import tempfile
from datetime import datetime, timedelta, timezone

# ---------- deny sockets before importing the code under test ----------
_SOCKET_DENIALS = []


def _denied(*a, **k):
    _SOCKET_DENIALS.append(1)
    raise RuntimeError("socket access denied by fixture")


class _DeniedSocket:
    def __init__(self, *a, **k):
        _denied()


socket.socket = _DeniedSocket
socket.create_connection = _denied
socket.getaddrinfo = _denied

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EXEC_PATH = os.path.join(HERE, "clean_capture_executor.py")
CANDIDATE = os.path.join(
    REPO, "research_notes/yahoo_rev3_pin_separation_20261016_r3/"
          "capture_manifest_rev3_pin_separated_candidate.json")
FROZEN = os.path.join(
    REPO, "research_notes/yahoo_clean_capture_preflight_20261015/capture_manifest.json")
PUB_PATH = os.path.join(
    REPO, "research_notes/yahoo_qfar1_journal_header_auth_20261016/qfar1_publisher_h16.py")
PUB_SHA256 = "1d4c192324744c77e294c0b3190e88666dce583b14ef4412b3e31f85127fdc10"
CID = "TEST-CAPTURE-01"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ex = _load("clean_capture_executor", EXEC_PATH)
HoldError = ex.HoldError
TransportFailure = ex.TransportFailure
PLAN = ex.load_plan(CANDIDATE)
SYMS = [p["symbol"] for p in PLAN]


class VClock:
    def __init__(self):
        self.t = 1700000000.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s

    def iso(self):
        return datetime.fromtimestamp(self.t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class CrashSim(BaseException):
    pass


def gen_bars(sym, rows=120, pad_ts=0):
    seed = int(hashlib.sha256(sym.encode()).hexdigest()[:8], 16)
    base = 100.0 + (seed % 500) / 10.0
    t0 = datetime(2024, 10, 18, 13, 30, tzinfo=timezone.utc)
    out = []
    for i in range(rows):
        ts = (t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ") + "X" * pad_ts
        o = base + (i % 7) * 0.25
        out.append({"Datetime": ts, "Open": o, "High": o + 0.5, "Low": o - 0.5,
                    "Close": o + 0.25, "Volume": 1000 + i,
                    "Dividends": 0, "Stock Splits": 0})
    return out


def good_resp(req, rows=120, pad_ts=0):
    sess = req["session"]
    meta = {"session": sess, "class": req["class"],
            "exchange": "XNYS" if sess == "XNYS" else "CCC",
            "timezone": "America/New_York" if sess == "XNYS" else "UTC",
            "currency": "USD", "source": "synthetic-fixture"}
    return {"status": 200, "symbol": req["symbol"], "meta": meta,
            "bars": gen_bars(req["symbol"], rows, pad_ts), "end_covered": True}


class Transport:
    """Recording scripted transport. script: fn(idx, req, default_fn)->resp."""

    def __init__(self, clock, script=None):
        self.clock = clock
        self.script = script
        self.calls = []        # symbols in call order
        self.starts = []       # virtual start times

    def __call__(self, req):
        idx = len(self.calls)
        self.calls.append(req["symbol"])
        self.starts.append(self.clock.now())
        if self.script:
            return self.script(idx, req, lambda: good_resp(req))
        return good_resp(req)


def fresh_exec(base):
    clock = VClock()
    return clock, ex.Limiter(clock)


def run(base, transport, clock, limiter, cid=CID):
    return ex.run_capture(CANDIDATE, base, cid, transport, clock, limiter)


def tree_map(root):
    out = {}
    for dp, dns, fns in os.walk(root):
        dns.sort()
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            out[rel] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


class Case:
    def __init__(self, cid_, title):
        self.id, self.title = cid_, title
        self.checks, self.failures = 0, []

    def check(self, ok, label):
        self.checks += 1
        if not ok:
            self.failures.append(label)

    def done(self):
        return {"id": self.id, "title": self.title, "checks": self.checks,
                "failures": self.failures,
                "verdict": "PASS" if not self.failures else "FAIL"}


def expect_hold(fn, code):
    try:
        fn()
    except HoldError as e:
        return e.code == code
    except Exception:
        return False
    return False


# ------------------------------------------------------------------ cases
def c1(d):
    c = Case("C-01", "52-call success: exact 156 payloads, journal outside root, limiter, no bookkeeping")
    base = os.path.join(d, "c1")
    clock, lim = fresh_exec(base)
    tr = Transport(clock)
    res = run(base, tr, clock, lim)
    c.check(res["status"] == "COMPLETE", f"status {res['status']}")
    c.check(tr.calls == SYMS, "call order == frozen order")
    c.check(len(tr.calls) == 52, "exactly 52 calls")
    gaps = [b - a for a, b in zip(tr.starts, tr.starts[1:])]
    c.check(all(g >= 1.0 for g in gaps), "limiter gaps >= 1.0s")
    root = os.path.join(base, CID)
    tm = tree_map(root)
    c.check(len(tm) == 156, f"payload count {len(tm)}")
    c.check(not any(os.path.basename(r) in ("manifest.json", "SHA256SUMS") for r in tm),
            "no bookkeeping files")
    c.check(sorted(os.listdir(root)) == ["actions", "meta", "raw"], "root top level exact")
    ctrl = os.path.join(base, CID + ".control")
    c.check(os.path.isfile(os.path.join(ctrl, "acquisition_attempt_journal.qfj2")),
            "journal in control dir")
    c.check(res["payload_bytes"] == sum(os.path.getsize(os.path.join(root, r)) for r in tm),
            "payload bytes accounted")
    # determinism twin: identical rebuild
    base2 = os.path.join(d, "c1twin")
    clock2, lim2 = fresh_exec(base2)
    tr2 = Transport(clock2)
    res2 = run(base2, tr2, clock2, lim2)
    c.check(tree_map(os.path.join(base2, CID)) == tm, "twin tree byte-identical")
    j1 = open(os.path.join(ctrl, "acquisition_attempt_journal.qfj2"), "rb").read()
    j2 = open(os.path.join(base2, CID + ".control",
                           "acquisition_attempt_journal.qfj2"), "rb").read()
    c.check(j1 == j2, "twin journal byte-identical")
    c.check(res2["status"] == "COMPLETE", "twin completes")
    return c.done(), base


def c2(d):
    c = Case("C-02", "crash after ATTEMPT before finalization -> restart zero calls, AMBIGUOUS hold")
    base = os.path.join(d, "c2")
    clock, lim = fresh_exec(base)

    def script(idx, req, default):
        if idx == 2:
            raise CrashSim()
        return default()

    tr = Transport(clock, script)
    crashed = False
    try:
        run(base, tr, clock, lim)
    except CrashSim:
        crashed = True
    c.check(crashed, "crash propagated (process-death equivalent)")
    c.check(len(tr.calls) == 3, "3 calls before crash")
    clock2, lim2 = fresh_exec(base)
    tr2 = Transport(clock2)
    c.check(expect_hold(lambda: run(base, tr2, clock2, lim2),
                        "HOLD:ATTEMPT_CONSUMED_AMBIGUOUS"), "restart holds AMBIGUOUS")
    c.check(tr2.calls == [], "restart made zero calls")
    return c.done()


def c3(d, c1base):
    c = Case("C-03", "valid COMPLETE restart skips with zero calls")
    clock, lim = fresh_exec(c1base)
    tr = Transport(clock)
    res = run(c1base, tr, clock, lim)
    c.check(res["status"] == "COMPLETE", "status COMPLETE")
    c.check(tr.calls == [], "zero calls")
    c.check(all(v == "SKIP_VERIFIED" for v in res["states"].values()), "all SKIP_VERIFIED")
    return c.done()


def c4(d, droot):
    c = Case("C-04", "missing/altered member of completed triplet -> zero-call FINAL_MISMATCH")
    import shutil
    for mode in ("missing", "altered"):
        base = os.path.join(droot, "c4" + mode)
        shutil.copytree(os.path.join(droot, "c1"), base)
        victim = os.path.join(base, CID, "raw", SYMS[0] + ".csv")
        if mode == "missing":
            os.unlink(victim)
        else:
            with open(victim, "ab") as f:
                f.write(b"X")
        clock, lim = fresh_exec(base)
        tr = Transport(clock)
        c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:FINAL_MISMATCH"),
                f"{mode}: FINAL_MISMATCH")
        c.check(tr.calls == [], f"{mode}: zero calls")
    return c.done()


def _seed_journal(base, records):
    """Craft a journal file directly (ATTEMPT+COMPLETE for symbol 0)."""
    ctrl = os.path.join(base, CID + ".control")
    os.makedirs(ctrl, exist_ok=True)
    jp = os.path.join(ctrl, "acquisition_attempt_journal.qfj2")
    with open(jp, "wb") as f:
        for i, rec in enumerate(records):
            f.write(ex._frame_bytes(rec, i))
    return jp


def c5(d):
    c = Case("C-05", "duplicate/conflicting/torn/interior-corrupt journal -> zero-call named HOLD")
    p0 = PLAN[0]
    attempt = {"type": "ATTEMPT", "symbol": p0["symbol"], "rels": p0["rels"], "clock": 1.0}
    complete = {"type": "COMPLETE", "symbol": p0["symbol"],
                "files": {r: "0" * 64 for r in p0["rels"]}, "bytes": 3, "clock": 2.0}
    variants = [
        ("dup_attempt", [attempt, attempt], "HOLD:JOURNAL_CONFLICT"),
        ("complete_no_attempt", [complete], "HOLD:JOURNAL_CONFLICT"),
        ("dup_complete", [attempt, complete, complete], "HOLD:JOURNAL_CONFLICT"),
    ]
    for name, recs, code in variants:
        base = os.path.join(d, "c5" + name)
        _seed_journal(base, recs)
        clock, lim = fresh_exec(base)
        tr = Transport(clock)
        c.check(expect_hold(lambda: run(base, tr, clock, lim), code), f"{name}: {code}")
        c.check(tr.calls == [], f"{name}: zero calls")
    # torn final frame
    base = os.path.join(d, "c5torn")
    jp = _seed_journal(base, [attempt, complete])
    data = open(jp, "rb").read()
    with open(jp, "wb") as f:
        f.write(data[:-7])
    clock, lim = fresh_exec(base)
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:JOURNAL_TORN"), "torn: JOURNAL_TORN")
    c.check(tr.calls == [], "torn: zero calls")
    # interior corruption: flip a payload byte in frame 0
    base = os.path.join(d, "c5corrupt")
    jp = _seed_journal(base, [attempt, complete])
    data = bytearray(open(jp, "rb").read())
    data[60] ^= 0x01
    with open(jp, "wb") as f:
        f.write(bytes(data))
    clock, lim = fresh_exec(base)
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:JOURNAL_CORRUPT"),
            "corrupt: JOURNAL_CORRUPT")
    c.check(tr.calls == [], "corrupt: zero calls")
    return c.done()


def c6(d):
    c = Case("C-06", "symlink/path/capture-ID/case adversaries fail before transport")
    bad_ids = ["test-capture-01", "../TEST-CAPTURE-01", "TEST-01", "TEST--CAPTURE-01",
               "TEST CAPTURE 01", "ТЕSТ-CAPTURE-01", "TEST-CAPTURE-01\n", "A" * 65,
               "TEST-CAPTURE_01", "-TEST-CAPTURE1", "TEST-CAPTURE1-"]
    for i, bid in enumerate(bad_ids):
        base = os.path.join(d, f"c6id{i}")
        clock, lim = fresh_exec(base)
        tr = Transport(clock)
        c.check(expect_hold(lambda: run(base, tr, clock, lim, cid=bid),
                            "HOLD:CAPTURE_ID_INVALID"), f"id {bid!r} rejected")
        c.check(tr.calls == [], f"id {bid!r}: zero calls")
    # case collision sibling
    base = os.path.join(d, "c6case")
    os.makedirs(os.path.join(base, CID.lower()))
    clock, lim = fresh_exec(base)
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:CAPTURE_ID_INVALID"),
            "case collision rejected")
    c.check(tr.calls == [], "case collision: zero calls")
    # root as symlink
    base = os.path.join(d, "c6rootlink")
    os.makedirs(base)
    os.makedirs(os.path.join(base, "elsewhere"))
    os.symlink(os.path.join(base, "elsewhere"), os.path.join(base, CID))
    clock, lim = fresh_exec(base)
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:PATH_TYPE"), "root symlink rejected")
    c.check(tr.calls == [], "root symlink: zero calls")
    # control as symlink
    base = os.path.join(d, "c6ctrllink")
    os.makedirs(base)
    os.makedirs(os.path.join(base, "elsewhere2"))
    os.symlink(os.path.join(base, "elsewhere2"), os.path.join(base, CID + ".control"))
    clock, lim = fresh_exec(base)
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:PATH_TYPE"), "control symlink rejected")
    c.check(tr.calls == [], "control symlink: zero calls")
    # symlink inside root
    base = os.path.join(d, "c6inner")
    os.makedirs(os.path.join(base, CID, "raw"))
    os.symlink("/etc/hostname", os.path.join(base, CID, "raw", "EVIL.csv"))
    clock, lim = fresh_exec(base)
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:PATH_TYPE"), "inner symlink rejected")
    c.check(tr.calls == [], "inner symlink: zero calls")
    return c.done()


def c7(d):
    c = Case("C-07", "429/exception/shape/schema/meta/partial + ceilings -> stop, named HOLD, no retry")

    def trial(name, script, want_code, want_calls, advance=None):
        base = os.path.join(d, "c7" + name)
        clock, lim = fresh_exec(base)
        tr = Transport(clock, script)
        res = run(base, tr, clock, lim)
        c.check(res["status"] == "INCOMPLETE_HOLD" and res["code"] == want_code,
                f"{name}: {res['status']}/{res['code']} != {want_code}")
        c.check(len(tr.calls) == want_calls, f"{name}: calls {len(tr.calls)} != {want_calls}")

    trial("429", lambda i, r, dfn: (_ for _ in ()).throw(TransportFailure(429)) if i == 3 else dfn(),
          "HOLD:THROTTLE_429", 4)
    trial("exc", lambda i, r, dfn: (_ for _ in ()).throw(ConnectionError("boom")) if i == 1 else dfn(),
          "HOLD:TRANSPORT", 2)

    def shape(i, r, dfn):
        if i == 0:
            x = dfn(); x["bars"] = {"nope": 1}; return x
        return dfn()
    trial("shape", shape, "HOLD:SHAPE_DRIFT", 1)

    def schema(i, r, dfn):
        if i == 0:
            x = dfn(); del x["bars"][0]["Close"]; return x
        return dfn()
    trial("schema", schema, "HOLD:SCHEMA_DRIFT", 1)

    def meta(i, r, dfn):
        if i == 0:
            x = dfn(); x["meta"]["session"] = "WRONG"; return x
        return dfn()
    trial("meta", meta, "HOLD:META_DRIFT", 1)

    def unknown(i, r, dfn):
        if i == 0:
            x = dfn(); x["symbol"] = "ZZZZ"; return x
        return dfn()
    trial("unknown", unknown, "HOLD:META_DRIFT", 1)

    def partial(i, r, dfn):
        if i == 2:
            x = dfn(); x["end_covered"] = False; return x
        return dfn()
    trial("partial", partial, "HOLD:PARTIAL_RESPONSE", 3)

    def symceil(i, r, dfn):
        if i == 0:
            return good_resp(r, rows=20000, pad_ts=1800)
        return dfn()
    trial("symceiling", symceil, "HOLD:SYMBOL_CEILING", 1)

    def rowceil(i, r, dfn):
        if i == 0:
            return good_resp(r, rows=20001)
        return dfn()
    trial("rowceiling", rowceil, "HOLD:ROW_CEILING", 1)

    def total(i, r, dfn):
        return good_resp(r, rows=12000, pad_ts=30)
    base = os.path.join(d, "c7total")
    clock, lim = fresh_exec(base)
    tr = Transport(clock, total)
    res = run(base, tr, clock, lim)
    c.check(res["code"] == "HOLD:TOTAL_CEILING", f"total: {res['code']}")
    c.check(40 <= len(tr.calls) <= 52, f"total: stopped at call {len(tr.calls)}")

    def wall(i, r, dfn):
        if i == 1:
            clock_holder[0].sleep(2000.0)
        return dfn()
    base = os.path.join(d, "c7wall")
    clock, lim = fresh_exec(base)
    clock_holder = [clock]
    tr = Transport(clock, wall)
    res = run(base, tr, clock, lim)
    c.check(res["code"] == "HOLD:WALL_CEILING", f"wall: {res['code']}")
    c.check(len(tr.calls) == 2, f"wall: calls {len(tr.calls)} != 2")
    return c.done()


def c8(d, c1base):
    c = Case("C-08", "fixture validator pins -> accepted publisher seals exactly 158, journals outside")
    c.check(hashlib.sha256(open(PUB_PATH, "rb").read()).hexdigest() == PUB_SHA256,
            "publisher file pin")
    pub = _load("qfar1_publisher_h16", PUB_PATH)
    root = os.path.join(c1base, CID)
    pins = {}
    for dp, dns, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            pins[rel] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    c.check(len(pins) == 156, "validator computed 156 pins")
    import base64 as _b64
    import fcntl as _fcntl

    class FakeRemote:
        def __init__(self, r):
            self.root = r
            for dd in ("blobs", "trees", "commits", "refs"):
                os.makedirs(os.path.join(r, dd), exist_ok=True)
            self._fd = os.open(os.path.join(r, "lock"), os.O_RDWR | os.O_CREAT, 0o600)

        def _put(self, kind, oid, data):
            p = os.path.join(self.root, kind, oid)
            if not os.path.exists(p):
                with open(p + ".tmp", "wb") as f:
                    f.write(data)
                os.rename(p + ".tmp", p)

        def _get(self, kind, oid):
            p = os.path.join(self.root, kind, oid)
            return open(p, "rb").read() if os.path.exists(p) else None

        def get_repo(self):
            return {"private": True, "owner": pub.DESIGNATED_OWNER, "name": pub.DESIGNATED_REPO}

        def get_ref(self, ref):
            data = self._get("refs", ref.replace("/", "_"))
            return data.decode() if data else None

        def create_ref(self, ref, sha):
            _fcntl.flock(self._fd, _fcntl.LOCK_EX)
            try:
                if os.path.exists(os.path.join(self.root, "refs", ref.replace("/", "_"))):
                    raise pub._ApiError(422, "reference already exists")
                self._put("refs", ref.replace("/", "_"), sha.encode())
                return {"ref": ref, "sha": sha}
            finally:
                _fcntl.flock(self._fd, _fcntl.LOCK_UN)

        def update_ref(self, ref, sha, force=False):
            cur = self.get_ref(ref)
            if cur is None:
                raise pub._ApiError(422, "reference does not exist")
            self._put("refs", ref.replace("/", "_"), sha.encode())
            return {"ref": ref, "sha": sha}

        def create_blob(self, content_b64, encoding):
            data = _b64.b64decode(content_b64)
            bid = hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()
            self._put("blobs", bid, data)
            return {"sha": bid}

        def get_blob_raw(self, sha):
            return self._get("blobs", sha)

        def get_blob_json(self, sha):
            data = self._get("blobs", sha)
            b = _b64.b64encode(data).decode()
            wrapped = "\n".join(b[i:i + 60] for i in range(0, len(b), 60))
            return {"content": wrapped, "encoding": "base64", "size": len(data)}

        def create_tree(self, base_tree, entries):
            tree = {}
            if base_tree:
                raw = self._get("trees", base_tree)
                if raw:
                    tree = json.loads(raw)
            for e in entries:
                entry = {"mode": e["mode"], "type": e["type"], "sha": e["sha"]}
                if e["type"] == "blob":
                    data = self._get("blobs", e["sha"])
                    if data is not None:
                        entry["size"] = len(data)
                tree[e["path"]] = entry
            tid = hashlib.sha1(b"tree %d\x00" % len(json.dumps(tree, sort_keys=True).encode())
                               + json.dumps(tree, sort_keys=True).encode()).hexdigest()
            self._put("trees", tid, json.dumps(tree, sort_keys=True).encode())
            return tid

        def tree_entry(self, tree_id, path):
            if tree_id is None:
                return None
            raw = self._get("trees", tree_id)
            return json.loads(raw).get(path) if raw else None

        def create_commit(self, message, tree, parents):
            parents = list(parents)
            body = (f"tree {tree}\n" + "".join(f"parent {p}\n" for p in parents)
                    + "author QF Publisher <qf@localhost> 1700000000 +0000\n"
                    + "committer QF Publisher <qf@localhost> 1700000000 +0000\n\n" + message).encode()
            cid_ = hashlib.sha1(b"commit %d\x00" % len(body) + body).hexdigest()
            self._put("commits", cid_,
                      json.dumps({"tree": tree, "parents": parents, "message": message}).encode())
            return cid_

        def get_commit(self, sha):
            raw = self._get("commits", sha)
            if raw is None:
                raise KeyError(sha)
            return json.loads(raw)

    info = pub.build_container(root, CID, os.path.join(d, "staging8"),
                               FROZEN, pins)
    c.check(len(info["pins"]) == 158, f"sealed members {len(info['pins'])}")
    os.close(info["fd"])
    remote = FakeRemote(os.path.join(d, "remote8"))
    pub_journal = os.path.join(c1base, CID + ".control", "qfj2_publication_journal.qfj2")
    res = pub.publish(root, CID, remote, pub_journal,
                      os.path.join(d, "staging8b"), FROZEN, pins)
    c.check(res.get("status") == "PUBLISHED", f"publish status {res.get('status')}")
    c.check(remote.get_ref("refs/heads/qf-archive") is not None, "archive ref updated")
    c.check(os.path.isfile(pub_journal), "publication journal in control dir")
    c.check(not os.path.exists(os.path.join(root, "manifest.json.tmp")), "no stray staging in root")
    c.check(sorted(os.listdir(root)) == ["actions", "meta", "raw"],
            "root still membership-pure after publish build inputs")
    return c.done()


def c9():
    c = Case("C-09", "import audit: no parked-executor dependency, stdlib only, sockets denied")
    src = open(EXEC_PATH).read()
    tree = ast.parse(src)
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    c.check(mods <= set(sys.stdlib_module_names), f"imports stdlib-only: {sorted(mods)}")
    for bad in ("execute_capture", "socket", "yfinance", "qfar1", "publish_snapshot",
                "import requests", "import urllib", "import yfinance"):
        c.check(bad not in src, f"source free of {bad!r}")
    try:
        socket.socket()
        denied = False
    except RuntimeError:
        denied = True
    c.check(denied, "socket constructor denied in fixture process")
    return c.done()


def main():
    out_path = sys.argv[1]
    d = tempfile.mkdtemp(prefix="qf19_")
    results = {"suite": "QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-OFFLINE-20261016-19 r1",
               "executor": "clean_capture_executor.py", "cases": []}
    r1, c1base = c1(d)
    results["cases"].append(r1)
    results["cases"].append(c2(d))
    results["cases"].append(c3(d, c1base))
    results["cases"].append(c4(d, d))
    results["cases"].append(c5(d))
    results["cases"].append(c6(d))
    results["cases"].append(c7(d))
    results["cases"].append(c8(d, c1base))
    results["cases"].append(c9())
    results["total_checks"] = sum(x["checks"] for x in results["cases"])
    results["total_failures"] = sum(len(x["failures"]) for x in results["cases"])
    results["verdict"] = "PASS" if results["total_failures"] == 0 else "FAIL"
    results["peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1, sort_keys=True)
        f.write("\n")
    print(results["verdict"], results["total_checks"], "checks,",
          results["total_failures"], "failures, peak RSS", results["peak_rss_mb"], "MB")


if __name__ == "__main__":
    main()
