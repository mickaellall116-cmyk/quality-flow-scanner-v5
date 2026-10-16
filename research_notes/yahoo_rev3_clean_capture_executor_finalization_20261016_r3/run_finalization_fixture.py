"""Focused real-process/no-socket fixture for
QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-FINALIZATION-20261016-19 r3.

Sockets are denied BEFORE the executor is imported. Cases R3-01..R3-07 map
to the focused case list in spec comment 6215975805; r1/r2 evidence is
reused, not rerun (the only full-path run is the in-process virtual-clock
retained smoke R3-07). Output: one deterministic results JSON.
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


def _denied(*a, **k):
    raise RuntimeError("socket access denied by fixture")


class _DeniedSocket:
    def __init__(self, *a, **k):
        _denied()


socket.socket = _DeniedSocket
socket.create_connection = _denied
socket.getaddrinfo = _denied

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EXEC_PATH = os.path.join(HERE, "clean_capture_executor_h19r3.py")
WORKER = os.path.join(HERE, "proc_worker3.py")
CANDIDATE = os.path.join(
    REPO, "research_notes/yahoo_rev3_pin_separation_20261016_r3/"
          "capture_manifest_rev3_pin_separated_candidate.json")
CID = "TEST-CAPTURE-01"
JOURNAL = "acquisition_attempt_journal.qfj2"
SHARED = {}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ex = _load("clean_capture_executor_h19r3", EXEC_PATH)
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


def gen_bars(sym, rows=120):
    seed = int(hashlib.sha256(sym.encode()).hexdigest()[:8], 16)
    base = 100.0 + (seed % 500) / 10.0
    t0 = datetime(2024, 10, 18, 13, 30, tzinfo=timezone.utc)
    out = []
    for i in range(rows):
        ts = (t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        o = base + (i % 7) * 0.25
        out.append({"Datetime": ts, "Open": o, "High": o + 0.5, "Low": o - 0.5,
                    "Close": o + 0.25, "Volume": 1000 + i,
                    "Dividends": 0, "Stock Splits": 0})
    return out


def good_resp(req, rows=120):
    sess = req["session"]
    meta = {"session": sess, "class": req["class"],
            "exchange": "XNYS" if sess == "XNYS" else "CCC",
            "timezone": "America/New_York" if sess == "XNYS" else "UTC",
            "currency": "USD", "source": "synthetic-fixture"}
    return {"status": 200, "symbol": req["symbol"], "meta": meta,
            "bars": gen_bars(req["symbol"], rows), "end_covered": True}


class Transport:
    def __init__(self, clock):
        self.clock = clock
        self.calls = []

    def __call__(self, req):
        self.calls.append(req["symbol"])
        return good_resp(req)


def fresh():
    clock = VClock()
    return clock, ex.Limiter(clock)


def run(base, transport, clock, limiter, cid=CID):
    return ex.run_capture(CANDIDATE, base, cid, transport, clock, limiter)


def journal_path(base, cid=CID):
    return os.path.join(base, cid + ".control", JOURNAL)


def read_records_at(path):
    return ex._journal_parse(open(path, "rb").read())


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


def capture_hold(fn):
    """Run fn; return (code, detail) of the HoldError it raises, else (None, '')."""
    try:
        fn()
    except HoldError as e:
        return e.code, e.detail
    return None, ""


def wait_for(path, timeout=30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path):
            return True
        time.sleep(0.05)
    return False


def spawn(mode, base, marker, evil=None):
    args = [sys.executable, WORKER, mode, base, CID, CANDIDATE, marker]
    if evil:
        args.append(evil)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
    proc.wait(timeout=180)
    return json.load(open(os.path.join(marker, "result.json")))


def reframe(records):
    out = b""
    for i, r in enumerate(records):
        body = {k: v for k, v in r.items() if k != "seq"}
        out += ex._frame_bytes(body, i)
    return out


def rewrite_in_place(path, data):
    with open(path, "r+b") as f:
        f.write(data)
        f.truncate(len(data))


# ------------------------------------------------------------------ cases
def r3_01(d):
    c = Case("R3-01", "coherent false COMPLETE bytes/hash, extra/missing keys, wrong journal identity fail closed, zero calls")
    base = os.path.join(d, "r301")
    clock, lim = fresh()
    tr = Transport(clock)
    res = run(base, tr, clock, lim)
    c.check(res["status"] == "COMPLETE", "seed capture completes")
    jp = journal_path(base)
    orig = open(jp, "rb").read()
    recs0 = read_records_at(jp)
    st = os.stat(jp)
    ident = f"{st.st_dev}:{st.st_ino}"

    def variant(name, mutate, want_code):
        recs = json.loads(json.dumps(recs0))
        mutate(recs)
        rewrite_in_place(jp, reframe(recs))
        clock2, lim2 = fresh()
        tr2 = Transport(clock2)
        code, _ = capture_hold(lambda: run(base, tr2, clock2, lim2))
        c.check(code == want_code, f"{name}: {code} != {want_code}")
        c.check(tr2.calls == [], f"{name}: zero calls")

    variant("false_bytes",
            lambda rs: rs[1].__setitem__("bytes", rs[1]["bytes"] + 10 ** 9),
            "HOLD:JOURNAL_CONFLICT")
    def bad_hash(rs):
        rel = PLAN[0]["rels"][0]
        h = rs[1]["files"][rel]
        rs[1]["files"][rel] = ("0" if h[0] != "0" else "1") + h[1:]
    variant("false_hash", bad_hash, "HOLD:JOURNAL_CONFLICT")
    variant("complete_extra_key",
            lambda rs: rs[1].__setitem__("zzz", 1), "HOLD:JOURNAL_CONFLICT")
    variant("attempt_missing_key",
            lambda rs: rs[0].pop("rels"), "HOLD:JOURNAL_CONFLICT")
    variant("wrong_journal_identity",
            lambda rs: [r.__setitem__("journal", "0:0") for r in rs],
            "HOLD:JOURNAL_SPLIT")
    # forged HOLD with an extra key appended (framing valid, schema not)
    forged = {"type": "HOLD", "capture_id": CID, "symbol": None,
              "code": "HOLD:TRANSPORT", "detail": "forged", "attempt_consumed": False,
              "clock": 9.0, "journal": ident, "extra": 1}
    rewrite_in_place(jp, orig + ex._frame_bytes(forged, len(recs0)))
    clock2, lim2 = fresh()
    tr2 = Transport(clock2)
    code, _ = capture_hold(lambda: run(base, tr2, clock2, lim2))
    c.check(code == "HOLD:JOURNAL_CONFLICT", f"hold_extra_key: {code}")
    c.check(tr2.calls == [], "hold_extra_key: zero calls")
    # restore: journal again verifies clean, restart completes, zero calls
    rewrite_in_place(jp, orig)
    clock3, lim3 = fresh()
    tr3 = Transport(clock3)
    res3 = run(base, tr3, clock3, lim3)
    actual = sum(os.path.getsize(os.path.join(dp, fn))
                 for dp, _, fns in os.walk(os.path.join(base, CID)) for fn in fns)
    c.check(res3["status"] == "COMPLETE" and tr3.calls == []
            and res3["payload_bytes"] == actual,
            "restored journal: restart verifies COMPLETE records equal files")
    return c.done()


def _worker_hold_case(d, mode, want_code, journal_kinds):
    base = os.path.join(d, "r3" + mode.replace("-", ""))
    marker = os.path.join(d, "m" + mode.replace("-", ""))
    out = spawn(mode, base, marker)
    return base, marker, out


def r3_02(d):
    c = Case("R3-02", "post-ATTEMPT temp/final collision + component race: one durable named HOLD; restart reproduces code/detail, zero calls")
    for mode, want in (("plant-temp", "HOLD:TEMP_COLLISION"),
                       ("plant-final", "HOLD:FINAL_COLLISION")):
        base, marker, out = _worker_hold_case(d, mode, want, None)
        c.check(out.get("status") == "INCOMPLETE_HOLD" and out.get("code") == want,
                f"{mode}: worker result {out.get('status')}/{out.get('code')} != {want}")
        c.check(out.get("calls") == 2, f"{mode}: exactly 2 calls (failure on 2nd symbol)")
        recs = read_records_at(journal_path(base))
        kinds = [r["type"] for r in recs]
        c.check(kinds == ["ATTEMPT", "COMPLETE", "ATTEMPT", "HOLD"],
                f"{mode}: journal shape {kinds}")
        hold = recs[-1]
        c.check(hold["code"] == want and hold["attempt_consumed"] is True
                and set(hold.keys()) == ex._HOLD_KEYS,
                f"{mode}: one durable terminal HOLD, exact keys")
        planted = open(os.path.join(marker, "planted")).read()
        sentinel = open(os.path.join(base, CID, "raw", planted), "rb").read()
        c.check(sentinel == b"SENTINEL-PLANTED", f"{mode}: planted artifact byte-identical")
        clock2, lim2 = fresh()
        tr2 = Transport(clock2)
        code, detail = capture_hold(lambda: run(base, tr2, clock2, lim2))
        c.check(code == want and hold["detail"] in detail,
                f"{mode}: restart reproduces code+detail")
        c.check(tr2.calls == [], f"{mode}: restart zero calls")
        if mode == "plant-temp":
            SHARED["durable_journal"] = journal_path(base)
    # component race post-ATTEMPT (root swapped to symlink during call 1)
    base = os.path.join(d, "r3swaproot")
    marker = os.path.join(d, "mswaproot")
    evil = os.path.join(d, "r3swaproot_evil")
    os.makedirs(evil)
    out = spawn("swaproot", base, marker, evil)
    c.check(out.get("status") == "INCOMPLETE_HOLD" and out.get("code") == "HOLD:PATH_RACE",
            f"swaproot: {out.get('status')}/{out.get('code')}")
    c.check(os.listdir(evil) == [], "swaproot: nothing written through the symlink")
    recs = read_records_at(journal_path(base))
    c.check([r["type"] for r in recs] == ["ATTEMPT", "HOLD"]
            and recs[-1]["code"] == "HOLD:PATH_RACE",
            "swaproot: durable PATH_RACE HOLD after ATTEMPT (no generic AMBIGUOUS)")
    clock2, lim2 = fresh()
    tr2 = Transport(clock2)
    code, detail = capture_hold(lambda: run(base, tr2, clock2, lim2))
    c.check(code == "HOLD:PATH_RACE" and recs[-1]["detail"] in detail,
            "swaproot: restart reproduces PATH_RACE code+detail")
    c.check(tr2.calls == [], "swaproot: restart zero calls")
    return c.done()


def r3_03(d):
    c = Case("R3-03", "destination created after temp fsync, before finalization: never overwritten (HOLD:FINAL_COLLISION)")
    base = os.path.join(d, "r303")
    marker = os.path.join(d, "m303")
    out = spawn("plant-race", base, marker)
    c.check(wait_for(os.path.join(marker, "raced"), 5), "watcher raced the destination in")
    c.check(out.get("status") == "INCOMPLETE_HOLD" and out.get("code") == "HOLD:FINAL_COLLISION",
            f"result {out.get('status')}/{out.get('code')}")
    dst = os.path.join(base, CID, "raw", SYMS[1] + ".csv")
    c.check(open(dst, "rb").read() == b"SENTINEL-RACED-DEST",
            "raced destination retained byte-identical (never overwritten)")
    tmp = os.path.join(base, CID, "raw", "." + SYMS[1] + ".csv.tmp")
    c.check(os.path.exists(tmp), "executor temp not deleted over the race")
    recs = read_records_at(journal_path(base))
    holds = [r for r in recs if r["type"] == "HOLD"]
    c.check(len(holds) == 1 and holds[0]["code"] == "HOLD:FINAL_COLLISION"
            and recs[-1]["type"] == "HOLD", "one durable terminal FINAL_COLLISION HOLD")
    clock2, lim2 = fresh()
    tr2 = Transport(clock2)
    code, _ = capture_hold(lambda: run(base, tr2, clock2, lim2))
    c.check(code == "HOLD:FINAL_COLLISION" and tr2.calls == [],
            "restart reproduces FINAL_COLLISION, zero calls")
    return c.done()


def r3_04(d):
    c = Case("R3-04", "journal-fd lock contention; journal-path symlink/replacement cannot yield two owners or split records")
    # (a) live owner + contender
    base = os.path.join(d, "r304")
    marker = os.path.join(d, "m304")
    os.makedirs(marker)
    proc = subprocess.Popen([sys.executable, WORKER, "hold", base, CID,
                             CANDIDATE, marker],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        c.check(wait_for(os.path.join(marker, "started")), "owner reached first call")
        snap = open(journal_path(base), "rb").read()
        clock, lim = fresh()
        tr = Transport(clock)
        c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:OWNER_BUSY"),
                "contender HOLD:OWNER_BUSY (flock on the journal fd)")
        c.check(tr.calls == [], "contender zero calls")
        c.check(open(journal_path(base), "rb").read() == snap,
                "contender made zero journal mutation")
        with open(os.path.join(marker, "release"), "w") as f:
            f.write("x")
        proc.wait(timeout=180)
    finally:
        if proc.poll() is None:
            proc.kill()
    out = json.load(open(os.path.join(marker, "result.json")))
    c.check(out.get("status") == "COMPLETE" and out.get("calls") == 52,
            f"owner completed 52 calls: {out.get('status')}/{out.get('calls')}")
    SHARED["completed_base"] = base
    # (b) journal path replaced by a symlink
    base2 = os.path.join(d, "r304sym")
    marker2 = os.path.join(d, "m304sym")
    os.makedirs(marker2)
    proc2 = subprocess.Popen([sys.executable, WORKER, "crash", base2, CID,
                              CANDIDATE, marker2],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc2.wait(timeout=60)
    c.check(proc2.returncode == 3, "crash owner died after fsynced ATTEMPT")
    jp2 = journal_path(base2)
    saved = open(jp2, "rb").read()
    os.unlink(jp2)
    os.symlink(os.path.join(base2, "elsewhere.qfj2"), jp2)
    clock, lim = fresh()
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base2, tr, clock, lim), "HOLD:PATH_TYPE"),
            "symlinked journal: HOLD:PATH_TYPE, no owner")
    c.check(tr.calls == [], "symlinked journal: zero calls")
    # (c) journal path replaced by a NEW file carrying copied records (new inode)
    os.unlink(jp2)
    with open(jp2, "wb") as f:
        f.write(saved)
    clock, lim = fresh()
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base2, tr, clock, lim), "HOLD:JOURNAL_SPLIT"),
            "replaced journal file: HOLD:JOURNAL_SPLIT (identity binding)")
    c.check(tr.calls == [], "replaced journal: zero calls")
    return c.done()


def r3_05(d):
    c = Case("R3-05", "base trust boundary: base/control/root symlink or swap fails before transport or stays confined to pinned dirfds")
    # (a) base itself reached through a symlink
    real = os.path.join(d, "r305real")
    os.makedirs(real)
    linkbase = os.path.join(d, "r305link")
    os.symlink(real, linkbase)
    clock, lim = fresh()
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(linkbase, tr, clock, lim), "HOLD:PATH_TYPE"),
            "base symlink component: HOLD:PATH_TYPE")
    c.check(tr.calls == [], "base symlink: zero calls")
    # (b) control component pre-created as a symlink
    base = os.path.join(d, "r305ctl")
    evil = os.path.join(d, "r305evil")
    os.makedirs(evil)
    os.makedirs(base)
    os.symlink(evil, os.path.join(base, CID + ".control"))
    clock, lim = fresh()
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:PATH_TYPE"),
            "control symlink: HOLD:PATH_TYPE before transport")
    c.check(tr.calls == [] and os.listdir(evil) == [], "control symlink: zero calls, evil untouched")
    # (c) control swapped to a symlink mid-run: appends stay on the pinned fd
    base = os.path.join(d, "r305swap")
    marker = os.path.join(d, "m305swap")
    evil2 = os.path.join(d, "r305evil2")
    os.makedirs(evil2)
    out = spawn("swapctrl", base, marker, evil2)
    c.check(out.get("status") == "INCOMPLETE_HOLD" and out.get("code") == "HOLD:PATH_RACE"
            and out.get("calls") == 1,
            f"swapctrl: confined fail-closed HOLD:PATH_RACE after 1 call: "
            f"{out.get('status')}/{out.get('code')}/{out.get('calls')}")
    c.check(os.listdir(evil2) == [], "swapctrl: nothing written through the control symlink")
    moved_jp = os.path.join(base, CID + ".control_moved", JOURNAL)
    recs = read_records_at(moved_jp)
    c.check([r["type"] for r in recs] == ["ATTEMPT", "HOLD"]
            and recs[-1]["code"] == "HOLD:PATH_RACE",
            "swapctrl: records stayed on the original journal inode (ATTEMPT + durable HOLD)")
    clock, lim = fresh()
    tr = Transport(clock)
    c.check(expect_hold(lambda: run(base, tr, clock, lim), "HOLD:PATH_TYPE"),
            "post-swap contender via symlinked control path: HOLD:PATH_TYPE")
    c.check(tr.calls == [], "post-swap contender: zero calls")
    return c.done()


def r3_06(d):
    c = Case("R3-06", "control dir holds exactly the acquisition journal (no lock file); journal parseable with one exact terminal HOLD")
    base = SHARED.get("completed_base")
    listing = sorted(os.listdir(os.path.join(base, CID + ".control")))
    c.check(listing == [JOURNAL], f"control listing exactly [journal]: {listing}")
    lock_found = []
    for dp, dns, fns in os.walk(os.path.join(d, "")):
        for fn in fns:
            if fn == "capture_owner.lock":
                lock_found.append(os.path.join(dp, fn))
    c.check(lock_found == [], "no capture_owner.lock anywhere in the fixture tree")
    recs = read_records_at(SHARED["durable_journal"])
    holds = [r for r in recs if r["type"] == "HOLD"]
    c.check(len(holds) == 1 and recs[-1]["type"] == "HOLD"
            and set(holds[0].keys()) == ex._HOLD_KEYS,
            "durable journal parseable, exactly one terminal HOLD, exact keys")
    return c.done()


def r3_07(d):
    c = Case("R3-07", "retained smoke: full capture + deterministic twin (journal modulo its identity binding), restart verifies")
    base = os.path.join(d, "r307")
    clock, lim = fresh()
    tr = Transport(clock)
    res = run(base, tr, clock, lim)
    c.check(res["status"] == "COMPLETE" and tr.calls == SYMS, "52 calls in frozen order")
    c.check(len(tree_map(os.path.join(base, CID))) == 156, "exactly 156 payloads")
    base2 = os.path.join(d, "r307twin")
    clock2, lim2 = fresh()
    tr2 = Transport(clock2)
    run(base2, tr2, clock2, lim2)
    c.check(tree_map(os.path.join(base2, CID)) == tree_map(os.path.join(base, CID)),
            "twin tree byte-identical")

    def normalized(bp):
        rs = read_records_at(journal_path(bp))
        return json.dumps([{**r, "journal": "JID"} for r in rs], sort_keys=True)

    c.check(normalized(base) == normalized(base2),
            "twin journals identical modulo the journal-identity binding")
    recs = read_records_at(journal_path(base))
    keysets = {"ATTEMPT": ex._ATTEMPT_KEYS, "COMPLETE": ex._COMPLETE_KEYS,
               "HOLD": ex._HOLD_KEYS}
    c.check(len(recs) == 104 and all(set(r.keys()) == keysets[r["type"]] for r in recs),
            "104 records, all exact-key strict")
    clock3, lim3 = fresh()
    tr3 = Transport(clock3)
    res3 = run(base, tr3, clock3, lim3)
    actual = sum(os.path.getsize(os.path.join(dp, fn))
                 for dp, _, fns in os.walk(os.path.join(base, CID)) for fn in fns)
    c.check(res3["status"] == "COMPLETE" and tr3.calls == []
            and res3["payload_bytes"] == actual,
            "restart: all SKIP_VERIFIED, payload bytes recomputed == files")
    return c.done()


def main():
    out_path = sys.argv[1]
    d = tempfile.mkdtemp(prefix="qf19r3_")
    results = {"suite": "QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-FINALIZATION-20261016-19 r3",
               "executor": "clean_capture_executor_h19r3.py", "cases": []}
    for fn in (r3_01, r3_02, r3_03, r3_04, r3_05, r3_06, r3_07):
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
