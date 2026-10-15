"""Fixture driver for QF-YAHOO-PUBLISH-SNAPSHOT-PREFLIGHT-20261015-11 r1.

Offline only: synthetic local archives + an in-memory fake remote.
Zero network, zero vendor calls, zero real publication. Executes the
design's adversarial set T-01..T-14 plus the capture-ID/prefix cases
from the -11 adjudication, against the NEW isolated publisher in
publish_snapshot.py. The parked executor is never imported or run; its
32/32 + 15/15 results are referenced as immutable pins in the memo.

Run twice and byte-compare the two results files (T-14).
Peak RSS is written to a separate file (kept out of the deterministic
results pair on purpose).
"""

import argparse
import builtins
import hashlib
import inspect
import io
import json
import os
import resource
import shutil
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import publish_snapshot as ps  # noqa: E402

WORK = os.path.join(HERE, "fixture_work")
MANIFEST_PATH = ps.FROZEN_MANIFEST_PATH
EXPECTED = ps.EXPECTED_MANIFEST_SHA256
CID = "QF-YAHOO1H-20261016-001"
CID2 = "QF-YAHOO1H-20261016-002"

with open(MANIFEST_PATH, "rb") as fh:
    _man = json.loads(fh.read().decode("utf-8"))
SYMBOLS = [e["symbol"] for e in sorted(_man["request_order"],
                                        key=lambda e: e["i"])]
S0, S1, S2 = SYMBOLS[0], SYMBOLS[1], SYMBOLS[2]


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Crash(BaseException):
    """Simulated process kill: BaseException, so no except-Exception
    handler in the publisher can convert it into a graceful HOLD."""


class FakeRemote:
    kind = "FAKE_LOCAL"

    def __init__(self, full_name=ps.EXPECTED_REPO_FULL_NAME,
                 visibility="private"):
        self.store = {}
        self._name = full_name
        self._vis = visibility
        self.put_calls = 0
        self.get_calls = 0
        self.meta_calls = 0
        self.fail_on_put = None
        self.drop_put = None
        self.crash_after = None
        self.corrupt = {}
        self.on_put = None

    def full_name(self):
        self.meta_calls += 1
        return self._name

    def visibility(self):
        self.meta_calls += 1
        return self._vis

    def has_prefix(self, base):
        self.meta_calls += 1
        return any(p == base or p.startswith(base + "/")
                   for p in self.store)

    def list_capture_prefixes(self):
        self.meta_calls += 1
        return sorted({"/".join(p.split("/")[:2]) for p in self.store
                       if p.startswith("captures/")})

    def put_file(self, path, data):
        self.put_calls += 1
        n = self.put_calls
        if self.crash_after is not None and n > self.crash_after:
            raise Crash()
        if self.fail_on_put is not None and n == self.fail_on_put:
            raise IOError("simulated put failure")
        if self.on_put is not None:
            self.on_put(self, path, data, n)
        if self.drop_put is not None and n == self.drop_put:
            return
        self.store[path] = bytes(data)
        mode = self.corrupt.get(path)
        if mode == "flip":
            b = bytearray(self.store[path])
            b[0] ^= 0xFF
            self.store[path] = bytes(b)
        elif isinstance(mode, tuple) and mode[0] == "sub":
            self.store[path] = self.store[mode[1]]
        elif isinstance(mode, bytes):
            self.store[path] = mode

    def get_file(self, path):
        self.get_calls += 1
        return self.store.get(path)

    def head_sha(self):
        h = hashlib.sha256()
        for p in sorted(self.store):
            h.update(f"{p}:{sha(self.store[p])}\n".encode())
        return h.hexdigest()

    @property
    def total_calls(self):
        return self.put_calls + self.get_calls + self.meta_calls


