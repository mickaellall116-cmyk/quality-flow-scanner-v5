"""Focused real-process/no-socket fixture for
QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-HARDENING-20261016-19 r2.

Sockets are denied BEFORE the executor is imported. Cases R2-01..R2-08 map
1:1 to the focused fixture list in spec comment 6214564508; the retained r1
happy-path smoke (R2-08) reuses the r1 fixture's FakeRemote for accepted-
publisher compatibility. The unrelated r1 negative matrix is NOT repeated.
Output: one deterministic results JSON (no volatile paths/timestamps).
"""
import hashlib
import importlib.util
import json
import os
import resource
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

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
EXEC_PATH = os.path.join(HERE, "clean_capture_executor_h19r2.py")
WORKER = os.path.join(HERE, "proc_worker.py")
CANDIDATE = os.path.join(
    REPO, "research_notes/yahoo_rev3_pin_separation_20261016_r3/"
          "capture_manifest_rev3_pin_separated_candidate.json")
FROZEN = os.path.join(
    REPO, "research_notes/yahoo_clean_capture_preflight_20261015/capture_manifest.json")
PUB_PATH = os.path.join(
    REPO, "research_notes/yahoo_qfar1_journal_header_auth_20261016/qfar1_publisher_h16.py")
PUB_SHA256 = "1d4c192324744c77e294c0b3190e88666dce583b14ef4412b3e31f85127fdc10"
CID = "TEST-CAPTURE-01"
JOURNAL = "acquisition_attempt_journal.qfj2"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ex = _load("clean_capture_executor_h19r2", EXEC_PATH)
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
    def __init__(self, clock, script=None):
        self.clock = clock
        self.script = script
        self.calls = []
        self.starts = []

    def __call__(self, req):
        idx = len(self.calls)
        self.calls.append(req["symbol"])
        self.starts.append(self.clock.now())
        if self.script:
            return self.script(idx, req, lambda: good_resp(req))
        return good_resp(req)


def fresh():
    clock = VClock()
    return clock, ex.Limiter(clock)


def run(base, transport, clock, limiter, cid=CID):
    return ex.run_capture(CANDIDATE, base, cid, transport, clock, limiter)


def journal_path(base, cid=CID):
    return os.path.join(base, cid + ".control", JOURNAL)


def read_records(base, cid=CID):
    return ex._journal_parse(open(journal_path(base, cid), "rb").read())


def tree_map(root):
    out = {}
    for dp, dns, fns in os.walk(root):
        dns.sort()
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            out[os.path.relpath(p, root)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
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


def wait_for(path, timeout=30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path):
            return True
        time.sleep(0.05)
    return False


# ------------------------------------------------------------------ cases
def r2_01(d):
    c = Case("R2-01", "two real processes: one owner calls, contender HOLD:OWNER_BUSY zero calls")
    base = os.path.join(d, "r201")
    marker = os.path.join(d, "r201marker")
    proc = subprocess.Popen([sys.executable, WORKER, "hold", base, CID,
                             CANDIDATE, marker],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        c.check(wait_for(os.path.join(marker, "started")), "owner reached first call")
        snap = open(journal_path(base), "rb").read()
        clock, lim = fresh()
        tr = Transport(clock)
        c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:OWNER_BUSY"),
                "contender HOLD:OWNER_BUSY")
        c.check(tr.calls == [], "contender zero calls")
        c.check(open(journal_path(base), "rb").read() == snap,
                "contender made zero journal mutation")
        with open(os.path.join(marker, "release"), "w") as f:
            f.write("x")
        proc.wait(timeout=120)
    finally:
        if proc.poll() is None:
            proc.kill()
    out = json.load(open(os.path.join(marker, "result.json")))
    c.check(out.get("status") == "COMPLETE", f"owner completed: {out}")
    c.check(out.get("calls") == 52, f"owner exactly 52 calls: {out.get('calls')}")
    recs = read_records(base)
    c.check(len(recs) == 104, f"journal records {len(recs)} == 104")
    c.check([r["symbol"] for r in recs if r["type"] == "ATTEMPT"] == SYMS,
            "one ATTEMPT per symbol in plan order, no duplicates")
    c.check(sum(1 for r in recs if r["type"] == "COMPLETE") == 52, "52 COMPLETEs")
    c.check(len(tree_map(os.path.join(base, CID))) == 156, "exactly 156 payloads")
    return c.done()


def r2_02(d):
    c = Case("R2-02", "owner killed after fsynced ATTEMPT: successor zero-call ATTEMPT_CONSUMED_AMBIGUOUS")
    base = os.path.join(d, "r202")
    marker = os.path.join(d, "r202marker")
    proc = subprocess.Popen([sys.executable, WORKER, "crash", base, CID,
                             CANDIDATE, marker],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc.wait(timeout=60)
    c.check(proc.returncode == 3, f"owner died mid-call (rc={proc.returncode})")
    recs = read_records(base)
    c.check(len(recs) == 1 and recs[0]["type"] == "ATTEMPT"
            and recs[0]["symbol"] == SYMS[0], "journal holds exactly the fsynced ATTEMPT")
    clock, lim = fresh()
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base, tr, clock, lim),
                        "HOLD:ATTEMPT_CONSUMED_AMBIGUOUS"),
            "successor (lock released by OS) holds AMBIGUOUS")
    c.check(tr.calls == [], "successor zero calls")
    return c.done()


