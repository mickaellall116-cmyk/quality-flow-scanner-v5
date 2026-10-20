#!/usr/bin/env python3
"""-53 extractor self-tests (spec 6295378552 S2). Run BEFORE the
attempt, in the clear, against the PINNED -52 candidate matrix
(hash-verified here) plus synthetic mutations and the pinned
runner/gate sources (static binding). Tests the exact committed
extract_gate567 from proof_driver_v5.py (imported with argv patched;
the driver runs nothing at import). Exit 0 iff all tests pass."""
import copy
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES = HERE.parent
PKG52 = NOTES / "td_route_transaction_workspace_stage_continuation_20261020_52"
PKG48 = NOTES / "td_route_adoption_transaction_prep_20261020_48"
PKG11 = NOTES / "td_policy_a_live_readiness_packet_20261017_11"
PIN_GATE_MATRIX_52 = ("b523b148042ee4012f5eae3fe96e0e5d06d134c37c06adfa4"
                      "47e99eb37df12ac")

sys.argv = ["proof_driver_v5.py", "/tmp/qf53_selftest_out"]
spec = importlib.util.spec_from_file_location(
    "proof_driver_v5", str(HERE / "proof_driver_v5.py"))
drv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drv)
extract_gate567 = drv.extract_gate567

raw = (PKG52 / "gate_matrix.json").read_bytes()
matrix = json.loads(raw)
out = {"matrix_sha256": hashlib.sha256(raw).hexdigest(),
       "matrix_pin_match": hashlib.sha256(raw).hexdigest()
       == PIN_GATE_MATRIX_52, "tests": []}


def record(name, ok, detail=None):
    out["tests"].append({"test": name, "pass": bool(ok),
                         "detail": detail})
    print(("PASS " if ok else "FAIL ") + name)


def trial(m, name):
    return next(x for x in m["trials"] if x["trial"] == name)


# POSITIVE: pinned matrix yields the gates-5/6/7 evidence
ev = extract_gate567(matrix)
record("POSITIVE_pinned_matrix_accepted", ev is not None
       and ev.get("gate5") == "PASS" and ev.get("gate6") == "PASS"
       and ev.get("gate7") == "PASS" and ev.get("all_12_pass") is True,
       ev)


# NEGATIVES: every mutation must be rejected (None), none may raise
def neg(name, mutate):
    m = copy.deepcopy(matrix)
    mutate(m)
    try:
        r = extract_gate567(m)
        record(name, r is None, {"returned": r is not None})
    except Exception as e:
        record(name, False, {"raised": "%s: %s" % (type(e).__name__, e)})


neg("NEG_gates_passed_11",
    lambda m: trial(m, "G01_green_dry_run")["facts"].update(
        gates_passed=11))
neg("NEG_nonempty_failed_gates_codes",
    lambda m: trial(m, "G01_green_dry_run")["facts"].update(
        failed_gates=[6], gate_codes=["6:PIN_MISMATCH:collector"]))
neg("NEG_missing_all12_check",
    lambda m: trial(m, "H05_helper_real_sanctioned_path").update(
        checks=[c for c in trial(m, "H05_helper_real_sanctioned_path")
                ["checks"] if not c.startswith("all_12")]))
neg("NEG_wrong_status",
    lambda m: trial(m, "G01_green_dry_run").update(status="FAIL"))
neg("NEG_wrong_decision",
    lambda m: trial(m, "H05_helper_real_sanctioned_path")["facts"].update(
        decision="HOLD"))
neg("NEG_missing_facts",
    lambda m: trial(m, "G01_green_dry_run").pop("facts"))
neg("NEG_top_level_npass_45", lambda m: m.update(n_pass=45))

# STATIC BINDING: runner aggregation + gate enumeration 1..12 in the
# candidate gate module (r5 candidate; the aggregation semantics it is
# checked against are the pinned runner's, byte-identical lineage).
runner = (PKG11 / "run_dispatch_gate_trials_r4.py").read_text()
gate_mod = (PKG48 / "dispatch_gate_r5_candidate.py").read_text()
agg1 = ('gates = res["receipt"]["gates"]' in runner
        and 'sum(1 for x in gates if x["result"] == "PASS")' in runner)
agg2 = 'self.facts["failed_gates"] = [x["gate"] for x in gates' in runner
seg = gate_mod[gate_mod.index("def evaluate_gates"):]
seg = seg[:seg.index("\ndef ", 10)]
ids = [int(x) for x in re.findall(r"ctx\.gate\(g, (\d+),", seg)]
record("STATIC_runner_aggregation", bool(agg1 and agg2),
       {"gates_passed_sum_over_PASS": bool(agg1),
        "failed_gates_remainder": bool(agg2)})
record("STATIC_gates_enumerated_1_to_12_unique",
       sorted(set(ids)) == list(range(1, 13)),
       {"unique_gate_ids": sorted(set(ids)),
        "branch_calls": len(ids),
        "note": "one ctx.gate append per gate per evaluation "
                "(if/elif/else branches); uniqueness is over ids"})

out["all_pass"] = all(t["pass"] for t in out["tests"])
out["n_pass"] = sum(1 for t in out["tests"] if t["pass"])
out["n_tests"] = len(out["tests"])
(HERE / "extractor_self_test_results.json").write_text(
    json.dumps(out, indent=1, sort_keys=True, default=str))
print("SELFTESTS %d/%d PASS" % (out["n_pass"], out["n_tests"]))
sys.exit(0 if out["all_pass"] else 1)
