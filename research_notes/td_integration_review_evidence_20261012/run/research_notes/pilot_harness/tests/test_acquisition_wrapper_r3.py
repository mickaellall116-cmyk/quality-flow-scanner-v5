#!/usr/bin/env python3
"""Wrapper-specific synthetic fixtures W11-W19 for r3 defects.

Task QF-TD-PILOT-READINESS-R3-20261010-06 (Issue #1 6099318779).
Bounded: one pass, no network, no vendor calls, no credits spent
against any real account. Fake transport / clock / sleeper throughout.
"""

import io
import json
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import pilot_acquire as pa  # noqa: E402
from pilot_acquire import (  # noqa: E402
    AcquisitionWrapper,
    ManifestDriver,
    RequestSpec,
    RetryBudget,
    Transport,
)
from rate_limiter import RollingCreditLimiter, FakeWallClock  # noqa: E402


def good_body(symbol="AAPL", interval="1h"):
    return json.dumps({
        "meta": {"symbol": symbol, "interval": interval},
        "values": [
            {"datetime": "2026-09-08 09:30:00", "open": "1.0",
             "high": "1.1", "low": "0.9", "close": "1.05",
             "volume": "100"},
        ],
        "status": "ok",
    }).encode()


class FakeTransport(Transport):
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def fetch(self, url):
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
             start_date="2026-04-01T00:00:00", end_date="2026-10-06T23:59:59",
             timezone="America/New_York", outputsize=5000, order="ASC",
             adjust="splits", leg="PAR", day="D0",
             output_name=f"{rid}.json")
    d.update(kw)
    return RequestSpec(**d)


def make_wrapper(store, transport, clock=None, retry_budget=None):
    ledger = RollingCreditLimiter(8, 800,
                                  state_path=store / "ledger.json",
                                  clock=clock)
    w = AcquisitionWrapper(store, ledger, transport,
                           clock=(clock or (lambda: 1000.0)),
                           sleeper=lambda x: None,
                           preflight=lambda: [],
                           retry_budget=retry_budget)
    return w, ledger


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name +
          (f" [{detail}]" if detail and not cond else ""))
    return cond


