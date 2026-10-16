"""Clean capture executor for QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-OFFLINE-20261016-19 r1.

Written fresh against the rev3 candidate (SHA-256 pinned below). Stages ONLY the
156 payload members (raw/<SYMBOL>.csv, actions/<SYMBOL>.actions.csv,
meta/<SYMBOL>.request.json) under a membership-pure capture root. It writes NO
manifest.json / SHA256SUMS (publisher bookkeeping), fabricates NO validation
pins, runs NO qualification gates, publishes nothing and creates no anchor.
Its output is staged bytes only (spec sec.6, separation of authority).

Control state is separated: the acquisition journal lives ONLY at
<base>/<capture_id>.control/acquisition_attempt_journal.qfj2, never under the
payload root. The journal uses authenticated QFJ2-style framing (header digest
verified before the declared length is used); any torn/corrupt/conflicting
journal state is a named HOLD -- never blind repair, never a re-request.

Transport and clock are injected. This module performs no network I/O and
imports nothing outside the standard library.
"""
import hashlib
import json
import os
import re
import struct

CANDIDATE_SHA256 = "3d3d4ef51e54f9e6d9bce6119673ddd7e41825049d13c58bead3b19bf4021248"
TASK_ID = "QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-OFFLINE-20261016-19 r1"

# Adjudicated budget literals (spec -19 sec.4); cross-checked against the
# candidate at load -- any disagreement is HOLD:CONSTANT_DRIFT.
SPEC_BYTES_PER_SYMBOL = 33554432          # 32 MiB
SPEC_PAYLOAD_BUDGET = 67076700
SPEC_ROWS_PER_SYMBOL = 20000
SPEC_WALL_SECONDS = 1800
SPEC_MIN_START_GAP = 1.0

_CAPTURE_ID_RE = re.compile(r"\A[A-Z0-9]+(?:-[A-Z0-9]+)*\Z")
_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")

# ---- journal framing (QFJ2-compatible, implemented fresh) ----
_FRAME_MAGIC = b"QFJ2"
_FRAME_VERSION = 2
_FRAME_CORE = 21          # magic(4) version(1) seq(8) len(4) complement(4)
_FRAME_HEADER = 53        # core + sha256(core)
_FRAME_TAG = 32
_MAX_FRAME_PAYLOAD = 1048576


class HoldError(Exception):
    def __init__(self, code, detail=""):
        super().__init__(code + (": " + detail if detail else ""))
        self.code = code
        self.detail = detail


class TransportFailure(Exception):
    """Raised by the injected transport. status: int HTTP-like code or None."""

    def __init__(self, status=None, message=""):
        super().__init__(message or f"transport failure status={status}")
        self.status = status


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _sha256(b):
    return hashlib.sha256(b).hexdigest()


def validate_capture_id(capture_id):
    if (not isinstance(capture_id, str) or not (8 <= len(capture_id) <= 64)
            or not _CAPTURE_ID_RE.match(capture_id)):
        raise HoldError("HOLD:CAPTURE_ID_INVALID", repr(capture_id))


# ---------------------------------------------------------------- journal
def _frame_bytes(record, seq):
    rec = dict(record)
    rec["seq"] = seq
    payload = _canonical(rec)
    if len(payload) > _MAX_FRAME_PAYLOAD:
        raise HoldError("HOLD:JOURNAL_CORRUPT", "frame payload over bound")
    core = (_FRAME_MAGIC + bytes([_FRAME_VERSION]) + struct.pack(">Q", seq)
            + struct.pack(">I", len(payload))
            + struct.pack(">I", (~len(payload)) & 0xFFFFFFFF))
    header = core + hashlib.sha256(core).digest()
    return header + payload + hashlib.sha256(header + payload).digest()


