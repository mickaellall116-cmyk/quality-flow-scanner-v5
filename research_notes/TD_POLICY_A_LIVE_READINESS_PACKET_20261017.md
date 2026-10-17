# QF-TD-POLICY-A-LIVE-READINESS-PACKET-20261017-11 r1 — WORK RESULT

**Verdict: `POLICY_A_LIVE_READINESS_PACKET_PASS_OFFLINE`** — preparation only.
Ordering, rollback, one-call ceiling and the no-data boundary are executable
and proven on fixtures; repeated matrices match byte-for-byte. This round
spent **none** of the 52 credits: no authenticated `/api_usage` call, no
helper invocation, no ledger write, no token, no armed transport, no
`time_series`. TD live / data screen and corrected performance remain HOLD.

Spec: Issue #1 comment 6234672225, fetched via the public API first and
followed exactly. Bases: `b8651a0` (Policy A), `9474400` (-08), `2f312a1`
(-07), `0a410ab` (-09). Authority basis: Mike's Policy A ceiling GO,
comment 6234434220 — a ceiling approval in principle, NOT an execution GO.

## 1. R4 gate candidate (new, separate; r3 bytes untouched)

`dispatch_gate_r4.py` (sha256 `b5399645…`) is derived from the pinned r3 gate
(`8564b2da…`, re-verified byte-identical after all work) with only these
changes:

- **Gate 2** now binds the Policy A authority: the packet must carry Mike's
  GO record (record id `QF-TD-POLICY-A-52-CREDIT-CEILING-GO-20261017`,
  comment 6234434220, ceiling 52 = 1 status + 51 manifest, $0) and the frozen
  Policy A digest `5d9d82ca…`. Absent GO → `GO_RECORD_MISSING` (UNKNOWN);
  malformed GO → `GO_RECORD_MALFORMED`; policy drift → `POLICY_DIGEST_MISMATCH`;
  ceiling drift → `POLICY_CEILING_MISMATCH` — all HOLD at gate 2, before any
  helper surface work (gate 9).
- **Gate 3** is the accepted -10 Policy A contract, loaded by exact path with
  a pin check (`7e44a2e0…`): plan identity via the joint 8/min + 800/day limit
  pair, standing via authenticated availability under documented error
  semantics, reported `daily_remaining >= 52` (status credit conservatively
  assumed NOT self-counted), minute headroom via `plan_limit == 8`, freshness
  3600 s, and vendor-vs-ledger same-day consistency fail-closed (the ledger
  is read read-only inside the gate; unreadable → UNKNOWN).
- Ceiling constant is 52; gate 1 separately requires the manifest's own
  budget to remain exactly 51 (the manifest is unchanged). Gate 4's day-fit
  reserves the full 52 against the 800/day cap (conservative).
- The credential resolver is loaded from the -08 package by exact path with
  a pin check (`c8271193…`); the r4 package carries its own lease
  holder/contender copies and helper-stub copy so the two-process and seam
  trials run against r4 code end-to-end.

## 2. One-use readiness transaction wrapper (executable, fixtures only)

`readiness_transaction.py` (sha256 `7ced7922…`) implements the exact future
sequence as a state machine: begin (one-use marker, consumed even on
failure) → preflight (all pins, GO record, policy digest/ceiling, manifest
byte pin + count + **ordered-sequence digest**, source-ledger pin, target
guards) → owner lease then ledger lock (accepted order) → helper
verification via the resolver slot → **exactly one** status call (the
counter is consumed before the call, so a failed call cannot be retried) →
Policy A gate-3 evaluation → only on PASS: fsynced exact backup → atomic
adoption (temp + fsync + `os.replace`) → post-write hash + consumer
verification, with atomic rollback to the exact legacy bytes on any
post-write failure → refreeze canonical evidence + derived card → dry-run →
terminal record. Token issuance, transport arming and `time_series` exist
only as guarded refusals (`NOT_IN_READINESS_SCOPE`). The constructor refuses
any non-fixture mode and any non-fixture hook; preflight refuses the real
pilot ledger as a target and any target outside the fixture root. In this
candidate the real helper **cannot** be invoked: the helper slot accepts
only injected fixture callables.

## 3. Proof — twice under kernel network denial (`unshare -n`), identical

- **Gate matrix** (`run_dispatch_gate_trials_r4.py`): the full r3 lineage
  (40 trials) adapted to the r4 evidence shape, plus 6 Policy A trials =
  **46/46 trials, 332/332 checks, PASS in both runs; matrices byte-identical**
  (sha256 `aafd4e1b…`). New trials: A01 policy-digest drift, A02 ceiling
  drift, A03 GO record absent, A04 GO record malformed (all HOLD at gate 2,
  zero side effects), A05 boundary PASS at reported remaining exactly 52
  (all 12 gates, dry-run), A06 remaining 51 → gate-3 FAIL only. The real
  pilot ledger and old SPOT8 state are unchanged in both runs (matrix flags
  true). Adapted F03/F04/F05 exercise the new gate 3 (capacity via
  `daily_usage`, staleness via the documented timestamp field, missing-field
  → UNKNOWN).
