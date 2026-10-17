#!/usr/bin/env python3
"""Contention holder process (r2 trial C01): runs the full wrapper
dispatch in test mode with the stub helper importable and a transport
factory that (a) records that the owner lease is HELD at the instant
of transport construction (an independent probe fd in the same process
is refused the flock), (b) signals readiness, then (c) blocks until
the contender has finished, before returning the fake transport."""
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dispatch_gate_r4 as G  # noqa: E402

NOTES = os.path.join(HERE, "..")
DRIVER_PATH = os.path.join(NOTES, "td_fresh_live_driver_integration_evidence_20261016", "live_driver.py")
spec = importlib.util.spec_from_file_location("qf_live_driver_holder", DRIVER_PATH)
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)


class FakeClock:
    def __init__(self, t):
        self.t = t

    def now(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def main():
    trial_dir, ev_path, ready_path, go_path, out_path = sys.argv[1:6]
    ev_bytes = open(ev_path, "rb").read()
    ev = json.loads(ev_bytes)
    now = ev["packet"]["dispatch_window"]["start"] + 3600
    facts = {}

    def factory():
        import fcntl
        lease_path = G.lease_path_for(ev["packet"]["state_dir"])
        fd = os.open(lease_path, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            facts["lease_held_at_construction"] = False
            fcntl.flock(fd, fcntl.LOCK_UN)
        except BlockingIOError:
            facts["lease_held_at_construction"] = True
        os.close(fd)
        facts["receipt_pass_durable_at_construction"] = (
            json.loads(open(ev["packet"]["receipt_path"], "rb").read())["decision"] == "PASS")
        with open(ready_path, "w") as f:
            f.write("ready")
        deadline = time.time() + 120
        while not os.path.exists(go_path):
            if time.time() > deadline:
                raise RuntimeError("contender never finished")
            time.sleep(0.05)
        return D.FakeTransport()

    tok = G.make_dispatch_token(ev["packet"]["run_id"], ev["packet"]["manifest_digest"],
                                G.H(ev_bytes), ev["packet"]["ledger_path"],
                                ev["packet"]["dispatch_window"])
    import hashlib
    _stub = os.path.join(HERE, "helper_stub", "dynamic_credentials.py")
    _stub_sha = hashlib.sha256(open(_stub, "rb").read()).hexdigest()
    res = G.dispatch(ev_bytes, dispatch_token=tok, mode="test",
                     clock=FakeClock(now), transport_factory=factory,
                     paths_override={"helper_path": _stub,
                                     "helper_sha256": _stub_sha})
    facts["decision"] = res["receipt"]["decision"]
    facts["lease_acquired"] = res["lease_acquired"]
    facts["outcome"] = res["outcome"]["outcome"] if res["outcome"] else None
    facts["transport_calls"] = len(res["outcome"]["transport_calls"]) if res["outcome"] else 0
    facts["reservations"] = res["outcome"]["reservations"] if res["outcome"] else 0
    _log = os.path.join(HERE, "helper_stub", "calls.jsonl")
    try:
        facts["helper_invoked_by_gate_or_holder"] = sum(1 for _ in open(_log))
    except Exception:
        facts["helper_invoked_by_gate_or_holder"] = 0
    with open(out_path, "w") as f:
        f.write(json.dumps(facts, sort_keys=True))
    print(json.dumps(facts, sort_keys=True))


if __name__ == "__main__":
    main()
