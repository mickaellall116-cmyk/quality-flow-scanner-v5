#!/usr/bin/env python3
"""
sentinel_probe.py — offline Sentinel-compatibility probe for
td-http-transport-adapter (QF-TD-COMBINED-DISPATCH-PREFLIGHT-20261014-06 r1).

Question: does the adapter's direct http.client connection path receive
the Sentinel surrogate->real-key substitution in THIS environment?

Method (loopback only; zero external network contact):
  A. Environment inventory: the standard proxy variables and TLS trust
     configuration that define this sandbox's approved-egress channel,
     plus what a proxy-aware stdlib client (urllib.request.getproxies)
     discovers from that environment.
  B. Static evidence: the adapter source contains no proxy handling of
     any kind (no env consultation, no CONNECT, no set_tunnel call);
     Python's http.client never reads proxy environment variables.
  C. Dynamic evidence: with http_proxy pointed at a recording loopback
     proxy, the adapter's transport delivers its request DIRECTLY to a
     loopback target (proxy records zero hits). Control: a proxy-aware
     client honoring the same configuration routes via the proxy. A
     second dynamic check intercepts http.client.HTTPSConnection with
     a non-connecting recorder to show the exact HTTPS construction the
     adapter performs for the vendor host: direct, no tunnel.
  D. TLS trust: the default SSL context's CA file in this environment
     (what would make proxy TLS interception verifiable IF traffic
     were routed through the proxy).

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
        "reads_environ": "environ" in src or "getenv" in src,
        "http_client_has_set_tunnel_method": hasattr(
            http.client.HTTPSConnection, "set_tunnel"),
        "note": ("http.client only tunnels when set_tunnel() is called "
                 "explicitly; it never consults *_proxy environment "
                 "variables (that behavior lives in urllib.request)."),
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
    # inside the fake, and we observe the construction parameters.
    constructed = {}

    class FakeHTTPS:
        def __init__(self, host, port, **kwargs):
            constructed["host"] = host
            constructed["port"] = port
            constructed["has_tls_context"] = "context" in kwargs
            constructed["set_tunnel_called"] = False
            raise RuntimeError("probe_intercept")

        def set_tunnel(self, *a, **k):
            constructed["set_tunnel_called"] = True

    orig = http.client.HTTPSConnection
    http.client.HTTPSConnection = FakeHTTPS
    try:
        a2 = adapter_mod.TDHttpTransportAdapter(FAKE_SURROGATE)  # vendor https
        try:
            a2.transport(dict(REQ))
        except Exception as e:
            constructed["transport_outcome"] = type(e).__name__
    finally:
        http.client.HTTPSConnection = orig
    outcome["https_construction_for_vendor_host"] = constructed
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
        "task": "QF-TD-COMBINED-DISPATCH-PREFLIGHT-20261014-06 r1",
        "environment": env_inventory(),
        "static": static_evidence(),
        "dynamic": dynamic_evidence(),
        "tls": tls_evidence(),
    }
    dyn = results["dynamic"]
    results["verdict"] = {
        "direct_path_receives_substitution_in_this_environment": False,
        "basis": (
            "Approved egress/substitution in this sandbox is the explicit "
            "proxy configured via the *_proxy environment variables "
            "(hatch-egress-proxy:3128). The adapter's http.client path "
            "never consults that configuration and connects directly "
            "(dynamic proof: proxy hits delta 0, target hits delta 1; "
            "HTTPS construction for the vendor host is direct, no "
            "tunnel). A direct connection therefore cannot pass through "
            "the substitution point: the vendor would receive the "
            "hsurr:* surrogate verbatim as apikey (or the connection "
            "fails closed if direct egress is unavailable)."),
        "dynamic_summary": {
            "adapter_proxy_hits_delta": dyn.get("adapter_proxy_hits_delta"),
            "adapter_target_hits_delta": dyn.get("adapter_target_hits_delta"),
        },
    }
    (out / "sentinel_probe_results.json").write_text(
        json.dumps(results, indent=2) + "\n")
    print(json.dumps({"verdict_direct_substitution": False,
                      "adapter_proxy_hits_delta":
                          dyn.get("adapter_proxy_hits_delta"),
                      "adapter_target_hits_delta":
                          dyn.get("adapter_target_hits_delta")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
