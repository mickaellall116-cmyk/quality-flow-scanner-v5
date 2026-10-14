#!/usr/bin/env python3
"""
Synthetic proof suite for td-http-transport-adapter + driver binding
(QF-TD-TRANSPORT-ADAPTER-IMPLEMENT-20261013-03 r1; vault-binding
correction QF-TD-VAULT-BINDING-CORRECTION-20261014-05 r1).

EVERYTHING here is local: test HTTP/HTTPS servers on 127.0.0.1 that this
suite starts and stops itself. ZERO vendor calls, zero credits, zero
spend. The collector under test is the accepted pinned bytes
(bd003c3c..., extracted from f64d12f and sha-verified before use); the
limiter is the real pilot_harness/rate_limiter.py (06ad383d...).

Key sourcing under test: the collector proofs run through the driver's
explicitly-named TEST FIXTURE source (TWELVEDATA_TEST_FIXTURE_API_KEY);
the BindingLevel proofs exercise the production vault binding
(custom.twelvedata via authd surrogate) with the authd fetch stubbed —
no real credential or surrogate is ever fetched by this suite.

Run with the pinned-dependency venv python:
  python3 test_transport_adapter.py --output-dir <NEW DIRECTORY>
Writes test_output.txt + results.json into the output directory.
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import http.client  # noqa: E402
import td_http_transport_adapter as adapter_mod  # noqa: E402
from td_http_transport_adapter import (  # noqa: E402
    TDHttpTransportAdapter, TransportError, PARAMETER_ORDER,
    CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS, MAX_BODY_BYTES,
    VENDOR_BASE_URL)
import driver as drv  # noqa: E402

FAKE_KEY = "TESTKEY-FAKE-DO-NOT-USE-7f3a9c"
FAKE_SURROGATE = "hsurr:TEST-SURROGATE-DO-NOT-USE-0000"
COLLECTOR_COMMIT = "f64d12f885339e9e2ab4fa38b4a55df78db39b9f"
COLLECTOR_GIT_PATH = "research_notes/td_lifecycle_repair_candidate/td_min_collector.py"
PREREQ = (REPO / "research_notes" /
          "td_acquisition_adapter_preflight_evidence_20261013" /
          "prerequisites.json")
REAL_HARNESS = REPO / "research_notes" / "pilot_harness"

REQ = {"symbol": "OK200", "interval": "1h",
       "start_date": "2026-09-08T00:00:00", "end_date": "2026-09-08T23:59:59",
       "timezone": "America/New_York", "outputsize": 5000,
       "order": "asc", "adjust": "none"}


# --------------------------------------------------------------------------
# Local test servers
# --------------------------------------------------------------------------
class Recorder:
    def __init__(self, expected_key=FAKE_KEY):
        self.expected_key = expected_key
        self.hits = []  # (symbol, [param names in order], apikey_matches)

    def record(self, query: str):
        pairs = parse_qsl(query, keep_blank_values=True)
        names = [k for k, _ in pairs]
        vals = dict(pairs)
        self.hits.append((vals.get("symbol", ""), names,
                          vals.get("apikey") == self.expected_key))
        return vals


def make_handler(behavior, recorder: Recorder):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):  # silence server logs
            pass

        def do_GET(self):
            parts = urlsplit(self.path)
            vals = recorder.record(parts.query)
            status, headers, body = behavior(vals, parts)
            self.send_response(status)
            for k, v in headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)
    return H


def start_server(behavior, recorder: Recorder, tls_context=None):
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(behavior, recorder))
    server.daemon_threads = True
    if tls_context is not None:
        server.socket = tls_context.wrap_socket(server.socket, server_side=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


def ok_body(day="2026-09-08", symbol="AAPL"):
    """Same construction the accepted integration used: real XNYS
    schedule + expected 1h starts from the pinned validate_input."""
    sys.path.insert(0, str(REAL_HARNESS))
    import pandas as pd
    from validate_input import expected_1h_starts, xnys_schedule
    starts = expected_1h_starts(*xnys_schedule(pd.Timestamp(day, tz="America/New_York")))
    values = []
    for i, t in enumerate(starts):
        price = 10 * (i + 1)
        values.append({"datetime": t.strftime("%Y-%m-%d %H:%M:%S"),
                       "open": str(price), "high": str(price + 1),
                       "low": str(price - 1), "close": str(price),
                       "volume": str(i + 1)})
    return json.dumps({"status": "ok",
                       "meta": {"symbol": symbol, "interval": "1h",
                                "exchange": "NASDAQ", "mic_code": "XNAS",
                                "currency": "USD"},
                       "values": values}).encode()


def fixture_manifest():
    r = {"request_id": "AAPL_FIXTURE", "symbol": "AAPL", "leg": "PAR",
         "interval": "1h", "start_date": "2026-09-08T00:00:00",
         "end_date": "2026-09-08T23:59:59", "timezone": "America/New_York",
         "adjust": "none", "order": "asc", "outputsize": 5000,
         "max_attempts": 1, "pagination": False, "credit_weight": 1,
         "expected_credits": 1, "output_name": "AAPL_FIXTURE.json",
         "one_response_bound_bars": 7,
         "venue_identity": {"exchange": "NASDAQ", "mic_code": "XNAS",
                            "currency": "USD"}}
    r["identity"] = (f"AAPL|/time_series|1h|{r['start_date']}|{r['end_date']}|"
                     f"America/New_York|adjust=none")
    return {"endpoint": "https://api.twelvedata.com/time_series",
            "requests": [r]}


# --------------------------------------------------------------------------
class AdapterLevel(unittest.TestCase):
    """Direct adapter proofs against symbol-keyed local behaviors."""

    @classmethod
    def setUpClass(cls):
        cls.rec = Recorder()
        cls.other_rec = Recorder()
        cls.other = start_server(lambda v, p: (200, {}, b"other-host"),
                                 cls.other_rec)
        other_port = cls.other.server_address[1]

        def behavior(vals, parts):
            sym = vals.get("symbol", "")
            if sym == "OK200":
                return 200, {}, b'{"status":"ok","probe":true}'
            if sym == "RATE429":
                return 429, {}, b'{"status":"error","message":"rate limited"}'
            if sym == "ERR500":
                return 500, {}, b'{"status":"error","message":"boom"}'
            if sym == "APIERR":
                return 200, {}, b'{"status":"error","message":"bad symbol"}'
            if sym == "SLOW":
                time.sleep(3)
                return 200, {}, b'{"status":"ok"}'
            if sym == "BIG":
                return 200, {}, b"x" * 4096
            if sym == "REDIR_SAME":
                return 302, {"Location": "/time_series?symbol=OK200"}, b""
            if sym == "REDIR_CROSS":
                return 302, {"Location":
                             f"http://127.0.0.1:{other_port}/time_series?symbol=OK200"}, b""
            return 404, {}, b"{}"
        cls.server = start_server(behavior, cls.rec)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.other.shutdown()

    def adapter(self, **kw):
        return TDHttpTransportAdapter(FAKE_KEY, base_url=self.base, **kw)

    def hits(self, symbol):
        return [h for h in self.rec.hits if h[0] == symbol]

    def test_defaults_pinned(self):
        a = TDHttpTransportAdapter(FAKE_KEY)
        self.assertEqual(a.base_url, VENDOR_BASE_URL)
        self.assertEqual(a.connect_timeout, CONNECT_TIMEOUT_SECONDS)
        self.assertEqual(a.read_timeout, READ_TIMEOUT_SECONDS)
        self.assertEqual(a.connect_timeout, 10.0)
        self.assertEqual(a.read_timeout, 30.0)
        self.assertEqual(a.max_body_bytes, MAX_BODY_BYTES)
        self.assertEqual(MAX_BODY_BYTES, 64 * 1024 * 1024)

    def test_http_non_loopback_rejected(self):
        with self.assertRaises(ValueError):
            TDHttpTransportAdapter(FAKE_KEY, base_url="http://example.com")

    def test_param_order_values_and_success_passthrough(self):
        status, body = self.adapter().transport(dict(REQ))
        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"status":"ok","probe":true}')
        hits = self.hits("OK200")
        self.assertGreaterEqual(len(hits), 1)
        _, names, key_ok = hits[-1]
        self.assertEqual(names, list(PARAMETER_ORDER))
        self.assertTrue(key_ok)

    def test_429_passthrough_exactly_one_attempt(self):
        before = len(self.hits("RATE429"))
        status, body = self.adapter().transport(dict(REQ, symbol="RATE429"))
        self.assertEqual(status, 429)
        self.assertEqual(body, b'{"status":"error","message":"rate limited"}')
        self.assertEqual(len(self.hits("RATE429")), before + 1)

    def test_500_passthrough_exactly_one_attempt(self):
        before = len(self.hits("ERR500"))
        status, _ = self.adapter().transport(dict(REQ, symbol="ERR500"))
        self.assertEqual(status, 500)
        self.assertEqual(len(self.hits("ERR500")), before + 1)

    def test_api_error_payload_passthrough(self):
        status, body = self.adapter().transport(dict(REQ, symbol="APIERR"))
        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"status":"error","message":"bad symbol"}')

    def test_read_timeout_enforced_and_sanitized(self):
        a = self.adapter(read_timeout=0.5)
        t0 = time.time()
        with self.assertRaises(TransportError) as cm:
            a.transport(dict(REQ, symbol="SLOW"))
        elapsed = time.time() - t0
        self.assertEqual(cm.exception.category, "read_timeout")
        self.assertLess(elapsed, 2.5)
        self.assertEqual(str(cm.exception), "read_timeout")

    def test_connect_refused_sanitized(self):
        a = TDHttpTransportAdapter(FAKE_KEY, base_url="http://127.0.0.1:1",
                                   connect_timeout=2.0)
        with self.assertRaises(TransportError) as cm:
            a.transport(dict(REQ))
        self.assertEqual(cm.exception.category, "connection_error")
        self.assertEqual(str(cm.exception), "connection_error")

    def test_connect_timeout_fail_closed(self):
        # TEST-NET-1 (192.0.2.1) is unroutable by design: the attempt must
        # fail closed, sanitized, within a bounded time. In this sandbox
        # the egress path terminates the attempt at the TLS layer, so the
        # observed category is tls_failure; on a plain SYN-drop network
        # it is connect_timeout / connection_error. All are fail-closed
        # TransportErrors — a live connect-timeout against the real
        # vendor origin cannot be produced locally (see result doc).
        a = TDHttpTransportAdapter(FAKE_KEY, base_url="https://192.0.2.1:8443",
                                   connect_timeout=1.0, read_timeout=1.0)
        t0 = time.time()
        with self.assertRaises(TransportError) as cm:
            a.transport(dict(REQ))
        self.assertLess(time.time() - t0, 5.0)
        self.assertIn(cm.exception.category,
                      ("connect_timeout", "connection_error", "tls_failure"))

    def test_body_cap(self):
        a = self.adapter(max_body_bytes=1024)
        before = len(self.hits("BIG"))
        with self.assertRaises(TransportError) as cm:
            a.transport(dict(REQ, symbol="BIG"))
        self.assertEqual(cm.exception.category, "body_cap_exceeded")
        self.assertEqual(len(self.hits("BIG")), before + 1)

    def test_redirect_same_host_followed(self):
        status, body = self.adapter().transport(dict(REQ, symbol="REDIR_SAME"))
        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"status":"ok","probe":true}')

    def test_redirect_cross_host_rejected(self):
        before = len(self.other_rec.hits)
        with self.assertRaises(TransportError) as cm:
            self.adapter().transport(dict(REQ, symbol="REDIR_CROSS"))
        self.assertEqual(cm.exception.category, "redirect_rejected")
        self.assertEqual(len(self.other_rec.hits), before)

    def test_malformed_request_no_network(self):
        before = len(self.rec.hits)
        with self.assertRaises(TransportError) as cm:
            self.adapter().transport({"symbol": "OK200"})
        self.assertEqual(cm.exception.category, "malformed_request")
        self.assertEqual(len(self.rec.hits), before)

    def test_tls_verification_on(self):
        import ssl as _ssl
        certdir = pathlib.Path(tempfile.mkdtemp())
        cert, key = certdir / "cert.pem", certdir / "key.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048",
                        "-keyout", str(key), "-out", str(cert), "-days", "1",
                        "-nodes", "-subj", "/CN=localhost"],
                       check=True, capture_output=True)
        ctx = _ssl.SSLContext(_ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        rec = Recorder()
        server = start_server(lambda v, p: (200, {}, b"tls-ok"), rec, ctx)
        try:
            a = TDHttpTransportAdapter(
                FAKE_KEY, base_url=f"https://127.0.0.1:{server.server_address[1]}")
            with self.assertRaises(TransportError) as cm:
                a.transport(dict(REQ))
            # Self-signed cert MUST be rejected: verification is on.
            self.assertEqual(cm.exception.category, "tls_failure")
        finally:
            server.shutdown()

    def test_exception_text_never_leaks(self):
        samples = []
        a = self.adapter(read_timeout=0.5)
        for req in (dict(REQ, symbol="SLOW"),):
            try:
                a.transport(req)
            except TransportError as e:
                samples.append(f"{e}|{e!r}")
        try:
            TDHttpTransportAdapter(FAKE_KEY, base_url="http://127.0.0.1:1",
                                   connect_timeout=1.0).transport(dict(REQ))
        except TransportError as e:
            samples.append(f"{e}|{e!r}")
        blob = " ".join(samples)
        self.assertNotIn(FAKE_KEY, blob)
        self.assertNotIn("apikey", blob)
        self.assertNotIn("127.0.0.1", blob)
        self.assertNotIn("http", blob)


# --------------------------------------------------------------------------
class CollectorLevel(unittest.TestCase):
    """Driver-bound collector proofs (pinned bytes, shared persisted
    limiter, scratch ledger)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        # Pinned collector layout: candidate dir + pilot_harness sibling.
        rn = root / "research_notes"
        cand = rn / "td_lifecycle_repair_candidate"
        cand.mkdir(parents=True)
        raw = subprocess.run(
            ["git", "-C", str(REPO), "show", f"{COLLECTOR_COMMIT}:{COLLECTOR_GIT_PATH}"],
            check=True, capture_output=True).stdout
        assert hashlib.sha256(raw).hexdigest() == drv.COLLECTOR_SHA256
        self.collector_path = cand / "td_min_collector.py"
        self.collector_path.write_bytes(raw)
        os.symlink(REAL_HARNESS, rn / "pilot_harness")
        self.state = root / "state"
        self.ledger = root / "credit_ledger.json"
        os.environ[drv.TEST_FIXTURE_KEY_ENV] = FAKE_KEY

    def tearDown(self):
        os.environ.pop(drv.TEST_FIXTURE_KEY_ENV, None)
        self.tmp.cleanup()

    def build(self, base, manifest=None):
        return drv.build_collector(self.state, manifest or fixture_manifest(),
                                   PREREQ,
                                   key_source=drv.get_test_fixture_key,
                                   base_url=base,
                                   ledger_path=self.ledger,
                                   collector_path=self.collector_path)

    def events(self):
        p = self.state / "lifecycle.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def test_driver_pin_enforced(self):
        bad = pathlib.Path(self.tmp.name) / "tampered.py"
        bad.write_bytes(b"# tampered collector")
        with self.assertRaises(drv.DriverError):
            drv.load_collector_module(bad)

    def test_full_synthetic_round_trip_success(self):
        rec = Recorder()
        served = {}

        def behavior(vals, parts):
            body = ok_body(vals.get("start_date", "2026-09-08")[:10])
            served["body"] = body
            return 200, {}, body
        server = start_server(behavior, rec)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            collector, _ = self.build(base)  # key via test fixture source
            result = collector.run()
            self.assertEqual(result["outcome"], "COMPLETE")
            self.assertEqual(result["completed"], 1)
            receipt = self.state / "receipts" / "AAPL_FIXTURE.json"
            self.assertEqual(receipt.read_bytes(), served["body"])
            kinds = [e["event"] for e in self.events()]
            for k in ("CREDIT_RESERVED", "STARTED", "RECEIVED", "COMPLETED",
                      "CONSTRUCTION_HOLD"):
                self.assertIn(k, kinds)
            self.assertEqual(json.loads(self.ledger.read_text())["spent"], 1)
            self.assertEqual(len(rec.hits), 1)
            # Reuse: a fresh collector over the same state makes NO call.
            collector2, _ = self.build(base)
            result2 = collector2.run()
            self.assertEqual(result2["reused"], 1)
            self.assertEqual(len(rec.hits), 1)
        finally:
            server.shutdown()

    def test_collector_429_hold_with_evidence_one_attempt(self):
        rec = Recorder()
        body429 = b'{"status":"error","message":"rate limited"}'
        server = start_server(lambda v, p: (429, {}, body429), rec)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            collector, _ = self.build(base)
            result = collector.run()
            self.assertIn("HOLD", result["outcome"])
            self.assertIn("HTTP 429", result["outcome"])
            rejected = self.state / "receipts" / "AAPL_FIXTURE.rejected.bin"
            self.assertEqual(rejected.read_bytes(), body429)
            self.assertIn("ERROR_EVIDENCE", [e["event"] for e in self.events()])
            self.assertEqual(len(rec.hits), 1)  # never retried
        finally:
            server.shutdown()

    def test_limiter_refusal_zero_dispatch_and_restart_persistence(self):
        sys.path.insert(0, str(REAL_HARNESS))
        from rate_limiter import RollingCreditLimiter
        warm = RollingCreditLimiter(8, 800, state_path=self.ledger)
        for _ in range(8):
            self.assertTrue(warm.try_acquire(1, "warmup"))
        # True process restart: a new python process must still be refused.
        child = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r);"
             "from rate_limiter import RollingCreditLimiter;"
             "lim = RollingCreditLimiter(8, 800, state_path=%r);"
             "print(lim.try_acquire(1, 'after-restart'), lim.daily_spent)"
             % (str(REAL_HARNESS), str(self.ledger))],
            capture_output=True, text=True)
        self.assertEqual(child.stdout.strip(), "False 8")
        # Collector run: REFUSED before any dispatch — zero server hits.
        rec = Recorder()
        server = start_server(lambda v, p: (200, {}, ok_body()), rec)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            collector, _ = self.build(base)
            result = collector.run()
            self.assertIn("REFUSED", result["outcome"])
            self.assertEqual(len(rec.hits), 0)
            self.assertIn("LIMITER_REFUSED", [e["event"] for e in self.events()])
        finally:
            server.shutdown()

    def test_secret_isolation_sweep(self):
        rec = Recorder()
        server = start_server(lambda v, p: (200, {}, ok_body()), rec)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            collector, _ = self.build(base)
            self.assertEqual(collector.run()["outcome"], "COMPLETE")
        finally:
            server.shutdown()
        # Walk EVERY runtime artifact this run produced (state, receipts,
        # lifecycle, ledger): the key and the credential parameter name
        # must appear nowhere.
        scanned = 0
        for path in pathlib.Path(self.tmp.name).rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            data = path.read_bytes()
            scanned += 1
            self.assertNotIn(FAKE_KEY.encode(), data, f"key leaked into {path}")
            if path.suffix in (".jsonl", ".json"):
                self.assertNotIn(b"apikey", data, f"apikey string in {path}")
        self.assertGreater(scanned, 3)


