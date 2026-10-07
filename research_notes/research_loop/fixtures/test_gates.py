#!/usr/bin/env python3
"""
Synthetic fixtures for the research-loop contract (Issue #1 6044381696 §7).
Corrected per ChatGPT adjudication 6047556037 (v1.1).

v1.1 changes:
  - ONE shared gate path (`_gate`) for ALL transitions and dispatch.
  - `transition(DESIGN, READY)` routes through the preregistration gate
    (no bypass).
  - `try_ready` REJECTS UNKNOWN values, invalid budgets, unresolved deps.
  - `add()` PREVENTS ID overwrite (killed IDs stay killed).
  - Field names validated against the real registry.json schema.
  - task_log + message_ledger persist across save/load (JSON file).
  - Second active RUNNING execution prohibited.
  - Message evidence: separate SENT/DELIVERED/ACK/WORK_RESULT fields,
    never a replacing status.
  - ChatGPT's counterexamples added as fixtures F6–F13.

Run: python3 test_gates.py
Exit 0 = all fixtures pass.
"""

import copy
import json
import os
import sys
import tempfile

PASS, FAIL = "PASS", "FAIL"

# ---- State machine (mirrors state_machine.md) ----

VALID_TRANSITIONS = {
    "QUEUED": ["DESIGN", "HOLD", "KILL"],
    "DESIGN": ["READY", "HOLD", "KILL"],
    "READY": ["RUNNING", "HOLD", "KILL"],
    "RUNNING": ["EVIDENCE_READY", "HOLD", "KILL"],
    "EVIDENCE_READY": ["REVIEW", "HOLD", "KILL"],
    "REVIEW": ["PASS", "FAIL", "HOLD", "KILL"],
    "PASS": [], "FAIL": [], "HOLD": ["DESIGN", "KILL"], "KILL": [],
}

# Real schema field names (mirrors registry_schema.md / registry.json).
SCHEMA_FIELDS = {
    "experiment_id", "title", "owner", "created_at", "state",
    "hypothesis", "primary_sources", "literature_intake",
    "rule_spec_version", "code_pin", "dataset_pin", "output_pin",
    "dependencies", "next_action", "attempted_variations",
    "trial_budget", "repair_budget",
    "baseline_design", "costs", "validation_split",
    "acceptance_criteria", "robustness_diagnostics",
    "limitations", "verdict", "decision_refs",
    "failure_reason", "failure_market", "failure_timeframe",
    "failure_data_source", "failure_strategy_family",
    "transitions",
}

# Preregistration gate: state_machine.md rule 2 mapped to real schema fields.
# "preregistered rules, trial budget, data permissions/provenance,
#  acceptance criteria, prerequisites" ->
READY_FIELD_MAP = {
    "rule_spec_version": "preregistered rules",
    "trial_budget": "trial budget",
    "dataset_pin": "data provenance",
    "acceptance_criteria": "acceptance criteria",
    "baseline_design": "baseline design",
}

MESSAGE_EVIDENCE_FIELDS = ("SENT", "DELIVERED", "ACK", "WORK_RESULT")


