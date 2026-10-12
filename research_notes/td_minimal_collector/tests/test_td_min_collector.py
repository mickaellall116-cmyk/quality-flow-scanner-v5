#!/usr/bin/env python3
"""
Synthetic tests for QF-TD-MINIMAL-COLLECTOR-20261012-01 r1 (spec point 5).
Zero vendor calls: every dispatch goes through an injected fake transport.
Run: python3 tests/test_td_min_collector.py
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG.parent / "pilot_harness"))

import td_min_collector as C  # noqa: E402
from rate_limiter import RollingCreditLimiter  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")


def make_req(rid="REQ-TST-01", symbol="AAPL", interval="1h",
             start="2026-10-05T00:00:00", end="2026-10-05T23:59:59",
             outputsize=5000, leg="PAR"):
    from datetime import date
    bound = ((date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days + 1) * C.BARS_PER_DAY[interval]
    return {"request_id": rid, "symbol": symbol, "interval": interval,
            "start_date": start, "end_date": end, "timezone": "America/New_York",
            "outputsize": outputsize, "order": "ASC", "adjust": "splits",
            "leg": leg, "day": "D0", "output_name": f"{rid}.json",
            "max_attempts": 1, "expected_credits": 1, "credit_weight": 1,
            "pagination": False, "one_response_bound_bars": bound,
            "identity": f"{symbol}|/time_series|{interval}|{start}|{end}|America/New_York|adjust=splits"}


def make_manifest(reqs):
    return {"endpoint": C.ENDPOINT, "requests": reqs}


def valid_body(symbol="AAPL", interval="1h"):
    vals = []
    for i, hh in enumerate(["09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"]):
        vals.append({"datetime": f"2026-10-05 {hh}:00", "open": "100.0", "high": "101.0",
                     "low": "99.0", "close": "100.5", "volume": "1000"})
    return json.dumps({"meta": {"symbol": symbol, "interval": interval},
                       "values": vals, "status": "ok"}).encode()


def fresh_collector(tmp, reqs, transport, limiter=None):
    man = make_manifest(reqs)
    errs = C.validate_manifest(man)
    assert not errs, errs
    lim = limiter or RollingCreditLimiter(8, 800, state_path=Path(tmp) / "ledger.json")
    return C.Collector(Path(tmp) / "state", man, lim, transport=transport)


class Counter:
    def __init__(self, fn):
        self.fn, self.n = fn, 0

    def __call__(self, req):
        self.n += 1
        return self.fn(req)


# --- 1. valid completion + reuse -------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    t = Counter(lambda req: (200, valid_body()))
    col = fresh_collector(tmp, [make_req()], t)
    s1 = col.run()
    col2 = fresh_collector(tmp, [make_req()], t)  # restart, same state dir
    s2 = col2.run()
    ev = [json.loads(l)["event"] for l in (Path(tmp) / "state" / "lifecycle.jsonl").read_text().splitlines()]
    check("valid completion", s1["outcome"] == "COMPLETE" and s1["completed"] == 1, str(s1))
    check("reuse after restart: no new dispatch, no new credit",
          s2["reused"] == 1 and t.n == 1 and col2._state["attempts"] == 1
          and col2._state["credit_reservations"] == 1, str(s2))
    check("construction gate: CONSTRUCTION_HOLD recorded (semantics INSUFFICIENT)",
          "CONSTRUCTION_HOLD" in ev, ",".join(ev))

# --- 2. no-overwrite / foreign receipt --------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    t = Counter(lambda req: (200, valid_body()))
    col = fresh_collector(tmp, [make_req()], t)
    (col.receipts / "REQ-TST-01.json").write_bytes(b'{"meta":{},"values":[],"status":"ok"}')
    s = col.run()
    check("foreign receipt (no RECEIVED record) -> HOLD, zero dispatch",
          s["outcome"].startswith("HOLD") and t.n == 0, s["outcome"])
    check("foreign receipt bytes untouched (no overwrite)",
          (col.receipts / "REQ-TST-01.json").read_bytes().startswith(b'{"meta":{}'), "")

# --- 3. stale receipt (hash mismatch) ---------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    t = Counter(lambda req: (200, valid_body()))
    col = fresh_collector(tmp, [make_req()], t)
    col.run()
    p = col.receipts / "REQ-TST-01.json"
    p.write_bytes(p.read_bytes() + b" ")
    col2 = fresh_collector(tmp, [make_req()], t)
    s = col2.run()
    check("stale/corrupt receipt (hash mismatch) -> HOLD, no re-dispatch",
          s["outcome"].startswith("HOLD") and t.n == 1, s["outcome"])

# --- 4. malformed receipt -----------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    t = Counter(lambda req: (200, valid_body()))
    col = fresh_collector(tmp, [make_req()], t)
    col.run()
    import hashlib
    bad = b"not json at all"
    # forge a RECEIVED record matching the malformed bytes' hash
    col._emit("RECEIVED", "REQ-TST-01", sha256=hashlib.sha256(bad).hexdigest(), bytes=len(bad))
    (col.receipts / "REQ-TST-01.json").write_bytes(bad)
    col2 = fresh_collector(tmp, [make_req()], Counter(lambda req: (200, valid_body())))
    s = col2.run()
    check("malformed receipt (unparseable) -> HOLD", s["outcome"].startswith("HOLD"), s["outcome"])

# --- 5. crash after STARTED ---------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    t = Counter(lambda req: (200, valid_body()))
    col = fresh_collector(tmp, [make_req()], t)
    col._emit("STARTED", "REQ-TST-01", attempt=1)  # crash: no receipt follows
    col2 = fresh_collector(tmp, [make_req()], t)
    s = col2.run()
    check("started-without-receipt after crash -> AMBIGUOUS/HOLD, never auto-recalled",
          s["outcome"].startswith("HOLD") and "AMBIGUOUS" in s["outcome"] and t.n == 0, s["outcome"])

# --- 6. persistent terminal error across restart ------------------------------
with tempfile.TemporaryDirectory() as tmp:
    t = Counter(lambda req: (500, b'{"status":"error","message":"boom"}'))
    col = fresh_collector(tmp, [make_req()], t)
    s1 = col.run()
    col2 = fresh_collector(tmp, [make_req()], t)
    s2 = col2.run()
    check("HTTP 500 -> terminal HOLD", s1["outcome"].startswith("HOLD"), s1["outcome"])
    check("HOLD persists across restart, no second attempt",
          s2["outcome"].startswith("HOLD") and t.n == 1, s2["outcome"])
    check("rejected payload preserved (bytes + hash)",
          (col.receipts / "REQ-TST-01.rejected.bin").read_bytes() == b'{"status":"error","message":"boom"}', "")

# --- 7. API-level + schema failures -------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    t = Counter(lambda req: (200, b'{"status":"error","code":429,"message":"limit"}'))
    s = fresh_collector(tmp, [make_req()], t).run()
    check("API status=error payload -> HOLD", s["outcome"].startswith("HOLD"), s["outcome"])
with tempfile.TemporaryDirectory() as tmp:
    body = json.dumps({"meta": {"symbol": "MSFT", "interval": "1h"},
                       "values": [{"datetime": "2026-10-05 09:30:00", "open": "1", "high": "1",
                                   "low": "1", "close": "1", "volume": "1"}], "status": "ok"}).encode()
    s = fresh_collector(tmp, [make_req()], Counter(lambda req: (200, body))).run()
    check("meta symbol mismatch -> HOLD (identity binding)", s["outcome"].startswith("HOLD"), s["outcome"])
with tempfile.TemporaryDirectory() as tmp:
    body = json.dumps({"meta": {"symbol": "AAPL", "interval": "1h"}, "status": "ok"}).encode()
    s = fresh_collector(tmp, [make_req()], Counter(lambda req: (200, body))).run()
    check("missing values -> HOLD (incomplete coverage)", s["outcome"].startswith("HOLD"), s["outcome"])

# --- 8. output-cap uncertainty (truncation) ------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    req = make_req(outputsize=7)  # bound is 7: a full page is indistinguishable from truncation
    s = fresh_collector(tmp, [req], Counter(lambda r: (200, valid_body()))).run()
    check("rows == outputsize -> HOLD (output-cap uncertainty, no pagination)",
          s["outcome"].startswith("HOLD") and "output-cap" in s["outcome"], s["outcome"])

# --- 9. limiter refusal ----------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    lim = RollingCreditLimiter(8, 800, state_path=Path(tmp) / "ledger.json")
    for _ in range(8):
        assert lim.try_acquire(1, label="pre-spend")
    t = Counter(lambda req: (200, valid_body()))
    col = fresh_collector(tmp, [make_req()], t, limiter=lim)
    s = col.run()
    check("limiter refusal -> REFUSED, zero attempts recorded",
          s["outcome"].startswith("REFUSED") and t.n == 0 and col._state["attempts"] == 0, s["outcome"])

# --- 10. invalid manifest ---------------------------------------------------------
bad = make_req(); bad["max_attempts"] = 3
check("invalid manifest: retry present rejected", len(C.validate_manifest(make_manifest([bad]))) > 0)
bad2 = make_req(); bad2["leg"] = "REV7"
check("invalid manifest: REV7 leg rejected", len(C.validate_manifest(make_manifest([bad2]))) > 0)
bad3 = make_req(); bad3["one_response_bound_bars"] = 99999
check("invalid manifest: bound/outputsize violation rejected", len(C.validate_manifest(make_manifest([bad3]))) > 0)
real = json.loads((PKG / "manifest_reduced.json").read_text())
check("shipped reduced manifest validates clean", C.validate_manifest(real) == [],
      str(C.validate_manifest(real))[:120])
check("shipped manifest: 51 requests, no REV/pagination/retry",
          len(real["requests"]) == 51 and all(r["max_attempts"] == 1 and not r["pagination"] for r in real["requests"]))

# --- 11. prerequisites --------------------------------------------------------------
fails = C.check_prerequisites(real, PKG / "prerequisites.json")
check("prerequisites pass on shipped evidence (sources pinned + entitlement/retention)",
      fails == [], "; ".join(fails)[:160])
fails2 = C.check_prerequisites(real, PKG / "does_not_exist.json")
check("missing prerequisites file -> dispatch blocked", len(fails2) > 0)

# --- 12. session / as-of boundary via the accepted validation path -------------------
import pandas as pd  # noqa: E402
from validate_input import validate, ValidationError  # noqa: E402

def bars_df(day="2026-10-05"):
    rows = [{"datetime": f"{day} {hh}:00", "open": 100.0, "high": 101.0, "low": 99.0,
             "close": 100.5, "volume": 1000}
            for hh in ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"]]
    df = pd.DataFrame(rows)
    df.index = pd.to_datetime(df["datetime"]).dt.tz_localize("America/New_York")
    return df

try:
    validate(bars_df(), "AAPL", "2026-10-05", "2026-10-05",
             as_of=pd.Timestamp("2026-10-06T00:00:00").tz_localize("America/New_York"))
    ok = True
except Exception:
    ok = False
check("session boundary: complete regular session validates (accepted path)", ok)

try:
    validate(bars_df("2026-10-06"), "AAPL", "2026-10-05", "2026-10-06",
             as_of=pd.Timestamp("2026-10-06T00:00:00").tz_localize("America/New_York"))
    ok = False
except ValidationError:
    ok = True
check("as-of boundary: bars after as_of rejected (V11, never silently dropped)", ok)

# --- 13. zero-call guarantee -----------------------------------------------------------
import td_min_collector as _c  # noqa: E402
src = Path(_c.__file__).read_text()
check("zero-call build: no HTTP client usage in collector source",
          all(s not in src for s in ("import urllib", "import requests",
                                      "http.client", "import socket",
                                      "urlopen")), "")

print()
n_pass = sum(1 for _, ok, _ in RESULTS if ok)
print(f"{n_pass}/{len(RESULTS)} synthetic tests passed")
sys.exit(0 if n_pass == len(RESULTS) else 1)