# --------------------------------------------------------------------------
class BindingLevel(unittest.TestCase):
    """Vault-binding proofs (QF-TD-VAULT-BINDING-CORRECTION-20261014-05 r1).

    The driver's production key source is the Secure Vault credential
    custom.twelvedata, fetched as an hsurr:* surrogate via authd. Here
    the authd fetch (drv._vault_entry) is stubbed with canned entries —
    the suite never fetches a real credential or surrogate. The local
    servers remain loopback-only; zero vendor calls."""

    GOOD_ENTRY = {"name": "access_token", "surrogate": FAKE_SURROGATE,
                  "placement": {"query_param": "apikey"}}

    def setUp(self):
        self._orig_vault_entry = drv._vault_entry
        self._saved_env = {k: os.environ.get(k) for k in
                           (drv.TEST_FIXTURE_KEY_ENV, "TWELVEDATA_API_KEY")}
        # Poison BOTH environment variables: the production binding must
        # never read key material from either of them.
        os.environ[drv.TEST_FIXTURE_KEY_ENV] = FAKE_KEY
        os.environ["TWELVEDATA_API_KEY"] = FAKE_KEY

    def tearDown(self):
        drv._vault_entry = self._orig_vault_entry
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def stub_entry(self, entry):
        drv._vault_entry = lambda: entry

    def test_vault_binding_returns_surrogate_despite_poisoned_env(self):
        self.stub_entry(dict(self.GOOD_ENTRY))
        self.assertEqual(drv.get_api_key(), FAKE_SURROGATE)

    def test_vault_binding_sends_surrogate_as_apikey_last(self):
        self.stub_entry(dict(self.GOOD_ENTRY))
        rec = Recorder(expected_key=FAKE_SURROGATE)
        server = start_server(lambda v, p: (200, {}, b'{"status":"ok"}'), rec)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            a = TDHttpTransportAdapter(drv.get_api_key(), base_url=base)
            status, _ = a.transport(dict(REQ))
            self.assertEqual(status, 200)
        finally:
            server.shutdown()
        self.assertEqual(len(rec.hits), 1)
        _, names, key_ok = rec.hits[0]
        self.assertEqual(names, list(PARAMETER_ORDER))
        self.assertEqual(names[-1], "apikey")
        self.assertTrue(key_ok)

    def test_vault_binding_failure_sanitized_no_env_fallback(self):
        # Seed a fake dynamic_credentials helper whose fetch raises with
        # sensitive text embedded. The driver's real _vault_entry must
        # convert it to a bare category token, and get_api_key must NOT
        # fall back to the poisoned environment.
        import types
        fake = types.ModuleType("dynamic_credentials")

        def fetch(name, entry):
            raise RuntimeError("authd response mentioning " + FAKE_KEY)
        fake.dynamic_credential_entry = fetch
        saved_mod = sys.modules.get("dynamic_credentials")
        sys.modules["dynamic_credentials"] = fake
        try:
            with self.assertRaises(drv.DriverError) as cm:
                drv.get_api_key()  # real _vault_entry, fake helper
        finally:
            if saved_mod is None:
                sys.modules.pop("dynamic_credentials", None)
            else:
                sys.modules["dynamic_credentials"] = saved_mod
        blob = f"{cm.exception}|{cm.exception!r}"
        self.assertEqual(str(cm.exception), "vault_credential_unavailable")
        self.assertNotIn(FAKE_KEY, blob)
        self.assertNotIn("authd response", blob)
        self.assertNotIn("hsurr", blob)

    def test_vault_binding_wrong_placement_fails_closed(self):
        self.stub_entry({"name": "access_token", "surrogate": FAKE_SURROGATE,
                         "placement": "bearer_header"})
        with self.assertRaises(drv.DriverError) as cm:
            drv.get_api_key()
        self.assertEqual(str(cm.exception), "vault_placement_mismatch")

    def test_vault_binding_non_surrogate_fails_closed(self):
        self.stub_entry({"name": "access_token", "surrogate": FAKE_KEY,
                         "placement": {"query_param": "apikey"}})
        with self.assertRaises(drv.DriverError) as cm:
            drv.get_api_key()
        self.assertEqual(str(cm.exception), "vault_non_surrogate_value")

    def test_fixture_source_explicit_and_separate(self):
        # The fixture source reads ONLY its explicitly-named variable.
        self.assertEqual(drv.get_test_fixture_key(), FAKE_KEY)
        saved = os.environ.pop(drv.TEST_FIXTURE_KEY_ENV)
        try:
            with self.assertRaises(drv.DriverError):
                drv.get_test_fixture_key()
        finally:
            os.environ[drv.TEST_FIXTURE_KEY_ENV] = saved
        # The old production env-var name is gone from the driver source:
        # no silent env fallback can reappear under the old spelling.
        src = (HERE / "driver.py").read_text()
        self.assertNotIn("TWELVEDATA_API_KEY", src.replace(
            "TWELVEDATA_TEST_FIXTURE_API_KEY", ""))
        self.assertFalse(hasattr(drv, "API_KEY_ENV"))

    def test_vault_sourced_round_trip_and_secret_isolation(self):
        # Full collector round trip with the key produced by the
        # PRODUCTION binding (authd fetch stubbed to a fake surrogate),
        # then the same byte-scan as the fixture-key sweep: neither the
        # surrogate nor the credential parameter name may appear in any
        # runtime artifact.
        self.stub_entry(dict(self.GOOD_ENTRY))
        tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(tmp.name)
        rn = root / "research_notes"
        cand = rn / "td_lifecycle_repair_candidate"
        cand.mkdir(parents=True)
        raw = subprocess.run(
            ["git", "-C", str(REPO), "show",
             f"{COLLECTOR_COMMIT}:{COLLECTOR_GIT_PATH}"],
            check=True, capture_output=True).stdout
        assert hashlib.sha256(raw).hexdigest() == drv.COLLECTOR_SHA256
        collector_path = cand / "td_min_collector.py"
        collector_path.write_bytes(raw)
        os.symlink(REAL_HARNESS, rn / "pilot_harness")
        state = root / "state"
        ledger = root / "credit_ledger.json"
        rec = Recorder(expected_key=FAKE_SURROGATE)
        server = start_server(lambda v, p: (200, {}, ok_body()), rec)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            collector, _ = drv.build_collector(
                state, fixture_manifest(), PREREQ,
                base_url=base, ledger_path=ledger,
                collector_path=collector_path)  # default source = vault
            self.assertEqual(collector.run()["outcome"], "COMPLETE")
            self.assertEqual(len(rec.hits), 1)
            self.assertTrue(rec.hits[0][2])  # server saw the surrogate
        finally:
            server.shutdown()
        scanned = 0
        for path in root.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            data = path.read_bytes()
            scanned += 1
            self.assertNotIn(FAKE_SURROGATE.encode(), data,
                             f"surrogate leaked into {path}")
            self.assertNotIn(FAKE_KEY.encode(), data,
                             f"fixture key leaked into {path}")
            if path.suffix in (".jsonl", ".json"):
                self.assertNotIn(b"apikey", data, f"apikey string in {path}")
        self.assertGreater(scanned, 3)
        tmp.cleanup()