def r2_03(d):
    c = Case("R2-03", "pre-existing temp/final retained byte-identical, zero call, named HOLD")
    # temp collision (fresh root, sentinel temp artifact)
    base = os.path.join(d, "r203tmp")
    os.makedirs(os.path.join(base, CID, "raw"))
    tmp = os.path.join(base, CID, "raw", "." + SYMS[0] + ".csv.tmp")
    with open(tmp, "wb") as f:
        f.write(b"SENTINEL-TEMP-BYTES")
    clock, lim = fresh()
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:TEMP_COLLISION"),
            "temp: HOLD:TEMP_COLLISION")
    c.check(tr.calls == [], "temp: zero calls")
    c.check(open(tmp, "rb").read() == b"SENTINEL-TEMP-BYTES",
            "temp retained byte-identical (never deleted)")
    # final collision (unjournaled final file present)
    base = os.path.join(d, "r203fin")
    os.makedirs(os.path.join(base, CID, "raw"))
    fin = os.path.join(base, CID, "raw", SYMS[0] + ".csv")
    with open(fin, "wb") as f:
        f.write(b"SENTINEL-FINAL-BYTES")
    clock, lim = fresh()
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:FINAL_MISMATCH"),
            "final: HOLD:FINAL_MISMATCH")
    c.check(tr.calls == [], "final: zero calls")
    c.check(open(fin, "rb").read() == b"SENTINEL-FINAL-BYTES",
            "final retained byte-identical (never overwritten)")
    return c.done()


def r2_04(d):
    c = Case("R2-04", "limiter sleep crosses 1800s wall: zero ATTEMPT/call after sleep, durable HOLD:WALL_CEILING")
    base = os.path.join(d, "r204")
    clock, lim = fresh()

    def script(idx, req, default):
        if idx == 0:
            clock.sleep(1799.0)   # first call completes at elapsed 1799.0
        return default()

    tr = Transport(clock, script)
    res = run(base, tr, clock, lim)
    c.check(res["status"] == "INCOMPLETE_HOLD" and res["code"] == "HOLD:WALL_CEILING",
            f"result {res['status']}/{res['code']}")
    c.check(tr.calls == SYMS[:2], f"calls stopped at 2: {len(tr.calls)}")
    recs = read_records(base)
    kinds = [r["type"] for r in recs]
    c.check(kinds == ["ATTEMPT", "COMPLETE", "ATTEMPT", "COMPLETE", "HOLD"],
            f"journal shape {kinds} (no third ATTEMPT after the sleep)")
    hold = recs[-1]
    c.check(hold["code"] == "HOLD:WALL_CEILING" and hold["symbol"] == SYMS[2]
            and hold["attempt_consumed"] is False, "durable HOLD binds wall/symbol/not-consumed")
    clock2, lim2 = fresh()
    tr2 = Transport(clock2)
    c.check(expect_hold(lambda: run(base, tr2, clock2, lim2), "HOLD:WALL_CEILING"),
            "restart reproduces WALL_CEILING from the durable record")
    c.check(tr2.calls == [], "restart zero calls")
    return c.done()