def build_archive(root, capture_id, seed="A", pad=None):
    """Deterministic synthetic COMPLETE archive in the exact capture
    format. Returns {rel: bytes} for all 158 payloads."""
    pad = pad or {}
    os.makedirs(os.path.join(root, "raw"))
    os.makedirs(os.path.join(root, "actions"))
    os.makedirs(os.path.join(root, "meta"))
    payloads = {}
    files = {}
    for s in SYMBOLS:
        digest = sha(f"{seed}:{s}".encode())
        raw = (f"ts,Open,High,Low,Close,Volume,Dividends,Stock Splits\n"
               f"2026-01-02T09:30,{digest[:8]},1,1,1,100,0,0\n"
               f"2026-01-02T13:30,{digest[8:16]},1,1,1,100,0,0\n").encode()
        act = f"ts,Dividends,Stock Splits\n{digest[16:24]},0,0\n".encode()
        meta = json.dumps({"symbol": s, "seed": seed,
                           "digest": digest},
                          sort_keys=True).encode()
        for rel, data in ((f"raw/{s}.csv", raw),
                          (f"actions/{s}.actions.csv", act),
                          (f"meta/{s}.request.json", meta)):
            if rel in pad:
                size = pad[rel]
                unit = b"0123456789abcdef"
                data = (unit * (size // 16 + 1))[:size]
            payloads[rel] = data
            files[rel] = sha(data)
    sums = "".join(f"{files[r]}  {r}\n" for r in sorted(files)).encode()
    doc = {"capture_id": capture_id, "status": "COMPLETE",
           "capture_manifest_sha256": EXPECTED,
           "symbols": len(SYMBOLS), "files": files}
    payloads["SHA256SUMS"] = sums
    payloads["manifest.json"] = json.dumps(doc, sort_keys=True,
                                           indent=1).encode()
    for rel, data in payloads.items():
        with open(os.path.join(root, rel), "wb") as fh:
            fh.write(data)
    with open(os.path.join(root, "attempt_journal.jsonl"), "w") as fh:
        fh.write('{"event":"DRIVER_FIXTURE"}\n')
    with open(os.path.join(root, "file_ledger.jsonl"), "w") as fh:
        fh.write('{"event":"DRIVER_FIXTURE"}\n')
    return payloads


def sandbox(name):
    path = os.path.join(WORK, name)
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path)
    return path


def attempt(fn):
    try:
        res = fn()
        return res.get("status", "?"), res
    except ps.HoldError as exc:
        return exc.code, None
    except TypeError:
        return "TypeError", None


RESULTS = {}
BASE = {}


def case(name, fn):
    RESULTS[name] = fn()
    print(f"{name}: {RESULTS[name].get('verdict')}")


# ---------------------------------------------------------------- cases

def c_baseline():
    sb = sandbox("baseline")
    cap = os.path.join(sb, "cap")
    expected = build_archive(cap, CID)
    remote = FakeRemote()
    verdict, res = attempt(lambda: ps.publish(cap, CID, remote))
    ok = all(remote.store.get(f"captures/{CID}/{rel}") == data
             for rel, data in expected.items())
    BASE["bundle_sha256"] = res["bundle_sha256"] if res else None
    BASE["expected"] = expected
    return {"verdict": verdict, "objects": res["objects"],
            "verified": res["verified"], "puts": remote.put_calls,
            "bundle_sha256": res["bundle_sha256"],
            "commit_sha": res["commit_sha"], "remote_matches": ok}


def c_t01():
    out = {}
    sb = sandbox("t01")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    v, _ = attempt(lambda: ps.publish(cap, CID, FakeRemote(), entries=[]))
    out["entries_kwarg"] = v
    v, _ = attempt(lambda: ps.publish(cap, CID, FakeRemote(),
                                      expected_repo="x/y"))
    out["expected_repo_kwarg"] = v
    saved = ps.EXPECTED_MANIFEST_SHA256
    ps.EXPECTED_MANIFEST_SHA256 = "0" * 64
    try:
        remote = FakeRemote()
        v, _ = attempt(lambda: ps.publish(cap, CID, remote))
        out["monkeypatched_pin"] = v
        out["monkeypatched_pin_puts"] = remote.put_calls
    finally:
        ps.EXPECTED_MANIFEST_SHA256 = saved
    os.environ["QF_PUBLISH_ENTRIES"] = "raw/EVIL.csv"
    try:
        remote = FakeRemote()
        v, res = attempt(lambda: ps.publish(cap, CID, remote))
        out["env_variation"] = v
        out["env_bundle_matches_baseline"] = (
            res is not None
            and res["bundle_sha256"] == BASE["bundle_sha256"])
    finally:
        del os.environ["QF_PUBLISH_ENTRIES"]
    return out


def c_t02():
    sb = sandbox("t02")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)

    def hook(remote, path, data, n):
        if n == 1:
            with open(os.path.join(cap, f"raw/{S0}.csv"), "wb") as fh:
                fh.write(b"mutated after seal\n")
            os.remove(os.path.join(cap, f"meta/{S1}.request.json"))
            os.rename(os.path.join(cap, f"raw/{S2}.csv"),
                      os.path.join(cap, f"raw/{S2}.csv.moved"))

    remote = FakeRemote()
    remote.on_put = hook
    verdict, res = attempt(lambda: ps.publish(cap, CID, remote))
    ok = all(remote.store.get(f"captures/{CID}/{rel}") == data
             for rel, data in BASE["expected"].items())
    return {"verdict": verdict,
            "bundle_matches_baseline":
                res is not None
                and res["bundle_sha256"] == BASE["bundle_sha256"],
            "remote_matches_original": ok}


