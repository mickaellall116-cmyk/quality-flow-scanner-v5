#!/usr/bin/env python3
"""Child-process recovery driver for the -14 trials.

Config: {workdir, target, swap: none|journal|ledger, result_file}.
With a swap mode, the mutation is applied via recover_live's
after_precheck_hook -- i.e. strictly between the binding precheck and
lock acquisition -- to prove the under-lock revalidation catches it.
Writes the recovery classification as JSON.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_readiness_executor as EX  # noqa: E402


def main():
    cfg = json.loads(open(sys.argv[1], "rb").read().decode())
    workdir, target = cfg["workdir"], cfg["target"]
    hook = None
    if cfg.get("swap") == "journal":
        def hook():
            p = os.path.join(workdir, "journal.json")
            st = json.loads(open(p, "rb").read().decode())
            st["backup_path"] = os.path.join(workdir, "evil_backup.bin")
            with open(p, "wb") as f:
                f.write(EX.canon(st))
    elif cfg.get("swap") == "ledger":
        def hook():
            with open(target, "wb") as f:
                f.write(b"drifted-bytes-not-original-not-candidate")
    res = EX.recover_live(workdir, target, after_precheck_hook=hook)
    with open(cfg["result_file"], "w") as f:
        f.write(json.dumps(res, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
