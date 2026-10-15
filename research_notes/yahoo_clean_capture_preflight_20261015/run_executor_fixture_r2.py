#!/usr/bin/env python3
"""QF-YAHOO-CAPTURE-EXECUTOR-PREFLIGHT-20261015-09 r2 — adversarial fixture.

r2 adds E19-E25: deleted/altered actions+meta companions on restart,
torn attempt journal, torn/conflicting completion ledger, slow middle
and final requests crossing the wall cap, unexpected transport
exception, and exact final object-set enforcement. All 21 r1 checks
preserved (E6's crash expectation amended per the r2 spec: unexpected
transport exceptions now convert to a retained INCOMPLETE_HOLD instead
of propagating — the attempted-once / never-re-requested semantics are
unchanged).

Proves the executor (execute_capture.py) offline against the frozen
manifest: zero sockets (denial installed before any other import), zero
vendor/API calls, zero writes to any GitHub repository, no capture
execution — a fake transport and a local fake remote only.

Checks E0-E18: network denial + source hygiene; manifest drift; runtime
drift; order/count drift; complete fake 52/52; restart ALREADY_COMPLETE;
crash after journal + second-attempt refusal; throttle / partial / schema
/ meta / ceiling aborts retained as INCOMPLETE_HOLD; collision
no-overwrite; publish happy path against the fake remote; target-name
drift; public-visibility refusal; existing-capture refusal; re-fetch
hash mismatch; real-remote forbidden.

All clocks are fake and all bytes synthetic, so the normalized results
file is deterministic and must be byte-identical across runs.
"""
import hashlib
import json
import os
import socket
import sys
import tempfile

SOCKET_ATTEMPTS = {"count": 0}


class NetworkDeniedError(RuntimeError):
    pass


def _deny(*a, **k):
    SOCKET_ATTEMPTS["count"] += 1
    raise NetworkDeniedError("network denied: executor preflight fixture")


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
    print(f"{cid:30s} expect={expect:26s} got={got:26s} match={match}")


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


class CrashError(Exception):
    """Simulates process death after the journal commit."""


class FakeTransport:
    """behavior: {symbol: THROTTLE|CRASH|PARTIAL|SCHEMA|META_TZ|
    META_SYMBOL|CEILING}. Records every call and whether the attempt
    journal already contained the symbol at call time."""

    def __init__(self, cap_dir, behavior=None, clock=None):
        self.cap_dir = cap_dir
        self.clock = clock
        self.behavior = behavior or {}
        self.calls = []
        self.journal_preceded = []

    def __call__(self, symbol, entry, params):
        self.calls.append(symbol)
        self.journal_preceded.append(
            symbol in ec.journaled_symbols(self.cap_dir))
        mode = self.behavior.get(symbol)
        if isinstance(mode, str) and mode.startswith("SLOW:"):
            if self.clock is not None:
                self.clock.t += float(mode.split(":", 1)[1])
            mode = None
        if mode == "BOOM":
            raise ValueError("simulated unexpected transport failure")
        if mode == "THROTTLE":
            raise ec.ThrottleError("simulated 429")
        if mode == "CRASH":
            raise CrashError("simulated death after journal commit")
        frame = synth_frame(entry)
        meta = {"symbol": symbol,
                "timezone": "UTC" if entry["class"] == "crypto" else NY,
                "currency": "USD"}
        if mode == "PARTIAL":
            frame = frame.iloc[:-4]  # final session truncated 7 -> 3 rows
        elif mode == "SCHEMA":
            frame = frame.drop(columns=["Volume"])
        elif mode == "META_TZ":
            meta["timezone"] = "UTC"
        elif mode == "META_SYMBOL":
            meta["symbol"] = symbol + "X"
        elif mode == "CEILING":
            idx = pd.date_range("2020-01-01", periods=20001, freq="h",
                                tz=NY)
            frame = pd.DataFrame(
                {"Open": 100.0, "High": 101.0, "Low": 99.0,
                 "Close": 100.5, "Volume": 1000, "Dividends": 0.0,
                 "Stock Splits": 0.0}, index=idx)
        return {"frame": frame, "meta": meta}


