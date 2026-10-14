#!/usr/bin/env python3
"""
td-http-transport-adapter v1.0.0 — implementation of the pinned contract
research_notes/td_acquisition_adapter_preflight_evidence_20261013/adapter_contract.json
(sha256 db6c44a2...), task QF-TD-TRANSPORT-ADAPTER-IMPLEMENT-20261013-03 r1.

The ONLY HTTP transport the accepted collector (td_min_collector.py,
sha256 bd003c3c..., PR #8) may be bound to. Stdlib only (http.client).

Contract properties implemented here:
  - transport(req) -> (status:int, body:bytes); raises TransportError on
    transport-level failure only. ANY HTTP status (incl. 429) is returned
    untouched for the collector to preserve as evidence and HOLD on.
  - Exactly ONE attempt per request. No retries at any layer: this module
    performs a single HTTP exchange per redirect hop and never repeats a
    request after any failure or status.
  - Parameters in the contract's fixed order, values copied verbatim from
    the manifest request; format=JSON; apikey LAST, sourced by the driver
    from the vault-style environment, held in memory only.
  - HTTPS only with certificate verification ON. Plain HTTP is accepted
    ONLY for loopback hosts (local synthetic test servers).
    Cross-host (or scheme-downgrading) redirects fail closed; same-host
    redirects are followed at most MAX_REDIRECTS times within the single
    attempt.
  - Connect timeout 10s / read timeout 30s (separately enforced).
    Response body cap 64 MiB; exceeding it is a transport failure.
  - Sanitized failures: TransportError's message is a category token ONLY
    (e.g. "read_timeout"). No exception, log line, or string produced by
    this module ever contains the API key, the request URL, response
    headers, or credential material. Underlying exceptions are never
    chained (raise ... from None) so tracebacks cannot leak them either.
  - The adapter emits no logs of its own.
"""
from __future__ import annotations

import http.client
import socket
import ssl
from urllib.parse import urlencode, urlsplit

ADAPTER_NAME = "td-http-transport-adapter"
ADAPTER_VERSION = "1.0.0"
VENDOR_BASE_URL = "https://api.twelvedata.com"
ENDPOINT_PATH = "/time_series"
PARAMETER_ORDER = ("symbol", "interval", "start_date", "end_date",
                    "timezone", "outputsize", "order", "adjust",
                    "format", "apikey")
CONNECT_TIMEOUT_SECONDS = 10.0
READ_TIMEOUT_SECONDS = 30.0
MAX_BODY_BYTES = 64 * 1024 * 1024
MAX_REDIRECTS = 3
_REDIRECT_STATUSES = (301, 302, 303, 307, 308)
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


class TransportError(Exception):
    """Sanitized transport-level failure.

    The message is exactly the category token and nothing else, so the
    string form, repr, and traceback of this exception are safe to record
    anywhere (collector lifecycle, run reports, logs)."""

    def __init__(self, category: str):
        super().__init__(category)
        self.category = category