class Registry:
    def __init__(self, persist_path=None):
        self.experiments = {}
        self.task_log = []          # [experiment_id, task_revision, evidence_pin]
        self.message_ledger = {}    # message_id -> {FIELD: {evidence, at}}
        self.persist_path = persist_path
        if persist_path and os.path.exists(persist_path):
            self._load()

    # ---- persistence ----
    def save(self):
        if not self.persist_path:
            return
        with open(self.persist_path, "w") as f:
            json.dump({
                "experiments": self.experiments,
                "task_log": self.task_log,
                "message_ledger": self.message_ledger,
            }, f, indent=1)

    def _load(self):
        with open(self.persist_path) as f:
            d = json.load(f)
        self.experiments = d.get("experiments", {})
        self.task_log = d.get("task_log", [])
        self.message_ledger = d.get("message_ledger", {})

    # ---- record management ----
    def add(self, exp):
        """Add experiment. PREVENTS ID overwrite (ChatGPT 6047556037)."""
        eid = exp.get("experiment_id")
        if not eid:
            return False, "missing experiment_id"
        if eid in self.experiments:
            return False, (
                f"ID {eid} already exists (state="
                f"{self.experiments[eid]['state']}) — overwrite prohibited; "
                "use a new experiment_id"
            )
        unknown_fields = set(exp) - SCHEMA_FIELDS
        if unknown_fields:
            return False, f"fields not in registry schema: {sorted(unknown_fields)}"
        self.experiments[eid] = copy.deepcopy(exp)
        self.save()
        return True, "added"

    # ---- the ONE shared gate path (ChatGPT 6047556037) ----
    def _gate(self, exp_id, to_state, justification, decision_ref):
        """Every transition and every dispatch goes through here. No bypass."""
        exp = self.experiments.get(exp_id)
        if exp is None:
            return False, f"unknown experiment {exp_id}"
        frm = exp["state"]

        # 1. Transition legality
        if to_state not in VALID_TRANSITIONS.get(frm, []):
            return False, f"illegal transition {frm} -> {to_state}"

        # 2. READY gate: full preregistration required (rejects UNKNOWN)
        if to_state == "READY":
            ok, problems = self._check_ready_requirements(exp)
            if not ok:
                # Per state_machine.md rule 2: record HOLD naming the blocker.
                self._apply(exp_id, "HOLD",
                            f"READY blocked: {problems}", decision_ref)
                return False, f"READY blocked, routed to HOLD: {problems}"

        # 3. RUNNING gate: prohibit second active execution
        if to_state == "RUNNING":
            active = [e["experiment_id"] for e in self.experiments.values()
                      if e["state"] == "RUNNING"]
            if active:
                return False, (
                    "second active execution prohibited; already running: "
                    + ", ".join(active)
                )

        self._apply(exp_id, to_state, justification, decision_ref)
        return True, "ok"

    def _apply(self, exp_id, to_state, justification, decision_ref):
        exp = self.experiments[exp_id]
        frm = exp["state"]
        exp["state"] = to_state
        exp.setdefault("transitions", []).append(
            {"from": frm, "to": to_state,
             "justification": justification, "decision_ref": decision_ref})
        self.save()

    def transition(self, exp_id, to_state, justification, decision_ref):
        """Public transition — routes through the shared gate. No bypass."""
        return self._gate(exp_id, to_state, justification, decision_ref)

    def _check_ready_requirements(self, exp):
        """Reject missing/UNKNOWN preregistration, invalid budgets,
        unresolved dependencies. (ChatGPT 6047556037)."""
        problems = []
        for field, label in READY_FIELD_MAP.items():
            v = exp.get(field)
            if not v or v == "UNKNOWN":
                problems.append(f"{field} ({label}) missing or UNKNOWN")
        # trial_budget.allocated must be a real allocation
        tb = exp.get("trial_budget")
        if not isinstance(tb, dict) or tb.get("allocated") in (None, "UNKNOWN"):
            problems.append("trial_budget.allocated missing or UNKNOWN")
        # repair_budget must be a valid bounded budget
        rb = exp.get("repair_budget")
        if not isinstance(rb, dict):
            problems.append("repair_budget invalid (not an object)")
        elif rb.get("allocated_rounds") in (None, "UNKNOWN"):
            problems.append("repair_budget.allocated_rounds missing or UNKNOWN")
        # dependencies must resolve to PASSed experiments (if they are experiment IDs)
        for dep in exp.get("dependencies") or []:
            if dep in self.experiments:
                st = self.experiments[dep]["state"]
                if st != "PASS":
                    problems.append(
                        f"dependency {dep} unresolved (state={st})")
        return (len(problems) == 0), problems

    def try_ready(self, exp_id):
        """DESIGN -> READY via the shared gate (preregistration enforced)."""
        return self._gate(exp_id, "READY", "preregistration check", "fixture")

    def dispatch(self, exp_id, task_revision, evidence_pin=""):
        """Dispatch routes through the shared gate: only READY -> RUNNING
        is permitted. QUEUED/DESIGN dispatch is blocked (ChatGPT 6047556037:
        dispatch on QUEUED must not return 'dispatched')."""
        key = [exp_id, task_revision, evidence_pin]
        if key in self.task_log:
            return False, "duplicate suppressed"
        ok, msg = self._gate(exp_id, "RUNNING",
                             f"dispatch rev {task_revision}", "fixture")
        if not ok:
            return False, f"dispatch blocked: {msg}"
        self.task_log.append(key)
        self.save()
        return True, "dispatched"

    def check_repair_budget(self, exp_id):
        exp = self.experiments[exp_id]
        b = exp.get("repair_budget", {})
        if b.get("used_rounds", 0) >= b.get("allocated_rounds", 0):
            self._gate(exp_id, "HOLD", "repair_budget_exhausted", "fixture")
            return False, "budget exhausted -> HOLD"
        return True, "budget available"

    # ---- message evidence ledger: separate fields, never replacing ----
    def record_message_evidence(self, message_id, field, evidence):
        """Record one evidence field for a message. Fields are independent;
        recording ACK never overwrites SENT. (ChatGPT 6047556037)."""
        if field not in MESSAGE_EVIDENCE_FIELDS:
            return False, f"unknown evidence field {field}"
        rec = self.message_ledger.setdefault(message_id, {})
        rec[field] = {"evidence": evidence}
        self.save()
        return True, "recorded"

    def message_evidence(self, message_id):
        return self.message_ledger.get(message_id, {})

    def search_failures(self, **filters):
        out = []
        for e in self.experiments.values():
            if e["state"] not in ("FAIL", "KILL", "HOLD"):
                continue
            if all(e.get("failure_" + k) == v for k, v in filters.items()):
                out.append(e["experiment_id"])
        return out


