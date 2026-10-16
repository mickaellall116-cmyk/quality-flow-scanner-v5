"""Real-process worker for the -19 r4 atomicity fixture.

Modes:
  hold            -- first transport call blocks until a release marker
                     appears; proves the control-dir fence + journal-fd
                     lock are held by a live owner.
  plain           -- ordinary full run (used as the contender).
  swapjournal-empty -- during call 1, replace the journal pathname with a
                     NEW EMPTY file (original renamed aside to .orig).
  swapjournal-copy  -- during call 1, replace the journal pathname with a
                     byte copy of its current records (.orig kept aside).
  swapjournal-link  -- during call 1, replace the journal pathname with a
                     symlink to a byte copy (.orig kept aside).

Sockets are denied before the executor is imported. Usage:
  proc_worker4.py MODE BASE CAPTURE_ID CANDIDATE MARKER_DIR
Writes MARKER_DIR/result.json.
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
EXEC_PATH = os.path.join(HERE, "clean_capture_executor_h19r4.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ex = _load("clean_capture_executor_h19r4", EXEC_PATH)
PLAN = None


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


def good_resp(req, rows=120):
    sess = req["session"]
    meta = {"session": sess, "class": req["class"],
            "exchange": "XNYS" if sess == "XNYS" else "CCC",
            "timezone": "America/New_York" if sess == "XNYS" else "UTC",
            "currency": "USD", "source": "synthetic-fixture"}
    return {"status": 200, "symbol": req["symbol"], "meta": meta,
            "bars": gen_bars(req["symbol"], rows), "end_covered": True}


def main():
    global PLAN
    mode, base, cid, candidate, marker = sys.argv[1:6]
    os.makedirs(marker, exist_ok=True)
    PLAN = ex.load_plan(candidate)
    clock = RealClock()
    calls = []
    jpath = os.path.join(base, cid + ".control", ex.JOURNAL_NAME)

    def transport(req):
        calls.append(req["symbol"])
        n = len(calls)
        if n == 1 and mode == "hold":
            with open(os.path.join(marker, "started"), "w") as f:
                f.write("x")
            deadline = time.time() + 60
            while not os.path.exists(os.path.join(marker, "release")):
                if time.time() > deadline:
                    raise RuntimeError("release marker timeout")
                time.sleep(0.05)
        if n == 1 and mode.startswith("swapjournal-"):
            data = open(jpath, "rb").read()
            os.rename(jpath, jpath + ".orig")
            kind = mode.split("-", 1)[1]
            if kind == "empty":
                open(jpath, "wb").close()
            elif kind == "copy":
                with open(jpath, "wb") as f:
                    f.write(data)
            elif kind == "link":
                copy = os.path.join(marker, "journal_copy.qfj2")
                with open(copy, "wb") as f:
                    f.write(data)
                os.symlink(copy, jpath)
            with open(os.path.join(marker, "swapped"), "w") as f:
                f.write(kind)
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
