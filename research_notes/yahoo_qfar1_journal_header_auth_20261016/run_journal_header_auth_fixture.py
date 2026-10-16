"""Journal-only fixture for QF-YAHOO-QFAR1-JOURNAL-HEADER-AUTH-20261016-16 r1.

Exercises ONLY the -16 candidate's journal layer (spec req 5): the
in-bound coherent length forgery, every fixed-header field/digest bit
class, exhaustive cut->append->reopen, and one real-process torn
append/restart. Staging, fencing, crash-reconciliation, validation-pin
and ceiling evidence is reused from pins 1778dba / cf929e0, not rerun.
Output: a deterministic results JSON (no times, no volatile paths).
"""
import hashlib
import importlib.util
import json
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CAND_PATH = os.path.join(HERE, "qfar1_publisher_h16.py")
WORKER = os.path.join(HERE, "crash_worker_h16.py")

spec = importlib.util.spec_from_file_location("cand", CAND_PATH)
cand = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cand)
HoldError = cand.HoldError
H = cand.FRAME_HEADER_BYTES       # 53
CB = cand.FRAME_HEADER_CORE_BYTES  # 21
TAG = cand.FRAME_TAG_BYTES        # 32
MAXP = cand.MAX_FRAME_PAYLOAD


def frames_for(records):
    out = []
    for i, r in enumerate(records):
        rec = dict(r)
        rec["seq"] = i
        out.append(cand._frame_bytes(rec))
    return out


def with_seq(records):
    return [dict(r, seq=i) for i, r in enumerate(records)]


def expect_corrupt(fn):
    try:
        fn()
    except HoldError as e:
        return str(e).startswith("HOLD:JOURNAL_CORRUPT")
    except Exception:
        return False
    return False


class Case:
    def __init__(self, cid, title):
        self.id, self.title = cid, title
        self.checks = 0
        self.failures = []

    def check(self, ok, label):
        self.checks += 1
        if not ok:
            self.failures.append(label)

    def done(self):
        return {"id": self.id, "title": self.title, "checks": self.checks,
                "failures": self.failures,
                "verdict": "PASS" if not self.failures else "FAIL"}


def j01(d):
    c = Case("J-01", "roundtrip append/read, exact verified end")
    p = os.path.join(d, "j01.bin")
    recs = [{"kind": "intent", "id": "A"}, {"kind": "note", "pad": "z" * 40},
            {"kind": "published", "id": "A"}]
    for r in recs:
        cand._journal_append(p, r)
    c.check(cand._journal_read(p) == with_seq(recs), "readback equals records")
    size = os.path.getsize(p)
    c.check(size == sum(len(f) for f in frames_for(recs)), "size == sum(frames)")
    cand._journal_append(p, {"kind": "extra"})
    c.check(cand._journal_read(p)[-1] == {"kind": "extra", "seq": 3},
            "fourth append seq 3")
    return c.done()


def j02(d):
    c = Case("J-02", "exhaustive cut->append->reopen at every byte offset")
    recs = [{"kind": "a", "pad": "x" * 10}, {"kind": "b", "pad": "y" * 57},
            {"kind": "c"}]
    frames = frames_for(recs)
    data = b"".join(frames)
    ends = []
    acc = 0
    for f in frames:
        acc += len(f)
        ends.append(acc)
    post = {"kind": "post"}
    for cut in range(len(data) + 1):
        p = os.path.join(d, "cut.bin")
        with open(p, "wb") as fh:
            fh.write(data[:cut])
        k = sum(1 for e in ends if e <= cut)          # complete frames in prefix
        prefix_end = ends[k - 1] if k else 0
        new_rec = dict(post, seq=k)
        cand._journal_append(p, new_rec)
        got = cand._journal_read(p)
        want = with_seq(recs)[:k] + [new_rec]
        ok = got == want
        blob = open(p, "rb").read()
        ok = ok and blob == data[:prefix_end] + cand._frame_bytes(new_rec)
        c.check(ok, f"cut={cut}")
        os.unlink(p)
    c.checks = len(data) + 1
    return c.done()


def _set_len(frame, n):
    b = bytearray(frame)
    b[13:17] = struct.pack(">I", n)
    b[17:21] = struct.pack(">I", (~n) & 0xFFFFFFFF)
    return bytes(b)


def j03(d):
    c = Case("J-03", "coherent IN-BOUND length+complement forgery -> CORRUPT, no truncate")
    recs = [{"kind": "a", "pad": "x" * 10}, {"kind": "b", "pad": "y" * 57},
            {"kind": "c"}]
    frames = frames_for(recs)
    n0 = len(json.dumps(with_seq(recs)[0], sort_keys=True).encode())
    n1 = len(json.dumps(with_seq(recs)[1], sort_keys=True).encode())
    variants = []
    f = list(frames); f[0] = _set_len(f[0], 500_000); variants.append(("frame0 n=500000", b"".join(f)))
    f = list(frames); f[0] = _set_len(f[0], n0 + 16); variants.append(("frame0 n+=16", b"".join(f)))
    f = list(frames); f[1] = _set_len(f[1], 500_000); variants.append(("frame1 n=500000", b"".join(f)))
    f = list(frames); f[0] = _set_len(f[0], MAXP); variants.append(("frame0 n=MAX", b"".join(f)))
    f = list(frames); f[0] = _set_len(f[0], MAXP + 1); variants.append(("frame0 n=MAX+1", b"".join(f)))
    for label, blob in variants:
        p = os.path.join(d, "forge.bin")
        with open(p, "wb") as fh:
            fh.write(blob)
        before = hashlib.sha256(blob).hexdigest()
        c.check(expect_corrupt(lambda: cand._journal_read(p)), label + " read")
        c.check(expect_corrupt(lambda: cand._journal_append(p, {"kind": "x"})),
                label + " append refuses")
        after = hashlib.sha256(open(p, "rb").read()).hexdigest()
        c.check(after == before, label + " file untouched (never truncated)")
        os.unlink(p)
    return c.done()


