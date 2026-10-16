"""Real-process worker for the -19 r3 finalization fixture.

Modes:
  hold       -- first transport call blocks until a release marker appears;
                proves the journal-fd flock is held by a live owner.
  crash      -- die via os._exit(3) inside the first transport call, after
                the fsynced ATTEMPT record.
  plant-temp -- during call 1, plant a sentinel temp for SYMS[1] in raw/;
                SYMS[1]'s finalize must hit HOLD:TEMP_COLLISION post-ATTEMPT.
  plant-final-- during call 1, plant a sentinel final for SYMS[1]; finalize
                must hit HOLD:FINAL_COLLISION post-ATTEMPT.
  plant-race -- during call 1 (SYMS[1] gets a large payload), a watcher
                thread creates raw/<SYMS[1]>.csv the moment the executor's
                temp appears — the destination races in AFTER the absence
                check and must never be overwritten (HOLD:FINAL_COLLISION).
  swapctrl   -- during call 1, rename <cid>.control aside and symlink it to
                an evil dir; appends must stay on the pinned journal fd.
  swaproot   -- during call 1, rename <cid> aside and symlink it to an evil
                dir; the run must end HOLD:PATH_RACE with no escape.

Sockets are denied before the executor is imported. Usage:
  proc_worker3.py MODE BASE CAPTURE_ID CANDIDATE MARKER_DIR [EVIL_DIR]
Writes MARKER_DIR/result.json.
"""
import hashlib
import importlib.util
import json
import os
import socket
import sys
import threading
import time
from datetime import datetime, timedelta, timezone


def _denied(*a, **k):
    raise RuntimeError("socket access denied by fixture worker")


socket.socket = _denied
socket.create_connection = _denied
socket.getaddrinfo = _denied

HERE = os.path.dirname(os.path.abspath(__file__))
EXEC_PATH = os.path.join(HERE, "clean_capture_executor_h19r3.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ex = _load("clean_capture_executor_h19r3", EXEC_PATH)
PLAN = None


class RealClock:
    def now(self):
        return time.time()

    def sleep(self, s):
        time.sleep(s)

    def iso(self):
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gen_bars(sym, rows=120, pad_ts=0):
    seed = int(hashlib.sha256(sym.encode()).hexdigest()[:8], 16)
    base = 100.0 + (seed % 500) / 10.0
    t0 = datetime(2024, 10, 18, 13, 30, tzinfo=timezone.utc)
    out = []
    for i in range(rows):
        ts = (t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ") + "X" * pad_ts
        o = base + (i % 7) * 0.25
        out.append({"Datetime": ts, "Open": o, "High": o + 0.5, "Low": o - 0.5,
                    "Close": o + 0.25, "Volume": 1000 + i,
                    "Dividends": 0, "Stock Splits": 0})
    return out


def good_resp(req, rows=120, pad_ts=0):
    sess = req["session"]
    meta = {"session": sess, "class": req["class"],
            "exchange": "XNYS" if sess == "XNYS" else "CCC",
            "timezone": "America/New_York" if sess == "XNYS" else "UTC",
            "currency": "USD", "source": "synthetic-fixture"}
    return {"status": 200, "symbol": req["symbol"], "meta": meta,
            "bars": gen_bars(req["symbol"], rows, pad_ts), "end_covered": True}


def main():
    global PLAN
    mode, base, cid, candidate, marker = sys.argv[1:6]
    evil = sys.argv[6] if len(sys.argv) > 6 else None
    os.makedirs(marker, exist_ok=True)
    PLAN = ex.load_plan(candidate)
    syms = [p["symbol"] for p in PLAN]
    clock = RealClock()
    calls = []

    def transport(req):
        calls.append(req["symbol"])
        n = len(calls)
        if mode == "crash" and n == 1:
            with open(os.path.join(marker, "started"), "w") as f:
                f.write("x")
            os._exit(3)
        if mode == "hold" and n == 1:
            with open(os.path.join(marker, "started"), "w") as f:
                f.write("x")
            deadline = time.time() + 60
            while not os.path.exists(os.path.join(marker, "release")):
                if time.time() > deadline:
                    raise RuntimeError("release marker timeout")
                time.sleep(0.05)
        if mode in ("plant-temp", "plant-final") and n == 1:
            raw = os.path.join(base, cid, "raw")
            name = ("." + syms[1] + ".csv.tmp") if mode == "plant-temp" \
                else (syms[1] + ".csv")
            with open(os.path.join(raw, name), "wb") as f:
                f.write(b"SENTINEL-PLANTED")
            with open(os.path.join(marker, "planted"), "w") as f:
                f.write(name)
        if mode == "plant-race" and n == 2:
            raw = os.path.join(base, cid, "raw")
            tmp = os.path.join(raw, "." + syms[1] + ".csv.tmp")
            dst = os.path.join(raw, syms[1] + ".csv")

            def watcher():
                deadline = time.time() + 30
                while time.time() < deadline:
                    if os.path.exists(tmp):
                        with open(dst, "wb") as f:
                            f.write(b"SENTINEL-RACED-DEST")
                        with open(os.path.join(marker, "raced"), "w") as f:
                            f.write("x")
                        return
                    time.sleep(0.0002)

            threading.Thread(target=watcher, daemon=True).start()
            return good_resp(req, rows=19999, pad_ts=40)
        if mode == "swapctrl" and n == 1:
            ctrl = os.path.join(base, cid + ".control")
            os.rename(ctrl, ctrl + "_moved")
            os.symlink(evil, ctrl)
            with open(os.path.join(marker, "swapped"), "w") as f:
                f.write("x")
        if mode == "swaproot" and n == 1:
            root = os.path.join(base, cid)
            os.rename(root, root + "_moved")
            os.symlink(evil, root)
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
