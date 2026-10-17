#!/usr/bin/env python3
"""Crash-injection child for T20: hard-exits (os._exit(42), no cleanup)
inside the transaction at the named point, simulating a process kill.

  crash_child.py <status|postwrite> <workdir>

mode=status:    the fixture status hook exits mid-call (before adoption)
mode=postwrite: the consumer-verify hook exits AFTER the atomic replace
                (adoption complete on disk, no terminal record)
"""
import os
import sys

PKG = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PKG)
import readiness_transaction as TX  # noqa: E402
import run_readiness_trials as RT  # noqa: E402


def main():
    mode, workdir = sys.argv[1], sys.argv[2]
    os.makedirs(workdir, exist_ok=True)
    pk = RT.build_packet(workdir)
    hooks = RT.Hooks()
    if mode == "status":
        def dying_status():
            sys.stdout.flush()
            os._exit(42)
        dying_status.is_fixture = True
        hooks.status_call = dying_status
    elif mode == "postwrite":
        def dying_verify(_path):
            sys.stdout.flush()
            os._exit(42)
        hooks.consumer_verify = dying_verify
    else:
        raise SystemExit("unknown mode")
    txn = TX.ReadinessTransaction(workdir, pk, hooks)
    txn.run()
    print("child completed without crash (unexpected)")


if __name__ == "__main__":
    main()