def _journal_parse(data):
    """Strict parse. Returns list of records. Torn tail -> HOLD:JOURNAL_TORN;
    any authenticated-framing violation -> HOLD:JOURNAL_CORRUPT."""
    records = []
    off = 0
    seq = 0
    n = len(data)
    while off < n:
        if n - off < _FRAME_HEADER:
            raise HoldError("HOLD:JOURNAL_TORN", f"partial header at frame {seq}")
        header = data[off:off + _FRAME_HEADER]
        core = header[:_FRAME_CORE]
        if core[:4] != _FRAME_MAGIC or core[4] != _FRAME_VERSION:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"bad magic/version frame {seq}")
        fseq, length, comp = struct.unpack(">QII", core[5:21])
        if fseq != seq:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"seq gap frame {seq}")
        if hashlib.sha256(core).digest() != header[_FRAME_CORE:]:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"header digest frame {seq}")
        if length > _MAX_FRAME_PAYLOAD or comp != (~length) & 0xFFFFFFFF:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"length/complement frame {seq}")
        end = off + _FRAME_HEADER + length + _FRAME_TAG
        if end > n:
            raise HoldError("HOLD:JOURNAL_TORN", f"partial frame {seq}")
        payload = data[off + _FRAME_HEADER:off + _FRAME_HEADER + length]
        tag = data[off + _FRAME_HEADER + length:end]
        if hashlib.sha256(header + payload).digest() != tag:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"frame tag frame {seq}")
        try:
            rec = json.loads(payload.decode())
        except Exception:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"frame JSON {seq}")
        if not isinstance(rec, dict) or rec.get("seq") != seq:
            raise HoldError("HOLD:JOURNAL_CORRUPT", f"frame body seq {seq}")
        records.append(rec)
        off = end
        seq += 1
    return records


def _journal_read(path):
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        return _journal_parse(f.read())


