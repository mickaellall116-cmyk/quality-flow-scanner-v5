# Research Loop — State Machine (v1.1)

Per Issue #1 comment 6044381696 §2. Research-only.
v1.1: shared gate path per ChatGPT adjudication 6047556037 (see §8).

## States

```
QUEUED → DESIGN → READY → RUNNING → EVIDENCE_READY → REVIEW → PASS
                                                              → FAIL
                                                              → HOLD
                                                              → KILL
```

| State | Meaning | Entry condition |
|---|---|---|
| `QUEUED` | Idea captured, not yet designed. | Literature intake or brainstorm produces falsifiable hypothesis. Can also go directly to `HOLD` if blocked on external input before design begins. |
| `DESIGN` | Preregistration in progress. | Owner assigned, hypothesis written. |
| `READY` | Cleared to run. | **ALL** of: preregistered rules, trial budget, data permissions/provenance, acceptance criteria, prerequisites explicit. Missing any → stays in DESIGN. |
| `RUNNING` | Execution in progress. | Task dispatched with idempotency key. |
| `EVIDENCE_READY` | Outputs produced, awaiting review. | Evidence pin recorded. **Cannot promote without REVIEW.** |
| `REVIEW` | Under adjudication (ChatGPT designs/adjudicates; Claude audits at gates; Mike decides). | Reviewer assigned. |
| `PASS` | Reviewed claim accepted. | **Scoped to the reviewed claim only.** Never grants deployment, CP2, or performance clearance. |
| `FAIL` | Claim rejected on evidence. | Recorded permanently; stays searchable. |
| `HOLD` | Paused with actionable reason. | Blocked prerequisites, repair budget exhausted, awaiting external input. |
| `KILL` | Terminated. | Cannot be revived without explicitly new evidence (new experiment ID). |

## Transition rules

1. **No skipping.** `QUEUED` → `READY` directly is forbidden. Every experiment passes through `DESIGN`.
2. **READY gate.** Transition `DESIGN` → `READY` requires all five preregistration items documented in the registry record. A cycle finding any missing MUST record `HOLD` with the missing item named.
3. **No promotion without review.** `EVIDENCE_READY` → `PASS`/`FAIL` directly is forbidden. Must pass through `REVIEW`.
4. **PASS is scoped.** A `PASS` verdict covers only the exact reviewed claim (e.g. "isolated offline harness prerequisite"). It never implies deployment readiness, CP2 clearance, or performance validity.
5. **Repair budget.** Each experiment declares `repair_budget.allocated_rounds`. When `used_rounds` reaches allocation, the cycle records `HOLD` with reason `repair_budget_exhausted` and stops. No open-ended repair loop. Evidence gates are never weakened to meet a deadline.
6. **Kill is sticky.** `KILL` and `FAIL` records remain in the registry permanently. Revival requires a new experiment ID with explicitly new evidence, linked to the killed record.
7. **Adjudication, not automation.** Kill/promotion judgments are explicit accountable decisions (ChatGPT adjudicates, Mike decides). No automatic promotion from a score.

## Roles

- **ChatGPT:** designs experiments, adjudicates reviews.
- **Muse:** implements, runs, evidences.
- **Claude:** independent FULL/TARGETED audits at designated gates.
- **Mike:** final authority on all kill/promotion/deployment decisions.
- **Watch (bridge watcher):** coordinates; does NOT execute Muse's runtime or invoke Claude.

## 8. v1.1 enforcement gate (ChatGPT 6047556037)

The v1 fixtures demonstrated happy paths, not enforceable invariants.
v1.1 adds ONE shared gate path that every transition and every dispatch
must pass through — there is no bypass:

1. **Transition legality** — the requested `from → to` must be in the
   transition table above.
2. **READY gate** — entering `READY` requires all preregistration fields
   present AND valid against the real registry schema (`rule_spec_version`,
   `trial_budget.allocated`, `dataset_pin`, `acceptance_criteria`,
   `baseline_design`). `UNKNOWN`, missing, or invalid values → blocked and
   routed to `HOLD` naming the blocker. `repair_budget.allocated_rounds`
   must be a bounded number. Dependencies that are experiment IDs must
   resolve to `PASS`.
3. **RUNNING gate** — a second active `RUNNING` execution is prohibited.
4. **Dispatch** routes through the same gate: only `READY → RUNNING`
   dispatches. Dispatch on `QUEUED`/`DESIGN` is blocked.
5. **ID immutability** — `add()` refuses an existing experiment ID
   (including killed records). Revival requires a new ID.
6. **Persistence** — task log and message ledger survive save/load/restart;
   idempotency holds across restarts.
7. **Message evidence** — `SENT`, `DELIVERED`, `ACK`, `WORK_RESULT` are
   separate fields, never a replacing status.

Fixtures: `fixtures/test_gates.py` (21/21 pass), output in
`fixtures/fixture_output.txt`.

## 9. v1.2 micro-patch (ChatGPT 6048255893, final scaffold allocation)

Three exact probes fixed. After this patch, no further scaffold repair
cycles are authorized — if a future probe fails, record the loop
executor HOLD and continue with reviewed documentation plus
manual/watch enforcement.

1. **Absent dependency IDs rejected.** A string dependency must be an
   experiment_id present in the registry (and `PASS` to clear READY).
   An absent ID is rejected UNLESS explicitly typed as an external
   prerequisite: `{"external_id": "...", "evidence_pin": "..."}` with a
   nonempty separately-verified evidence pin. An external prerequisite
   without evidence is rejected.
2. **Budget validation.** `trial_budget.allocated/used` and
   `repair_budget.allocated_rounds/used_rounds` must be integers (bool
   excluded), ≥ 0, with used ≤ allocated. `trial_budget.unit`, when
   present, must be a nonempty string. Violations block
   `DESIGN → READY` and route to `HOLD` naming the blocker.
3. **Dispatch pin required.** `dispatch()` requires a nonempty immutable
   evidence/spec pin; an empty pin is rejected before the idempotency
   check or any state change. The pin is part of the idempotency key.

**Persistence:** `save()` uses atomic temp-file + `os.replace` + fsync
so a reader never sees a torn file. The Registry is **single-process
only** — no interprocess lock is implemented; two concurrent writers
would lose updates. Do not claim concurrency safety from the fixtures.

Fixtures: `fixtures/test_gates.py` (28/28 pass), output in
`fixtures/fixture_output.txt`.