def r2_05(d):
    c = Case("R2-05", "429/schema/partial/total-ceiling failures: one durable HOLD; restart reproduces code/detail, zero calls")

    def trial(name, script, want_code, want_calls):
        base = os.path.join(d, "r205" + name)
        clock, lim = fresh()
        tr = Transport(clock, script)
        res = run(base, tr, clock, lim)
        c.check(res["status"] == "INCOMPLETE_HOLD" and res["code"] == want_code,
                f"{name}: {res['status']}/{res['code']} != {want_code}")
        c.check(len(tr.calls) == want_calls, f"{name}: calls {len(tr.calls)} != {want_calls}")
        recs = read_records(base)
        holds = [r for r in recs if r["type"] == "HOLD"]
        c.check(len(holds) == 1 and holds[0]["code"] == want_code
                and recs[-1]["type"] == "HOLD",
                f"{name}: exactly one terminal durable HOLD")
        clock2, lim2 = fresh()
        tr2 = Transport(clock2)
        got = {}

        def again():
            try:
                run(base, tr2, clock2, lim2)
            except HoldError as e:
                got["code"], got["detail"] = e.code, e.detail
                raise
        c.check(expect_hold(again, want_code), f"{name}: restart reproduces {want_code}")
        c.check(holds[0]["detail"] in got.get("detail", ""),
                f"{name}: restart reproduces original detail")
        c.check(tr2.calls == [], f"{name}: restart zero calls")

    trial("429", lambda i, r, dfn: (_ for _ in ()).throw(TransportFailure(429)) if i == 1 else dfn(),
          "HOLD:THROTTLE_429", 2)

    def schema(i, r, dfn):
        if i == 0:
            x = dfn(); del x["bars"][0]["Close"]; return x
        return dfn()
    trial("schema", schema, "HOLD:SCHEMA_DRIFT", 1)

    def partial(i, r, dfn):
        if i == 0:
            x = dfn(); x["end_covered"] = False; return x
        return dfn()
    trial("partial", partial, "HOLD:PARTIAL_RESPONSE", 1)

    base = os.path.join(d, "r205total")
    clock, lim = fresh()
    tr = Transport(clock, lambda i, r, dfn: good_resp(r, rows=12000, pad_ts=30))
    res = run(base, tr, clock, lim)
    c.check(res["code"] == "HOLD:TOTAL_CEILING", f"total: {res['code']}")
    recs = read_records(base)
    holds = [r for r in recs if r["type"] == "HOLD"]
    c.check(len(holds) == 1 and holds[0]["code"] == "HOLD:TOTAL_CEILING",
            "total: one durable TOTAL_CEILING HOLD")
    clock2, lim2 = fresh()
    tr2 = Transport(clock2)
    c.check(expect_hold(lambda: run(base, tr2, clock2, lim2), "HOLD:TOTAL_CEILING"),
            "total: restart reproduces TOTAL_CEILING")
    c.check(tr2.calls == [], "total: restart zero calls")
    return c.done()


def _seed_journal(base, records):
    ctrl = os.path.join(base, CID + ".control")
    os.makedirs(ctrl, exist_ok=True)
    jp = os.path.join(ctrl, JOURNAL)
    with open(jp, "wb") as f:
        for i, rec in enumerate(records):
            f.write(ex._frame_bytes(rec, i))
    return jp