def c_t03():
    sb = sandbox("t03")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID, seed="A")
    other = os.path.join(sb, "cap_b")
    build_archive(other, CID, seed="B")

    def hook(remote, path, data, n):
        if n == 1:
            shutil.rmtree(cap)
            shutil.copytree(other, cap)

    remote = FakeRemote()
    remote.on_put = hook
    verdict, res = attempt(lambda: ps.publish(cap, CID, remote))
    ok = all(remote.store.get(f"captures/{CID}/{rel}") == data
             for rel, data in BASE["expected"].items())
    return {"verdict": verdict,
            "bundle_matches_baseline":
                res is not None
                and res["bundle_sha256"] == BASE["bundle_sha256"],
            "remote_matches_original": ok}


def c_t04():
    out = {}
    sb = sandbox("t04a")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    os.remove(os.path.join(cap, f"raw/{S0}.csv"))
    os.symlink(os.path.join(cap, f"raw/{S1}.csv"),
               os.path.join(cap, f"raw/{S0}.csv"))
    remote = FakeRemote()
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    out["symlink_to_archive_file"] = v
    out["symlink_to_archive_file_puts"] = remote.put_calls

    sb = sandbox("t04b")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    outside = os.path.join(sb, "outside.txt")
    with open(outside, "wb") as fh:
        fh.write(b"outside the tree\n")
    os.remove(os.path.join(cap, f"meta/{S0}.request.json"))
    os.symlink(outside, os.path.join(cap, f"meta/{S0}.request.json"))
    remote = FakeRemote()
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    out["symlink_to_outside"] = v
    out["symlink_to_outside_puts"] = remote.put_calls

    sb = sandbox("t04c")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    raw_copy = os.path.join(sb, "raw_copy")
    shutil.copytree(os.path.join(cap, "raw"), raw_copy)
    shutil.rmtree(os.path.join(cap, "raw"))
    os.symlink(raw_copy, os.path.join(cap, "raw"))
    remote = FakeRemote()
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    out["symlinked_directory"] = v
    out["symlinked_directory_puts"] = remote.put_calls

    sb = sandbox("t04d")
    cap = os.path.join(sb, "cap")
    big_rel = f"raw/{S0}.csv"
    build_archive(cap, CID, pad={big_rel: 24 * 1024 * 1024})
    target = os.path.join(cap, big_rel)
    stop = threading.Event()

    def churn():
        t = 1_700_000_000_000_000_000
        while not stop.is_set():
            t += 1
            try:
                os.utime(target, ns=(t, t))
            except OSError:
                pass
            time.sleep(0.0002)

    th = threading.Thread(target=churn, daemon=True)
    th.start()
    try:
        remote = FakeRemote()
        v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    finally:
        stop.set()
        th.join()
    out["fstat_drift_during_read"] = v
    out["fstat_drift_puts"] = remote.put_calls
    return out


def c_t05():
    out = {}
    sb = sandbox("t05a")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    remote = FakeRemote()
    remote.corrupt[f"captures/{CID}/raw/{S0}.csv"] = "flip"
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    out["bit_flip"] = v
    out["bit_flip_puts"] = remote.put_calls

    sb = sandbox("t05b")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    remote = FakeRemote()
    remote.corrupt[f"captures/{CID}/meta/{S0}.request.json"] = (
        "sub", f"captures/{CID}/actions/{S0}.actions.csv")
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    out["cross_object_substitution"] = v

    sb = sandbox("t05c")
    cap = os.path.join(sb, "cap")
    b_bytes = build_archive(os.path.join(sb, "cap_b"), CID, seed="B")
    build_archive(cap, CID, seed="A")
    remote = FakeRemote()
    remote.corrupt[f"captures/{CID}/raw/{S0}.csv"] = \
        b_bytes[f"raw/{S0}.csv"]
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    out["foreign_capture_substitution"] = v
    return out


