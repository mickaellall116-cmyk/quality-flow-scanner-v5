#!/usr/bin/env python3
"""Wrapper-specific synthetic fixtures W01-W10 for pilot_acquire.py.

Task QF-TD-PILOT-READINESS-R2-20261010-04. Bounded: one pass, no
network, no vendor calls, no credits spent against any real account.
Fake transport / clock / sleeper throughout. This does NOT reopen
fd03906: no existing harness fixture is touched.
"""

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from pilot_acquire import (  # noqa: E402
    AcquisitionWrapper,
    RequestSpec,
    Transport,
    scrub,
)
from rate_limiter import RollingCreditLimiter, FakeWallClock  # noqa: E402


def good_body(symbol="AAPL"):
    return json.dumps({
        "meta": {"symbol": symbol, "interval": "1h"},
        "values": [
            {"datetime": "2026-09-08 09:30:00", "open": "1.0",
             "high": "1.1", "low": "0.9", "close": "1.05",
             "volume": "100"},
        ],
        "status": "ok",
    }).encode()


class FakeTransport(Transport):
    def __init__(self, script):
        # script: list of ("ok",) | ("status", code, body) | ("timeout",)
        self.script = list(script)
        self.calls = []
        self.urls = []

    def fetch(self, url):
        self.urls.append(url)
        self.calls.append(url)
        step = self.script.pop(0) if self.script else ("ok",)
        if step[0] == "ok":
            return 200, {}, good_body()
        if step[0] == "status":
            return step[1], {}, step[2]
        if step[0] == "timeout":
            raise TimeoutError("fake timeout")
        raise AssertionError(step)


def make_spec(rid, symbol="AAPL", **kw):
    d = dict(request_id=rid, symbol=symbol, interval="1h",
             start_date="2026-09-08T00:00:00", end_date="2026-10-06T23:59:59",
             timezone="America/New_York", outputsize=5000, order="ASC",
             adjust="splits", leg="PAR", day_offset=0,
             output_name=f"{rid}.json")
    d.update(kw)
    return RequestSpec(**d)


def make_wrapper(store, transport, clock=None):
    ledger = RollingCreditLimiter(8, 800,
                                  state_path=store / "ledger.json",
                                  clock=clock)
    sleeps = []
    w = AcquisitionWrapper(store, ledger, transport,
                           clock=(clock or (lambda: 1000.0)),
                           sleeper=sleeps.append,
                           preflight=lambda: [])
    return w, sleeps, ledger


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name +
          (f" [{detail}]" if detail and not cond else ""))
    return cond


