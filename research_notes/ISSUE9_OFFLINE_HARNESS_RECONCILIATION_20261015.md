# Issue #9 offline harness reconciliation integrity — QF-ISSUE9-RECONCILIATION-INTEGRITY-20261015-06 r1

**Verdict: RECONCILIATION_INTEGRITY_PASS** (synthetic enforcement only — see §4)

Spec: ChatGPT secondary bounded repair, GitHub Issue #1 comment
`6187987162` (independent review of the -05 accounting candidate at
commit `6c455c6`: the intended -05 accounting changes were **accepted**;
`OFFLINE_HARNESS_PASS` remained **HOLD** on reconciliation integrity —
one load-bearing gap in `Ledger.append_reconciliation()` /
`Ledger.billed_total()`). The comment governs where this memo and the
dispatch brief differ. Repair executed 2026-10-15, inside the ≤35-minute
box including the one ≤10-minute repair allowance (**~3 minutes used**,
fixture-driver only — §3). TD derivation -06 was not delayed by this
task (it had already completed).

**What this PASS means — and does not mean.** Identical in scope to
-03/-04/-05: the enforcement code behaves correctly against a scripted
fake transport under adversarial fixtures. Even at PASS this is an
offline harness result only: it authorizes **no** provider/model call
and no Arm A/B run. Live Issue #9 execution still requires Mike's
separate explicit GO plus same-day verified $0 pin/quota evidence and
the existing route checklist (E1–E8). Nothing here is wired into any
live path; `bin/or_chat.py` was not touched, per spec.

## 1. The HOLD gap and its repair

All repairs are in the isolated candidate only:
`research_notes/issue9_offline_harness_20261014/tools/offline_harness.py`.

**(1) Any nonempty `evidence_ref` counted as evidence → an injected
evidence-verification boundary with a structured, bound bundle**
(spec points 1–2). `append_reconciliation` now takes an `evidence`
bundle: `{provider, account_id, day, evidence_ref,
target_outcome_hash, digest}`, where `digest` recomputes over every
bundle field except itself. Every check runs **before append**; any
refusal leaves the ledger byte-unchanged (zero append) and the resume
block in force:

- absent evidence → `RECONCILIATION_EVIDENCE_MISSING`; a bare string
  (the pre--06 gate, via either the `evidence` argument or the legacy
  `evidence_ref` kwarg) or a malformed bundle →
  `RECONCILIATION_EVIDENCE_MALFORMED`;
- the target must be an existing `call_outcome` —
  `RECONCILIATION_TARGET_UNKNOWN` — that is actually flagged
  `reconciliation_required` — `RECONCILIATION_TARGET_NOT_OUTSTANDING`
  — and not already resolved — `RECONCILIATION_DUPLICATE` (a second
  resolution, identical or conflicting, always refuses);
- the bundle digest must recompute (`…_EVIDENCE_DIGEST_MISMATCH`); its
  identity must not already be used for a different call
  (`…_EVIDENCE_REUSED`); it must bind **this** outcome's record hash
  (`…_EVIDENCE_TARGET_MISMATCH`) and the day the call was dispatched
  (`…_EVIDENCE_DAY_MISMATCH`);
- authenticity (issued identity, expiry) is decided **only** by a
  verifier callable injected into `Ledger` — none configured →
  `…_EVIDENCE_UNVERIFIABLE`; verifier raising →
  `…_EVIDENCE_VERIFIER_ERROR`; verifier falsy →
  `…_EVIDENCE_UNVERIFIED`. Fixtures use an explicit `FakeEvidenceVerifier`
  (issued-ref registry + expiry), never a real provider.

The -05 defect ChatGPT named — a wrong-call reconciliation being
*appended as pollution* that merely failed to clear — is now
impossible: it refuses pre-append with zero ledger change (F35/F44).

**(2) Resolved fields accepted anything → strict validation +
complete-dimension rule + conflict refusal** (spec point 3).
`resolved_billed_tokens` must be an integer, not bool, ≥ 0
(`RECONCILIATION_TOKENS_INVALID`); `resolved_cost_usd` must be a
finite, non-bool number ≥ 0 (`RECONCILIATION_COST_INVALID` — string,
bool, negative, NaN and inf all refuse). Every dimension that was
originally UNKNOWN must be resolved in the single record
(`RECONCILIATION_RESOLUTION_INCOMPLETE` — a timeout's usage-only or
cost-only resolution refuses). A resolved value that contradicts an
originally KNOWN dimension refuses as
`RECONCILIATION_RESOLUTION_CONFLICT`. A **nonzero** resolved cost is
recorded authoritatively but marks the record `NONZERO_COST`:
`resume_state()` returns the terminal `NONZERO_COST` state and `run()`
refuses any dispatch with `NONZERO_COST` — it is never a clean resume
under the $0 protocol.

