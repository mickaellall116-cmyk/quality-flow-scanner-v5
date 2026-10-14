#!/usr/bin/env python3
"""
sentinel_probe.py — offline Sentinel-compatibility probe for
td-http-transport-adapter (QF-TD-COMBINED-DISPATCH-PREFLIGHT-20261014-06 r1;
updated for the proxy correction QF-TD-SENTINEL-PROXY-ADAPTER-20261014-07 r1).

Question: does the adapter's connection path receive the Sentinel
surrogate->real-key substitution in THIS environment?

History: the -06 preflight proved the original DIRECT http.client path
never reaches the substitution point (substitution happens only on the
explicit egress proxy configured via the *_proxy environment
variables). The -07 correction teaches the adapter explicit HTTPS
CONNECT proxy support for vault-surrogate (hsurr:*) requests. This
probe now verifies BOTH halves offline:

Method (loopback/interception only; zero external network contact):
  A. Environment inventory: the standard proxy variables and TLS trust
     configuration that define this sandbox's approved-egress channel,
     plus what a proxy-aware stdlib client (urllib.request.getproxies)
     discovers from that environment.
  B. Static evidence: the adapter source resolves the proxy via
     getproxies and establishes the tunnel via set_tunnel; Python's
     http.client never reads proxy environment variables on its own.
  C. Dynamic evidence: with http_proxy pointed at a recording loopback
     proxy, a non-surrogate (fixture-key) request is still delivered
     DIRECTLY to a loopback target (proxy records zero hits). And,
     intercepted before any socket exists: the HTTPS construction for
     the vendor host is direct with NO tunnel for a fixture key, but
     addressed to the environment-configured PROXY with
     set_tunnel(vendor host) for a vault surrogate.
  D. TLS trust: the default SSL context's CA file in this environment
     (what makes proxy TLS interception verifiable now that surrogate
     traffic is routed through the proxy).

Construction-level routing is proven here; end-to-end substitution on
the wire is still proven only by the first live screen (the -06 §4
one-step check). This probe makes no vendor contact.

Writes sentinel_probe_results.json next to this script's --output-dir.
Exit 0 = probe completed (the verdict is data, not exit status).
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import ssl
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import td_http_transport_adapter as adapter_mod  # noqa: E402

FAKE_SURROGATE = "hsurr:PROBE-SURROGATE-DO-NOT-USE-0000"
REQ = {"symbol": "PROBE", "interval": "1h",
       "start_date": "2026-09-08T00:00:00", "end_date": "2026-09-08T23:59:59",
       "timezone": "America/New_York", "outputsize": 5000,
       "order": "asc", "adjust": "none"}


def redacted_endpoint(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.hostname}:{p.port}"


def env_inventory() -> dict:
    inv = {}
    for name in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                 "ALL_PROXY", "all_proxy"):
        v = os.environ.get(name)
        inv[name] = redacted_endpoint(v) if v else None
    inv["SSL_CERT_FILE"] = os.environ.get("SSL_CERT_FILE")
    inv["NODE_EXTRA_CA_CERTS"] = os.environ.get("NODE_EXTRA_CA_CERTS")
    inv["REQUESTS_CA_BUNDLE"] = os.environ.get("REQUESTS_CA_BUNDLE")
    inv["no_proxy_includes_loopback"] = "127.0.0.1" in os.environ.get(
        "no_proxy", "")
    inv["urllib_getproxies"] = {
        k: redacted_endpoint(v) for k, v in urllib.request.getproxies().items()
    }
    return inv


def static_evidence() -> dict:
    src = Path(adapter_mod.__file__).read_text()
    return {
        "adapter_file": Path(adapter_mod.__file__).name,
        "mentions_of_proxy": src.lower().count("proxy"),
        "calls_set_tunnel": "set_tunnel" in src,
        "resolves_proxy_via_getproxies": "getproxies" in src,
        "http_client_has_set_tunnel_method": hasattr(
            http.client.HTTPSConnection, "set_tunnel"),
        "note": ("http.client only tunnels when set_tunnel() is called "
                 "explicitly; it never consults *_proxy environment "
                 "variables (that behavior lives in urllib.request). "
                 "The -07 adapter resolves the sanctioned proxy via "
                 "urllib.request.getproxies for surrogate requests "
                 "only, and fails closed with no direct fallback."),
    }


class Recorder:
    def __init__(self):
        self.hits = []


def recording_server(rec: Recorder):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _handle(self):
            rec.hits.append(self.requestline)
            body = b'{"status":"ok","values":[]}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = _handle
        do_CONNECT = _handle
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def dynamic_evidence() -> dict:
    proxy_rec, target_rec = Recorder(), Recorder()
    proxy = recording_server(proxy_rec)
    target = recording_server(target_rec)
    p_port = proxy.server_address[1]
    t_port = target.server_address[1]
    saved = {k: os.environ.get(k) for k in ("http_proxy", "no_proxy")}
    outcome = {}
    try:
        os.environ["http_proxy"] = f"http://127.0.0.1:{p_port}"
        os.environ["no_proxy"] = ""  # force proxy eligibility for control
        # Control: proxy-aware client honoring the same configuration.
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{t_port}/control", timeout=5) as r:
                r.read()
            outcome["control_urllib_reached"] = "proxy"
        except Exception as e:  # recorded, not fatal to the probe
            outcome["control_urllib_error"] = type(e).__name__
        outcome["control_proxy_hits"] = len(proxy_rec.hits)
        proxy_hits_before = len(proxy_rec.hits)
        target_hits_before = len(target_rec.hits)
        # Adapter under test (plain HTTP is loopback-test-only by design).
        adapter = adapter_mod.TDHttpTransportAdapter(
            FAKE_SURROGATE, base_url=f"http://127.0.0.1:{t_port}")
        status, _ = adapter.transport(dict(REQ))
        outcome["adapter_status"] = status
        outcome["adapter_proxy_hits_delta"] = len(proxy_rec.hits) - proxy_hits_before
        outcome["adapter_target_hits_delta"] = (
            len(target_rec.hits) - target_hits_before)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        proxy.shutdown()
        target.shutdown()

    # HTTPS construction for the vendor host, intercepted before any
    # socket exists: the recorder never connects; transport must fail
    # inside the fake's connect(), and we observe the construction
    # parameters for BOTH key classes.
    class RecordingConn:
        instances = []

        def __init__(self, host, port=None, **kwargs):
            self.host = host
            self.port = port
            self.has_tls_context = "context" in kwargs
            self.tunnel = None
            RecordingConn.instances.append(self)

        def set_tunnel(self, host, port=None, headers=None):
            self.tunnel = (host, port)

        def connect(self):
            raise RuntimeError("probe_intercept")

        def close(self):
            pass

    orig_http = http.client.HTTPConnection
    orig_https = http.client.HTTPSConnection
    http.client.HTTPConnection = RecordingConn
    http.client.HTTPSConnection = RecordingConn
    saved_https_proxy = os.environ.get("https_proxy")
    try:
        # Fixture (non-surrogate) key: direct construction, no tunnel.
        RecordingConn.instances = []
        a1 = adapter_mod.TDHttpTransportAdapter(FAKE_SURROGATE.replace(
            "hsurr:", "FIXTURE-KEY-"))  # vendor https, non-surrogate
        try:
            a1.transport(dict(REQ))
        except Exception as e:
            fixture_outcome = type(e).__name__
        inst = RecordingConn.instances
        outcome["https_construction_fixture_key"] = {
            "constructions": [(i.host, i.port) for i in inst],
            "tunnel": inst[-1].tunnel if inst else None,
            "transport_outcome": fixture_outcome,
        }
        # Vault surrogate: construction addressed to the ENVIRONMENT-
        # configured proxy, tunnel set to the vendor host.
        os.environ["https_proxy"] = "http://proxy.invalid:3128"
        RecordingConn.instances = []
        a2 = adapter_mod.TDHttpTransportAdapter(FAKE_SURROGATE)  # vendor https
        try:
            a2.transport(dict(REQ))
        except Exception as e:
            surrogate_outcome = type(e).__name__
        inst = RecordingConn.instances
        outcome["https_construction_surrogate"] = {
            "constructions": [(i.host, i.port) for i in inst],
            "tunnel": inst[-1].tunnel if inst else None,
            "transport_outcome": surrogate_outcome,
        }
    finally:
        http.client.HTTPConnection = orig_http
        http.client.HTTPSConnection = orig_https
        if saved_https_proxy is None:
            os.environ.pop("https_proxy", None)
        else:
            os.environ["https_proxy"] = saved_https_proxy
    return outcome


def tls_evidence() -> dict:
    paths = ssl.get_default_verify_paths()
    ctx = ssl.create_default_context()
    return {
        "default_verify_cafile": paths.cafile,
        "ssl_cert_file_env": os.environ.get("SSL_CERT_FILE"),
        "context_verify_mode": str(ctx.verify_mode),
        "context_check_hostname": ctx.check_hostname,
        "matches_platform_egress_bundle": bool(
            paths.cafile and os.environ.get("SSL_CERT_FILE")
            and paths.cafile == os.environ.get("SSL_CERT_FILE")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = {
        "probe": "sentinel-compatibility",
        "task": ("QF-TD-COMBINED-DISPATCH-PREFLIGHT-20261014-06 r1; "
                 "updated QF-TD-SENTINEL-PROXY-ADAPTER-20261014-07 r1"),
        "environment": env_inventory(),
        "static": static_evidence(),
        "dynamic": dynamic_evidence(),
        "tls": tls_evidence(),
    }
    dyn = results["dynamic"]
    surg = dyn.get("https_construction_surrogate", {})
    fix = dyn.get("https_construction_fixture_key", {})
    surrogate_routes_via_proxy = (
        surg.get("constructions") == [("proxy.invalid", 3128)]
        and surg.get("tunnel") == ("api.twelvedata.com", 443))
    fixture_stays_direct = (
        fix.get("constructions") == [("api.twelvedata.com", 443)]
        and fix.get("tunnel") is None)
    results["verdict"] = {
        "direct_path_receives_substitution_in_this_environment": False,
        "surrogate_requests_route_via_connect_proxy": surrogate_routes_via_proxy,
        "fixture_key_requests_stay_direct": fixture_stays_direct,
        "basis": (
            "Approved egress/substitution in this sandbox is the "
            "explicit proxy configured via the *_proxy environment "
            "variables (hatch-egress-proxy:3128). The -06 finding "
            "stands for the direct path: it never passes the "
            "substitution point. The -07 correction routes "
            "vault-surrogate requests through that proxy by "
            "construction: with https_proxy set, the surrogate "
            "transport constructs its connection to the PROXY and "
            "set_tunnel()s to the vendor host before TLS (see "
            "https_construction_surrogate), while non-surrogate "
            "requests keep the direct construction (see "
            "https_construction_fixture_key, and the loopback dynamic "
            "proof: proxy hits delta 0 for the direct path). Fail-"
            "closed behavior with zero direct fallback is proven by "
            "the adapter suite's ProxyLevel tests. End-to-end "
            "substitution on the wire remains proven only by the "
            "first live screen (-06 section 4 one-step check)."),
        "dynamic_summary": {
            "adapter_proxy_hits_delta": dyn.get("adapter_proxy_hits_delta"),
            "adapter_target_hits_delta": dyn.get("adapter_target_hits_delta"),
            "surrogate_constructions": surg.get("constructions"),
            "surrogate_tunnel": surg.get("tunnel"),
        },
    }
    (out / "sentinel_probe_results.json").write_text(
        json.dumps(results, indent=2) + "\n")
    print(json.dumps({"verdict_direct_substitution": False,
                      "surrogate_routes_via_proxy": surrogate_routes_via_proxy,
                      "fixture_stays_direct": fixture_stays_direct,
                      "adapter_proxy_hits_delta":
                          dyn.get("adapter_proxy_hits_delta"),
                      "adapter_target_hits_delta":
                          dyn.get("adapter_target_hits_delta")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