def base_exp(eid="EXP-FIXTURE-1", state="QUEUED"):
    return {
        "experiment_id": eid, "title": "fixture", "owner": "Muse",
        "created_at": "2026-10-07T00:00:00Z",
        "state": state,
        "hypothesis": "fixture hypothesis",
        "repair_budget": {"allocated_rounds": 2, "used_rounds": 0},
        "trial_budget": {"allocated": 10, "used": 0, "unit": "runs"},
        "dependencies": [],
    }


def preregistered_exp(eid):
    """Experiment with all READY requirements satisfied (real schema fields)."""
    e = base_exp(eid, "DESIGN")
    e.update({
        "rule_spec_version": "rules-v1",
        "dataset_pin": "data-manifest-abc",
        "acceptance_criteria": "criterion-x",
        "baseline_design": "baseline-y",
    })
    return e


results = []
def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


# ---- Fixture 1: duplicate input -> no duplicate task ----
r = Registry()
r.add(base_exp())
r.transition("EXP-FIXTURE-1", "DESIGN", "design", "fixture")
r.add(preregistered_exp("EXP-FIXTURE-1B"))  # separate ID for dispatch test
r.transition("EXP-FIXTURE-1B", "READY", "ready", "fixture")
ok1, _ = r.dispatch("EXP-FIXTURE-1B", "rev-a", "pin-1")
ok2, msg2 = r.dispatch("EXP-FIXTURE-1B", "rev-a", "pin-1")   # duplicate
check("F1 duplicate input suppressed", ok1 and not ok2, msg2)
check("F1 task log has 1 entry", len(r.task_log) == 1)

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
e = base_exp("EXP-FIXTURE-4", "EVIDENCE_READY")
r.add(e)
ok, msg = r.transition("EXP-FIXTURE-4", "PASS", "skip review", "fixture")
check("F4 EVIDENCE_READY -> PASS blocked",
      not ok and r.experiments["EXP-FIXTURE-4"]["state"] == "EVIDENCE_READY", msg)
ok2, _ = r.transition("EXP-FIXTURE-4", "REVIEW", "send to review", "fixture")
ok3, _ = r.transition("EXP-FIXTURE-4", "PASS", "review accepted", "fixture")
check("F4 EVIDENCE_READY -> REVIEW -> PASS allowed", ok2 and ok3)

