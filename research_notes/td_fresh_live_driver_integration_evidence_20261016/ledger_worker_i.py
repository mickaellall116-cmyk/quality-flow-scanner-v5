#!/usr/bin/env python3
"""Real-process worker for the r2 cross-process limiter trials.

Runs as a separate OS process against ONE account-shared limiter ledger.
Usage:
  ledger_worker.py <driver_dir> <ledger_path> <out_json> <prefix>
                   <attempts> <start_ts> [go_file] [crash_after_ok]

Reserves <attempts> credits of weight 1 at a fixed FakeClock start time,
optionally waiting for a go-file barrier so sibling processes race, and
optionally dying hard (os._exit(42), no cleanup, no output) after
<crash_after_ok> successful reservations to model process death.
On normal completion writes {"ok": n, "wait": n, "refused_day": n,
"ok_rids": [...]} to <out_json>.
"""
import json
import os
import sys
import time

sys.path.insert(0, sys.argv[1])
import live_driver as D


def main():
    ledger_path, out_json, prefix = sys.argv[2], sys.argv[3], sys.argv[4]
    attempts, start_ts = int(sys.argv[5]), int(sys.argv[6])
    go_file = sys.argv[7] if len(sys.argv) > 7 and sys.argv[7] != "-" else None
    crash_after = int(sys.argv[8]) if len(sys.argv) > 8 else 0
    if go_file:
        deadline = time.time() + 30
        while not os.path.exists(go_file):
            if time.time() > deadline:
                raise SystemExit("go-file timeout")
            time.sleep(0.01)
    clock = D.FakeClock(start_ts)
    lim = D.Limiter(ledger_path)
    ok, wait, refused, ok_rids = 0, 0, 0, []
    for i in range(attempts):
        rid = "%s-%02d" % (prefix, i)
        res, _rel = lim.reserve(rid, 1, clock)
        if res == "OK":
            ok += 1
            ok_rids.append(rid)
            if crash_after and ok >= crash_after:
                os._exit(42)  # process death: no cleanup, lock dies with us
        elif res == "WAIT":
            wait += 1
        else:
            refused += 1
    with open(out_json, "w") as f:
        f.write(json.dumps({"ok": ok, "wait": wait, "refused_day": refused,
                            "ok_rids": ok_rids}, sort_keys=True))


if __name__ == "__main__":
    main()