- **Transaction suite** (`run_readiness_trials.py`): **20/20 trials, 79/79
  checks, PASS in both runs; matrices byte-identical** (sha256 `32ce082e…`).
  Coverage: happy path with the **real r4 gate** as the dry-run hook (step
  order and lock order asserted; exactly one status call; backup bytes ==
  legacy bytes; adopted bytes == candidate pin; card verifies); one-use
  consumption incl. retry-after-failure; GO absent/malformed; policy digest
  and ceiling drift (helper never verified — preflight precedes it);
  manifest reordered and dropped; pin drift; status call before locks,
  locks before preflight, adoption before gate 3 (all refused); second
  status request refused with the hook called exactly once; gate-3 FAIL
  followed by a ledger-write attempt (refused, target byte-identical, no
  backup created); backup failure; replace failure (target intact, backup
  intact, no temp left); post-write consumer failure → **exact rollback**;
  token/transport/time_series attempts refused; card drift refused;
  real-ledger target + live-mode + non-fixture-hook guards; **crash
  atomicity** via `os._exit(42)` children — crash inside the status call
  leaves the target byte-identical, crash after the atomic replace leaves
  the target either the complete candidate or the complete original
  (parses, backup intact), never a half-written ledger.

## 4. Return artifact

`FUTURE_READINESS_EXECUTION_PROPOSAL.md` — the source-pinned one-use
readiness-execution proposal for a future separately accepted step. It
authorizes (only if separately cleared) the single status request +
conditional ledger adoption + 12/12 dry-run, and **explicitly excludes**
the 51 market-data requests and token issuance.

## Attempts and repair accounting

Elapsed ≈20 min of the ≤30 cap; of that, ≈6 min was the one repair
allowance, used for adaptation defects found by the preserved failed smoke runs —
all in the new -11 glue, none in the pinned bases: (1) helper defs placed
after the TRIALS list (NameError at import); (2) r3-package-relative paths
for the driver/lease helpers in the copied runner; (3) A02 test isolation
(GO-shape check fires before the ceiling code when the GO record itself is
mutated — test corrected to mutate packet/authority only); (4) A05 code
assertion read the failed-gates-only code list (corrected to read the
receipt); (5) C01 subprocesses needed r4 holder/contender + stub copies in
the r4 package; (6) wrapper `call_status` reported ORDER_VIOLATION instead
of STATUS_CALL_ALREADY_MADE on a repeat call (counter check moved first).
Failed attempt trees preserved in the package (`trials_gate_attempt_failed_45of46/`,
`trials_txn_attempt_failed_19of20/`); the earlier 42/46 and 19/20 matrices
were overwritten by later smoke runs using the same output name — stated
plainly here and in FAILURE_MEMORY, with each defect and fix enumerated.
Final formal runs were executed fresh, twice, after the last fix.

## Scope confirmation

Offline/network-denied throughout; zero authenticated or vendor calls
beyond the spec fetch and the GO-record read; helper invoked **zero** times
(surface inspection only, inside the inherited gate trials); zero credits
spent; zero ledger writes (source ledger re-verified `7e5ccef0…` after all
runs; adoption exercised only on fixture copies); zero token issuance/use;
zero installs/downloads; no backtest/performance/holdout/production/trading;
no Issue #9 execution; no merge/adoption (r4 gate + wrapper are uncommitted
candidates); no PARKED-lane reuse; all prior packages byte-identical.

## Package (uncommitted)

`research_notes/td_policy_a_live_readiness_packet_20261017_11/` —
`dispatch_gate_r4.py` `b5399645…`; `run_dispatch_gate_trials_r4.py` `93b911e0…`;
`readiness_transaction.py` `7ced7922…`; `run_readiness_trials.py` `bcd54587…`;
`crash_child.py` `7514e8ce…`; `lease_holder.py` `9ed435b4…`; `lease_contender.py`
`97e61a97…`; `dispatch_matrix_run1.json` = `dispatch_matrix_run2.json`
`aafd4e1b…`; `txn_matrix_run1.json` = `txn_matrix_run2.json` `32ce082e…`;
`FUTURE_READINESS_EXECUTION_PROPOSAL.md`; `FAILURE_MEMORY_20261017_11.md`;
trial trees + hash lists; `SHA256_MANIFEST.txt`.