# ---- Fixture 5: failures retained and searchable ----
r = Registry()
e = base_exp("EXP-FIXTURE-5", "KILL")
e.update({"failure_reason": "null_mismatch",
          "failure_market": "QQQ", "failure_timeframe": "15m",
          "failure_data_source": "Tiingo", "failure_strategy_family": "orb"})
r.add(e)
found = r.search_failures(strategy_family="orb", reason="null_mismatch")
check("F5 killed experiment retained + searchable", found == ["EXP-FIXTURE-5"])
ok, _ = r.transition("EXP-FIXTURE-5", "DESIGN", "revive attempt", "fixture")
check("F5 KILL is terminal (no direct revival)", not ok)

# ---- Fixture 6 (ChatGPT counterexample): dispatch on QUEUED blocked ----
r = Registry()
r.add(base_exp("EXP-FIXTURE-6"))  # state QUEUED
ok, msg = r.dispatch("EXP-FIXTURE-6", "rev-a", "pin-1")
check("F6 dispatch on QUEUED blocked (not 'dispatched')",
      not ok and r.experiments["EXP-FIXTURE-6"]["state"] == "QUEUED", msg)

# ---- Fixture 7 (ChatGPT counterexample): direct DESIGN->READY goes through gate ----
r = Registry()
r.add(base_exp("EXP-FIXTURE-7"))
r.transition("EXP-FIXTURE-7", "DESIGN", "design", "fixture")
ok, msg = r.transition("EXP-FIXTURE-7", "READY", "bypass attempt", "fixture")
check("F7 direct DESIGN->READY without preregistration blocked",
      not ok and r.experiments["EXP-FIXTURE-7"]["state"] == "HOLD", msg)

# ---- Fixture 8 (ChatGPT counterexample): try_ready rejects UNKNOWN ----
r = Registry()
e = base_exp("EXP-FIXTURE-8")
e.update({
    "rule_spec_version": "UNKNOWN",
    "trial_budget": {"allocated": "UNKNOWN", "used": 0, "unit": "runs"},
    "dataset_pin": "UNKNOWN",
    "acceptance_criteria": "UNKNOWN",
    "baseline_design": "UNKNOWN",
})
r.add(e)
r.transition("EXP-FIXTURE-8", "DESIGN", "design", "fixture")
ok, msg = r.try_ready("EXP-FIXTURE-8")
check("F8 try_ready rejects all-UNKNOWN preregistration",
      not ok and r.experiments["EXP-FIXTURE-8"]["state"] == "HOLD", msg)

# ---- Fixture 8b: unresolved dependency blocks READY ----
r = Registry()
r.add(base_exp("EXP-DEP", "DESIGN"))  # dependency stuck in DESIGN
e = preregistered_exp("EXP-FIXTURE-8B")
e["dependencies"] = ["EXP-DEP"]
r.add(e)
ok, msg = r.try_ready("EXP-FIXTURE-8B")
check("F8b try_ready rejects unresolved dependency",
      not ok and "EXP-DEP" in msg, msg)

# ---- Fixture 8c: invalid repair budget blocks READY ----
r = Registry()
e = preregistered_exp("EXP-FIXTURE-8C")
e["repair_budget"] = {"allocated_rounds": "UNKNOWN", "used_rounds": 0}
r.add(e)
ok, msg = r.try_ready("EXP-FIXTURE-8C")
check("F8c try_ready rejects UNKNOWN repair budget", not ok, msg)

# ---- Fixture 9 (ChatGPT counterexample): add() prevents ID overwrite ----
r = Registry()
e = base_exp("EXP-FIXTURE-9", "KILL")
r.add(e)
ok, msg = r.add(base_exp("EXP-FIXTURE-9"))  # same ID, fresh QUEUED record
check("F9 add(existing killed ID) refused — no overwrite",
      not ok and r.experiments["EXP-FIXTURE-9"]["state"] == "KILL", msg)

# ---- Fixture 10: field names validated against real schema ----
r = Registry()
e = base_exp("EXP-FIXTURE-10")
e["preregistered_rules"] = "rules-v1"  # WRONG: not a real schema field
ok, msg = r.add(e)
check("F10 non-schema field name rejected",
      not ok and "preregistered_rules" in msg, msg)

