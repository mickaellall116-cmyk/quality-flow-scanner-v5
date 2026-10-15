#!/usr/bin/env python3
"""QF-YAHOO-CAPTURE-EXECUTOR-PREFLIGHT-20261015-09 r2 — FINAL AMENDMENT.

Adds the strict completed-archive validator gate: one
validate_complete_archive() used by BOTH the ALREADY_COMPLETE restart
branch and publish_capture(). Checks A0-A11 exercise post-completion
mutation (extra object, temp leftover), duplicate/conflicting/
malformed SHA256SUMS lines, manifest capture-ID / files-mapping /
frozen-hash drift, a retained INCOMPLETE_HOLD marker, and attempted
publication of each invalid archive (all must HOLD with zero uploads),
plus the untouched happy path. The prior r2 suite is re-run twice as
a subprocess and must pass 32/32 with byte-identical results.

Offline only: socket denial installed before any other import; fake
transport and fake local remote only; zero vendor/API calls, zero
GitHub writes, no capture execution, no publication.
"""
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile

SOCKET_ATTEMPTS = {"count": 0}


class NetworkDeniedError(RuntimeError):
    pass


def _deny(*a, **k):
    SOCKET_ATTEMPTS["count"] += 1
    raise NetworkDeniedError("network denied: amendment fixture")


socket.socket = _deny
socket.create_connection = _deny
socket.getaddrinfo = _deny
socket.gethostbyname = _deny

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pandas as pd  # noqa: E402

import execute_capture as ec  # noqa: E402

MANIFEST_PATH = os.path.join(HERE, "capture_manifest.json")
NY = "America/New_York"
EQ_DATES = ["2026-10-14", "2026-10-15"]
RESULTS = []