def c_t06():
    out = {"fail_put": {}}
    for n in (1, 2, 79, 157, 158):
        sb = sandbox(f"t06_{n}")
        cap = os.path.join(sb, "cap")
        build_archive(cap, CID)
        remote = FakeRemote()
        remote.fail_on_put = n
        v, _ = attempt(lambda: ps.publish(cap, CID, remote))
        out["fail_put"][str(n)] = {
            "verdict": v, "puts_attempted": remote.put_calls,
            "sums_present": f"captures/{CID}/SHA256SUMS" in remote.store,
            "manifest_present":
                f"captures/{CID}/manifest.json" in remote.store}
    sb = sandbox("t06_drop")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    remote = FakeRemote()
    remote.drop_put = 10
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    out["silent_drop"] = {"verdict": v, "puts": remote.put_calls}
    return out


def c_t07():
    out = {}
    b_bytes = build_archive(os.path.join(sandbox("t07_pre"), "cap_b"),
                            CID, seed="B")
    sb = sandbox("t07a")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    remote = FakeRemote()
    for rel, data in b_bytes.items():
        remote.store[f"captures/{CID}/{rel}"] = data
    head_before = remote.head_sha()
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    out["full_older_capture"] = v
    out["full_older_capture_puts"] = remote.put_calls
    out["remote_unchanged"] = remote.head_sha() == head_before

    sb = sandbox("t07b")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    remote = FakeRemote()
    remote.store[f"captures/{CID}/raw/{S0}.csv"] = b"stub"
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    out["one_file_stub"] = v
    out["one_file_stub_puts"] = remote.put_calls

    sb = sandbox("t07c")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    remote = FakeRemote()
    remote.store[f"captures/{CID.lower()}/raw/{S0}.csv"] = b"stub"
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    out["case_variant_prefix"] = v
    out["case_variant_prefix_puts"] = remote.put_calls
    return out


def c_t08():
    src = inspect.getsource(ps._publish_bundle)
    static = {"cap_dir_in_publish_phase": "cap_dir" in src,
              "open_in_publish_phase": "open(" in src,
              "read_once_in_publish_phase": "_read_once" in src}
    sb = sandbox("t08")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    _m, entries = ps._load_frozen_manifest()
    bundle = ps._build_bundle(cap, CID, entries)
    journal = ps._journal_for(cap, CID)
    cap_abs = os.path.abspath(cap)
    hits = []
    real_bopen, real_iopen, real_oopen = builtins.open, io.open, os.open

    def guard(path, *a, **k):
        if isinstance(path, (str, bytes, os.PathLike)) and \
                os.path.abspath(os.fspath(path)).startswith(
                        cap_abs + os.sep):
            hits.append(str(path))
            raise AssertionError("payload open after seal")
        return real_bopen(path, *a, **k)

    def oguard(path, *a, **k):
        if isinstance(path, (str, bytes, os.PathLike)) and \
                os.path.abspath(os.fspath(path)).startswith(
                        cap_abs + os.sep):
            hits.append(str(path))
            raise AssertionError("payload open after seal")
        return real_oopen(path, *a, **k)

    builtins.open, io.open, os.open = guard, guard, oguard
    try:
        remote = FakeRemote()
        verdict, _res = attempt(
            lambda: ps._publish_bundle(bundle, CID, remote, journal))
    finally:
        builtins.open, io.open, os.open = real_bopen, real_iopen, real_oopen
    return {"verdict": verdict, "trap_hits": len(hits),
            "static_audit": static}


