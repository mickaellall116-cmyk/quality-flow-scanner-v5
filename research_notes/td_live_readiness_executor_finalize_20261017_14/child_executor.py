#!/usr/bin/env python3
"""Child-process executor driver for the -14 concurrency/crash trials.

Reads a JSON config: {packet, spy_kind, counter_file, crash_at,
go_file, pause_locks:{signal, release}, result_file}. Builds offline
fixture hooks (spy transport counting invocations into counter_file),
optionally waits for go_file, optionally pauses after locks are held,
runs the integrated executor, and writes the outcome as JSON. A crash
injection (os._exit) simply kills this process with the injected code.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_readiness_executor as EX  # noqa: E402

NOW = 1792224000  # aligns with the -14 runner / -11 fixture clock


def fmt(ts):
    import datetime
    return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


RAW = {
    "pass": {"timestamp": fmt(NOW - 60), "current_usage": 0,
             "plan_limit": 8, "daily_usage": 100, "plan_daily_limit": 800,
             "plan_category": "basic"},
    "edge": {"timestamp": fmt(NOW - 60), "current_usage": 0,
             "plan_limit": 8, "daily_usage": 748, "plan_daily_limit": 800,
             "plan_category": "basic"},
    "fail": {"timestamp": fmt(NOW - 60), "current_usage": 0,
             "plan_limit": 8, "daily_usage": 760, "plan_daily_limit": 800,
             "plan_category": "basic"},
}


class FileSpy:
    def __init__(self, kind, counter_file):
        self.kind = kind
        self.counter_file = counter_file
        self.calls = 0

    def http_get(self, url):
        self.calls += 1
        with open(self.counter_file, "a") as f:
            f.write("1\n")
        return 200, EX.canon(RAW[self.kind])


def main():
    cfg = json.loads(open(sys.argv[1], "rb").read().decode())
    if cfg.get("go_file"):
        for _ in range(600):
            if os.path.exists(cfg["go_file"]):
                break
            time.sleep(0.1)
    spy = FileSpy(cfg.get("spy_kind", "pass"), cfg["counter_file"])
    hooks = {"fixture": True, "clock": lambda: NOW, "transport": spy,
             "dry_run": lambda ev: ["PASS"] * 12}
    if cfg.get("crash_at"):
        hooks["crash_at"] = cfg["crash_at"]
    if cfg.get("pause_locks"):
        sig, rel = cfg["pause_locks"]["signal"], cfg["pause_locks"]["release"]

        def pause():
            with open(sig, "w") as f:
                f.write("locked")
            for _ in range(600):
                if os.path.exists(rel):
                    return
                time.sleep(0.1)
            raise RuntimeError("pause timeout")
        hooks["pause_at_locks"] = pause
    ex = EX.LiveReadinessExecutor(cfg["packet"], hooks)
    try:
        out = ex.run()
        out = dict(out)
    except EX.Refusal as e:
        out = {"outcome": "REFUSED", "reason": e.code}
    out["spy_calls"] = spy.calls
    with open(cfg["result_file"], "w") as f:
        f.write(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