class TDHttpTransportAdapter:
    """Callable transport binding for td_min_collector.Collector."""

    def __init__(self, api_key: str, base_url: str = VENDOR_BASE_URL,
                 connect_timeout: float = CONNECT_TIMEOUT_SECONDS,
                 read_timeout: float = READ_TIMEOUT_SECONDS,
                 max_body_bytes: int = MAX_BODY_BYTES,
                 max_redirects: int = MAX_REDIRECTS):
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("api_key must be a non-empty string")
        parts = urlsplit(base_url)
        host = parts.hostname or ""
        if parts.scheme == "https":
            pass  # the only scheme allowed for non-loopback use
        elif parts.scheme == "http" and host in _LOOPBACK_HOSTS:
            pass  # local synthetic test servers only
        else:
            raise ValueError("base_url must be https (http is loopback-test-only)")
        if not host:
            raise ValueError("base_url has no host")
        self._scheme = parts.scheme
        self._host = host
        self._port = parts.port or (443 if parts.scheme == "https" else 80)
        self._connect_timeout = float(connect_timeout)
        self._read_timeout = float(read_timeout)
        self._max_body_bytes = int(max_body_bytes)
        self._max_redirects = int(max_redirects)
        # Memory only: never written to disk, argv, logs, or exceptions.
        self.__api_key = api_key

    # -- contract-visible pinned defaults (tests assert these) ---------
    @property
    def base_url(self) -> str:
        scheme, host, port = self._scheme, self._host, self._port
        default = 443 if scheme == "https" else 80
        return f"{scheme}://{host}" + ("" if port == default else f":{port}")

    @property
    def connect_timeout(self) -> float:
        return self._connect_timeout

    @property
    def read_timeout(self) -> float:
        return self._read_timeout

    @property
    def max_body_bytes(self) -> int:
        return self._max_body_bytes

    # -- request construction ------------------------------------------
    def _request_path(self, req: dict) -> str:
        try:
            values = {
                "symbol": req["symbol"],
                "interval": req["interval"],
                "start_date": req["start_date"],
                "end_date": req["end_date"],
                "timezone": req["timezone"],
                "outputsize": str(req["outputsize"]),
                "order": req["order"],
                "adjust": req["adjust"],
                "format": "JSON",
                "apikey": self.__api_key,
            }
        except (KeyError, TypeError):
            raise TransportError("malformed_request") from None
        query = urlencode([(k, values[k]) for k in PARAMETER_ORDER])
        return ENDPOINT_PATH + "?" + query

    # -- redirect policy -------------------------------------------------
    def _validate_redirect(self, scheme: str, host: str, port: int,
                           location: str) -> tuple[str, str, int, str]:
        """Same-host only, no scheme downgrade, no userinfo. Relative
        redirects keep the current origin. Anything else fails closed."""
        target = urlsplit(location)
        if target.username or target.password:
            raise TransportError("redirect_rejected")
        if not target.netloc:
            path = target.path or "/"
            if target.query:
                path += "?" + target.query
            return scheme, host, port, path
        t_host = target.hostname or ""
        t_port = target.port or (443 if target.scheme == "https" else 80)
        if target.scheme != scheme or t_host != host or t_port != port:
            raise TransportError("redirect_rejected")
        path = target.path or "/"
        if target.query:
            path += "?" + target.query
        return target.scheme, t_host, t_port, path

    # -- one HTTP exchange ------------------------------------------------
    def _exchange(self, scheme: str, host: str, port: int,
                  path: str) -> tuple[int, dict, bytes]:
        conn_cls = (http.client.HTTPSConnection if scheme == "https"
                    else http.client.HTTPConnection)
        kwargs: dict = {"timeout": self._connect_timeout}
        if scheme == "https":
            # Default context: certificate verification ON, hostname checked.
            kwargs["context"] = ssl.create_default_context()
        conn = conn_cls(host, port, **kwargs)
        phase = "connect"
        try:
            conn.connect()  # connect + (for https) TLS handshake, 10s budget
            if conn.sock is not None:
                conn.sock.settimeout(self._read_timeout)
            phase = "read"
            conn.request("GET", path, headers={"Accept": "application/json"})
            resp = conn.getresponse()
            headers = {k.lower(): v for k, v in resp.getheaders()}
            body = resp.read(self._max_body_bytes + 1)
            if len(body) > self._max_body_bytes:
                raise TransportError("body_cap_exceeded")
            return resp.status, headers, body
        except TransportError:
            raise
        except ssl.SSLError:  # includes CertificateError
            raise TransportError("tls_failure") from None
        except (socket.timeout, TimeoutError):
            raise TransportError(f"{phase}_timeout") from None
        except http.client.HTTPException:
            raise TransportError("protocol_error") from None
        except OSError:
            raise TransportError("connection_error") from None
        finally:
            try:
                conn.close()
            except Exception:
                pass

    # -- the transport callable -------------------------------------------
    def transport(self, req: dict) -> tuple[int, bytes]:
        """One attempt. Returns (status, body) for ANY HTTP response;
        raises TransportError (sanitized category only) on transport
        failure."""
        scheme, host, port = self._scheme, self._host, self._port
        path = self._request_path(req)
        for hop in range(self._max_redirects + 1):
            status, headers, body = self._exchange(scheme, host, port, path)
            if status not in _REDIRECT_STATUSES:
                return status, body
            location = headers.get("location")
            if location is None:
                raise TransportError("redirect_rejected")
            if hop == self._max_redirects:
                raise TransportError("redirect_limit")
            scheme, host, port, path = self._validate_redirect(
                scheme, host, port, location)
        raise TransportError("redirect_limit")  # unreachable

    __call__ = transport