def c_t09():
    out = {}

    def variant(name, mutate):
        sb = sandbox(f"t09_{name}")
        cap = os.path.join(sb, "cap")
        build_archive(cap, CID)
        mutate(cap)
        remote = FakeRemote()
        v, _ = attempt(lambda: ps.publish(cap, CID, remote))
        out[name] = v
        out[name + "_puts"] = remote.put_calls

    variant("extra_in_subdir", lambda cap: open(
        os.path.join(cap, "raw/EXTRA.txt"), "w").write("x"))
    variant("temp_top_level", lambda cap: open(
        os.path.join(cap, "scratch.tmp"), "w").write("x"))
    variant("missing_object", lambda cap: os.remove(
        os.path.join(cap, f"meta/{S0}.request.json")))

    def fiftythird(cap):
        for rel in ("raw/ZZZZ.csv", "actions/ZZZZ.actions.csv",
                    "meta/ZZZZ.request.json"):
            with open(os.path.join(cap, rel), "w") as fh:
                fh.write("x")
    variant("fifty_third_symbol", fiftythird)
    variant("case_variant_duplicate", lambda cap: open(
        os.path.join(cap, f"raw/{S0.lower()}.csv"), "w").write("x"))
    return out


def c_t10():
    out = {}
    for name, kw in (("wrong_name", {"full_name": "mickaellall116-cmyk/other"}),
                     ("public", {"visibility": "public"}),
                     ("internal", {"visibility": "internal"})):
        sb = sandbox(f"t10_{name}")
        cap = os.path.join(sb, "cap")
        build_archive(cap, CID)
        remote = FakeRemote(**kw)
        v, _ = attempt(lambda: ps.publish(cap, CID, remote))
        out[name] = v
        out[name + "_puts"] = remote.put_calls
    return out


def c_t11():
    sb = sandbox("t11")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    import gc
    import sys as _sys

    def hook(remote, path, data, n):
        if n != 10:
            return
        frame = _sys._getframe(1)
        bundle = None
        while frame is not None:
            if "bundle" in frame.f_locals and hasattr(
                    frame.f_locals["bundle"], "bundle_sha256"):
                bundle = frame.f_locals["bundle"]
                break
            frame = frame.f_back
        assert bundle is not None
        underlying = None
        for ref in gc.get_referents(bundle._payloads):
            if isinstance(ref, dict):
                underlying = ref
        assert underlying is not None
        victim = bundle.upload_order[100]
        underlying[victim] = b"corrupted-in-memory"

    remote = FakeRemote()
    remote.on_put = hook
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    return {"verdict": v, "puts": remote.put_calls}


def c_t12():
    out = {}
    last_remote = None
    for k in (0, 1, 50, 157):
        sb = sandbox(f"t12_{k}")
        cap = os.path.join(sb, "cap")
        build_archive(cap, CID)
        remote = FakeRemote()
        remote.crash_after = k
        crashed = False
        try:
            ps.publish(cap, CID, remote)
        except Crash:
            crashed = True
        remote.crash_after = None
        v, _ = attempt(lambda: ps.publish(cap, CID, remote))
        out[f"k{k}"] = {"crashed": crashed, "restart_same_id": v}
        last_remote = remote
    sb = sandbox("t12_newid")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID2)
    v, _ = attempt(lambda: ps.publish(cap, CID2, last_remote))
    out["new_capture_id"] = v
    return out


def c_t13():
    out = {}
    sb = sandbox("t13a")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID, pad={f"raw/{S0}.csv": 33 * 1024 * 1024})
    remote = FakeRemote()
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    out["single_object_over_32mib"] = v
    out["single_object_puts"] = remote.put_calls

    sb = sandbox("t13b")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID, pad={f"raw/{S0}.csv": 25 * 1024 * 1024,
                                 f"raw/{S1}.csv": 25 * 1024 * 1024,
                                 f"raw/{S2}.csv": 25 * 1024 * 1024})
    remote = FakeRemote()
    v, _ = attempt(lambda: ps.publish(cap, CID, remote))
    out["total_over_64mib"] = v
    out["total_puts"] = remote.put_calls
    return out


def c_ids():
    sb = sandbox("ids")
    cap = os.path.join(sb, "cap")
    build_archive(cap, CID)
    bad = ["qf-yahoo1h-20261016-001", "QF-YAHOO/20261016",
           "../QF-20261016-XX", "QF..20261016", "QF%2D20261016X",
           "QF-YAHOO1H-20261016-00А", "QF-YAHOO\n20261016",
           "QF-2026", "A" * 65, "-QF-YAHOO1H-2026", "QF-YAHOO1H-2026-",
           "QF--YAHOO1H-2026", "", "QF YAHOO1H 2026",
           "QF-YAHOO\\20261016"]
    out = []
    for bad_id in bad:
        remote = FakeRemote()
        v, _ = attempt(lambda: ps.publish(cap, bad_id, remote))
        out.append({"id": bad_id, "verdict": v,
                    "remote_calls": remote.total_calls})
    return {"invalid_ids": out}


