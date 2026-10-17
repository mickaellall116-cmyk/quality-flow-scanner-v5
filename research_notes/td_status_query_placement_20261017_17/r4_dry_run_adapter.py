#!/usr/bin/env python3
"""r4 dry-run adapter for the -14 live readiness executor.

Wires the executor's dry-run step to the REAL -11 r4 gate
(dispatch_gate_r4.py, b5399645...) through the accepted -11 trial
machinery (run_dispatch_gate_trials_r4.py, 93b911e0...), exactly as
the -11 readiness transaction's happy path did: the gate evaluates
all 12 gates in test mode against an evidence packet whose
ledger_path is the transaction target and whose account section
carries the transaction's status facts, with a recording (never
sending) transport factory. Both pins are verified before import.
Returns the 12 gate results as a list of "PASS"/"FAIL" strings.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG11 = os.path.join(os.path.dirname(HERE),
                     "td_policy_a_live_readiness_packet_20261017_11")
PIN_R4_GATE = "b53996454650dafc77e647a8497eba91beb3785fb52c13d70fa81768fd370117"
PIN_R4_RUNNER = "93b911e067eb6ff6bc7e797b08df44eb1ac17a2417ac2102f3fd347087447864"


def _sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _load_runner():
    gate = os.path.join(PKG11, "dispatch_gate_r4.py")
    runner = os.path.join(PKG11, "run_dispatch_gate_trials_r4.py")
    if _sha256_file(gate) != PIN_R4_GATE:
        raise RuntimeError("PIN_MISMATCH:r4_gate")
    if _sha256_file(runner) != PIN_R4_RUNNER:
        raise RuntimeError("PIN_MISMATCH:r4_runner")
    if PKG11 not in sys.path:
        sys.path.insert(0, PKG11)
    import run_dispatch_gate_trials_r4 as R
    return R


R = _load_runner()


def make_r4_dry_run_hook(packet, target_path, account_raw=None):
    """Returns a hook(evidence_path) -> list of 12 gate results."""
    root = packet["dryrun_root"]

    def hook(_evidence_path):
        t = R.Trial("dryrun", root)
        ev = R.base_evidence(t)
        ev["packet"]["ledger_path"] = target_path
        if account_raw is not None:
            ev["account"] = {"api_usage": dict(account_raw),
                             "source": "readiness_executor"}
        fac = R.RecordingFactory(t)
        res = t.dispatch(R.G.canon(ev), transport_factory=fac)
        return [g["result"] for g in res["receipt"]["gates"]]

    hook.is_r4_adapter = True
    return hook
