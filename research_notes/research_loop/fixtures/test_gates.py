#!/usr/bin/env python3
"""
Synthetic fixtures for the research-loop contract (Issue #1 6044381696 §7).

Demonstrates, with no external dependencies:
  1. Duplicate input causes no duplicate task (idempotency).
  2. Blocked prerequisites cause HOLD.
  3. Repair exhaustion stops work.
  4. Unreviewed evidence cannot promote.
  5. Failures are retained and searchable.

Run: python3 test_gates.py
Exit 0 = all fixtures pass.
"""

import copy
import json
import sys

PASS, FAIL = "PASS", "FAIL"

# ---- Minimal in-memory registry + state machine (mirrors registry_schema.md) ----

VALID_TRANSITIONS = {
    "QUEUED": ["DESIGN", "HOLD", "KILL"],
    "DESIGN": ["READY", "HOLD", "KILL"],
    "READY": ["RUNNING", "HOLD", "KILL"],
    "RUNNING": ["EVIDENCE_READY", "HOLD", "KILL"],
    "EVIDENCE_READY": ["REVIEW", "HOLD", "KILL"],
    "REVIEW": ["PASS", "FAIL", "HOLD", "KILL"],
    "PASS": [], "FAIL": [], "HOLD": ["DESIGN", "KILL"], "KILL": [],
}

READY_REQUIREMENTS = [
    "preregistered_rules", "trial_budget", "data_provenance",
    "acceptance_criteria", "prerequisites",
]


class Registry:
    def __init__(self):
        self.experiments = {}
        self.task_log = []          # (experiment_id, task_revision, evidence_pin)
        self.message_ledger = []    # (message_id, status)

    def add(self, exp):
        self.experiments[exp["experiment_id"]] = copy.deepcopy(exp)

    def transition(self, exp_id, to_state, justification, decision_ref):
        exp = self.experiments[exp_id]
        frm = exp["state"]
        if to_state not in VALID_TRANSITIONS.get(frm, []):
            return False, f"illegal transition {frm} -> {to_state}"
        exp["state"] = to_state
        exp.setdefault("transitions", []).append(
            {"from": frm, "to": to_state,
             "justification": justification, "decision_ref": decision_ref})
        return True, "ok"

    def try_ready(self, exp_id):
        """DESIGN -> READY only if all preregistration items present."""
        exp = self.experiments[exp_id]
        missing = [r for r in READY_REQUIREMENTS if not exp.get(r)]
        if missing:
            self.transition(exp_id, "HOLD",
                            f"blocked prerequisites: {missing}", "fixture")
            return False, missing
        return self.transition(exp_id, "READY", "all preregistration explicit",
                               "fixture")

    def dispatch(self, exp_id, task_revision, evidence_pin=""):
        """Idempotent dispatch: same key -> no duplicate task."""
        key = (exp_id, task_revision, evidence_pin)
        if key in self.task_log:
            return False, "duplicate suppressed"
        self.task_log.append(key)
        return True, "dispatched"

    def check_repair_budget(self, exp_id):
        exp = self.experiments[exp_id]
        b = exp.get("repair_budget", {})
        if b.get("used_rounds", 0) >= b.get("allocated_rounds", 0):
            self.transition(exp_id, "HOLD", "repair_budget_exhausted", "fixture")
            return False, "budget exhausted -> HOLD"
        return True, "budget available"

    def search_failures(self, **filters):
        out = []
        for e in self.experiments.values():
            if e["state"] not in ("FAIL", "KILL", "HOLD"):
                continue
            if all(e.get("failure_" + k) == v for k, v in filters.items()):
                out.append(e["experiment_id"])
        return out


def base_exp(eid="EXP-FIXTURE-1"):
    return {
        "experiment_id": eid, "title": "fixture", "owner": "Muse",
        "state": "QUEUED", "repair_budget": {"allocated_rounds": 2, "used_rounds": 0},
    }


results = []
def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


# ---- Fixture 1: duplicate input -> no duplicate task ----
r = Registry()
r.add(base_exp())
ok1, _ = r.dispatch("EXP-FIXTURE-1", "rev-a", "pin-1")
ok2, msg2 = r.dispatch("EXP-FIXTURE-1", "rev-a", "pin-1")   # duplicate
ok3, _ = r.dispatch("EXP-FIXTURE-1", "rev-b", "pin-1")      # new revision ok
check("F1 duplicate input suppressed", ok1 and not ok2 and ok3, msg2)
check("F1 task log has 2 entries", len(r.task_log) == 2)

# ---- Fixture 2: blocked prerequisites -> HOLD ----
r = Registry()
r.add(base_exp("EXP-FIXTURE-2"))
r.transition("EXP-FIXTURE-2", "DESIGN", "start design", "fixture")
ok, missing = r.try_ready("EXP-FIXTURE-2")   # nothing preregistered
check("F2 blocked prerequisites -> HOLD",
      not ok and r.experiments["EXP-FIXTURE-2"]["state"] == "HOLD",
      f"missing={missing}")

# ---- Fixture 3: repair exhaustion stops work ----
r = Registry()
e = base_exp("EXP-FIXTURE-3")
e["repair_budget"] = {"allocated_rounds": 2, "used_rounds": 2}
r.add(e)
ok, msg = r.check_repair_budget("EXP-FIXTURE-3")
check("F3 repair exhaustion -> HOLD",
      not ok and r.experiments["EXP-FIXTURE-3"]["state"] == "HOLD", msg)

# ---- Fixture 4: unreviewed evidence cannot promote ----
r = Registry()
e = base_exp("EXP-FIXTURE-4")
e["state"] = "EVIDENCE_READY"
r.add(e)
ok, msg = r.transition("EXP-FIXTURE-4", "PASS", "skip review", "fixture")
check("F4 EVIDENCE_READY -> PASS blocked",
      not ok and r.experiments["EXP-FIXTURE-4"]["state"] == "EVIDENCE_READY", msg)
ok2, _ = r.transition("EXP-FIXTURE-4", "REVIEW", "send to review", "fixture")
ok3, _ = r.transition("EXP-FIXTURE-4", "PASS", "review accepted", "fixture")
check("F4 EVIDENCE_READY -> REVIEW -> PASS allowed", ok2 and ok3)

# ---- Fixture 5: failures retained and searchable ----
r = Registry()
e = base_exp("EXP-FIXTURE-5")
e.update({"state": "KILL", "failure_reason": "null_mismatch",
          "failure_market": "QQQ", "failure_timeframe": "15m",
          "failure_data_source": "Tiingo", "failure_strategy_family": "orb"})
r.add(e)
found = r.search_failures(strategy_family="orb", reason="null_mismatch")
check("F5 killed experiment retained + searchable", found == ["EXP-FIXTURE-5"])
# revival requires new ID
ok, _ = r.transition("EXP-FIXTURE-5", "DESIGN", "revive attempt", "fixture")
check("F5 KILL is terminal (no direct revival)", not ok)

# ---- Summary ----
failed = [n for n, c, _ in results if not c]
print(f"\n{len(results) - len(failed)}/{len(results)} fixtures pass")
sys.exit(1 if failed else 0)