def api_audit():
    funcs = sorted(n for n, f in inspect.getmembers(ps, inspect.isfunction)
                   if not n.startswith("_") and f.__module__ == ps.__name__)
    classes = sorted(n for n, c in inspect.getmembers(ps, inspect.isclass)
                     if not n.startswith("_")
                     and c.__module__ == ps.__name__)
    mutables = sorted(n for n, v in vars(ps).items()
                      if not n.startswith("_")
                      and isinstance(v, (list, dict, set)))
    with open(ps.__file__, encoding="utf-8") as fh:
        source = fh.read()
    return {"public_functions": funcs, "public_classes": classes,
            "public_mutable_module_state": mutables,
            "publish_signature": list(
                inspect.signature(ps.publish).parameters),
            "environ_reads": ("environ" in source
                              or "getenv" in source),
            "module_sha256": sha(source.encode("utf-8"))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--rss-out", required=True)
    ap.add_argument("--audit-out", required=True)
    ap.add_argument("--parity-out", required=True)
    args = ap.parse_args()

    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)

    case("BASELINE", c_baseline)
    case("T-01", c_t01)
    case("T-02", c_t02)
    case("T-03", c_t03)
    case("T-04", c_t04)
    case("T-05", c_t05)
    case("T-06", c_t06)
    case("T-07", c_t07)
    case("T-08", c_t08)
    case("T-09", c_t09)
    case("T-10", c_t10)
    case("T-11", c_t11)
    case("T-12", c_t12)
    case("T-13", c_t13)
    case("CAPTURE-ID", c_ids)

    audit = api_audit()
    RESULTS["API-AUDIT"] = audit
    with open(args.audit_out, "w") as fh:
        json.dump(audit, fh, indent=1, sort_keys=True)
        fh.write("\n")

    frozen_total = int(_man["call_budget"]["ceilings"]["bytes_total"])
    parity = {
        "record": "CEILING_PARITY_REQUIRED",
        "status": "UNRESOLVED",
        "publisher_bundle_ceiling_bytes": ps.BUNDLE_CEILING_BYTES,
        "publisher_single_object_ceiling_bytes":
            ps.SINGLE_OBJECT_CEILING_BYTES,
        "frozen_capture_total_ceiling_bytes": frozen_total,
        "frozen_capture_per_symbol_ceiling_bytes":
            int(_man["call_budget"]["ceilings"]["bytes_per_symbol"]),
        "frozen_manifest_sha256": EXPECTED,
        "ceilings_equal": ps.BUNDLE_CEILING_BYTES == frozen_total,
        "consequence": "A capture valid under the frozen 512 MiB total "
                       "ceiling could exceed the publisher 64 MiB bundle "
                       "ceiling and be unpublishable (HOLD:CEILING) after "
                       "vendor calls were consumed. No acquisition GO "
                       "until a separately reviewed unified capture "
                       "manifest/executor packet sets one shared "
                       "total-byte ceiling.",
    }
    with open(args.parity_out, "w") as fh:
        json.dump(parity, fh, indent=1, sort_keys=True)
        fh.write("\n")

    with open(args.out, "w") as fh:
        json.dump(RESULTS, fh, indent=1, sort_keys=True)
        fh.write("\n")

    rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with open(args.rss_out, "w") as fh:
        json.dump({"peak_rss_kib": rss_kib,
                   "peak_rss_mib": round(rss_kib / 1024, 2),
                   "scope": "fixture driver process (publisher + harness)"
                            ", Linux ru_maxrss",
                   "bundle_ceiling_bytes": ps.BUNDLE_CEILING_BYTES},
                  fh, indent=1, sort_keys=True)
        fh.write("\n")
    shutil.rmtree(WORK, ignore_errors=True)
    print(f"peak_rss_mib: {rss_kib / 1024:.2f}")


if __name__ == "__main__":
    main()