**(3) `billed_total()` ignored reconciled usage → effective total,
counted exactly once** (spec point 4). The total now sums, per
arm-seed: the outcome's own billed tokens when usage was originally
known (a reconciliation never adds them again), otherwise the verified
`resolved_billed_tokens` from its reconciliation record once one
exists. The pre-dispatch reservation check and the acceptance overrun
check both read this effective total, so a timed-out call reconciled
to 119,500 (or 120,001) tokens is enforced against the 120,000 ceiling
exactly like originally-known usage (F53/F54) — the cap-evasion path
in the HOLD is closed. A known-usage/unknown-cost call reconciled on
cost alone stays counted once (F55: mid-total 1,250, final 2,500).

**(4) Immutability / chain preserved** (spec point 5). Originals are
never rewritten; the chain is verified before any reconciliation
append (`LEDGER_CORRUPT`); duplicate/conflicting resolutions and
cross-call evidence reuse refuse (F46/F52/F58).

## 2. What changed in the fixture suite

- **F35 amended** (the only prior expectation set touched, disclosed
  here exactly as -05 disclosed its F14 amendment): the mechanism it
  exercises changed by spec — the clearing reconciliation now presents
  a structured verified bundle instead of a bare string, and the
  wrong-call attempt now *refuses* (`RECONCILIATION_TARGET_UNKNOWN`,
  zero append) instead of being appended. All semantic expectations
  are unchanged, including `wrong_call_recon_no_clear`, the
  evidence-missing refusal, and the exactly-once final total of 2,500.
  One check was added: `wrong_call_recon_refused`.
- **19 new fixtures (F40–F58)**, one or more per spec-point-6 case:
  arbitrary string (F40); verifier false — unissued ref and expired
  evidence (F41); verifier exception (F42); no verifier configured
  (F43); wrong target (F44); target not outstanding (F45); duplicate
  (F46); evidence target mismatch (F47); digest mismatch (F48); day
  mismatch (F49); partial resolution (F50); invalid field values —
  string/bool/negative/float tokens, NaN/inf/negative/string/bool cost
  (F51); conflicting resolution vs known dimensions (F52); reconciled
  near cap (F53) and over cap (F54); known-usage not double-counted
  (F55); nonzero resolved cost terminal (F56); restart after valid
  reconciliation, counted once across two reopens (F57); evidence
  reuse across calls in a shared ledger (F58). Every negative asserts
  zero append (record-count delta) and, where a run follows, zero
  dispatch.

## 3. Fixture results — 61/61 matched, twice, byte-identical

Complete suite = the 42 prior fixtures (expectations preserved except
the disclosed F35 amendment) + F40–F58. **Trial disclosure:** the
first full run matched 60/61 — F47's driver built its "foreign"
scenario identically to the target scenario, and because the suite is
fully deterministic the two ledgers were byte-identical, so the
foreign outcome hash legitimately coincided (a driver defect, not a
harness defect: the harness was presented with evidence that did bind
the target). The single repair (~3 minutes of the ≤10-minute
allowance) gave the foreign scenario a distinct prompt and added a
`foreign_hash_distinct` self-check to F47; no harness bytes changed
during the repair. The repaired suite was then run twice end to end;
both runs exit 0 with **61/61 matched** and byte-identical outputs:

| Output | sha256 (both runs) |
|---|---|
| `fixtures/fixture_results.json` | `d26b9a559a80385788ea900640a08302d28bb429783b91ca25093f26009d79f3` |
| `evidence/f01_clean_control_ledger.jsonl` | `82a7497ded34cb28dfd36aea9a78b8b07715a0050ae6a1639e7318fa4badff37` |
| `evidence/f01_clean_control_summary.json` | `c129547de4b646f478a66372c0a8a7bee290827bb383900fe16f5e0300072e1b` |

The F01 clean-control hashes are **unchanged from -03, -04 and -05** —
the compliant path's behavior did not move across any of the four
repairs, as spec point 7 requires.

## 4. What did NOT change; scope confirmations

- The frozen protocol (`comparison_protocol.json`), the 120,000-token
  cap, the prep package, and the -02 preflight guard are untouched.
  All -03/-04/-05 enforcement semantics not named in this HOLD are
  preserved: usage-before-rejection accounting, UNKNOWN (never
  zero-filled) interrupted accounting, resume blocked while any
  reconciliation is outstanding, preflight-first, empty-content stop,
  reservation + overrun quarantine, exact version equality, strict
  cost evidence for acceptance, acceptance-time wall cap, pre-dispatch
  chain verification, crash-orphan accounting, no retries, quota/reset
  evidence rules, seed order, prompt registration.
- Fake transport only; the fixture runner patches the socket layer to
  raise before anything runs (F00 proves the denial is installed).
  **Zero** provider/model/API calls, **zero** spend, **zero** installs,
  **zero** live changes, **zero** adoption or merge. The live V5.4
  harness/state and the TD packages were not touched.
- This PASS is an offline harness result only. It does not lift the
  Issue #9 execution gate: Mike's separate explicit GO, same-day
  verified $0 pin/quota evidence (B1), and checklist E1–E8 remain
  required, exactly as the governing comment states.