results = []
with tempfile.TemporaryDirectory() as td:
    td = Path(td)

    # W11 HTTPError boundary: monkeypatched urlopen raising real HTTPError
    # -> UrllibTransport preserves 401 status/body (defect 4), and URLError
    # -> TimeoutError. Never conflated.
    s = td / "w11"
    orig_urlopen = urllib.request.urlopen
    orig_surrogate = pa.url_with_surrogate_query_param
    pa.url_with_surrogate_query_param = (
        lambda url, cred, allowed_hosts: url + "&apikey=hsurr:x")

    def fake_401(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, 401, "Unauthorized",
            {"Content-Type": "application/json"},
            io.BytesIO(b'{"status":"error"}'))

    def fake_refused(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    urllib.request.urlopen = fake_401
    tr = pa.UrllibTransport()
    st, hd, body = tr.fetch("https://api.twelvedata.com/time_series?x=1")
    w11a = (st == 401 and body == b'{"status":"error"}' and
            hd.get("content-type") == "application/json")
    urllib.request.urlopen = fake_refused
    try:
        tr.fetch("https://api.twelvedata.com/time_series?x=1")
        w11b = False
    except TimeoutError:
        w11b = True
    urllib.request.urlopen = orig_urlopen
    pa.url_with_surrogate_query_param = orig_surrogate
    results.append(check("W11-http-error-boundary", w11a and w11b))

    # W12 orphan snapshot: no receipt -> quarantined + refetched (defect 6)
    s = td / "w12"; s.mkdir()
    (s / "REQ-W12-01.json").write_bytes(b'{"stale": 1}')
    t = FakeTransport([("ok",)])
    w, _ = make_wrapper(s, t)
    o = w.run([make_spec("REQ-W12-01")])
    orphans = list(s.glob("REQ-W12-01.json.orphan.*"))
    results.append(check("W12-orphan-refetch",
                         o[0].outcome == "OK" and len(t.calls) == 1 and
                         len(orphans) == 1 and
                         orphans[0].read_bytes() == b'{"stale": 1}'))

    # W13 shared retry budget: cap 1 -> second request's retry refused
    s = td / "w13"
    t = FakeTransport([("status", 503, b"{}"), ("ok",),
                       ("status", 503, b"{}"), ("status", 503, b"{}")])
    w, _ = make_wrapper(s, t, retry_budget=RetryBudget(cap=1))
    o = w.run([make_spec("REQ-W13-01"), make_spec("REQ-W13-02")])
    results.append(check("W13-shared-retry-budget",
                         o[0].outcome == "OK" and o[0].attempts == 2 and
                         o[1].outcome == "RETRIES_EXHAUSTED" and
                         o[1].attempts == 1 and len(t.calls) == 3))

    # W14 warmup manifest: PAR starts 2026-04-01, ADJ bounds include the
    # preregistered 215-4H-bar warmup (defects 1, 11); driver enforces
    s = td / "w14"
    w, _ = make_wrapper(s, FakeTransport([]))
    manifest_path = HERE / "request_manifest.json"
    drv = ManifestDriver(
        manifest_path,
        s, RollingCreditLimiter(8, 800), FakeTransport([]),
        preflight=lambda: [])
    par1 = next(r for r in drv.manifest["requests"]
                if r["request_id"] == "REQ-P1H-01")
    adj1 = next(r for r in drv.manifest["requests"]
                if r["request_id"] == "REQ-ADJ-01")
    results.append(check(
        "W14-warmup-manifest",
        par1["start_date"] == "2026-04-01T00:00:00" and
        adj1["start_date"] < "2024-05-20T00:00:00" and  # warmup prepended
        len({r["request_id"] for r in drv.manifest["requests"]}) ==
        len(drv.manifest["requests"])))

    # W15 budget arithmetic: ONE non-overlapping formula (defects 2, 12)
    s = td / "w15"
    m = json.loads((HERE / "request_manifest.json").read_text())
    b = m["budget"]
    base = len(m["requests"])
    results.append(check(
        "W15-budget-arithmetic",
        b["base_requests"] == base == 91 and
        b["max_total"] == base + b["pagination_pages_max"] +
        b["retries_max"] == 171 and
        b["expected_total"] == base and
        b["pagination_pages_max"] == 40 and  # excludes PAR base calls
        sum(d["base"] for d in b["day_maxima"].values()) == base))

    # W16 minute-window resume: refusal -> exit -> fresh-window resume,
    # no request lost or duplicated (defect 10)
    s = td / "w16"
    clock = FakeWallClock(3000.0)
    t = FakeTransport([("ok",)] * 3)
    ledger = RollingCreditLimiter(8, 800, state_path=s / "ledger.json",
                                  clock=clock)
    for _ in range(6):
        assert ledger.try_acquire(1, label="prefill")
    w = AcquisitionWrapper(s, ledger, t, clock=clock,
                           sleeper=lambda x: None, preflight=lambda: [])
    specs16 = [make_spec(f"REQ-W16-0{i}") for i in (1, 2, 3)]
    o1 = w.run(specs16)
    clock.advance(61)  # fresh rate window
    t2 = FakeTransport([("ok",)])
    ledger2 = RollingCreditLimiter(8, 800, state_path=s / "ledger.json",
                                   clock=clock)
    w2 = AcquisitionWrapper(s, ledger2, t2, clock=clock,
                            sleeper=lambda x: None, preflight=lambda: [])
    o2 = w2.run(specs16)
    results.append(check(
        "W16-window-resume",
        [x.outcome for x in o1] == ["OK", "OK", "LEDGER_REFUSED"] and
        [x.outcome for x in o2] ==
        ["SKIPPED_RESUMED", "SKIPPED_RESUMED", "OK"] and
        len(t.calls) + len(t2.calls) == 3))

    # W17 429 semantics: non-429 resets consecutive counter (defect 8);
    # rolling window counts DISTINCT request IDs
    s = td / "w17"
    t = FakeTransport([("status", 429, b"{}"), ("status", 503, b"{}"),
                       ("ok",)])
    w, _ = make_wrapper(s, t)
    o = w.run([make_spec("REQ-W17-01")])
    w17a = (o[0].outcome == "OK" and o[0].attempts == 3)
    # distinct-request window: 3rd distinct 429 in 10 min -> RATE_STOP
    s2 = td / "w17b"
    t2 = FakeTransport([("status", 429, b"{}"), ("ok",),
                        ("status", 429, b"{}"), ("ok",),
                        ("status", 429, b"{}")])
    w2, _ = make_wrapper(s2, t2)
    o2 = w2.run([make_spec(f"REQ-W17B-0{i}") for i in (1, 2, 3)])
    w17b = ([x.outcome for x in o2] == ["OK", "OK", "RATE_STOP"])
    results.append(check("W17-429-semantics", w17a and w17b))

    # W18 schema binding: status-ok payload for wrong symbol/interval
    # must fail (defect 9)
    s = td / "w18"

    class WrongSymbol(Transport):
        def fetch(self, url):
            return 200, {}, good_body(symbol="MSFT", interval="1h")

    w, _ = make_wrapper(s, WrongSymbol())
    o = w.run([make_spec("REQ-W18-01", symbol="AAPL")])
    w18a = (o[0].outcome == "SCHEMA_QUARANTINE")

    class WrongInterval(Transport):
        def fetch(self, url):
            return 200, {}, good_body(symbol="AAPL", interval="4h")

    w, _ = make_wrapper(s, WrongInterval())
    o = w.run([make_spec("REQ-W18-02", symbol="AAPL", interval="1h")])
    results.append(check("W18-schema-binding", w18a and
                         o[0].outcome == "SCHEMA_QUARANTINE"))

    # W19 durable attempt receipts: every attempt persisted, scrubbed
    s = td / "w19"
    t = FakeTransport([("status", 503, b"{}"), ("ok",)])
    w, _ = make_wrapper(s, t)
    o = w.run([make_spec("REQ-W19-01")])
    lines = (s / "REQ-W19-01.attempts.jsonl").read_text().strip().split("\n")
    entries = [json.loads(x) for x in lines]
    results.append(check(
        "W19-attempt-receipts",
        o[0].outcome == "OK" and len(entries) == 2 and
        entries[0]["event"] == "retry_scheduled" and
        entries[1]["event"] == "ok" and
        all("apikey" not in json.dumps(e) for e in entries) and
        all(e["http_status"] in (503, 200) for e in entries)))

print(f"\n{sum(results)}/{len(results)} r3 fixtures passed")
sys.exit(0 if all(results) else 1)
