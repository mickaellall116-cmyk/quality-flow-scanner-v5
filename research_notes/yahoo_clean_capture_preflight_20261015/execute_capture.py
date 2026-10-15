#!/usr/bin/env python3
"""QF-YAHOO-CAPTURE-EXECUTOR-PREFLIGHT-20261015-09 r1 — capture executor.

Built against the frozen packet of QF-YAHOO-CLEAN-CAPTURE-PREFLIGHT-08 r2
(commit 0d7ccfb): the executor is bound to the capture manifest by exact
SHA256 and reuses the r2-proven mechanisms — os.link atomic no-clobber
publication, the fsync'd attempt journal with restart reconciliation
(SKIP_VERIFIED | ATTEMPT_CONSUMED_AMBIGUOUS | HOLD:FINAL_MISMATCH |
ELIGIBLE), and calendar-derived qualification expectations.

PREFLIGHT BUILD — safety posture:
  * This module imports NO vendor client (no yfinance) and contains NO
    network code. The transport is an injected callable; the CLI binds
    none, so `execute` from the command line HOLDs unconditionally.
  * Capture and publication are separate phases. The executor only ever
    creates the local write-once archive. publish_capture() refuses any
    remote that is not explicitly a local fake (kind == "FAKE_LOCAL");
    no real remote implementation exists in this file.
  * A PASS of the accompanying fixture authorizes neither the 52 Yahoo
    requests nor publication; acquisition is a separate explicit gate.
"""
import argparse
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import sys
import time

import pandas as pd

EXPECTED_MANIFEST_SHA256 = \
    "634c4541a8b30ade50e45898e80ee65806fa323c953020edc149530642d9bef3"
EXPECTED_SCHEMA = "qf.yahoo_clean_capture.manifest/1"
EXPECTED_REPO_FULL_NAME = "mickaellall116-cmyk/qf-data-archive"
REQUIRED_FIELDS = ["Open", "High", "Low", "Close", "Volume",
                   "Dividends", "Stock Splits"]
JOURNAL_REL = "attempt_journal.jsonl"
LEDGER_REL = "file_ledger.jsonl"
MARKER_REL = "INCOMPLETE_HOLD.json"