# ---- Fixture 11: task_log + message_ledger persist across save/load ----
with tempfile.TemporaryDirectory() as td:
    p = os.path.join(td, "registry.json")
    r = Registry(persist_path=p)
    r.add(preregistered_exp("EXP-FIXTURE-11"))
    r.transition("EXP-FIXTURE-11", "READY", "ready", "fixture")
    r.dispatch("EXP-FIXTURE-11", "rev-a", "pin-1")
    r.record_message_evidence("msg-1", "SENT", "slack-ts-123")
    r.record_message_evidence("msg-1", "DELIVERED", "read-back-ok")
    # new Registry instance loads from disk
    r2 = Registry(persist_path=p)
    check("F11 task_log survives restart",
          r2.task_log == [["EXP-FIXTURE-11", "rev-a", "pin-1"]],
          f"task_log={r2.task_log}")
    ev = r2.message_evidence("msg-1")
    check("F11 message ledger survives restart with separate fields",
          ev.get("SENT", {}).get("evidence") == "slack-ts-123"
          and ev.get("DELIVERED", {}).get("evidence") == "read-back-ok",
          f"ledger={ev}")
    # duplicate dispatch still suppressed after restart
    ok, _ = r2.dispatch("EXP-FIXTURE-11", "rev-a", "pin-1")
    check("F11 duplicate suppressed after restart", not ok)

# ---- Fixture 12: second active RUNNING prohibited ----
r = Registry()
r.add(preregistered_exp("EXP-FIXTURE-12A"))
r.add(preregistered_exp("EXP-FIXTURE-12B"))
r.transition("EXP-FIXTURE-12A", "READY", "ready", "fixture")
r.transition("EXP-FIXTURE-12B", "READY", "ready", "fixture")
ok1, _ = r.dispatch("EXP-FIXTURE-12A", "rev-a", "pin-1")
ok2, msg2 = r.dispatch("EXP-FIXTURE-12B", "rev-a", "pin-1")
check("F12 second active RUNNING prohibited",
      ok1 and not ok2
      and r.experiments["EXP-FIXTURE-12A"]["state"] == "RUNNING"
      and r.experiments["EXP-FIXTURE-12B"]["state"] == "READY",
      msg2)

# ---- Fixture 13: message evidence fields are separate, never replacing ----
r = Registry()
r.record_message_evidence("msg-2", "SENT", "slack-ts-456")
r.record_message_evidence("msg-2", "ACK", "explicit-ack")
ev = r.message_evidence("msg-2")
check("F13 SENT and ACK recorded as separate fields",
      ev.get("SENT", {}).get("evidence") == "slack-ts-456"
      and ev.get("ACK", {}).get("evidence") == "explicit-ack"
      and "DELIVERED" not in ev and "WORK_RESULT" not in ev,
      f"ledger={ev}")

# ---- Fixture 14: full happy path still works through the gate ----
r = Registry()
r.add(preregistered_exp("EXP-FIXTURE-14"))
ok1, _ = r.try_ready("EXP-FIXTURE-14")
ok2, _ = r.dispatch("EXP-FIXTURE-14", "rev-a", "pin-1")
ok3, _ = r.transition("EXP-FIXTURE-14", "EVIDENCE_READY", "outputs pinned", "fixture")
ok4, _ = r.transition("EXP-FIXTURE-14", "REVIEW", "reviewer assigned", "fixture")
ok5, _ = r.transition("EXP-FIXTURE-14", "PASS", "claim accepted", "fixture")
check("F14 DESIGN->READY->RUNNING->EVIDENCE_READY->REVIEW->PASS via gate",
      all([ok1, ok2, ok3, ok4, ok5])
      and r.experiments["EXP-FIXTURE-14"]["state"] == "PASS")

# ---- Summary ----
failed = [n for n, c, _ in results if not c]
print(f"\n{len(results) - len(failed)}/{len(results)} fixtures pass")
sys.exit(1 if failed else 0)
