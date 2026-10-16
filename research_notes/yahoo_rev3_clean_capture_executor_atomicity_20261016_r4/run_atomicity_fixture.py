"""Focused real-process/no-socket fixture for
QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-ATOMICITY-20261016-19 r4 (spec:
Issue #1 comment 6217441495, item 4).

Cases R4-01..R4-07. r1/r2/r3 evidence is reused, not rerun; the only
full-path run is the in-process virtual-clock retained smoke R4-07.
Every attempt writes its OWN results file (argv[1]); failed or crashed
attempts are never overwritten — a crash still writes a results JSON
carrying the traceback. Sockets are denied before the executor import.
"""
import errno
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
import traceback
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
EXEC_PATH = os.path.join(HERE, "clean_capture_executor_h19r4.py")
WORKER = os.path.join(HERE, "proc_worker4.py")
CANDIDATE = os.path.join(
    REPO, "research_notes/yahoo_rev3_pin_separation_20261016_r3/"
          "capture_manifest_rev3_pin_separated_candidate.json")
CID = "TEST-CAPTURE-01"
JOURNAL = "acquisition_attempt_journal.qfj2"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "fixture_results_run1.json")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ex = _load("clean_capture_executor_h19r4", EXEC_PATH)
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
        return datetime.fromtimestamp(self.t, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")


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
    def __init__(self):
        self.calls = []
        self.fail_status = None

    def __call__(self, req):
        self.calls.append(req["symbol"])
        if self.fail_status is not None:
            raise TransportFailure(self.fail_status, "injected transport failure")
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


def wait_for(path, timeout=30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path):
            return True
        time.sleep(0.05)
    return False


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


def spawn(mode, base, marker):
    return subprocess.Popen(
        [sys.executable, WORKER, mode, base, CID, CANDIDATE, marker],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def worker_result(marker):
    with open(os.path.join(marker, "result.json")) as f:
        return json.load(f)


# ------------------------------------------------------------------ cases
def r4_01():
    """Empty journal-path replacement while the owner holds the fences:
    contender makes zero calls (control-dir fence); the owner detects the
    split before its next call and durably records it on the pinned fd."""
    c = Case("R4-01", "empty journal replacement: fence + owner drift detection")
    base = tempfile.mkdtemp(prefix="qf19r4_01_")
    m_owner = os.path.join(base, "_m_owner")
    m_cont = os.path.join(base, "_m_cont")
    jp = journal_path(base)
    owner = spawn("hold", base, m_owner)
    c.check(wait_for(os.path.join(m_owner, "started")), "owner started")
    orig = jp + ".orig"
    os.rename(jp, orig)
    with open(jp, "wb"):
        pass  # the empty replacement
    cont = spawn("plain", base, m_cont)
    cont.wait(timeout=60)
    cres = worker_result(m_cont)
    c.check(cres.get("hold") == "HOLD:OWNER_BUSY",
            f"contender OWNER_BUSY (got {cres})")
    c.check(cres.get("calls") == 0, "contender zero transport calls")
    with open(os.path.join(m_owner, "release"), "w") as f:
        f.write("x")
    owner.wait(timeout=60)
    ores = worker_result(m_owner)
    c.check(ores.get("code") == "HOLD:JOURNAL_SPLIT",
            f"owner detects split (got {ores})")
    c.check(ores.get("calls") == 1, "owner made no call after the split")
    c.check(os.path.getsize(jp) == 0, "empty replacement never written")
    recs = read_records_at(orig)
    c.check([r["type"] for r in recs] == ["ATTEMPT", "HOLD"]
            and recs[1]["code"] == "HOLD:JOURNAL_SPLIT"
            and recs[1]["attempt_consumed"] is True,
            "durable HOLD landed on the pinned journal inode")
    return c.done()


def _swapjournal_case(kind):
    c = Case(f"R4-02-{kind}" if kind == "copy" else f"R4-03-{kind}",
             f"journal pathname replaced with {kind} mid-run")
    base = tempfile.mkdtemp(prefix=f"qf19r4_{kind}_")
    marker = os.path.join(base, "_m")
    w = spawn(f"swapjournal-{kind}", base, marker)
    w.wait(timeout=60)
    res = worker_result(marker)
    c.check(res.get("code") == "HOLD:JOURNAL_SPLIT",
            f"owner fails closed JOURNAL_SPLIT (got {res})")
    c.check(res.get("calls") == 1, "zero calls after the swap")
    jp = journal_path(base)
    recs = read_records_at(jp + ".orig")
    c.check([r["type"] for r in recs] == ["ATTEMPT", "HOLD"]
            and recs[1]["code"] == "HOLD:JOURNAL_SPLIT",
            "durable HOLD on the original journal inode")
    if kind == "copy":
        crecs = read_records_at(jp)
        c.check([r["type"] for r in crecs] == ["ATTEMPT"],
                "copied-records file received no owner appends")
    else:
        c.check(os.path.islink(jp), "journal pathname is still the symlink")
        target = os.path.join(marker, "journal_copy.qfj2")
        trecs = read_records_at(target)
        c.check([r["type"] for r in trecs] == ["ATTEMPT"],
                "symlink target received no owner appends")
    return c.done()


def _temp_substitution_case(kind):
    c = Case("R4-04" if kind == "file" else "R4-05",
             f"temp substituted with {kind} in the finalize window")
    base = tempfile.mkdtemp(prefix=f"qf19r4_temp_{kind}_")
    clock, limiter = fresh()
    transport = Transport()
    foreign = os.path.join(base, "foreign_target.bin")
    with open(foreign, "wb") as f:
        f.write(b"FOREIGN-TARGET-BYTES")
    state = {"done": False}
    real_link = os.link

    def link_wrapper(src, dst, src_dir_fd=None, dst_dir_fd=None,
                     follow_symlinks=True):
        if not state["done"]:
            state["done"] = True
            dirpath = os.readlink(f"/proc/self/fd/{src_dir_fd}")
            tmppath = os.path.join(dirpath, src)
            os.unlink(tmppath)
            if kind == "file":
                with open(tmppath, "wb") as f:
                    f.write(b"FOREIGN-TEMP-BYTES")
            else:
                os.symlink(foreign, tmppath)
        return real_link(src, dst, src_dir_fd=src_dir_fd,
                         dst_dir_fd=dst_dir_fd,
                         follow_symlinks=follow_symlinks)

    os.link = link_wrapper
    try:
        res = run(base, transport, clock, limiter)
    finally:
        os.link = real_link
    c.check(res["code"] == "HOLD:FINAL_COLLISION",
            f"substitution yields FINAL_COLLISION (got {res['code']})")
    c.check(len(transport.calls) == 1, "exactly one transport call")
    rawdir = os.path.join(base, CID, "raw")
    tmpname = "." + SYMS[0] + ".csv.tmp"
    tmppath = os.path.join(rawdir, tmpname)
    c.check(not os.path.exists(os.path.join(rawdir, SYMS[0] + ".csv")),
            "foreign bytes were not published at the final path")
    if kind == "file":
        c.check(open(tmppath, "rb").read() == b"FOREIGN-TEMP-BYTES",
                "foreign temp file retained byte-identical")
    else:
        c.check(os.path.islink(tmppath), "foreign symlink retained")
        c.check(open(foreign, "rb").read() == b"FOREIGN-TARGET-BYTES",
                "symlink target retained byte-identical")
    recs = read_records_at(journal_path(base))
    c.check([r["type"] for r in recs] == ["ATTEMPT", "HOLD"]
            and recs[1]["code"] == "HOLD:FINAL_COLLISION",
            "durable HOLD recorded for the substitution")
    clock2, limiter2 = fresh()
    t2 = Transport()
    c.check(expect_hold(lambda: run(base, t2, clock2, limiter2),
                        "HOLD:FINAL_COLLISION")
            and len(t2.calls) == 0, "restart reproduces HOLD, zero calls")
    return c.done()


def _injected_case(cid_, title, setup):
    c = Case(cid_, title)
    base = tempfile.mkdtemp(prefix=f"qf19r4_inj_{cid_}_")
    clock, limiter = fresh()
    transport = Transport()
    restore = setup(transport)
    try:
        res = run(base, transport, clock, limiter)
    finally:
        if restore:
            restore()
    return c, base, res, transport


def r4_06():
    out = []

    def fd_is_tmp(fd):
        try:
            return os.readlink(f"/proc/self/fd/{fd}").endswith(".tmp")
        except OSError:
            return False

    # (a) payload write OSError -> durable HOLD:FILESYSTEM
    def setup_write(transport):
        real_write = os.write

        def w(fd, data):
            if fd_is_tmp(fd):
                raise OSError(errno.EIO, "injected write failure")
            return real_write(fd, data)
        os.write = w
        return lambda: setattr(os, "write", real_write)

    c, base, res, transport = _injected_case("R4-06a", "write OSError", setup_write)
    c.check(res["code"] == "HOLD:FILESYSTEM", f"code (got {res['code']})")
    recs = read_records_at(journal_path(base))
    c.check([r["type"] for r in recs] == ["ATTEMPT", "HOLD"]
            and recs[1]["code"] == "HOLD:FILESYSTEM"
            and recs[1]["attempt_consumed"] is True,
            "one exact durable terminal HOLD")
    clock2, limiter2 = fresh()
    t2 = Transport()
    c.check(expect_hold(lambda: run(base, t2, clock2, limiter2),
                        "HOLD:FILESYSTEM") and len(t2.calls) == 0,
            "restart reproduces FILESYSTEM, zero calls")
    out.append(c.done())

    # (b) payload fsync OSError -> durable HOLD:FILESYSTEM
    def setup_fsync(transport):
        real_fsync = os.fsync

        def fs(fd):
            if fd_is_tmp(fd):
                raise OSError(errno.EIO, "injected fsync failure")
            return real_fsync(fd)
        os.fsync = fs
        return lambda: setattr(os, "fsync", real_fsync)

    c, base, res, transport = _injected_case("R4-06b", "fsync OSError", setup_fsync)
    c.check(res["code"] == "HOLD:FILESYSTEM", f"code (got {res['code']})")
    recs = read_records_at(journal_path(base))
    c.check([r["type"] for r in recs] == ["ATTEMPT", "HOLD"]
            and recs[1]["code"] == "HOLD:FILESYSTEM",
            "one exact durable terminal HOLD")
    out.append(c.done())

    # (c) link OSError -> durable HOLD:FILESYSTEM
    def setup_link(transport):
        real_link = os.link

        def lk(*a, **k):
            raise OSError(errno.EIO, "injected link failure")
        os.link = lk
        return lambda: setattr(os, "link", real_link)

    c, base, res, transport = _injected_case("R4-06c", "link OSError", setup_link)
    c.check(res["code"] == "HOLD:FILESYSTEM", f"code (got {res['code']})")
    recs = read_records_at(journal_path(base))
    c.check([r["type"] for r in recs] == ["ATTEMPT", "HOLD"]
            and recs[1]["code"] == "HOLD:FILESYSTEM",
            "one exact durable terminal HOLD")
    out.append(c.done())

    # (d) unlink OSError -> durable HOLD:FILESYSTEM (final published first)
    def setup_unlink(transport):
        real_unlink = os.unlink

        def ul(*a, **k):
            raise OSError(errno.EIO, "injected unlink failure")
        os.unlink = ul
        return lambda: setattr(os, "unlink", real_unlink)

    c, base, res, transport = _injected_case("R4-06d", "unlink OSError", setup_unlink)
    c.check(res["code"] == "HOLD:FILESYSTEM", f"code (got {res['code']})")
    recs = read_records_at(journal_path(base))
    c.check([r["type"] for r in recs] == ["ATTEMPT", "HOLD"]
            and recs[1]["code"] == "HOLD:FILESYSTEM",
            "one exact durable terminal HOLD")
    out.append(c.done())

    # (e) ATTEMPT append failure -> JOURNAL_DURABILITY, zero calls
    def setup_attempt_append(transport):
        real_append = ex.JournalSession.append

        def ap(self, record):
            if record.get("type") == "ATTEMPT":
                raise OSError(errno.EIO, "injected ATTEMPT append failure")
            return real_append(self, record)
        ex.JournalSession.append = ap
        return lambda: setattr(ex.JournalSession, "append", real_append)

    c, base, res, transport = _injected_case(
        "R4-06e", "ATTEMPT append failure", setup_attempt_append)
    c.check(res["code"] == "HOLD:JOURNAL_DURABILITY",
            f"code (got {res['code']})")
    c.check(len(transport.calls) == 0, "no transport call after failed ATTEMPT")
    c.check(read_records_at(journal_path(base)) == [],
            "journal carries no records")
    c.check("no cause recorded" in (res.get("detail") or ""),
            "no persistence falsely claimed")
    out.append(c.done())

    # (f) COMPLETE append failure -> JOURNAL_DURABILITY, nothing claimed
    def setup_complete_append(transport):
        real_append = ex.JournalSession.append

        def ap(self, record):
            if record.get("type") == "COMPLETE":
                raise OSError(errno.EIO, "injected COMPLETE append failure")
            return real_append(self, record)
        ex.JournalSession.append = ap
        return lambda: setattr(ex.JournalSession, "append", real_append)

    c, base, res, transport = _injected_case(
        "R4-06f", "COMPLETE append failure", setup_complete_append)
    c.check(res["code"] == "HOLD:JOURNAL_DURABILITY",
            f"code (got {res['code']})")
    c.check(len(transport.calls) == 1, "exactly one transport call")
    recs = read_records_at(journal_path(base))
    c.check([r["type"] for r in recs] == ["ATTEMPT"],
            "journal holds only the ATTEMPT; HOLD was not fabricated")
    c.check(os.path.exists(os.path.join(base, CID, "raw", SYMS[0] + ".csv")),
            "payload files exist (publication is a separate stage)")
    out.append(c.done())

    # (g) HOLD append failure behind a transport failure -> durability
    # outcome, exactly one HOLD append attempt, no retry, no false claim
    def setup_hold_append(transport):
        real_append = ex.JournalSession.append
        state = {"hold_appends": 0}
        transport.fail_status = 500

        def ap(self, record):
            if record.get("type") == "HOLD":
                state["hold_appends"] += 1
                raise OSError(errno.EIO, "injected HOLD append failure")
            return real_append(self, record)
        ex.JournalSession.append = ap
        transport.hold_appends = state
        return lambda: setattr(ex.JournalSession, "append", real_append)

    c, base, res, transport = _injected_case(
        "R4-06g", "HOLD append failure (durability)", setup_hold_append)
    c.check(res["code"] == "HOLD:JOURNAL_DURABILITY",
            f"code (got {res['code']})")
    c.check(transport.hold_appends["hold_appends"] == 1,
            "exactly one HOLD append attempt")
    c.check(len(transport.calls) == 1, "no retry after durability failure")
    recs = read_records_at(journal_path(base))
    c.check([r["type"] for r in recs] == ["ATTEMPT"],
            "no HOLD record fabricated in the journal")
    c.check("NOT recorded" in (res.get("detail") or ""),
            "original cause explicitly NOT claimed recorded")
    out.append(c.done())
    return out


def r4_07():
    c = Case("R4-07", "retained smoke: full run + control contents + restart")
    base = tempfile.mkdtemp(prefix="qf19r4_07_")
    clock, limiter = fresh()
    transport = Transport()
    res = run(base, transport, clock, limiter)
    c.check(res["status"] == "COMPLETE" and res["code"] == "OK",
            f"full run completes (got {res['status']}/{res['code']})")
    c.check(len(transport.calls) == 52, "52 transport calls")
    ctrl_entries = sorted(os.listdir(os.path.join(base, CID + ".control")))
    c.check(ctrl_entries == [JOURNAL],
            f"control dir holds only the acquisition journal (got {ctrl_entries})")
    lock_found = []
    npayload = 0
    for dp, dns, fns in os.walk(base):
        for fn in fns:
            if "lock" in fn:
                lock_found.append(fn)
            if not fn.startswith("."):
                npayload += 1
    c.check(not lock_found, "no lock artifact anywhere")
    c.check(npayload == 157, f"156 payloads + journal on disk (got {npayload})")
    clock2, limiter2 = fresh()
    t2 = Transport()
    res2 = run(base, t2, clock2, limiter2)
    c.check(res2["status"] == "COMPLETE" and len(t2.calls) == 0,
            "restart: all SKIP_VERIFIED, zero calls")
    c.check(all(v == "SKIP_VERIFIED" for v in res2["states"].values()),
            "every symbol SKIP_VERIFIED on restart")
    return c.done()


def main():
    started = time.time()
    cases = []
    crash = None
    try:
        cases.append(r4_01())
        cases.append(_swapjournal_case("copy"))
        cases.append(_swapjournal_case("link"))
        cases.append(_temp_substitution_case("file"))
        cases.append(_temp_substitution_case("symlink"))
        cases.extend(r4_06())
        cases.append(r4_07())
    except Exception:
        crash = traceback.format_exc()
    total = sum(x["checks"] for x in cases)
    failures = sum(len(x["failures"]) for x in cases)
    results = {
        "task": "QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-ATOMICITY-20261016-19 r4",
        "executor": "clean_capture_executor_h19r4.py",
        "executor_sha256": hashlib.sha256(open(EXEC_PATH, "rb").read()).hexdigest(),
        "candidate_sha256": hashlib.sha256(open(CANDIDATE, "rb").read()).hexdigest(),
        "cases": cases,
        "total_checks": total,
        "total_failures": failures + (1 if crash else 0),
        "crash": crash,
        "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
        "elapsed_s": round(time.time() - started, 2),
        "verdict": "PASS" if not failures and not crash else "FAIL",
    }
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, sort_keys=True)
        f.write("\n")
    print(results["verdict"], total, "checks,", results["total_failures"],
          "failures", "crash" if crash else "")
    return 0 if results["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
