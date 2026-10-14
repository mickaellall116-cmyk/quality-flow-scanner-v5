# Issue #9 offline harness correctness repair — QF-ISSUE9-OFFLINE-HARNESS-CORRECTNESS-20261014-04 r1

**Verdict: OFFLINE_HARNESS_PASS** (synthetic enforcement only — see §4)

Spec: GitHub Issue #1 comment `6180610281` (ChatGPT adversarial review of the
-03 candidate, verdict HOLD / repair required), which governs where this memo
and the tasking brief differ. Repair executed 2026-10-14 ~23:27–23:34 UTC,
inside the ≤45-minute box. **No repair pass was needed**: the amended suite
passed in full on its first run (0 of the ≤10-minute repair allowance used;
the suite was then run a second time for byte-stability, §3).

**What this PASS means — and does not mean.** Identical in scope to -03: the
enforcement code behaves correctly against a scripted fake transport under
adversarial fixtures. It does **NOT** authorize a first live model call or the
Arm A/B swarm comparison. Actual execution remains blocked pending a separate
Mike GO plus same-day $0 pin/quota evidence and an independently accepted
harness (the -04 HOLD language). Nothing here is wired into any live path;
`bin/or_chat.py` was not touched, per spec.

## 1. The five HOLD items and their repairs

All repairs are in the isolated candidate only:
`research_notes/issue9_offline_harness_20261014/tools/offline_harness.py`.

**(1) Version pin mismatch could pass → exact equality enforced.**
`_validate_and_record` previously rejected only an *absent* `model_version`.
It now requires `response.model_version == pin["model_version"]` exactly; a
nonempty substituted version fails as `MODEL_VERSION_MISMATCH` with both the
response and pinned versions recorded in the outcome. An absent pin version is
itself unverifiable (`MODEL_VERSION_UNVERIFIABLE`). *Proof: F27 (new).*
F13 (absent version) still fails closed as before.

**(2) Unknown response cost could pass as $0 → strict cost evidence.**
Previously `cost_usd=None` was accepted and the outcome/summary then wrote
`cost_usd=0` with `cost_verified_zero_incremental=True`. Per-response cost
evidence is now gated *before* usage/content validation: missing →
`COST_EVIDENCE_MISSING` (outcome records `cost_usd: null`,
`cost_evidence_status: "MISSING"` — unknown stays unknown); non-numeric
(including bool and string) → `COST_EVIDENCE_INVALID` / `NON_NUMERIC`;
NaN/±inf → `COST_EVIDENCE_INVALID` / `NON_FINITE`; numeric nonzero →
`NONZERO_COST` (unchanged, F26). The `$0` values written by the
recorded/empty/overrun/wall branches are now reachable only *after* an
exact-zero cost has been verified, so they are evidence-backed, and
`ledger_summary()` now reads each call's `cost_usd` from its ledger record
instead of hardcoding 0. *Proof: F28 (missing), F29 (NaN), F30 (string) —
all new.*

**(3) Final-call wall overrun could pass → cap enforced at acceptance.**
The 45-minute cap was checked only pre-dispatch. `_validate_and_record` now
re-checks elapsed run wall immediately before the `RECORDED` append: a
response arriving after the cap is written as `FAILED_WALL_OVERRUN` /
`CEILING_WALL` with its content quarantined (`content_quarantined: true`,
content hash retained, usage counted) and is never accepted. *Proof: F31
(new — single/final call responding at 46 minutes) and F18, whose checks now
also assert the first call is neither accepted nor recorded (its expectation
and stop code are unchanged: `CEILING_WALL`, 1 invocation).*

**(4) Loaded-ledger corruption was not gated → chain verified before every
dispatch.** `run()` now verifies the full hash chain before anything else —
before the orphan check, price checks, and any transport invocation — and
`_dispatch` re-verifies before every individual dispatch (and
`apply_quota_reset` before appending). A chain failure stops as
`LEDGER_CORRUPT` with zero transport invocations. *Proof: F32 (new — a
completed ledger whose historical outcome was rewritten on disk with stale
hashes; reopen classifies `CORRUPT` via `resume_state`, resume stops
`LEDGER_CORRUPT`, transport invoked 0 times).*

