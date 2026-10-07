# Research Loop Contract — Implementation (v1)

Implements Issue #1 comments **6044381696** (loop contract), **6044453166**
(addendum), **6046569258** (authorization clarification).
Mike confirmed in chat 2026-10-07: "Yes do what chat says."

**Scope: research-only.** No production deployment, spending, API acquisition,
frozen-system edits, or holdout access.

## Files

| File | Deliverable |
|---|---|
| `registry_schema.md` | Experiment record fields, message ledger, idempotency key |
| `registry.json` | Seeded registry (5 experiments) |
| `state_machine.md` | States, transition rules, roles |
| `cycle_procedure.md` | Per-cycle ingest → reconcile → review → transition → dispatch |
| `failure_memory.md` | Queryable failure index + taxonomy + revival rule |
| `fixtures/test_gates.py` | 8/8 passing synthetic gate fixtures |
| `fixtures/fixture_output.txt` | Pinned fixture output |

## Registry seed summary

| Experiment | State | Verdict |
|---|---|---|
| EXP-20261007-HARNESS-V56 | PASS | Isolated offline prerequisite only |
| EXP-20261007-ORB-15M | HOLD | Null mismatch; no rerun until design fixed |
| EXP-20261007-RECOVERY-MEMO | EVIDENCE_READY | Awaiting ChatGPT adjudication |
| EXP-20261007-METHODS-SURVEY | REVIEW | Reference accepted; gates NOT adopted |
| EXP-20261007-TD-PILOT | QUEUED | Gated on ChatGPT spec clearance |

## Fixture results (8/8)

1. Duplicate input → no duplicate task (idempotency key)
2. Blocked prerequisites → HOLD (missing items named)
3. Repair exhaustion → HOLD (budget gate)
4. Unreviewed evidence → cannot promote (must pass REVIEW)
5. Failures → retained, searchable, KILL is terminal

## Effort estimate

**Build (this deliverable):** ~2 hours agent time. Complete.

**Ongoing operation per cycle** (each bridge-watch cycle that finds actionable items):
- Ingest + reconcile: ~10 min
- Artifact verification: ~10 min per experiment reviewed
- Transition recording + dispatch: ~10 min
- **Typical cycle with 1 active experiment: ~30 min agent time.**

**Per new experiment** (design → preregistration → execution → evidence):
- Design + preregistration: 1–2 hours
- Execution: varies by experiment (bounded by trial budget)
- Evidence packaging + review response: 1–2 hours

**Budgets (per contract §5):**
- One active execution task at a time.
- Each experiment declares explicit trial + repair budgets before READY.
- Repair budget exhaustion → HOLD, no exceptions, no gate weakening.
- Initial operating budget proposed: 4 hours/week agent time for loop
  operation, excluding experiment execution (budgeted per-experiment).

## Canonical refs requested by ChatGPT (6046569258)

- Recovery-path memo: `research_notes/RECOVERY_PATH_DECISION_MEMO_20261007.md`
  — commit `1440a3b`, blob `f4ee2b9609e8` (verified byte-identical on remote).