results = []
with tempfile.TemporaryDirectory() as td:
    td = Path(td)

    # W01 idempotency: second run makes zero transport calls
    s = td / "w01"; t = FakeTransport([("ok",), ("ok",)])
    w, _, _ = make_wrapper(s, t)
    specs = [make_spec("REQ-W01-01"), make_spec("REQ-W01-02")]
    o1 = w.run(specs); calls1 = len(t.calls)
    o2 = w.run(specs)
    results.append(check("W01-idempotent-rerun",
                         calls1 == 2 and len(t.calls) == 2 and
                         all(o.outcome == "SKIPPED_RESUMED" for o in o2)))

    # W02 no-overwrite: pre-existing snapshot refused, untouched
    s = td / "w02"; s.mkdir()
    (s / "REQ-W02-01.json").write_bytes(b'{"orig": true}')
    t = FakeTransport([("ok",)])
    w, _, _ = make_wrapper(s, t)
    o = w.run([make_spec("REQ-W02-01")])
    results.append(check("W02-no-overwrite",
                         o[0].outcome == "SKIPPED_RESUMED" and
                         len(t.calls) == 0 and
                         (s / "REQ-W02-01.json").read_bytes() == b'{"orig": true}'))

    # W03 resume partial: only missing requests fetched
    s = td / "w03"; s.mkdir()
    (s / "REQ-W03-01.json").write_bytes(b"x")
    (s / "REQ-W03-03.json").write_bytes(b"x")
    t = FakeTransport([("ok",), ("ok",)])
    w, _, _ = make_wrapper(s, t)
    o = w.run([make_spec(f"REQ-W03-0{i}") for i in (1, 2, 3, 4)])
    results.append(check("W03-resume-partial",
                         len(t.calls) == 2 and
                         [x.outcome for x in o] ==
                         ["SKIPPED_RESUMED", "OK",
                          "SKIPPED_RESUMED", "OK"]))

    # W04 retry-then-success: 503 once, then 200
    s = td / "w04"
    t = FakeTransport([("status", 503, b"{}"), ("ok",)])
    w, sleeps, ledger = make_wrapper(s, t)
    o = w.run([make_spec("REQ-W04-01")])
    results.append(check("W04-retry-success",
                         o[0].outcome == "OK" and o[0].attempts == 2 and
                         sleeps == [60] and ledger.daily_spent == 2))

    # W05 retry exhaustion: always 503, 3 attempts, run stops
    s = td / "w05"
    t = FakeTransport([("status", 503, b"{}")] * 10)
    w, sleeps, _ = make_wrapper(s, t)
    o = w.run([make_spec("REQ-W05-01"), make_spec("REQ-W05-02")])
    results.append(check("W05-retry-exhausted",
                         o[0].outcome == "RETRIES_EXHAUSTED" and
                         o[0].attempts == 3 and len(t.calls) == 3 and
                         len(o) == 1 and sleeps == [60, 300] and
                         not (s / "REQ-W05-01.json").exists()))

    # W06 401: AUTH_STOP, run halts immediately
    s = td / "w06"
    t = FakeTransport([("status", 401, b"{}"), ("ok",)])
    w, _, _ = make_wrapper(s, t)
    o = w.run([make_spec("REQ-W06-01"), make_spec("REQ-W06-02")])
    results.append(check("W06-auth-stop",
                         o[0].outcome == "AUTH_STOP" and len(o) == 1 and
                         len(t.calls) == 1))

    # W07 schema break: 200 but values missing -> quarantine, no snapshot
    s = td / "w07"
    t = FakeTransport([("status", 200,
                        json.dumps({"status": "ok"}).encode())])
    w, _, _ = make_wrapper(s, t)
    o = w.run([make_spec("REQ-W07-01")])
    results.append(check("W07-schema-quarantine",
                         o[0].outcome == "SCHEMA_QUARANTINE" and
                         not (s / "REQ-W07-01.json").exists()))

    # W08 shared-ledger refusal: minute window spent -> no transport call
    s = td / "w08"
    clock = FakeWallClock(2000.0)
    t = FakeTransport([("ok",)])
    ledger = RollingCreditLimiter(8, 800, state_path=s / "ledger.json",
                                  clock=clock)
    for _ in range(8):
        assert ledger.try_acquire(1, label="prefill")
    w = AcquisitionWrapper(s, ledger, t, clock=clock,
                           sleeper=lambda x: None,
                           preflight=lambda: [])
    o = w.run([make_spec("REQ-W08-01")])
    results.append(check("W08-ledger-refusal",
                         o[0].outcome == "LEDGER_REFUSED" and
                         len(t.calls) == 0))

    # W09 redaction: no key material in receipts, URLs, or scrubbed errors
    s = td / "w09"
    t = FakeTransport([("ok",)])
    w, _, _ = make_wrapper(s, t)
    o = w.run([make_spec("REQ-W09-01")])
    receipt = json.loads((s / "REQ-W09-01.receipt.json").read_text())
    results.append(check("W09-redaction",
                         o[0].outcome == "OK" and
                         "apikey" not in json.dumps(receipt["params"]) and
                         all("apikey" not in u for u in t.urls) and
                         scrub("x?apikey=SECRET&y=1") == "x?apikey=REDACTED&y=1"))

    # W10 receipt metadata: complete, hash matches snapshot
    s = td / "w10"
    t = FakeTransport([("ok",)])
    w, _, _ = make_wrapper(s, t)
    o = w.run([make_spec("REQ-W10-01")])
    snap = (s / "REQ-W10-01.json").read_bytes()
    import hashlib
    r = o[0].receipt
    results.append(check(
        "W10-receipt-metadata",
        o[0].outcome == "OK" and r["sha256"] == hashlib.sha256(snap).hexdigest()
        and r["bytes"] == len(snap) and r["http_status"] == 200
        and r["request_ts_ms"] <= r["receipt_ts_ms"]
        and r["params"]["symbol"] == "AAPL" and r["attempt"] == 1
        and (s / "REQ-W10-01.receipt.json").exists()))

print(f"\n{sum(results)}/{len(results)} wrapper fixtures passed")
sys.exit(0 if all(results) else 1)