class DispatchGateLevel(unittest.TestCase):
    """Combined-dispatch gate proofs
    (QF-TD-COMBINED-DISPATCH-PREFLIGHT-20261014-06 r1).

    The raw-key bypass is removed: build_collector has no api_key
    parameter, and the production default is the vault surrogate flow
    only. Every refusal below must occur BEFORE any transport object
    exists — proven by counting fakes patched over the adapter class
    and over http.client's connection classes (zero constructions,
    zero sockets)."""

    GOOD_ENTRY = {"name": "access_token", "surrogate": FAKE_SURROGATE,
                  "placement": {"query_param": "apikey"}}

    def setUp(self):
        self._orig_vault_entry = drv._vault_entry
        self._orig_adapter_cls = adapter_mod.TDHttpTransportAdapter
        self._orig_http = http.client.HTTPConnection
        self._orig_https = http.client.HTTPSConnection
        self.counts = {"adapter": 0, "http_conn": 0, "https_conn": 0}
        counts = self.counts

        class CountingAdapter:
            def __init__(self, *a, **k):
                counts["adapter"] += 1
                self.transport = lambda req: (200, b"{}")
        adapter_mod.TDHttpTransportAdapter = CountingAdapter

        class CountingHTTP:
            def __init__(self, *a, **k):
                counts["http_conn"] += 1
        class CountingHTTPS:
            def __init__(self, *a, **k):
                counts["https_conn"] += 1
        http.client.HTTPConnection = CountingHTTP
        http.client.HTTPSConnection = CountingHTTPS

        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        rn = root / "research_notes"
        cand = rn / "td_lifecycle_repair_candidate"
        cand.mkdir(parents=True)
        raw = subprocess.run(
            ["git", "-C", str(REPO), "show",
             f"{COLLECTOR_COMMIT}:{COLLECTOR_GIT_PATH}"],
            check=True, capture_output=True).stdout
        assert hashlib.sha256(raw).hexdigest() == drv.COLLECTOR_SHA256
        self.collector_path = cand / "td_min_collector.py"
        self.collector_path.write_bytes(raw)
        os.symlink(REAL_HARNESS, rn / "pilot_harness")
        self.state = root / "state"
        self.ledger = root / "credit_ledger.json"

    def tearDown(self):
        drv._vault_entry = self._orig_vault_entry
        adapter_mod.TDHttpTransportAdapter = self._orig_adapter_cls
        http.client.HTTPConnection = self._orig_http
        http.client.HTTPSConnection = self._orig_https
        self.tmp.cleanup()

    def assert_no_transport(self):
        self.assertEqual(self.counts,
                         {"adapter": 0, "http_conn": 0, "https_conn": 0})

    def build(self, **kw):
        kw.setdefault("ledger_path", self.ledger)
        kw.setdefault("collector_path", self.collector_path)
        return drv.build_collector(self.state, fixture_manifest(), PREREQ, **kw)

    def test_raw_key_kwarg_refused_before_transport(self):
        with self.assertRaises(TypeError):
            self.build(api_key="RAW-KEY-DO-NOT-USE-1234")
        self.assert_no_transport()

    def test_raw_key_as_key_source_refused_before_transport(self):
        with self.assertRaises(drv.DriverError) as cm:
            self.build(key_source="RAW-KEY-DO-NOT-USE-1234")
        self.assertEqual(str(cm.exception), "key_source_not_callable")
        self.assert_no_transport()

    def test_vault_failure_refused_before_transport(self):
        # Fake the authd HELPER (not _vault_entry): the real
        # _vault_entry sanitizes its failure into the bare token, and
        # the refusal must precede any transport construction.
        import types
        fake = types.ModuleType("dynamic_credentials")

        def fetch(name, entry):
            raise RuntimeError("sensitive helper text KEY=RAW-KEY-9999")
        fake.dynamic_credential_entry = fetch
        saved_mod = sys.modules.get("dynamic_credentials")
        sys.modules["dynamic_credentials"] = fake
        try:
            with self.assertRaises(drv.DriverError) as cm:
                self.build()  # default source = production vault binding
        finally:
            if saved_mod is None:
                sys.modules.pop("dynamic_credentials", None)
            else:
                sys.modules["dynamic_credentials"] = saved_mod
        self.assertEqual(str(cm.exception), "vault_credential_unavailable")
        self.assertNotIn("RAW-KEY", str(cm.exception))
        self.assert_no_transport()

    def test_non_surrogate_refused_at_build_level(self):
        drv._vault_entry = lambda: {
            "name": "access_token", "surrogate": "RAW-KEY-DO-NOT-USE-1234",
            "placement": {"query_param": "apikey"}}
        with self.assertRaises(drv.DriverError) as cm:
            self.build()
        self.assertEqual(str(cm.exception), "vault_non_surrogate_value")
        self.assert_no_transport()

    def test_invocation_order_vault_adapter_collector(self):
        order = []
        seen = {}
        drv._vault_entry = lambda: (order.append("vault_fetch"),
                                    dict(self.GOOD_ENTRY))[1]

        class RecordingAdapter:
            def __init__(self, api_key=None, base_url=None, **k):
                order.append("adapter_construct")
                seen["api_key"] = api_key
                self.transport = lambda req: (200, b"{}")
        adapter_mod.TDHttpTransportAdapter = RecordingAdapter

        orig_load = drv.load_collector_module

        def wrapped_load(path):
            mod = orig_load(path)

            class RecordingCollector:
                def __init__(self, *a, **k):
                    order.append("collector_construct")
            mod.Collector = RecordingCollector
            return mod
        drv.load_collector_module = wrapped_load
        try:
            collector, adapter = self.build()
        finally:
            drv.load_collector_module = orig_load
        self.assertEqual(order,
                         ["vault_fetch", "adapter_construct",
                          "collector_construct"])
        self.assertEqual(seen["api_key"], FAKE_SURROGATE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    out = pathlib.Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=False)
    import importlib.metadata
    import platform

    class Captured(unittest.TextTestResult):
        def __init__(self, *a):
            super().__init__(*a); self.passed = []
        def addSuccess(self, test):
            super().addSuccess(test); self.passed.append(test.id())

    with (out / "test_output.txt").open("w") as stream:
        runner = unittest.TextTestRunner(stream=stream, verbosity=2,
                                         resultclass=Captured)
        suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
        result = runner.run(suite)
    deps = {n: importlib.metadata.version(n) for n in
            ("pandas", "pandas_market_calendars")}
    files = [HERE / "td_http_transport_adapter.py", HERE / "driver.py",
             HERE / "test_transport_adapter.py"]
    summary = {"tests_run": result.testsRun, "passed": result.passed,
               "failures": [(t.id(), e) for t, e in result.failures],
               "errors": [(t.id(), e) for t, e in result.errors],
               "success": result.wasSuccessful(),
               "python": platform.python_version(), "dependencies": deps,
               "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in files},
               "collector_pin": drv.COLLECTOR_SHA256,
               "limiter_pin": drv.LIMITER_SHA256,
               "key_binding": ("production: Secure Vault custom.twelvedata "
                               "hsurr:* surrogate via authd "
                               "(dynamic_credentials); suite: stubbed "
                               "fetch + test fixture source only"),
               "vendor_calls": 0, "credits": 0,
               "transport": "local synthetic servers only (127.0.0.1)"}
    (out / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"output_dir": str(out), "tests_run": result.testsRun,
                      "success": result.wasSuccessful()}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
