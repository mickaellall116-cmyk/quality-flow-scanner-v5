"""Synthetic transport/clock module for probe_runner CLI tests.

Loaded by probe_runner --transport-module. Construction of either
transport appends a line to the file named by env TD_FAKE_MARKER, so
tests can prove the runner's scope checks run BEFORE any transport
construction. No network, no credentials — all responses are canned
synthetic bytes.
"""

import json
import os
import urllib.parse


def _mark(name):
    marker = os.environ.get("TD_FAKE_MARKER")
    if marker:
        with open(marker, "a", encoding="utf-8") as f:
            f.write(name + "\n")


def _payload(symbol):
    bars = []
    for i, dt in enumerate(("2024-06-07 09:30:00",
                            "2024-06-07 10:30:00",
                            "2024-06-10 09:30:00")):
        px = str(100 + i)
        bars.append({"datetime": dt, "open": px, "high": px,
                     "low": px, "close": px, "volume": "1000"})
    obj = {"meta": {"symbol": symbol, "interval": "1h"},
           "values": bars, "status": "ok"}
    return json.dumps(obj, sort_keys=True).encode()


class FakeDataTransport:
    def __init__(self):
        self.calls = []

    def fetch(self, url):
        self.calls.append(url)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        return 200, {"content-type": "application/json"}, \
            _payload(q["symbol"][0])


class FakeUsageTransport:
    def fetch(self, url):
        status = int(os.environ.get("TD_FAKE_USAGE_STATUS", "200"))
        if status != 200:
            return status, {}, b'{"status":"error"}'
        return 200, {"content-type": "application/json"}, json.dumps(
            {"current_usage": 3, "plan_limit": 800}).encode()


def make_data_transport():
    _mark("data_transport_constructed")
    return FakeDataTransport()


def make_usage_transport():
    _mark("usage_transport_constructed")
    return FakeUsageTransport()


class FakeClock:
    def __init__(self, start, step=7.0):
        self.t = start
        self.step = step

    def __call__(self):
        v = self.t
        self.t += self.step
        return v


def make_clock():
    return FakeClock(float(os.environ.get("TD_FAKE_NOW_S",
                                          "1700000000")))


def make_sleeper():
    return lambda s: None