def j04(d):
    c = Case("J-04", "bit flip in every fixed-header field/digest class -> CORRUPT")
    recs = [{"kind": "a", "pad": "x" * 10}, {"kind": "b", "pad": "y" * 57},
            {"kind": "c"}]
    frames = frames_for(recs)
    regions = [("magic", 0), ("version", 4), ("seq", 12), ("length", 16),
               ("complement", 20), ("header_digest", 21 + 31),
               ("payload", H), ("frame_tag", None)]
    for fi in (0, 1):
        base = list(frames)
        tag_off = H + len(json.dumps(with_seq(recs)[fi], sort_keys=True).encode())
        for name, rel in regions:
            off = tag_off if name == "frame_tag" else rel
            f = bytearray(base[fi])
            f[off] ^= 0x01
            base2 = list(frames)
            base2[fi] = bytes(f)
            blob = b"".join(base2)
            p = os.path.join(d, "flip.bin")
            with open(p, "wb") as fh:
                fh.write(blob)
            before = hashlib.sha256(blob).hexdigest()
            c.check(expect_corrupt(lambda: cand._journal_read(p)),
                    f"frame{fi} {name} flip")
            after = hashlib.sha256(open(p, "rb").read()).hexdigest()
            c.check(after == before, f"frame{fi} {name} file untouched")
            os.unlink(p)
    return c.done()


def j05(d):
    c = Case("J-05", "malformed available header vs genuine byte-prefix tear")
    recs = [{"kind": "a"}, {"kind": "b"}]
    frames = frames_for(recs)
    head = frames[0]
    # (a) full garbage header present -> CORRUPT
    p = os.path.join(d, "j05.bin")
    with open(p, "wb") as fh:
        fh.write(head + b"\xaa" * 60)
    c.check(expect_corrupt(lambda: cand._journal_read(p)), "full garbage header")
    # (b) short tail with wrong magic -> CORRUPT
    with open(p, "wb") as fh:
        fh.write(head + b"BAD!" + b"\x00" * 6)
    c.check(expect_corrupt(lambda: cand._journal_read(p)), "short tail bad magic")
    # (c) short tail with wrong seq in fixed fields -> CORRUPT
    bad = bytearray(cand._frame_bytes({"kind": "b", "seq": 99})[:13])
    with open(p, "wb") as fh:
        fh.write(head + bytes(bad))
    c.check(expect_corrupt(lambda: cand._journal_read(p)), "partial header wrong seq")
    # (d) genuine byte-prefix tear of the next frame -> recovers + appends
    nxt = cand._frame_bytes(dict(recs[1], seq=1))
    with open(p, "wb") as fh:
        fh.write(head + nxt[:20])
    c.check(cand._journal_read(p) == with_seq(recs)[:1], "genuine tear tolerated")
    cand._journal_append(p, recs[1])
    c.check(cand._journal_read(p) == with_seq(recs), "append after tear completes")
    c.check(open(p, "rb").read() == head + nxt, "torn bytes truncated exactly")
    return c.done()


def j06(d):
    c = Case("J-06", "real-process torn append -> restart recovers exactly")
    p = os.path.join(d, "j06.bin")
    cand._journal_append(p, {"kind": "intent", "id": "R"})
    frame1 = cand._frame_bytes({"kind": "attempt", "id": "R", "seq": 1})
    r = subprocess.run([sys.executable, WORKER, CAND_PATH, p,
                        json.dumps({"kind": "attempt", "id": "R"}),
                        str(len(frame1) * 3 // 5)],
                       capture_output=True, text=True)
    c.check(r.returncode == 3, "worker died mid-append (exit 3)")
    c.check(os.path.getsize(p) ==
            len(cand._frame_bytes({"kind": "intent", "id": "R", "seq": 0}))
            + len(frame1) * 3 // 5, "torn bytes present before recovery")
    cand._journal_append(p, {"kind": "attempt", "id": "R"})
    got = cand._journal_read(p)
    c.check(got == [{"kind": "intent", "id": "R", "seq": 0},
                    {"kind": "attempt", "id": "R", "seq": 1}],
            "restart yields exactly the two records")
    blob = open(p, "rb").read()
    c.check(blob == cand._frame_bytes({"kind": "intent", "id": "R", "seq": 0})
            + frame1, "journal ends exactly at verified end")
    return c.done()


def main():
    out_path = sys.argv[1]
    d = tempfile.mkdtemp(prefix="qfj16_")
    cases = [j01(d), j02(d), j03(d), j04(d), j05(d), j06(d)]
    results = {
        "suite": "QF-YAHOO-QFAR1-JOURNAL-HEADER-AUTH-20261016-16 r1 (journal cases only)",
        "candidate": "qfar1_publisher_h16.py",
        "frame": {"magic": "QFJ2", "version": 2, "header_bytes": H,
                  "header_core_bytes": CB, "tag_bytes": TAG,
                  "max_frame_payload": MAXP},
        "cases": cases,
        "total_checks": sum(x["checks"] for x in cases),
        "total_failures": sum(len(x["failures"]) for x in cases),
        "verdict": "PASS" if all(not x["failures"] for x in cases) else "FAIL",
    }
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(results["verdict"], results["total_checks"], "checks,",
          results["total_failures"], "failures")


if __name__ == "__main__":
    main()
