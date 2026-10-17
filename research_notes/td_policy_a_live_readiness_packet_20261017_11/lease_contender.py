#!/usr/bin/env python3
"""Contention contender process (r2 trial C01): while the holder holds
the owner lease (blocked inside its transport factory), run the full
wrapper flow for the SAME namespace identity. Must HOLD at gate 8
(OWNER_LEASE_HELD), construct zero transports, and create neither the
namespace nor any ledger change."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dispatch_gate_r4 as G  # noqa: E402


class FakeClock:
    def __init__(self, t):
        self.t = t

    def now(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def main():
    ev_path, out_path = sys.argv[1], sys.argv[2]
    ev_bytes = open(ev_path, "rb").read()
    ev = json.loads(ev_bytes)
    now = ev["packet"]["dispatch_window"]["start"] + 3600
    factory_calls = []

    def factory():
        factory_calls.append(1)
        raise RuntimeError("contender must never construct a transport")

    import hashlib
    _stub = os.path.join(HERE, "helper_stub", "dynamic_credentials.py")
    _stub_sha = hashlib.sha256(open(_stub, "rb").read()).hexdigest()
    res = G.dispatch(ev_bytes, mode="test", clock=FakeClock(now),
                     transport_factory=factory,
                     paths_override={"helper_path": _stub,
                                     "helper_sha256": _stub_sha})
    gates = {x["gate"]: (x["result"], x["code"]) for x in res["receipt"]["gates"]}
    facts = {
        "decision": res["receipt"]["decision"],
        "gate8": list(gates[8]),
        "gates_passed": sum(1 for v in gates.values() if v[0] == "PASS"),
        "factory_calls": len(factory_calls),
        "transport_constructed": res["transport_constructed"],
        "lease_acquired": res["lease_acquired"],
        "namespace_exists_after": os.path.exists(ev["packet"]["state_dir"]),
        "ledger_hash": G.H(open(ev["packet"]["ledger_path"], "rb").read()),
    }
    with open(out_path, "w") as f:
        f.write(json.dumps(facts, sort_keys=True))
    print(json.dumps(facts, sort_keys=True))


if __name__ == "__main__":
    main()