def report(cid, desc, expect, got, checks):
    match = (got == expect) and all(checks.values())
    RESULTS.append({"id": cid, "desc": desc, "expect": expect, "got": got,
                    "checks": checks, "match": match})
    print(f"{cid:34s} expect={expect:26s} got={got:26s} match={match}")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, dt):
        self.t += dt

    def stamp(self):
        base = pd.Timestamp("2026-10-15T00:00:00Z")
        return (base + pd.Timedelta(seconds=self.t)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")


class FakeCalendar:
    def sessions(self, kind):
        if kind == "crypto":
            return [(d, 24) for d in EQ_DATES]
        return [(d, 7) for d in EQ_DATES]


def synth_frame(entry):
    rows, idx = [], []
    if entry["class"] == "crypto":
        for d in EQ_DATES:
            start = pd.Timestamp(f"{d} 00:00", tz="UTC")
            for i in range(24):
                o = 200.0 + i
                rows.append({"Open": o, "High": o + 1.0, "Low": o - 1.0,
                             "Close": o + 0.5, "Volume": 500 + i,
                             "Dividends": 0.0, "Stock Splits": 0.0})
                idx.append(start + pd.Timedelta(hours=i))
    else:
        for d in EQ_DATES:
            start = pd.Timestamp(f"{d} 09:30", tz=NY)
            for i in range(7):
                o = 100.0 + i
                rows.append({"Open": o, "High": o + 1.0, "Low": o - 1.0,
                             "Close": o + 0.5, "Volume": 1000 + 10 * i,
                             "Dividends": 0.0, "Stock Splits": 0.0})
                idx.append(start + pd.Timedelta(hours=i))
    return pd.DataFrame(rows, index=pd.DatetimeIndex(idx))


class FakeTransport:
    def __init__(self, cap_dir):
        self.cap_dir = cap_dir
        self.calls = []

    def __call__(self, symbol, entry, params):
        self.calls.append(symbol)
        meta = {"symbol": symbol,
                "timezone": "UTC" if entry["class"] == "crypto" else NY,
                "currency": "USD"}
        return {"frame": synth_frame(entry), "meta": meta}


class FakeRemote:
    kind = "FAKE_LOCAL"

    def __init__(self, name=ec.EXPECTED_REPO_FULL_NAME,
                 visibility="private"):
        self._name = name
        self._visibility = visibility
        self.store = {}
        self.puts = []

    def full_name(self):
        return self._name

    def visibility(self):
        return self._visibility

    def has_prefix(self, prefix):
        return any(k.startswith(prefix + "/") for k in self.store)

    def put_file(self, path, data):
        self.puts.append(path)
        self.store[path] = data

    def get_file(self, path):
        return self.store.get(path)

    def head_sha(self):
        listing = "".join(f"{p} {sha256_bytes(self.store[p])}\n"
                          for p in sorted(self.store))
        return sha256_bytes(listing.encode())


MAN = ec.load_and_verify_manifest(MANIFEST_PATH)
ENTRIES = ec.verify_order(MAN)
SYMBOLS = [e["symbol"] for e in ENTRIES]


def completed_archive(tag):
    tmp = tempfile.mkdtemp(prefix=f"qf_amd_{tag}_")
    clock = FakeClock()
    limiter = ec.SharedLimiter(1.0, clock.now, clock.sleep)
    root = os.path.join(tmp, "archive")
    cid = "TEST-CAPTURE-001"
    cap_dir = os.path.join(root, cid)
    transport = FakeTransport(cap_dir)
    res = ec.run_capture(MAN, root, cid, transport, FakeCalendar(),
                         limiter, clock.now, clock.stamp)
    assert res["status"] == "COMPLETE", res
    return root, cap_dir, cid


def restart(cap_dir, root, cid):
    clock = FakeClock()
    limiter = ec.SharedLimiter(1.0, clock.now, clock.sleep)
    transport = FakeTransport(cap_dir)
    res = ec.run_capture(MAN, root, cid, transport, FakeCalendar(),
                         limiter, clock.now, clock.stamp)
    return res, transport


def pub_attempt(cap_dir, cid):
    remote = FakeRemote()
    try:
        out = ec.publish_capture(cap_dir, cid, remote)
        return out["status"], remote
    except ec.HoldError as exc:
        return exc.code, remote


def edit_file(cap_dir, rel, fn):
    p = os.path.join(cap_dir, rel)
    with open(p, "rb") as fh:
        data = fh.read()
    with open(p, "wb") as fh:
        fh.write(fn(data))


def main():
    # A0 — socket denial is live before anything else ran.
    try:
        socket.socket()
        denied = False
    except NetworkDeniedError:
        denied = True
    report("A0-network-denial", "socket denial installed first",
           "DENIED", "DENIED" if denied else "ALLOWED",
           {"attempts_counted": SOCKET_ATTEMPTS["count"] >= 1})

    # A-prior — the r2 suite, twice, 32/32, byte-identical results.
    r2_script = os.path.join(HERE, "run_executor_fixture_r2.py")
    r2_out = os.path.join(HERE, "executor_fixture_results_r2.json")
    runs = []
    for _ in range(2):
        proc = subprocess.run([sys.executable, r2_script],
                              capture_output=True, text=True)
        with open(r2_out, "rb") as fh:
            runs.append((proc.returncode, fh.read()))
    doc = json.loads(runs[0][1].decode())
    report("A-prior-r2-suite-x2", "prior 32 checks preserved, x2 identical",
           "PASSx2", "PASSx2" if runs[0][0] == 0 and runs[1][0] == 0
           else "FAIL",
           {"exit0_both": runs[0][0] == 0 and runs[1][0] == 0,
            "byte_identical": runs[0][1] == runs[1][1],
            "checks_32_of_32": doc.get("checks_total") == 32
                and doc.get("checks_matched") == 32
                and doc.get("all_match") is True})

    # A1 — extra object added AFTER completion: restart must HOLD.
    root, cd, cid = completed_archive("a1")
    with open(os.path.join(cd, "raw", "EXTRA.csv"), "wb") as fh:
        fh.write(b"smuggled\n")
    res, t_ = restart(cd, root, cid)
    report("A1-restart-extra-object", "post-completion extra file: restart",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res.get("code") == "HOLD:OBJECT_SET",
            "zero_transport_calls": len(t_.calls) == 0})

    # A2 — temp leftover added after completion: restart must HOLD.
    root, cd, cid = completed_archive("a2")
    with open(os.path.join(cd, "meta", f"{SYMBOLS[0]}.request.json.tmp-7"),
              "wb") as fh:
        fh.write(b"torn temp\n")
    res, t_ = restart(cd, root, cid)
    report("A2-restart-temp-leftover", "post-completion temp file: restart",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res.get("code") == "HOLD:OBJECT_SET",
            "zero_transport_calls": len(t_.calls) == 0})

    # A3 — publication attempted on the extra-object archive: zero uploads.
    root, cd, cid = completed_archive("a3")
    with open(os.path.join(cd, "actions", "EXTRA.actions.csv"), "wb") as fh:
        fh.write(b"smuggled\n")
    code, remote = pub_attempt(cd, cid)
    report("A3-publish-extra-object", "publish invalid archive (extra obj)",
           "HOLD:OBJECT_SET", code, {"zero_uploads": len(remote.puts) == 0})

    # A4 — duplicate SHA256SUMS line (same path, same hash).
    def dup_sums(data):
        lines = data.decode().splitlines()
        return (data.decode() + lines[0] + "\n").encode()
    root, cd, cid = completed_archive("a4")
    edit_file(cd, "SHA256SUMS", dup_sums)
    code, remote = pub_attempt(cd, cid)
    report("A4-publish-dup-sums", "duplicate SHA256SUMS line: publish",
           "HOLD:SUMS_INVALID", code,
           {"zero_uploads": len(remote.puts) == 0})
    root, cd, cid = completed_archive("a4r")
    edit_file(cd, "SHA256SUMS", dup_sums)
    res, t_ = restart(cd, root, cid)
    report("A4b-restart-dup-sums", "duplicate SHA256SUMS line: restart",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res.get("code") == "HOLD:SUMS_INVALID",
            "zero_transport_calls": len(t_.calls) == 0})

    # A5 — conflicting SHA256SUMS line (same path, different valid hash).
    def conflict_sums(data):
        lines = data.decode().splitlines()
        h, rel = lines[0].split(None, 1)
        fake = ("0" * 64) if h != "0" * 64 else ("1" * 64)
        return (data.decode() + f"{fake}  {rel.strip()}\n").encode()
    root, cd, cid = completed_archive("a5")
    edit_file(cd, "SHA256SUMS", conflict_sums)
    code, remote = pub_attempt(cd, cid)
    report("A5-publish-conflict-sums", "conflicting SHA256SUMS line",
           "HOLD:SUMS_INVALID", code,
           {"zero_uploads": len(remote.puts) == 0})

    # A6 — malformed SHA256SUMS line (non-hex hash).
    def malformed_sums(data):
        lines = data.decode().splitlines()
        _h, rel = lines[0].split(None, 1)
        return (data.decode() + f"{'z' * 64}  {rel.strip()}\n").encode()
    root, cd, cid = completed_archive("a6")
    edit_file(cd, "SHA256SUMS", malformed_sums)
    code, remote = pub_attempt(cd, cid)
    report("A6-publish-malformed-sums", "malformed SHA256SUMS line",
           "HOLD:SUMS_INVALID", code,
           {"zero_uploads": len(remote.puts) == 0})

    # A7 — manifest capture-ID drift.
    def drift_id(data):
        doc = json.loads(data.decode())
        doc["capture_id"] = "TEST-CAPTURE-999"
        return json.dumps(doc, sort_keys=True).encode()
    root, cd, cid = completed_archive("a7")
    edit_file(cd, "manifest.json", drift_id)
    code, remote = pub_attempt(cd, cid)
    report("A7-publish-manifest-id-drift", "manifest capture_id drift",
           "HOLD:ARCHIVE_MANIFEST_INVALID", code,
           {"zero_uploads": len(remote.puts) == 0})

    # A8 — manifest files-mapping drift (one hash altered in manifest).
    def drift_files(data):
        doc = json.loads(data.decode())
        rel = sorted(doc["files"])[0]
        doc["files"][rel] = "0" * 64
        return json.dumps(doc, sort_keys=True).encode()
    root, cd, cid = completed_archive("a8")
    edit_file(cd, "manifest.json", drift_files)
    code, remote = pub_attempt(cd, cid)
    report("A8-publish-manifest-files-drift", "manifest files mapping drift",
           "HOLD:ARCHIVE_MANIFEST_INVALID", code,
           {"zero_uploads": len(remote.puts) == 0})

    # A9 — manifest frozen capture-manifest hash drift.
    def drift_frozen(data):
        doc = json.loads(data.decode())
        doc["capture_manifest_sha256"] = "f" * 64
        return json.dumps(doc, sort_keys=True).encode()
    root, cd, cid = completed_archive("a9")
    edit_file(cd, "manifest.json", drift_frozen)
    code, remote = pub_attempt(cd, cid)
    report("A9-publish-manifest-hash-drift", "manifest frozen-hash drift",
           "HOLD:ARCHIVE_MANIFEST_INVALID", code,
           {"zero_uploads": len(remote.puts) == 0})

    # A10 — retained INCOMPLETE_HOLD marker on a completed archive.
    root, cd, cid = completed_archive("a10")
    with open(os.path.join(cd, "INCOMPLETE_HOLD.json"), "wb") as fh:
        fh.write(b'{"status": "INCOMPLETE_HOLD", "code": "HOLD:X"}\n')
    code, remote = pub_attempt(cd, cid)
    report("A10-publish-incomplete-marker", "HOLD marker present: publish",
           "HOLD:INCOMPLETE_MARKER", code,
           {"zero_uploads": len(remote.puts) == 0})
    root, cd, cid = completed_archive("a10r")
    with open(os.path.join(cd, "INCOMPLETE_HOLD.json"), "wb") as fh:
        fh.write(b'{"status": "INCOMPLETE_HOLD", "code": "HOLD:X"}\n')
    res, t_ = restart(cd, root, cid)
    report("A10b-restart-incomplete-marker", "HOLD marker present: restart",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res.get("code") == "HOLD:INCOMPLETE_MARKER",
            "zero_transport_calls": len(t_.calls) == 0})

    # A11 — untouched completed archive: restart + publish happy path,
    # and the uploaded set is EXACTLY the validated set.
    root, cd, cid = completed_archive("a11")
    res, t_ = restart(cd, root, cid)
    remote = FakeRemote()
    pub = ec.publish_capture(cd, cid, remote)
    expected_puts = {f"captures/{cid}/{rel}"
                     for rel in ec.expected_object_rels(ENTRIES)}
    expected_puts |= {f"captures/{cid}/SHA256SUMS",
                      f"captures/{cid}/manifest.json"}
    report("A11-happy-path-exact-set", "valid archive: restart + publish",
           "PUBLISHED_FAKE", pub["status"],
           {"restart_already_complete": res["status"] == "ALREADY_COMPLETE"
                and res.get("files_verified") == 156,
            "objects_158": pub["objects"] == 158
                and pub["verified"] == 158,
            "uploaded_set_exact": set(remote.puts) == expected_puts})

    ok = all(r["match"] for r in RESULTS)
    summary = {"task": "QF-YAHOO-CAPTURE-EXECUTOR-PREFLIGHT-20261015-09 r2 "
                       "final amendment",
               "executor_sha256": sha256_bytes(open(
                   os.path.join(HERE, "execute_capture.py"), "rb").read()),
               "manifest_sha256": ec.EXPECTED_MANIFEST_SHA256,
               "checks_total": len(RESULTS),
               "checks_matched": sum(1 for r in RESULTS if r["match"]),
               "all_match": ok,
               "verdict": "CAPTURE_EXECUTOR_PREFLIGHT_PASS" if ok
                          else "CAPTURE_EXECUTOR_PREFLIGHT_HOLD",
               "socket_attempts_after_denial_check":
                   SOCKET_ATTEMPTS["count"],
               "results": RESULTS}
    out_path = os.path.join(HERE,
                            "executor_fixture_results_r2_amendment.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)
    print(f"{summary['checks_matched']}/{summary['checks_total']} checks "
          f"matched — verdict {summary['verdict']}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