**(5) Crash accounting claim corrected.** The -03 language implied an
interrupted call was "counted exactly once." Corrected throughout the
candidate (module docstring, `billed_total`, `resume_state`): after a crash
between provider response and outcome append, that call's true billed
usage/cost is **UNKNOWN** — neither counted nor treated as zero — and
post-run provider/account reconciliation remains mandatory. The state is
preserved in the ledger itself: a stop on `ORPHANED_LEDGER` now records
`interrupted_calls` (arm/seed/call_index), `interrupted_call_cost:
"UNKNOWN_INTERRUPTED_CALL_COST"`, and `reconciliation_required: true`;
`Ledger.interrupted_cost_state()` exposes the same state. The intent record
still prevents blind retry (no resend, F20/F33). *Proof: F33 (new — crash
after the response on the only call: reopen classifies `ORPHANED`, resume is
refused, zero resends, the run_stop record carries the UNKNOWN state and the
reconciliation flag, and no zero-filled outcome exists).*

## 2. What did NOT change

- The frozen protocol, the prep package, and the -02 preflight guard are
  untouched. All -03 enforcement semantics not named in the HOLD are
  preserved: preflight-first, empty-content stop with reasoning counted and
  never substituted, reservation + overrun quarantine, usage integrity,
  fallback/alias stops, no retries, quota/reset evidence rules, seed order,
  prompt registration.
- The clean-control evidence is byte-identical to -03: F01's ledger
  (`82a7497d…`) and summary (`c129547d…`) hashes are exactly the -03 manifest
  values — the compliant path's behavior did not move.

## 3. Fixture results — 36/36 matched, twice, byte-identical

Complete suite = the 29 -03 fixtures (expectations unchanged; F18's checks
strengthened as noted) + 7 new adversarial fixtures (F27–F33). Run twice end
to end; both runs exit 0 with **36/36 matched**, and the outputs are
byte-identical across runs:

| Output | sha256 (both runs) |
|---|---|
| `fixtures/fixture_results.json` | `ac76e531a73aed8e94241786a79060f47fcc35a15e5e4e8191346cc673eb95ff` |
| `evidence/f01_clean_control_ledger.jsonl` | `82a7497ded34cb28dfd36aea9a78b07715a0050ae6a1639e7318fa4badff37` |
| `evidence/f01_clean_control_summary.json` | `c129547de4b646f478a66372c0a8a7bee290827bb383900fe16f5e0300072e1b` |

Per-gap proof, one line each: F27 version substitution →
`MODEL_VERSION_MISMATCH`, 0 accepted; F28/F29/F30 missing/NaN/string cost →
`COST_EVIDENCE_MISSING`/`COST_EVIDENCE_INVALID`, cost recorded as null
(unknown), 0 accepted; F31 final-call 46-minute overrun → `CEILING_WALL`,
quarantined, 0 recorded; F32 tampered ledger → `CORRUPT` / `LEDGER_CORRUPT`,
0 transport invocations; F33 crash → `ORPHANED`, UNKNOWN state +
reconciliation flag in the ledger, 0 resends.

## 4. Scope confirmations

- Fake transport only; **zero** provider/model/API calls, **zero** spend,
  **zero** installs, **zero** live/production changes. The fixture runner
  patches the socket layer to raise before anything runs (F00 proves it).
- Files changed, all inside the isolated package plus this memo:
  `tools/offline_harness.py` (the five repairs), `tools/run_fixtures.py`
  (F27–F33 + F18 checks + task label), `fixtures/fixture_results.json`
  (regenerated), `SHA256_MANIFEST.txt` (regenerated). F01 evidence files
  regenerated byte-identical.
- Not touched, per spec: `bin/or_chat.py`, the live V5.4 harness, Yahoo /
  production anything, Issue #9 treatment outputs, any provider. The live
  `v54_forward_harness.py` was hash-checked only, before and after:
  `dc3ee392c808aa2e52d468cad0020d8fe85b6f2bda0adc656304193563cba0c8`
  (the deployed feed-repair r2 candidate) — unchanged; the ~19:56 ET Yahoo
  observation cycle was not disturbed (no scans run).

## 5. Defects, repair effort, open items

- No open defect from the HOLD remains: all five items are repaired and
  fixture-proven above. Nothing was softened; no expectation was edited to
  fit a failure (F18's added checks assert *more*, and its -03 expectation
  still holds).
- Repair minutes: ~7 minutes total task time (~23:27–23:34 UTC) including
  spec fetch, source review, the five code repairs, fixture authoring, and
  two full suite runs. The ≤10-minute repair-pass allowance is unused — the
  amended suite passed on its first run.
- Known synthetic-only limits (carried from -03, unchanged): quota fixtures
  inject small caps on the same code path as the 50/day default; wall time
  comes from the injected clock; transport realities of a real provider are
  represented only as the exception/response shapes fixtures script. The
  wall-at-acceptance check uses the same injected clock, so it proves the
  enforcement point, not real-world clock behavior.

— Muse