def r2_06(d):
    c = Case("R2-06", "malformed/conflicting/duplicate HOLD + false byte-total COMPLETE fail closed / not trusted")
    p0 = PLAN[0]
    attempt = {"type": "ATTEMPT", "capture_id": CID, "symbol": p0["symbol"],
               "rels": p0["rels"], "clock": 1.0}
    complete = {"type": "COMPLETE", "capture_id": CID, "symbol": p0["symbol"],
                "files": {r: "0" * 64 for r in p0["rels"]}, "bytes": 3, "clock": 2.0}
    good_hold = {"type": "HOLD", "capture_id": CID, "symbol": None,
                 "code": "HOLD:TRANSPORT", "detail": "x",
                 "attempt_consumed": False, "clock": 3.0}
    variants = [
        ("malformed_hold", [dict(good_hold, detail=123)], "HOLD:JOURNAL_CONFLICT"),
        ("duplicate_hold", [good_hold, good_hold], "HOLD:JOURNAL_CONFLICT"),
        ("hold_after_complete",
         [attempt, complete, dict(good_hold, symbol=p0["symbol"])], "HOLD:JOURNAL_CONFLICT"),
        ("consumed_without_attempt",
         [dict(good_hold, symbol=p0["symbol"], attempt_consumed=True)], "HOLD:JOURNAL_CONFLICT"),
        ("record_after_hold", [good_hold, attempt], "HOLD:JOURNAL_CONFLICT"),
    ]
    for name, recs, code in variants:
        base = os.path.join(d, "r206" + name)
        _seed_journal(base, recs)
        clock, lim = fresh()
        tr = Transport(clock)
        c.check(expect_hold(lambda: run(base, tr, clock, lim), code), f"{name}: {code}")
        c.check(tr.calls == [], f"{name}: zero calls")
    # false byte-total in a COMPLETE record: bytes are recomputed from files
    base = os.path.join(d, "r206falsebytes")
    clock, lim = fresh()
    tr = Transport(clock)
    res = run(base, tr, clock, lim)
    c.check(res["status"] == "COMPLETE", "seed capture completes")
    root = os.path.join(base, CID)
    actual = sum(os.path.getsize(os.path.join(dp, fn))
                 for dp, _, fns in os.walk(root) for fn in fns)
    jp = journal_path(base)
    recs = ex._journal_parse(open(jp, "rb").read())
    for r in recs:
        if r["type"] == "COMPLETE" and r["symbol"] == SYMS[0]:
            r["bytes"] += 10 ** 9     # journal now lies about completed bytes
    with open(jp, "wb") as f:
        for i, r in enumerate(recs):
            body = {k: v for k, v in r.items() if k != "seq"}
            f.write(ex._frame_bytes(body, i))
    clock2, lim2 = fresh()
    tr2 = Transport(clock2)
    res2 = run(base, tr2, clock2, lim2)
    c.check(res2["status"] == "COMPLETE" and tr2.calls == [], "restart completes, zero calls")
    c.check(res2["payload_bytes"] == actual,
            f"payload bytes recomputed from files ({res2['payload_bytes']} == {actual}), journal bytes field not trusted")
    return c.done()