class HoldError(Exception):
    """Fail-closed abort carrying a stable machine-readable code."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class ThrottleError(Exception):
    """Transport signals HTTP 429 / throttle (a frozen fail-closed trigger)."""


class WriteOnceCollision(Exception):
    pass


# ---------------------------------------------------------------------------
# Primitives (r2-proven)
# ---------------------------------------------------------------------------
def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def archive_write(root, rel, data_bytes):
    """Atomic no-clobber publication: temp -> fsync -> os.link -> fsync dir."""
    final = os.path.join(root, rel)
    os.makedirs(os.path.dirname(final), exist_ok=True)
    tmp = final + f".tmp-{os.getpid()}"
    with open(tmp, "wb") as fh:
        fh.write(data_bytes)
        fh.flush()
        os.fsync(fh.fileno())
    try:
        os.link(tmp, final)
    except FileExistsError:
        os.unlink(tmp)
        raise WriteOnceCollision(rel)
    os.unlink(tmp)
    fsync_dir(os.path.dirname(final))
    return sha256_bytes(data_bytes)


def _append_jsonl(root, rel, record):
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, rel)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    fsync_dir(root)


def journal_attempt(root, symbol, index):
    """The attempt record is committed (fsync) BEFORE any request."""
    _append_jsonl(root, JOURNAL_REL,
                  {"event": "ATTEMPT", "symbol": symbol, "i": index})


def _read_jsonl(root, rel):
    path = os.path.join(root, rel)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def journaled_symbols(root):
    return {r["symbol"] for r in _read_jsonl(root, JOURNAL_REL)
            if r.get("event") == "ATTEMPT"}


def file_ledger(root):
    out = {}
    for r in _read_jsonl(root, LEDGER_REL):
        out[r["rel"]] = r["sha256"]
    return out


def reconcile(root, rel, symbol, ledger):
    """Restart state for one symbol (r2 semantics, ledger-backed hashes)."""
    final = os.path.join(root, rel)
    if os.path.exists(final):
        expected = ledger.get(rel)
        if expected is not None and sha256_file(final) == expected:
            return "SKIP_VERIFIED"
        return "HOLD:FINAL_MISMATCH"
    if symbol in journaled_symbols(root):
        return "ATTEMPT_CONSUMED_AMBIGUOUS"
    return "ELIGIBLE"


# ---------------------------------------------------------------------------
# Binding: manifest hash, frozen order, runtime pins — checked pre-transport
# ---------------------------------------------------------------------------
def load_and_verify_manifest(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    if sha256_bytes(raw) != EXPECTED_MANIFEST_SHA256:
        raise HoldError("HOLD:MANIFEST_DRIFT")
    man = json.loads(raw.decode("utf-8"))
    if man.get("schema") != EXPECTED_SCHEMA:
        raise HoldError("HOLD:MANIFEST_DRIFT")
    return man


def verify_order(man):
    """Frozen 52-request order/count: exact i sequence, unique symbols."""
    entries = sorted(man["request_order"], key=lambda e: e["i"])
    idx = [e["i"] for e in entries]
    symbols = [e["symbol"] for e in entries]
    if idx != list(range(1, len(entries) + 1)):
        raise HoldError("HOLD:ORDER_DRIFT")
    if len(entries) != int(man["call_budget"]["max_requests_total"]):
        raise HoldError("HOLD:ORDER_DRIFT")
    if len(set(symbols)) != len(symbols):
        raise HoldError("HOLD:ORDER_DRIFT")
    return entries


def probe_runtime():
    """Observe the live runtime WITHOUT importing the vendor client."""
    probe = {"python": platform.python_version()}
    for pkg in ("pandas", "numpy"):
        try:
            probe[pkg] = importlib.import_module(pkg).__version__
        except Exception:
            probe[pkg] = None
    try:
        probe["yfinance"] = importlib.metadata.version("yfinance")
    except Exception:
        probe["yfinance"] = None
    files = {}
    spec = importlib.util.find_spec("yfinance")
    if spec is not None and spec.origin:
        pkg_dir = os.path.dirname(spec.origin)
        for name in ("__init__.py", "multi.py", "ticker.py"):
            p = os.path.join(pkg_dir, name)
            files[name] = sha256_file(p)[:16] if os.path.exists(p) else None
    probe["yfinance_files_sha256_16"] = files
    return probe


def verify_runtime(man, probe):
    pins = man["runtime_pins"]
    for key in ("python", "pandas", "numpy", "yfinance"):
        if probe.get(key) != pins.get(key):
            raise HoldError("HOLD:RUNTIME_DRIFT")
    observed = probe.get("yfinance_files_sha256_16") or {}
    for name, prefix in pins["yfinance_files_sha256_16"].items():
        if observed.get(name) != prefix:
            raise HoldError("HOLD:RUNTIME_DRIFT")
    return True


# ---------------------------------------------------------------------------
# Shared limiter: exactly one instance governs every request start.
# ---------------------------------------------------------------------------
class SharedLimiter:
    def __init__(self, min_interval, now_fn, sleep_fn):
        self.min_interval = float(min_interval)
        self._now = now_fn
        self._sleep = sleep_fn
        self._last_start = None
        self.starts = []

    def wait(self):
        if self._last_start is not None:
            gap = self._now() - self._last_start
            if gap < self.min_interval:
                self._sleep(self.min_interval - gap)
        self._last_start = self._now()
        self.starts.append(self._last_start)


# ---------------------------------------------------------------------------
# Response validation — every frozen fail-closed trigger aborts the capture.
# `calendar` supplies expected sessions: sessions(kind) -> [(date, rows)].
# ---------------------------------------------------------------------------
def _expected_meta(entry):
    if entry["class"] == "crypto":
        return {"timezone": "UTC", "currency": "USD"}
    return {"timezone": "America/New_York", "currency": "USD"}


def validate_response(entry, frame, meta, calendar, man):
    symbol = entry["symbol"]
    if meta.get("symbol") != symbol:
        raise HoldError("HOLD:SCHEMA_DRIFT")
    for key, want in _expected_meta(entry).items():
        if meta.get(key) != want:
            raise HoldError("HOLD:META_DRIFT")
    if frame is None or len(frame) == 0:
        raise HoldError("HOLD:PARTIAL")
    if any(f not in frame.columns for f in REQUIRED_FIELDS):
        raise HoldError("HOLD:SCHEMA_DRIFT")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise HoldError("HOLD:INTEGRITY")
    bad = (frame["High"] < frame[["Open", "Close"]].max(axis=1)) | \
          (frame["Low"] > frame[["Open", "Close"]].min(axis=1)) | \
          (frame["Volume"] < 0)
    if bad.any():
        raise HoldError("HOLD:IMPOSSIBLE_OHLCV")
    ceilings = man["call_budget"]["ceilings"]
    if len(frame) > int(ceilings["rows_per_symbol"]):
        raise HoldError("HOLD:CEILING")
    kind = "crypto" if entry["class"] == "crypto" else "equity"
    counts = frame.index.normalize().value_counts()
    for date_str, expected in calendar.sessions(kind):
        actual = int(counts.get(pd.Timestamp(date_str,
                                             tz=frame.index.tz), 0))
        if actual != expected:
            raise HoldError("HOLD:PARTIAL")
    return True


def _serialize(frame):
    return frame.to_csv(index_label="Datetime").encode("utf-8")


def _actions_bytes(frame):
    act = frame[(frame["Dividends"] != 0) | (frame["Stock Splits"] != 0)]
    return act.to_csv(index_label="Datetime").encode("utf-8")


# ---------------------------------------------------------------------------
# Capture phase — local write-once archive only.
# ---------------------------------------------------------------------------
def run_capture(man, archive_root, capture_id, transport, calendar,
                limiter, now_fn, stamp_fn):
    cap_dir = os.path.join(archive_root, capture_id)
    os.makedirs(cap_dir, exist_ok=True)
    entries = verify_order(man)
    budget = man["call_budget"]
    ceilings = budget["ceilings"]
    t0 = now_fn()
    stats = {"requests": 0, "bytes_total": 0, "skipped_verified": 0}

    def abort(code):
        marker = {"status": "INCOMPLETE_HOLD", "code": code,
                  "capture_id": capture_id,
                  "requests_made": stats["requests"]}
        try:
            archive_write(cap_dir, MARKER_REL,
                          json.dumps(marker, sort_keys=True).encode())
        except WriteOnceCollision:
            _append_jsonl(cap_dir, JOURNAL_REL,
                          {"event": "ABORT_AGAIN", "code": code})
        return {"status": "INCOMPLETE_HOLD", "code": code, **stats}

    # Completed capture: verify and report; never re-request.
    if os.path.exists(os.path.join(cap_dir, "manifest.json")):
        sums = {}
        sums_path = os.path.join(cap_dir, "SHA256SUMS")
        if not os.path.exists(sums_path):
            return abort("HOLD:FINAL_MISMATCH")
        with open(sums_path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    h, rel = line.split(None, 1)
                    sums[rel.strip()] = h
        for rel, h in sums.items():
            p = os.path.join(cap_dir, rel)
            if not os.path.exists(p) or sha256_file(p) != h:
                return abort("HOLD:FINAL_MISMATCH")
        return {"status": "ALREADY_COMPLETE",
                "files_verified": len(sums), **stats}

    # Restart pre-scan: a consumed-but-unfulfilled attempt, or a final file
    # whose bytes do not match the ledger, blocks the whole capture before
    # any new request is made (no second attempt is ever issued).
    ledger = file_ledger(cap_dir)
    for entry in entries:
        state = reconcile(cap_dir, f"raw/{entry['symbol']}.csv",
                          entry["symbol"], ledger)
        if state == "ATTEMPT_CONSUMED_AMBIGUOUS":
            return abort("ATTEMPT_CONSUMED_AMBIGUOUS")
        if state == "HOLD:FINAL_MISMATCH":
            return abort("HOLD:FINAL_MISMATCH")
        if state == "SKIP_VERIFIED":
            stats["skipped_verified"] += 1

    params = man["request_params"]
    for entry in entries:
        symbol = entry["symbol"]
        rel = f"raw/{symbol}.csv"
        if reconcile(cap_dir, rel, symbol, file_ledger(cap_dir)) \
                == "SKIP_VERIFIED":
            continue
        if stats["requests"] >= int(budget["max_requests_total"]):
            return abort("HOLD:CEILING")
        if now_fn() - t0 > float(ceilings["wall_seconds_total"]):
            return abort("HOLD:CEILING")
        # Journal commits BEFORE the request; exactly one attempt.
        journal_attempt(cap_dir, symbol, entry["i"])
        limiter.wait()
        stats["requests"] += 1
        try:
            resp = transport(symbol, entry, params)
        except ThrottleError:
            return abort("HOLD:THROTTLED")
        frame, meta = resp["frame"], resp["meta"]
        try:
            validate_response(entry, frame, meta, calendar, man)
            raw_bytes = _serialize(frame)
            if len(raw_bytes) > int(ceilings["bytes_per_symbol"]):
                raise HoldError("HOLD:CEILING")
            if stats["bytes_total"] + len(raw_bytes) \
                    > int(ceilings["bytes_total"]):
                raise HoldError("HOLD:CEILING")
            h = archive_write(cap_dir, rel, raw_bytes)
            archive_write(cap_dir, f"actions/{symbol}.actions.csv",
                          _actions_bytes(frame))
            meta_doc = {"symbol": symbol, "i": entry["i"],
                        "class": entry["class"],
                        "params": {k: params[k] for k in
                                   ("interval", "auto_adjust", "prepost",
                                    "actions")},
                        "source": "yahoo/yfinance",
                        "acquisition_utc": stamp_fn(),
                        "raw_sha256": h}
            archive_write(cap_dir, f"meta/{symbol}.request.json",
                          json.dumps(meta_doc, sort_keys=True).encode())
        except WriteOnceCollision:
            return abort("HOLD:WRITE_ONCE_COLLISION")
        except HoldError as exc:
            return abort(exc.code)
        _append_jsonl(cap_dir, LEDGER_REL,
                      {"rel": rel, "sha256": h, "symbol": symbol})
        stats["bytes_total"] += len(raw_bytes)

    # Completion: pin every file, then the archive manifest.
    files = {}
    for sub in ("raw", "actions", "meta"):
        d = os.path.join(cap_dir, sub)
        for name in sorted(os.listdir(d)):
            rel = f"{sub}/{name}"
            files[rel] = sha256_file(os.path.join(cap_dir, rel))
    sums_text = "".join(f"{files[rel]}  {rel}\n" for rel in sorted(files))
    archive_write(cap_dir, "SHA256SUMS", sums_text.encode())
    archive_doc = {"capture_id": capture_id, "status": "COMPLETE",
                   "capture_manifest_sha256": EXPECTED_MANIFEST_SHA256,
                   "symbols": len(entries), "files": files}
    archive_write(cap_dir, "manifest.json",
                  json.dumps(archive_doc, sort_keys=True).encode())
    return {"status": "COMPLETE", "files": len(files) + 2, **stats}


# ---------------------------------------------------------------------------
# Publication phase — SEPARATE from capture. In this preflight build only a
# local fake remote (kind == "FAKE_LOCAL") can ever be exercised; there is
# deliberately no real-remote implementation in this file.
# ---------------------------------------------------------------------------
def publish_capture(cap_dir, capture_id, remote,
                    expected_repo=EXPECTED_REPO_FULL_NAME):
    if getattr(remote, "kind", None) != "FAKE_LOCAL":
        raise HoldError("HOLD:REAL_REMOTE_FORBIDDEN")
    if remote.full_name() != expected_repo:
        raise HoldError("HOLD:TARGET_NAME_DRIFT")
    if remote.visibility() != "private":
        raise HoldError("HOLD:VISIBILITY_REFUSAL")
    base = f"captures/{capture_id}"
    if remote.has_prefix(base):
        raise HoldError("HOLD:CAPTURE_EXISTS")
    rels = []
    for sub in ("raw", "actions", "meta"):
        d = os.path.join(cap_dir, sub)
        for name in sorted(os.listdir(d)):
            rels.append(f"{sub}/{name}")
    rels += ["SHA256SUMS", "manifest.json"]
    uploaded = {}
    for rel in sorted(rels):
        with open(os.path.join(cap_dir, rel), "rb") as fh:
            data = fh.read()
        remote.put_file(f"{base}/{rel}", data)
        uploaded[rel] = sha256_bytes(data)
    verified = 0
    for rel, h in uploaded.items():
        got = remote.get_file(f"{base}/{rel}")
        if got is None or sha256_bytes(got) != h:
            raise HoldError("HOLD:REFETCH_MISMATCH")
        verified += 1
    return {"status": "PUBLISHED_FAKE", "commit_sha": remote.head_sha(),
            "objects": len(uploaded), "verified": verified}


# ---------------------------------------------------------------------------
# CLI — binds no transport and no remote: verification only. A real capture
# requires the separately authorized execution task, which injects both.
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--archive-root")
    ap.add_argument("--capture-id")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args(argv)
    try:
        man = load_and_verify_manifest(args.manifest)
        entries = verify_order(man)
        verify_runtime(man, probe_runtime())
    except HoldError as exc:
        print(json.dumps({"status": exc.code}, sort_keys=True))
        return 3
    if args.execute or args.publish:
        print(json.dumps(
            {"status": "HOLD:EXECUTION_NOT_AUTHORIZED_IN_PREFLIGHT",
             "detail": "preflight build binds no transport/remote; "
                       "acquisition is a separate explicit gate"},
            sort_keys=True))
        return 3
    print(json.dumps({"status": "BINDINGS_VERIFIED",
                      "symbols": len(entries),
                      "manifest_sha256": EXPECTED_MANIFEST_SHA256},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