class FakeRemote:
    kind = "FAKE_LOCAL"

    def __init__(self, name=ec.EXPECTED_REPO_FULL_NAME, visibility="private",
                 corrupt=None, drop=False):
        self._name = name
        self._visibility = visibility
        self.store = {}
        self.puts = []
        self.corrupt = corrupt
        self.drop = drop

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
        data = self.store.get(path)
        if data is None or self.drop:
            return None
        if self.corrupt == path:
            return data + b"tampered"
        return data

    def head_sha(self):
        listing = "".join(f"{p} {sha256_bytes(self.store[p])}\n"
                          for p in sorted(self.store))
        return sha256_bytes(listing.encode())


def fresh_capture(tmp, behavior=None, capture_id="TEST-CAPTURE-001"):
    clock = FakeClock()
    limiter = ec.SharedLimiter(1.0, clock.now, clock.sleep)
    root = os.path.join(tmp, "archive")
    cap_dir = os.path.join(root, capture_id)
    transport = FakeTransport(cap_dir, behavior, clock)
    return clock, limiter, root, cap_dir, transport, capture_id


def run_capture(man, root, cap_dir, transport, clock, limiter, capture_id):
    return ec.run_capture(man, root, capture_id, transport, FakeCalendar(),
                          limiter, clock.now, clock.stamp)