def r2_07(d):
    c = Case("R2-07", "real-process component swap/symlink race cannot escape trusted dirfds; named HOLD")
    base = os.path.join(d, "r207")
    target = os.path.join(d, "r207evil")
    os.makedirs(target)
    marker = os.path.join(d, "r207marker")
    proc = subprocess.Popen([sys.executable, WORKER, "swap", base, CID,
                             CANDIDATE, marker, target],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc.wait(timeout=60)
    out = json.load(open(os.path.join(marker, "result.json")))
    c.check(out.get("hold") == "HOLD:PATH_RACE", f"run ends HOLD:PATH_RACE: {out}")
    c.check(out.get("calls") == 1, "exactly one call before the swap took effect")
    c.check(os.listdir(target) == [], "nothing written through the symlink (no escape)")
    c.check(os.path.islink(os.path.join(base, CID, "raw")), "swap really happened")
    moved = os.path.join(base, CID, "raw_moved", SYMS[0] + ".csv")
    c.check(os.path.isfile(moved), "payload write landed in the pinned dirfd inode")
    recs = read_records(base)
    c.check([r["type"] for r in recs] == ["ATTEMPT"],
            "journal holds ATTEMPT only; no COMPLETE blessed the raced write")
    return c.done()


def r2_08(d):
    c = Case("R2-08", "retained r1 happy-path smoke: 52 calls/156 payloads, deterministic twin, publisher compatibility")
    base = os.path.join(d, "r208")
    clock, lim = fresh()
    tr = Transport(clock)
    res = run(base, tr, clock, lim)
    c.check(res["status"] == "COMPLETE" and tr.calls == SYMS, "52 calls in frozen order")
    tm = tree_map(os.path.join(base, CID))
    c.check(len(tm) == 156, "exactly 156 payloads")
    base2 = os.path.join(d, "r208twin")
    clock2, lim2 = fresh()
    tr2 = Transport(clock2)
    run(base2, tr2, clock2, lim2)
    c.check(tree_map(os.path.join(base2, CID)) == tm, "twin tree byte-identical")
    c.check(open(journal_path(base), "rb").read() == open(journal_path(base2), "rb").read(),
            "twin journal byte-identical")
    # accepted-publisher compatibility (fixture-side pins only) — r1 FakeRemote
    c.check(hashlib.sha256(open(PUB_PATH, "rb").read()).hexdigest() == PUB_SHA256,
            "publisher file pin")
    pub = _load("qfar1_publisher_h16", PUB_PATH)
    root = os.path.join(base, CID)
    pins = {}
    for dp, dns, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            pins[os.path.relpath(p, root)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
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

    info = pub.build_container(root, CID, os.path.join(d, "staging8"), FROZEN, pins)
    c.check(len(info["pins"]) == 158, f"sealed members {len(info['pins'])}")
    os.close(info["fd"])
    remote = FakeRemote(os.path.join(d, "remote8"))
    pub_journal = os.path.join(base, CID + ".control", "qfj2_publication_journal.qfj2")
    res3 = pub.publish(root, CID, remote, pub_journal,
                       os.path.join(d, "staging8b"), FROZEN, pins)
    c.check(res3.get("status") == "PUBLISHED", f"publish status {res3.get('status')}")
    c.check(os.path.isfile(pub_journal), "publication journal in control dir")
    try:
        socket.socket()
        denied = False
    except RuntimeError:
        denied = True
    c.check(denied, "socket constructor denied in fixture process")
    return c.done()


def main():
    out_path = sys.argv[1]
    d = tempfile.mkdtemp(prefix="qf19r2_")
    results = {"suite": "QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-HARDENING-20261016-19 r2",
               "executor": "clean_capture_executor_h19r2.py", "cases": []}
    for fn in (r2_01, r2_02, r2_03, r2_04, r2_05, r2_06, r2_07, r2_08):
        results["cases"].append(fn(d))
    results["total_checks"] = sum(x["checks"] for x in results["cases"])
    results["total_failures"] = sum(len(x["failures"]) for x in results["cases"])
    results["verdict"] = "PASS" if results["total_failures"] == 0 else "FAIL"
    results["peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1, sort_keys=True)
        f.write("\n")
    print(results["verdict"], results["total_checks"], "checks,",
          results["total_failures"], "failures, peak RSS", results["peak_rss_mb"], "MB")
    for x in results["cases"]:
        print(" ", x["id"], x["verdict"], x["checks"], "checks", x["failures"] or "")


if __name__ == "__main__":
    main()
