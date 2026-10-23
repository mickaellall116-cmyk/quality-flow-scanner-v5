# QUALIFICATION SEQUENCE — QF-DATA-ROUTE-READINESS-20261023-01

The exact checks captured bytes must pass, in order, before any
edge/performance test may touch them. Each step is pass/fail with
an independent reviewer; a failure stops the sequence and the
bytes stay UNQUALIFIED. No step may be waived by a later step's
result.

1. **Receipt integrity.** Verify the hash chain over every capture
   receipt against `capture_manifest.json`'s root digest; verify
   SHA256SUMS by re-fetching the qf-data-archive copies and
   comparing byte-for-byte with the local store (the Day-1
   precedent: 20/20). Any mismatch = HOLD, bytes quarantined.
2. **Coverage 44+7.** Run the completeness checker (checker v3
   candidate-2 lineage; adoption = G4) with the adopted 751-session
   table as a REQUIRED input: every session-bound leg's rows vs
   calendar expectation, zero-row session = COMPLETENESS_FAIL,
   crypto legs against S-C1…S-C6 date spans (23/24/25-bar DST
   sessions by UTC instants). Row deltas enumerated in receipts
   are adjudicated here, leg by leg — the TSLA C2 precedent
   (NOT_EVALUABLE) is the standing outcome class for a
   volume-completeness failure.
3. **Corrected session-grid reconstruction.** Build 4H bars from
   the qualified 1h bytes with the calendar-bound constructor
   (guard v3 lineage; adoption = G3): session-anchored 09:30/13:30
   ET grid, DST-invariant, early-close sessions exactly one
   09:30→13:00 bar, crypto on its own continuous calendar, never
   through the equity constructor. End-to-end parity gate: the
   rebuilt bars must match the live path's construction on
   identical inputs, bar for bar (the standing 2026-10-03 rule).
4. **Actual-byte signal parity.** Feed the rebuilt DEV-window bars
   through the pinned V5.4 engine (stack pins as frozen in the
   shadow closeout) and compare emitted signals against the
   corrected-grid expectation set. W-HO bytes are NOT used here —
   the holdout's single governed use remains -25 §50, separately
   authorized, after qualification. Parity failure = HOLD with
   the divergent bars named.
5. **Independent PASS/HOLD.** Claude replicates steps 1–4 from the
   archive bytes (not the local store) and issues an independent
   verdict; ChatGPT adjudicates; Mike decides adoption. Only a
   PASS at this step makes the dataset QUALIFIED — and only then
   does the separately-authorized corrected-baseline run get
   scheduled. **No edge/performance test before qualification,
   under any intermediate result.**
