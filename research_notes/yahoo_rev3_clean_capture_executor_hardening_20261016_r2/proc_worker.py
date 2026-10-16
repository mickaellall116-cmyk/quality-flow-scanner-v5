"""Real-process worker for the -19 r2 hardening fixture.

Modes:
  hold  -- run a capture whose first transport call blocks until a release
           marker appears; proves a live owner holds the flock throughout.
  crash -- die via os._exit(3) inside the first transport call, i.e. after
           the fsynced ATTEMPT record and before any finalization.
  swap  -- during the first transport call, rename root/raw aside and put a
           symlink root/raw -> <target> in its place; the run must end in a
           named HOLD and write nothing through the symlink.

Sockets are denied before the executor is imported. Usage:
  proc_worker.py MODE BASE CAPTURE_ID CANDIDATE MARKER_DIR [SWAP_TARGET]
Writes MARKER_DIR/result.json in hold/swap modes.
"""
import hashlib
import importlib.util
import json
import os
import socket
import sys
import time
from datetime import datetime, timedelta, timezone


def _denied(*a, **k):
    raise RuntimeError("socket access denied by fixture worker")


socket.socket = _denied
socket.create_connection = _denied
socket.getaddrinfo = _denied

HERE = os.path.dirname(os.path.abspath(__file__))
EXEC_PATH = os.path.join(HERE, "clean_capture_executor_h19r2.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ex = _load("clean_capture_executor_h19r2", EXEC_PATH)


class RealClock:
    def now(self):
        return time.time()

    def sleep(self, s):
        time.sleep(s)

    def iso(self):
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gen_bars(sym, rows=120):
    seed = int(hashlib.sha256(sym.encode()).hexdigest()[:8], 16)
    base = 100.0 + (seed % 500) / 10.0
    t0 = datetime(2024, 10, 18, 13, 30, tzinfo=timezone.utc)
    out = []
    for i in range(rows):
        ts = (t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        o = base + (i % 7) * 0.25
        out.append({"Datetime": ts, "Open": o, "High": o + 0.5, "Low": o - 0.5,
                    "Close": o + 0.25, "Volume": 1000 + i,
                    "Dividends": 0, "Stock Splits": 0})
    return out


def good_resp(req):
    sess = req["session"]
    meta = {"session": sess, "class": req["class"],
            "exchange": "XNYS" if sess == "XNYS" else "CCC",
            "timezone": "America/New_York" if sess == "XNYS" else "UTC",
            "currency": "USD", "source": "synthetic-fixture"}
    return {"status": 200, "symbol": req["symbol"], "meta": meta,
            "bars": gen_bars(req["symbol"]), "end_covered": True}


def main():
    mode, base, cid, candidate, marker = sys.argv[1:6]
    swap_target = sys.argv[6] if len(sys.argv) > 6 else None
    os.makedirs(marker, exist_ok=True)
    clock = RealClock()
    calls = []

    def note():
        with open(os.path.join(marker, "calls.json"), "w") as f:
            json.dump({"calls": len(calls), "symbols": list(calls)}, f)

    def transport(req):
        calls.append(req["symbol"])
        note()
        if mode == "crash" and len(calls) == 1:
            with open(os.path.join(marker, "started"), "w") as f:
                f.write("x")
            os._exit(3)   # death after fsynced ATTEMPT, before finalization
        if mode == "hold" and len(calls) == 1:
            with open(os.path.join(marker, "started"), "w") as f:
                f.write("x")
            deadline = time.time() + 60
            while not os.path.exists(os.path.join(marker, "release")):
                if time.time() > deadline:
                    raise RuntimeError("release marker timeout")
                time.sleep(0.05)
        if mode == "swap" and len(calls) == 1:
            raw = os.path.join(base, cid, "raw")
            os.rename(raw, raw + "_moved")
            os.symlink(swap_target, raw)
            with open(os.path.join(marker, "swapped"), "w") as f:
                f.write("x")
        return good_resp(req)

    out = {"mode": mode, "calls": 0}
    try:
        res = ex.run_capture(candidate, base, cid, transport, clock,
                             ex.Limiter(clock))
        out.update(status=res["status"], code=res["code"])
    except ex.HoldError as e:
        out.update(hold=e.code, detail=e.detail)
    out["calls"] = len(calls)
    with open(os.path.join(marker, "result.json"), "w") as f:
        json.dump(out, f)


if __name__ == "__main__":
    main()