def _journal_append(path, record, seq):
    frame = _frame_bytes(record, seq)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(frame)
        while view:
            w = os.write(fd, view)
            view = view[w:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _journal_state(records):
    """Per-symbol state from journal records; conflicts -> HOLD:JOURNAL_CONFLICT."""
    attempts, completes = {}, {}
    for rec in records:
        kind, sym = rec.get("type"), rec.get("symbol")
        if kind == "ATTEMPT":
            if sym in attempts or sym in completes:
                raise HoldError("HOLD:JOURNAL_CONFLICT", f"duplicate ATTEMPT {sym}")
            attempts[sym] = rec
        elif kind == "COMPLETE":
            if sym not in attempts:
                raise HoldError("HOLD:JOURNAL_CONFLICT", f"COMPLETE without ATTEMPT {sym}")
            if sym in completes:
                raise HoldError("HOLD:JOURNAL_CONFLICT", f"duplicate COMPLETE {sym}")
            completes[sym] = rec
        else:
            raise HoldError("HOLD:JOURNAL_CONFLICT", f"unknown record {kind!r}")
    return attempts, completes


# ---------------------------------------------------------------- plan
def load_plan(candidate_path):
    with open(candidate_path, "rb") as f:
        raw = f.read()
    if _sha256(raw) != CANDIDATE_SHA256:
        raise HoldError("HOLD:CANDIDATE_PIN", "candidate SHA-256 mismatch")
    cand = json.loads(raw.decode())
    order = cand["request_order"]
    if len(order) != 52 or cand["call_budget"]["max_requests_total"] != 52:
        raise HoldError("HOLD:CONSTANT_DRIFT", "request count != 52")
    ceil = cand["call_budget"]["ceilings"]
    got = (ceil["bytes_per_symbol"], ceil["payload_budget_bytes"],
           ceil["rows_per_symbol"], ceil["wall_seconds_total"])
    want = (SPEC_BYTES_PER_SYMBOL, SPEC_PAYLOAD_BUDGET,
            SPEC_ROWS_PER_SYMBOL, SPEC_WALL_SECONDS)
    if got != want:
        raise HoldError("HOLD:CONSTANT_DRIFT", f"ceilings {got} != spec {want}")
    symbols = [e["symbol"] for e in order]
    if len(set(symbols)) != 52:
        raise HoldError("HOLD:CONSTANT_DRIFT", "duplicate symbol in order")
    params = cand["request_params"]
    plan = []
    for e in order:
        sym = e["symbol"]
        plan.append({
            "symbol": sym, "class": e["class"], "session": e["session"],
            "interval": params["interval"], "auto_adjust": params["auto_adjust"],
            "prepost": params["prepost"], "actions": params["actions"],
            "required_fields": list(params["required_fields"]),
            "date_policy": params["date_policy"]["form"],
            "start_rule": params["date_policy"]["start"],
            "end_rule": params["date_policy"]["end"],
            "rels": [f"raw/{sym}.csv", f"actions/{sym}.actions.csv",
                     f"meta/{sym}.request.json"],
        })
    return plan


# ---------------------------------------------------------------- fs helpers
def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_once(root, rel, data):
    """Write data to root/rel via temp + atomic rename; refuse overwrite."""
    final = os.path.join(root, rel)
    if os.path.lexists(final):
        raise HoldError("HOLD:FINAL_MISMATCH", f"final path exists: {rel}")
    tmp = os.path.join(os.path.dirname(final),
                       "." + os.path.basename(final) + ".tmp")
    if os.path.lexists(tmp):
        os.unlink(tmp)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(data)
        while view:
            w = os.write(fd, view)
            view = view[w:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.rename(tmp, final)
    _fsync_dir(os.path.dirname(final))


def _census_root(root, plan):
    """Root may contain only raw/actions/meta dirs; no symlinks/non-regular."""
    allowed_dirs = {"raw", "actions", "meta"}
    expected = {rel for p in plan for rel in p["rels"]}
    seen = set()
    for entry in sorted(os.listdir(root)):
        p = os.path.join(root, entry)
        if os.path.islink(p) or not os.path.isdir(p) or entry not in allowed_dirs:
            raise HoldError("HOLD:MEMBERSHIP", f"stray capture-root entry {entry!r}")
        for name in sorted(os.listdir(p)):
            fp = os.path.join(p, name)
            if os.path.islink(fp) or not os.path.isfile(fp):
                raise HoldError("HOLD:PATH_TYPE", f"non-regular file {entry}/{name}")
            seen.add(f"{entry}/{name}")
    extra = seen - expected
    if extra:
        raise HoldError("HOLD:MEMBERSHIP", f"unjournaled/extra files {sorted(extra)}")
    return seen


# ---------------------------------------------------------------- serialization
def _fmt_num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise HoldError("HOLD:SCHEMA_DRIFT", f"non-numeric bar value {v!r}")
    return repr(v)


def _serialize(req, resp, clock_now_iso):
    """Validate the injected response; return (raw_csv, actions_csv, meta_json)."""
    if not isinstance(resp, dict):
        raise HoldError("HOLD:SHAPE_DRIFT", "response not an object")
    if resp.get("symbol") != req["symbol"]:
        raise HoldError("HOLD:META_DRIFT", "symbol echo mismatch (unknown symbol)")
    meta_in = resp.get("meta")
    if not isinstance(meta_in, dict) or meta_in.get("session") != req["session"] \
            or meta_in.get("class") != req["class"]:
        raise HoldError("HOLD:META_DRIFT", "session/class echo mismatch")
    for k in ("exchange", "timezone", "currency", "source"):
        if not isinstance(meta_in.get(k), str) or not meta_in[k]:
            raise HoldError("HOLD:META_DRIFT", f"meta missing {k}")
    bars = resp.get("bars")
    if not isinstance(bars, list) or not bars:
        raise HoldError("HOLD:SHAPE_DRIFT", "bars missing/empty")
    fields = req["required_fields"]
    raw_lines = ["Datetime,Open,High,Low,Close,Volume"]
    act_lines = ["Datetime,Dividends,Stock Splits"]
    for row in bars:
        if not isinstance(row, dict) or set(row.keys()) != set(fields) | {"Datetime"}:
            raise HoldError("HOLD:SCHEMA_DRIFT",
                            f"row fields {sorted(row.keys()) if isinstance(row, dict) else row!r}")
        ts = row["Datetime"]
        if not isinstance(ts, str) or not ts:
            raise HoldError("HOLD:SCHEMA_DRIFT", "bad Datetime")
        raw_lines.append(",".join([ts] + [_fmt_num(row[f]) for f in
                                          ("Open", "High", "Low", "Close", "Volume")]))
        act_lines.append(",".join([ts, _fmt_num(row["Dividends"]),
                                   _fmt_num(row["Stock Splits"])]))
    if resp.get("end_covered") is not True:
        raise HoldError("HOLD:PARTIAL_RESPONSE", "end-of-window not covered")
    rows = len(bars)
    if rows > SPEC_ROWS_PER_SYMBOL:
        raise HoldError("HOLD:ROW_CEILING", f"{rows} rows > {SPEC_ROWS_PER_SYMBOL}")
    meta = {
        "symbol": req["symbol"], "class": req["class"], "session": req["session"],
        "interval": req["interval"], "auto_adjust": req["auto_adjust"],
        "prepost": req["prepost"], "actions": req["actions"],
        "required_fields": req["required_fields"],
        "date_policy": req["date_policy"], "start_rule": req["start_rule"],
        "end_rule": req["end_rule"], "rows": rows,
        "exchange": meta_in["exchange"], "timezone": meta_in["timezone"],
        "currency": meta_in["currency"], "source": meta_in["source"],
        "acquisition_utc": clock_now_iso,
    }
    return ("\n".join(raw_lines) + "\n").encode(), \
           ("\n".join(act_lines) + "\n").encode(), \
           _canonical(meta) + b"\n"


# ---------------------------------------------------------------- limiter
class Limiter:
    """One process-wide limiter: >= gap seconds between request starts."""

    def __init__(self, clock, gap=SPEC_MIN_START_GAP):
        self.clock = clock
        self.gap = gap
        self._last_start = None

    def wait(self):
        now = self.clock.now()
        if self._last_start is not None:
            delta = now - self._last_start
            if delta < self.gap:
                self.clock.sleep(self.gap - delta)
                now = self.clock.now()
        self._last_start = now
        return now


# ---------------------------------------------------------------- executor
def run_capture(candidate_path, base_dir, capture_id, transport, clock, limiter):
    """Stage the 156 payloads. Returns a result dict; raises HoldError for
    named HOLD states that precede any staging decision (journal/path/ID).
    Transport failures and ceiling breaches end the run as INCOMPLETE_HOLD
    (returned, with the attempt consumed in the journal)."""
    plan = load_plan(candidate_path)
    validate_capture_id(capture_id)
    root = os.path.join(base_dir, capture_id)
    control = os.path.join(base_dir, capture_id + ".control")
    # case-collision: a sibling differing only by case is an alias risk
    if os.path.isdir(base_dir):
        for entry in os.listdir(base_dir):
            if entry != capture_id and entry.lower() == capture_id.lower():
                raise HoldError("HOLD:CAPTURE_ID_INVALID", f"case collision {entry!r}")
            if entry != capture_id + ".control" and \
                    entry.lower() == (capture_id + ".control").lower():
                raise HoldError("HOLD:CAPTURE_ID_INVALID", f"case collision {entry!r}")
    for p in (root, control):
        if os.path.islink(p):
            raise HoldError("HOLD:PATH_TYPE", f"symlink at {p}")
        if os.path.exists(p) and not os.path.isdir(p):
            raise HoldError("HOLD:PATH_TYPE", f"non-directory at {p}")
    os.makedirs(root, exist_ok=True)
    os.makedirs(control, exist_ok=True)
    for d in ("raw", "actions", "meta"):
        dp = os.path.join(root, d)
        if os.path.islink(dp):
            raise HoldError("HOLD:PATH_TYPE", f"symlink at {dp}")
        os.makedirs(dp, exist_ok=True)
    journal_path = os.path.join(control, "acquisition_attempt_journal.qfj2")
    if os.path.islink(journal_path):
        raise HoldError("HOLD:PATH_TYPE", "journal is a symlink")
    records = _journal_read(journal_path)          # torn/corrupt -> named HOLD
    attempts, completes = _journal_state(records)  # conflicts -> named HOLD
    on_disk = _census_root(root, plan)

    result = {"task": TASK_ID, "capture_id": capture_id, "status": None,
              "code": None, "calls_this_run": 0, "states": {},
              "payload_bytes": 0}
    seq = len(records)
    t0 = clock.now()

    # ---- restart reconciliation before any new attempt ----
    for p in plan:
        sym = p["symbol"]
        if sym in completes:
            rec = completes[sym]
            bound = rec.get("files")
            ok = isinstance(bound, dict) and set(bound) == set(p["rels"])
            if ok:
                for rel in p["rels"]:
                    fp = os.path.join(root, rel)
                    if rel not in on_disk or _sha256(open(fp, "rb").read()) != bound[rel]:
                        ok = False
                        break
            if not ok:
                raise HoldError("HOLD:FINAL_MISMATCH",
                                f"completed triplet missing/altered: {sym}")
            result["states"][sym] = "SKIP_VERIFIED"
            result["payload_bytes"] += rec.get("bytes", 0)
        elif sym in attempts:
            raise HoldError("HOLD:ATTEMPT_CONSUMED_AMBIGUOUS",
                            f"attempt without COMPLETE: {sym}")
        else:
            stray = [r for r in p["rels"] if r in on_disk]
            if stray:
                raise HoldError("HOLD:FINAL_MISMATCH",
                                f"files without journal records: {sym} {stray}")
            result["states"][sym] = "ELIGIBLE"

    # ---- acquisition loop ----
    for p in plan:
        sym = p["symbol"]
        if result["states"][sym] != "ELIGIBLE":
            continue
        if clock.now() - t0 > SPEC_WALL_SECONDS:
            result.update(status="INCOMPLETE_HOLD", code="HOLD:WALL_CEILING")
            return result
        limiter.wait()
        _journal_append(journal_path, {
            "type": "ATTEMPT", "symbol": sym, "rels": p["rels"],
            "clock": clock.now()}, seq)
        seq += 1
        result["calls_this_run"] += 1
        req = {k: p[k] for k in ("symbol", "class", "session", "interval",
                                 "auto_adjust", "prepost", "actions",
                                 "required_fields")}
        try:
            resp = transport(req)
        except TransportFailure as e:
            code = "HOLD:THROTTLE_429" if e.status == 429 else "HOLD:TRANSPORT"
            result.update(status="INCOMPLETE_HOLD", code=code)
            result["states"][sym] = "ATTEMPT_CONSUMED"
            return result
        except Exception:
            result.update(status="INCOMPLETE_HOLD", code="HOLD:TRANSPORT")
            result["states"][sym] = "ATTEMPT_CONSUMED"
            return result
        if isinstance(resp, dict) and resp.get("status") not in (None, 200):
            code = "HOLD:THROTTLE_429" if resp.get("status") == 429 else "HOLD:TRANSPORT"
            result.update(status="INCOMPLETE_HOLD", code=code)
            result["states"][sym] = "ATTEMPT_CONSUMED"
            return result
        try:
            raw_b, act_b, meta_b = _serialize(p, resp, clock.iso())
            triplet = {p["rels"][0]: raw_b, p["rels"][1]: act_b, p["rels"][2]: meta_b}
            sym_bytes = sum(len(b) for b in triplet.values())
            if sym_bytes > SPEC_BYTES_PER_SYMBOL:
                raise HoldError("HOLD:SYMBOL_CEILING",
                                f"{sym} {sym_bytes} > {SPEC_BYTES_PER_SYMBOL}")
            if result["payload_bytes"] + sym_bytes > SPEC_PAYLOAD_BUDGET:
                raise HoldError("HOLD:TOTAL_CEILING",
                                f"payload budget {SPEC_PAYLOAD_BUDGET} would breach")
            if clock.now() - t0 > SPEC_WALL_SECONDS:
                raise HoldError("HOLD:WALL_CEILING", "wall limit before COMPLETE")
        except HoldError as e:
            result.update(status="INCOMPLETE_HOLD", code=e.code)
            result["states"][sym] = "ATTEMPT_CONSUMED"
            return result
        hashes = {}
        for rel in p["rels"]:
            _write_once(root, rel, triplet[rel])
            hashes[rel] = _sha256(triplet[rel])
        _journal_append(journal_path, {
            "type": "COMPLETE", "symbol": sym, "files": hashes,
            "bytes": sym_bytes, "clock": clock.now()}, seq)
        seq += 1
        result["payload_bytes"] += sym_bytes
        result["states"][sym] = "COMPLETE"

    done = all(result["states"][p["symbol"]] in ("COMPLETE", "SKIP_VERIFIED")
               for p in plan)
    result["status"] = "COMPLETE" if done else "INCOMPLETE_HOLD"
    if done:
        result["code"] = "OK"
    return result