def main():
    man = ec.load_and_verify_manifest(MANIFEST_PATH)
    entries = ec.verify_order(man)
    symbols = [e["symbol"] for e in entries]

    # E0 — network denial + executor source hygiene
    try:
        socket.create_connection(("example.invalid", 443), timeout=1)
        denied = False
    except NetworkDeniedError:
        denied = True
    except Exception:
        denied = False
    import ast
    tree = ast.parse(open(os.path.join(HERE, "execute_capture.py"),
                          encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    banned = {"yfinance", "socket", "urllib", "requests", "http",
              "subprocess"}
    report("E0-network-and-hygiene", "sockets denied; no vendor/net imports",
           "CLEAN", "CLEAN" if denied and not (imported & banned) else "DIRTY",
           {"socket_raises": denied,
            "attempts_recorded": SOCKET_ATTEMPTS["count"] >= 1,
            "no_banned_imports": not (imported & banned),
            "yfinance_not_loaded": "yfinance" not in sys.modules})

    # E1 — manifest drift HOLDs before transport
    raw = open(MANIFEST_PATH, "rb").read()
    drifted = bytearray(raw)
    drifted[len(drifted) // 2] ^= 0x01
    tmp = tempfile.mkdtemp(prefix="qf_exec_e1_")
    bad_path = os.path.join(tmp, "manifest.json")
    with open(bad_path, "wb") as fh:
        fh.write(bytes(drifted))
    code = None
    try:
        ec.load_and_verify_manifest(bad_path)
    except ec.HoldError as exc:
        code = exc.code
    report("E1-manifest-drift", "1-byte manifest flip -> HOLD pre-transport",
           "HOLD:MANIFEST_DRIFT", code or "LOADED",
           {"real_manifest_hash_pinned":
                sha256_bytes(raw) == ec.EXPECTED_MANIFEST_SHA256,
            "drift_refused": code == "HOLD:MANIFEST_DRIFT"})

    # E2 — runtime drift (probe-based; live probe matches the frozen pins)
    probe = ec.probe_runtime()
    clean_ok = ec.verify_runtime(man, probe)
    codes = {}
    for tag, mut in (("version", {"pandas": "9.9.9"}),
                     ("filehash", {"yfinance_files_sha256_16":
                                   {"__init__.py": "0" * 16,
                                    "multi.py": "61aa5ec181f26c13",
                                    "ticker.py": "6f9a72fc35cd55da"}}),
                     ("missing", {"yfinance": None})):
        doctored = dict(probe)
        doctored.update(mut)
        try:
            ec.verify_runtime(man, doctored)
            codes[tag] = "PASSED"
        except ec.HoldError as exc:
            codes[tag] = exc.code
    report("E2-runtime-drift", "live probe passes; doctored probes HOLD",
           "HOLD:RUNTIME_DRIFT",
           codes["version"],
           {"live_probe_matches_pins": clean_ok is True,
            "version_drift": codes["version"] == "HOLD:RUNTIME_DRIFT",
            "filehash_drift": codes["filehash"] == "HOLD:RUNTIME_DRIFT",
            "missing_client": codes["missing"] == "HOLD:RUNTIME_DRIFT"})

    # E3 — order/count drift on parsed manifest dicts
    import copy
    variants = {}
    m_swap = copy.deepcopy(man)
    m_swap["request_order"][0]["i"], m_swap["request_order"][1]["i"] = \
        m_swap["request_order"][1]["i"], m_swap["request_order"][0]["i"]
    # swapping i values keeps a valid 1..52 sequence only if sort stable —
    # use a duplicated index instead for true drift:
    m_swap["request_order"][1]["i"] = m_swap["request_order"][0]["i"]
    variants["dup_index"] = m_swap
    m_drop = copy.deepcopy(man)
    m_drop["request_order"] = m_drop["request_order"][:-1]
    variants["count_51"] = m_drop
    m_dup = copy.deepcopy(man)
    m_dup["request_order"][3]["symbol"] = m_dup["request_order"][0]["symbol"]
    variants["dup_symbol"] = m_dup
    ocodes = {}
    for tag, variant in variants.items():
        try:
            ec.verify_order(variant)
            ocodes[tag] = "PASSED"
        except ec.HoldError as exc:
            ocodes[tag] = exc.code
    report("E3-order-count-drift", "dup index / 51 count / dup symbol HOLD",
           "HOLD:ORDER_DRIFT", ocodes["dup_index"],
           {f"case_{k}": v == "HOLD:ORDER_DRIFT"
            for k, v in ocodes.items()})

    # E4 — complete fake 52/52 path
    tmp = tempfile.mkdtemp(prefix="qf_exec_e4_")
    clock, limiter, root, cap_dir, transport, cid = fresh_capture(tmp)
    res = run_capture(man, root, cap_dir, transport, clock, limiter, cid)
    rels = []
    for sub in ("raw", "actions", "meta"):
        rels += [f"{sub}/{n}" for n in
                 sorted(os.listdir(os.path.join(cap_dir, sub)))]
    sums_ok = True
    sums = {}
    with open(os.path.join(cap_dir, "SHA256SUMS"), encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                h, rel = line.split(None, 1)
                sums[rel.strip()] = h
    for rel, h in sums.items():
        if sha256_bytes(open(os.path.join(cap_dir, rel), "rb").read()) != h:
            sums_ok = False
    report("E4-complete-52", "fake transport: full capture completes",
           "COMPLETE", res["status"],
           {"requests_52": res["requests"] == 52
                and len(transport.calls) == 52,
            "order_exact": transport.calls == symbols,
            "journal_before_every_request": all(transport.journal_preceded),
            "limiter_spacing_exact":
                limiter.starts == [float(i) for i in range(52)],
            "files_52x3_plus_2": len(rels) == 156 and res["files"] == 158,
            "sha256sums_verify": sums_ok and len(sums) == 156,
            "marker_absent": not os.path.exists(
                os.path.join(cap_dir, ec.MARKER_REL))})
    e4_cap, e4_cid = cap_dir, cid  # snapshot: later cases rebind these names

    # E5 — restart of the completed capture: zero requests
    clock2 = FakeClock()
    limiter2 = ec.SharedLimiter(1.0, clock2.now, clock2.sleep)
    transport2 = FakeTransport(cap_dir, clock=clock2)
    res2 = run_capture(man, root, cap_dir, transport2, clock2, limiter2, cid)
    report("E5-restart-complete", "completed capture re-run: no re-request",
           "ALREADY_COMPLETE", res2["status"],
           {"zero_transport_calls": len(transport2.calls) == 0,
            "files_verified_156": res2["files_verified"] == 156})

    # E6 — crash after journal: restart refuses a second attempt
    tmp = tempfile.mkdtemp(prefix="qf_exec_e6_")
    clock, limiter, root, cap_dir, transport, cid = fresh_capture(
        tmp, behavior={symbols[2]: "CRASH"})
    res_1 = run_capture(man, root, cap_dir, transport, clock, limiter, cid)
    crashed = res_1["status"] == "INCOMPLETE_HOLD" \
        and res_1["code"] == "HOLD:TRANSPORT_ERROR"
    calls_run1 = list(transport.calls)
    clock_b = FakeClock()
    limiter_b = ec.SharedLimiter(1.0, clock_b.now, clock_b.sleep)
    transport_b = FakeTransport(cap_dir, clock=clock_b)
    res_b = run_capture(man, root, cap_dir, transport_b, clock_b, limiter_b,
                        cid)
    report("E6-crash-second-attempt", "consumed attempt never re-requested",
           "INCOMPLETE_HOLD", res_b["status"],
           {"crash_converted_to_hold": crashed,
            "run1_calls_3": calls_run1 == symbols[:3],
            "code_ambiguous": res_b["code"] == "ATTEMPT_CONSUMED_AMBIGUOUS",
            "run2_zero_calls": len(transport_b.calls) == 0,
            "symbol_attempted_once_total":
                calls_run1.count(symbols[2])
                + transport_b.calls.count(symbols[2]) == 1,
            "marker_written": os.path.exists(
                os.path.join(cap_dir, ec.MARKER_REL))})

    # E7-E11 — fail-closed aborts, each in a fresh archive
    abort_cases = [
        ("E7-throttle", {symbols[1]: "THROTTLE"}, "HOLD:THROTTLED", 2),
        ("E8-partial", {symbols[0]: "PARTIAL"}, "HOLD:PARTIAL", 1),
        ("E9-schema-drift", {symbols[0]: "SCHEMA"}, "HOLD:SCHEMA_DRIFT", 1),
        ("E10a-meta-drift", {symbols[0]: "META_TZ"}, "HOLD:META_DRIFT", 1),
        ("E10b-symbol-mismatch", {symbols[0]: "META_SYMBOL"},
         "HOLD:SCHEMA_DRIFT", 1),
        ("E11-ceiling", {symbols[0]: "CEILING"}, "HOLD:CEILING", 1),
    ]
    for cid_, behavior, want_code, want_calls in abort_cases:
        tmp = tempfile.mkdtemp(prefix="qf_exec_ab_")
        clock, limiter, root, cap_dir, transport, capt = fresh_capture(
            tmp, behavior=behavior)
        res = run_capture(man, root, cap_dir, transport, clock, limiter,
                          capt)
        marker = {}
        mpath = os.path.join(cap_dir, ec.MARKER_REL)
        if os.path.exists(mpath):
            marker = json.load(open(mpath))
        retained = os.path.exists(
            os.path.join(cap_dir, "raw", f"{symbols[0]}.csv")) \
            if want_calls > 1 else True
        report(cid_, f"abort case {want_code}",
               "INCOMPLETE_HOLD", res["status"],
               {"code": res["code"] == want_code,
                "calls_stopped": len(transport.calls) == want_calls,
                "marker_status": marker.get("status") == "INCOMPLETE_HOLD",
                "marker_code": marker.get("code") == want_code,
                "partial_archive_retained": retained})

    # E12 — collision / no-overwrite on a foreign pre-placed file
    tmp = tempfile.mkdtemp(prefix="qf_exec_e12_")
    clock, limiter, root, cap_dir, transport, cid = fresh_capture(tmp)
    os.makedirs(os.path.join(cap_dir, "raw"), exist_ok=True)
    foreign = b"foreign bytes - not from this executor\n"
    with open(os.path.join(cap_dir, "raw", f"{symbols[0]}.csv"), "wb") as fh:
        fh.write(foreign)
    res = run_capture(man, root, cap_dir, transport, clock, limiter, cid)
    after = open(os.path.join(cap_dir, "raw", f"{symbols[0]}.csv"),
                 "rb").read()
    direct_collision = False
    try:
        ec.archive_write(cap_dir, f"raw/{symbols[0]}.csv", b"clobber?\n")
    except ec.WriteOnceCollision:
        direct_collision = True
    after2 = open(os.path.join(cap_dir, "raw", f"{symbols[0]}.csv"),
                  "rb").read()
    report("E12-collision-no-overwrite",
           "foreign final file: pre-scan HOLD + os.link refuses overwrite",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res["code"] == "HOLD:FINAL_MISMATCH",
            "zero_transport_calls": len(transport.calls) == 0,
            "foreign_bytes_unchanged": after == foreign and after2 == foreign,
            "direct_link_collision": direct_collision})

    # E13-E18 — publication phase against the fake remote only,
    # reusing the completed E4 archive.
    pub_cap = e4_cap
    pub_cid = e4_cid
    remote = FakeRemote()
    pub = ec.publish_capture(pub_cap, pub_cid, remote)
    report("E13-publish-happy", "fake remote: upload + re-fetch verify",
           "PUBLISHED_FAKE", pub["status"],
           {"objects_158": pub["objects"] == 158
                and pub["verified"] == 158,
            "commit_sha_64hex": len(pub["commit_sha"]) == 64,
            "under_captures_prefix": all(
                p.startswith(f"captures/{pub_cid}/") for p in remote.puts)})

    def pub_code(remote_obj):
        try:
            ec.publish_capture(pub_cap, pub_cid, remote_obj)
            return "PUBLISHED"
        except ec.HoldError as exc:
            return exc.code

    r_name = FakeRemote(name="mickaellall116-cmyk/qf-data-archive-evil")
    report("E14-target-name-drift", "wrong repo full name refused",
           "HOLD:TARGET_NAME_DRIFT", pub_code(r_name),
           {"zero_puts": len(r_name.puts) == 0})
    r_pub = FakeRemote(visibility="public")
    report("E15-public-visibility", "public target refused",
           "HOLD:VISIBILITY_REFUSAL", pub_code(r_pub),
           {"zero_puts": len(r_pub.puts) == 0})
    r_exist = FakeRemote()
    r_exist.store[f"captures/{pub_cid}/SHA256SUMS"] = b"prior"
    report("E16-existing-capture", "existing captures/<id> refused",
           "HOLD:CAPTURE_EXISTS", pub_code(r_exist),
           {"zero_puts": len(r_exist.puts) == 0})
    victim = f"captures/{pub_cid}/raw/{symbols[0]}.csv"
    r_bad = FakeRemote(corrupt=victim)
    report("E17-refetch-mismatch", "corrupted re-fetch detected",
           "HOLD:REFETCH_MISMATCH", pub_code(r_bad),
           {"uploads_happened": len(r_bad.puts) == 158})
    r_drop = FakeRemote(drop=True)
    code_drop = pub_code(r_drop)
    report("E17b-refetch-missing", "missing object on re-fetch detected",
           "HOLD:REFETCH_MISMATCH", code_drop, {"same_code": True})

    class RealishRemote:
        kind = "REAL"
    report("E18-real-remote-forbidden", "non-fake remote refused outright",
           "HOLD:REAL_REMOTE_FORBIDDEN", pub_code(RealishRemote()), {})

    # ---- r2 adversarial cases -------------------------------------------
    def completed_archive(tag):
        tmp = tempfile.mkdtemp(prefix=f"qf_exec_{tag}_")
        c, l, r_, cd, t_, ci = fresh_capture(tmp)
        res = run_capture(man, r_, cd, t_, c, l, ci)
        assert res["status"] == "COMPLETE", res
        return r_, cd, ci

    def restart(cd, r_, ci):
        c = FakeClock()
        l = ec.SharedLimiter(1.0, c.now, c.sleep)
        t_ = FakeTransport(cd, clock=c)
        return run_capture(man, r_, cd, t_, c, l, ci), t_

    def strip_finalization(cd):
        for name in ("manifest.json", "SHA256SUMS"):
            p = os.path.join(cd, name)
            if os.path.exists(p):
                os.unlink(p)

    # E19a — deleted actions companion: restart HOLDs pre-transport
    r_, cd, ci = completed_archive("e19a")
    strip_finalization(cd)
    os.unlink(os.path.join(cd, "actions", f"{symbols[3]}.actions.csv"))
    res, t_ = restart(cd, r_, ci)
    report("E19a-restart-actions-deleted",
           "missing actions companion blocks restart",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res["code"] == "HOLD:COMPLETION_INCOMPLETE",
            "zero_transport_calls": len(t_.calls) == 0})
    # E19b — altered meta companion: restart HOLDs pre-transport
    r_, cd, ci = completed_archive("e19b")
    strip_finalization(cd)
    mp = os.path.join(cd, "meta", f"{symbols[4]}.request.json")
    with open(mp, "ab") as fh:
        fh.write(b" ")
    res, t_ = restart(cd, r_, ci)
    report("E19b-restart-meta-altered",
           "altered meta companion blocks restart",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res["code"] == "HOLD:FINAL_MISMATCH",
            "zero_transport_calls": len(t_.calls) == 0})
    # E19c — altered raw companion (retained r1 behavior, new binding)
    r_, cd, ci = completed_archive("e19c")
    strip_finalization(cd)
    rp = os.path.join(cd, "raw", f"{symbols[0]}.csv")
    with open(rp, "ab") as fh:
        fh.write(b"x")
    res, t_ = restart(cd, r_, ci)
    report("E19c-restart-raw-altered", "altered raw blocks restart",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res["code"] == "HOLD:FINAL_MISMATCH",
            "zero_transport_calls": len(t_.calls) == 0})

    # E20 — torn attempt journal tail: named HOLD, no uncontrolled crash
    tmp = tempfile.mkdtemp(prefix="qf_exec_e20_")
    clock, limiter, root, cap_dir, transport, cid = fresh_capture(tmp)
    os.makedirs(cap_dir, exist_ok=True)
    with open(os.path.join(cap_dir, ec.JOURNAL_REL), "w",
              encoding="utf-8") as fh:
        fh.write(json.dumps({"event": "ATTEMPT", "symbol": symbols[0],
                             "i": 1}, sort_keys=True) + "\n")
        fh.write('{"event": "ATTEMPT", "symbol": "TOR')
    escaped = False
    try:
        res = run_capture(man, root, cap_dir, transport, clock, limiter,
                          cid)
    except Exception:
        escaped = True
        res = {"status": "ESCAPED", "code": "NONE"}
    report("E20-torn-journal", "truncated journal tail fails closed",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res.get("code") == "HOLD:JOURNAL_CORRUPT",
            "no_exception_escaped": not escaped,
            "zero_transport_calls": len(transport.calls) == 0,
            "marker_written": os.path.exists(
                os.path.join(cap_dir, ec.MARKER_REL))})

    # E21a — torn completion ledger tail
    r_, cd, ci = completed_archive("e21a")
    strip_finalization(cd)
    lp = os.path.join(cd, ec.LEDGER_REL)
    data = open(lp, "rb").read()
    with open(lp, "wb") as fh:
        fh.write(data[:-25])  # truncate the final record mid-JSON
    res, t_ = restart(cd, r_, ci)
    report("E21a-torn-ledger", "truncated completion record fails closed",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res["code"] == "HOLD:LEDGER_CORRUPT",
            "zero_transport_calls": len(t_.calls) == 0})
    # E21b — conflicting duplicate completion record
    r_, cd, ci = completed_archive("e21b")
    strip_finalization(cd)
    lp = os.path.join(cd, ec.LEDGER_REL)
    first = open(lp, encoding="utf-8").readline()
    rec = json.loads(first)
    sym0 = rec["symbol"]
    rec["files"][f"raw/{sym0}.csv"] = "0" * 64
    with open(lp, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    res, t_ = restart(cd, r_, ci)
    report("E21b-conflicting-ledger",
           "duplicate/conflicting completion record fails closed",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res["code"] == "HOLD:LEDGER_CONFLICT",
            "zero_transport_calls": len(t_.calls) == 0})

    # E22 — slow middle request crosses the wall cap after returning
    wall = float(man["call_budget"]["ceilings"]["wall_seconds_total"])
    tmp = tempfile.mkdtemp(prefix="qf_exec_e22_")
    clock, limiter, root, cap_dir, transport, cid = fresh_capture(
        tmp, behavior={symbols[5]: f"SLOW:{wall + 100}"})
    res = run_capture(man, root, cap_dir, transport, clock, limiter, cid)
    report("E22-slow-middle-request",
           "post-return wall check aborts before publication",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res["code"] == "HOLD:CEILING",
            "calls_stop_at_slow": len(transport.calls) == 6,
            "slow_symbol_not_published": not os.path.exists(
                os.path.join(cap_dir, "raw", f"{symbols[5]}.csv")),
            "marker_written": os.path.exists(
                os.path.join(cap_dir, ec.MARKER_REL))})
    # E23 — slow FINAL request crosses the wall cap: no finalization
    tmp = tempfile.mkdtemp(prefix="qf_exec_e23_")
    clock, limiter, root, cap_dir, transport, cid = fresh_capture(
        tmp, behavior={symbols[51]: f"SLOW:{wall + 100}"})
    res = run_capture(man, root, cap_dir, transport, clock, limiter, cid)
    report("E23-slow-final-request",
           "final request crossing the cap is never finalized",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res["code"] == "HOLD:CEILING",
            "all_52_attempted": len(transport.calls) == 52,
            "final_symbol_not_published": not os.path.exists(
                os.path.join(cap_dir, "raw", f"{symbols[51]}.csv")),
            "no_finalization": not os.path.exists(
                os.path.join(cap_dir, "manifest.json"))
                and not os.path.exists(os.path.join(cap_dir,
                                                     "SHA256SUMS"))})
    # E24 — unexpected transport exception: named retained HOLD, no retry
    tmp = tempfile.mkdtemp(prefix="qf_exec_e24_")
    clock, limiter, root, cap_dir, transport, cid = fresh_capture(
        tmp, behavior={symbols[1]: "BOOM"})
    res = run_capture(man, root, cap_dir, transport, clock, limiter, cid)
    marker = {}
    mpath = os.path.join(cap_dir, ec.MARKER_REL)
    if os.path.exists(mpath):
        marker = json.load(open(mpath))
    report("E24-unexpected-transport-error",
           "unexpected exception converts to retained INCOMPLETE_HOLD",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res["code"] == "HOLD:TRANSPORT_ERROR",
            "calls_stopped_no_retry": len(transport.calls) == 2,
            "marker_code": marker.get("code") == "HOLD:TRANSPORT_ERROR"})
    # E25a — unexpected extra object blocks finalization
    r_, cd, ci = completed_archive("e25a")
    strip_finalization(cd)
    with open(os.path.join(cd, "raw", "EXTRA.csv"), "wb") as fh:
        fh.write(b"unexpected\n")
    res, t_ = restart(cd, r_, ci)
    report("E25a-object-set-extra", "extra object fails finalization gate",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res["code"] == "HOLD:OBJECT_SET",
            "zero_transport_calls": len(t_.calls) == 0,
            "no_finalization": not os.path.exists(
                os.path.join(cd, "manifest.json"))})
    # E25b — leftover temp object blocks finalization
    r_, cd, ci = completed_archive("e25b")
    strip_finalization(cd)
    with open(os.path.join(cd, "raw", f"{symbols[0]}.csv.tmp-999"),
              "wb") as fh:
        fh.write(b"torn temp\n")
    res, t_ = restart(cd, r_, ci)
    report("E25b-object-set-temp", "temp leftover fails finalization gate",
           "INCOMPLETE_HOLD", res["status"],
           {"code": res["code"] == "HOLD:OBJECT_SET",
            "zero_transport_calls": len(t_.calls) == 0,
            "no_finalization": not os.path.exists(
                os.path.join(cd, "manifest.json"))})

    ok = all(r["match"] for r in RESULTS)
    summary = {"task": "QF-YAHOO-CAPTURE-EXECUTOR-PREFLIGHT-20261015-09 r2",
               "executor_sha256": sha256_bytes(open(
                   os.path.join(HERE, "execute_capture.py"), "rb").read()),
               "manifest_sha256": ec.EXPECTED_MANIFEST_SHA256,
               "checks_total": len(RESULTS),
               "checks_matched": sum(1 for r in RESULTS if r["match"]),
               "all_match": ok,
               "verdict": "CAPTURE_EXECUTOR_PREFLIGHT_PASS" if ok else "HOLD",
               "socket_attempts_after_denial_check":
                   SOCKET_ATTEMPTS["count"],
               "results": RESULTS}
    out_path = os.path.join(HERE, "executor_fixture_results_r2.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)
    print(f"{summary['checks_matched']}/{summary['checks_total']} checks "
          f"matched — verdict {summary['verdict']}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
