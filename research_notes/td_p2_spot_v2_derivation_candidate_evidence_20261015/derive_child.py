#!/usr/bin/env python3
"""QF-TD-...-06 r1 child process: derivation / run in a fresh process.

Used by the suite driver for crash injection, concurrency and
library-absent proofs. Network is stubbed to raise before any import of
the collector. Prints one normalized JSON line (no timestamps/paths).

Modes:
  derive [--crash STAGE] [--sleep STAGE:SECONDS]
  run-closed   (fake transport: closed-session body for REQ-SPT-08 only)
Env: PF06_BLOCK_MCAL=1 blocks pandas_market_calendars imports.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import socket
import sys
import time


def _no_net(*a, **k):
    raise RuntimeError("network disabled (PF06 child)")


socket.socket.connect = _no_net
socket.socket.connect_ex = _no_net
socket.create_connection = _no_net
socket.getaddrinfo = _no_net

if os.environ.get("PF06_BLOCK_MCAL") == "1":
    class _Blocker:
        def find_spec(self, name, path=None, target=None):
            if name == "pandas_market_calendars":
                raise ImportError("pandas_market_calendars blocked (PF06 fixture)")
            return None

    sys.meta_path.insert(0, _Blocker())

P = argparse.ArgumentParser()
P.add_argument("mode", choices=["derive", "run-closed"])
P.add_argument("--candidate-dir", required=True)
P.add_argument("--supplement", required=True)
P.add_argument("--manifest", required=True)
P.add_argument("--state-dir", required=True)
P.add_argument("--root", required=True)
P.add_argument("--crash", default=None)
P.add_argument("--sleep", default=None)
A = P.parse_args()

CAND = pathlib.Path(A.candidate_dir).resolve()
sys.path.insert(0, str(CAND.parent / "pilot_harness"))
spec = importlib.util.spec_from_file_location("pf06_child_collector", CAND / "td_min_collector.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from rate_limiter import RollingCreditLimiter

SUP = json.loads(pathlib.Path(A.supplement).read_text())
MAN = json.loads(pathlib.Path(A.manifest).read_text())
ROOT = pathlib.Path(A.root)
EPOCH = 1792000000


def make(transport=None):
    lim = RollingCreditLimiter(8, 800, state_path=ROOT / "shared_credit.json",
                               clock=lambda: EPOCH)
    return mod.Collector(pathlib.Path(A.state_dir), MAN, lim, transport=transport,
                         prereq_path=ROOT / "prereq.json",
                         closed_session_supplement=SUP)


def out(doc):
    print(json.dumps(doc, sort_keys=True))


if A.mode == "derive":
    hook = None
    if A.crash or A.sleep:
        def hook(stage):
            if A.sleep:
                s_stage, s_secs = A.sleep.split(":")
                if stage == s_stage:
                    time.sleep(float(s_secs))
            if A.crash and stage == A.crash:
                os._exit(3)
    try:
        c = make()
        res = c.derive_closed_session(hook=hook)
        out({"mode": "derive", "outcome": res["outcome"], "derived": res["derived"]})
    except Exception as e:
        out({"mode": "derive", "error": f"{type(e).__name__}: {e}"})
else:
    calls = []

    def transport(req):
        calls.append(req["request_id"])
        if req["request_id"] != "REQ-SPT-08":
            raise AssertionError(f"unexpected dispatch {req['request_id']}")
        return 400, json.dumps(
            {"code": 400, "message": mod.CLOSED_SESSION_MESSAGE, "status": "error",
             "meta": {"symbol": req["symbol"], "interval": "1h", "exchange": ""}}).encode()

    try:
        c = make(transport)
        res = c.run()
        out({"mode": "run-closed", "outcome": res["outcome"], "calls": calls,
             "dispatched": res["dispatched"], "reused": res["reused"],
             "closed_day_evidenced": res["closed_day_evidenced"]})
    except Exception as e:
        out({"mode": "run-closed", "error": f"{type(e).__name__}: {e}", "calls": calls})
