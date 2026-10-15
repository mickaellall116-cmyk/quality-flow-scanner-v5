# Trial log — QF-TD-P2-SPOT-V2-FULL-MANIFEST-STATE-PREFLIGHT-20261015-05 r1

Budget: ≤40 min total incl. one ≤10-min repair. All times EDT, 2026-10-15.

| # | Trial | Outcome |
|---|---|---|
| 1 | Environment check: `/tmp/tdqual/venv` absent at start (again). Rebuilt exactly by the qualified download-hash-then-`--no-index` procedure from the f64d12f lock. | 11/11 wheel hashes identical to qualified records; rebuilt freeze identical to qualified freeze; CPython 3.12.3. Disclosed in memo §1. No substitution. |
| 2 | Pin recomputation + original-state inventory (driver cases 1–2). | PASS (11/11, 12/12). V1 state: 11 files; binding = SPOT8 digest; pilot HOLD / 7 attempts / 7 reservations / completed SPT01–06; 34 lifecycle events; ERROR_EVIDENCE sha = preserved body sha (`3339c341…`, 180 B). |
| 3 | Suite run 1 (pre-repair driver). | 7/9 cases passed. `transition_attempt_full_manifest`, `transition_restart_again`, `classifier_direct_proof_on_preserved_evidence` failed ONLY the byte-unchanged checks on lifecycle.jsonl. Transition outcome itself was the predicted persistent HOLD with zero calls; pilot-state bytes unchanged throughout. |
| 4 | Diagnosis (isolated reproduction). | A clean copy + transition attempt with NO probe phase changed zero bytes. Root cause: the driver's receipt-revalidation probe shared the transition copy, and the candidate's `_verify_receipt` → `_validate_bars` **emits** one CONSTRUCTION_HOLD lifecycle event per 1h receipt — 6 appends, all in the probe phase. A driver accounting defect, and a genuine candidate finding (verification is not read-only; see design_gap_analysis.md). |
| 5 | Repair (driver-only, ~4 min, within the single ≤10-min allowance). | Probe moved to its own dedicated copy; the side effect is now asserted exactly (6 CONSTRUCTION_HOLD appends, pilot state/receipts untouched) as a recorded finding. No candidate, supplement, manifest, environment, or state bytes changed. |
| 6 | Suite run 1 (post-repair). | 9/9 cases PASS; `transition_supported: false` (the honest result). |
| 7 | Suite run 2 (post-repair). | 9/9 cases PASS; results file and all four side artifacts (inventory, mapping, fake-call ledger, classifier proof) byte-identical to run 1. |

Candidate failures in final trials: none — the candidate behaved exactly as
its code dictates. The HOLD verdict is a **design-gap** result (spec point
3's explicit branch), not a candidate malfunction and not a rehearsal error.

Spec points 4–6 (SPT08 outcome matrix, derived-state restarts, crash /
write-once controls in the derived state) were **not run**: no v2 state can
be honestly derived, and fabricating one was forbidden. The restart control
was run against the copied v1 state itself (persistent HOLD, zero calls,
zero writes). The SPT08 outcome matrix remains proven at -04 scope in fresh
state.
