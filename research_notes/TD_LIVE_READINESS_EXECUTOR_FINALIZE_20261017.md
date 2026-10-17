# TD LIVE READINESS EXECUTOR FINALIZE — 2026-10-17 (-14 r1)

**Task:** QF-TD-LIVE-READINESS-EXECUTOR-FINALIZE-20261017-14 r1
(canonical spec: Issue #1 comment 6236814063)
**Verdict: `LIVE_READINESS_EXECUTOR_FINALIZE_PASS_OFFLINE`**
(offline integration PASS only, per the spec's acceptance language.
The first real `/api_usage` call remains HOLD until these exact bytes
are independently reviewed and a distinct one-use readiness clearance
is recorded.)

## What was built

One separate live-capable readiness executor candidate,
`live_readiness_executor.py` (sha256 `689ab473…`), wiring the accepted
r3 journal/recovery semantics to the exact r4 gate, the -08
resolver/helper handle, the -10 Policy A gate-3 contract and the -07
ledger candidate. It exposes only the readiness scope: one
`GET /api_usage`, conditional ledger adoption, refreeze, and a 12/12
r4 dry-run. Token issuance, armed market-data transport and
`time_series` exist only as `NOT_IN_READINESS_SCOPE` refusals.

**The -13 integration defect is closed — lock-first, structurally:**
the one-use marker is created with exclusive-create semantics
(`O_CREAT|O_EXCL`); the owner lease and then the shared-ledger lock
are acquired **before any ledger byte is read**; the ledger is read
only under lock, its exact hash and legacy schema are required
against the adjudicated pin, and **those locked bytes** — never a
pre-lock snapshot — are bound into the journal, the backup and any
rollback. Locked bytes that fail the pin produce HOLD with the
mutated bytes left exactly in place (never "restored" to stale
bytes). Target/journal/path bindings are revalidated under lock
immediately before the adoption mutation. Both locks are held
through status validation, backup/adoption, the r4 dry-run and the
durable terminal commit. Recovery revalidates marker/journal/path/
target state **again after acquiring locks** (journal bytes hashed at
precheck must be byte-identical under lock, plus a fresh binding
precheck), closing the precheck→lock TOCTOU.

**Status boundary, pinned exactly:** `GET /api_usage` only, Twelve
Data allowed host, URL constructed solely through the verified
helper handle (`custom.twelvedata`), the slot consumed and journaled
**before** invocation, no retry, redirects refused, no alternate
endpoint. Live mode uses actual UTC and the exact sanctioned helper
handle; offline trials inject a transport spy — the sanctioned helper
is never imported on the offline path.

**Arming:** live mode requires the distinct one-use readiness
clearance artifact defined in the proposal (JSON binding txn id,
executor source sha256, r4 gate sha256, Policy A digest, candidate
sha256, legacy ledger sha256, ceiling 52, scope
`READINESS_ONLY_ONE_API_USAGE`), pinned by sha256 in the live packet
and verified before the marker, locks, or any file touch. Absent →
`CLEARANCE_MISSING`; pin drift → `CLEARANCE_PIN_MISMATCH`; any test
hook in live mode → `LIVE_HOOKS_REFUSED` — all with zero side effects
(trial e16).

## Proof (all offline, kernel network denial)

Executor matrix — **23/23 trials, 82/82 checks, twice under
`unshare -n`, byte-identical** (`19e8dc67…`):

- e01 happy path with the **real r4 gate** as the dry-run hook
  (adapter `7a56d86a…`): COMPLETE, backup == locked legacy bytes,
  adopted == candidate pin, exactly 1 spy call to
  `api.twelvedata.com/api_usage`, recovery → ADOPTED_VERIFIED with 0
  status calls.
- e02 ledger mutated by a child process **before** lock acquisition →
  HOLD `LOCKED_LEDGER_PIN_MISMATCH`; mutated bytes never overwritten;
  0 status calls.
- e03 mutation attempt while locks held: nonblocking attempt refused,
  blocking attempt waits until release, executor completes, target ==
  candidate (no overwrite).
- e04 two executors / same workdir: exactly one COMPLETE, loser
  `TXN_ALREADY_CONSUMED` at exclusive marker create, total status
  calls == 1. e05 two executors / different workdirs / same target:
  exactly one COMPLETE, loser HOLD `LOCK_CONTENTION_*`, total status
  calls == 1.
- e06 recovery TOCTOU: journal swapped between precheck and lock →
  HOLD_MANUAL `RECOVERY_JOURNAL_DRIFT_UNDER_LOCK`, ledger untouched;
  ledger drifted in the same window → HOLD_MANUAL
  `TARGET_UNKNOWN_BYTES`, drifted bytes left exactly in place.
- e07 gate-3 FAIL → HOLD, no adoption, 1 status call consumed;
  e08 gate-3 boundary (remaining exactly 52) → PASS/COMPLETE;
  e09 transport exception → HOLD, exactly one invocation, no retry;
  e10 second status call → `STATUS_SLOT_ALREADY_CONSUMED`.
- e11 the accepted exception cases against the integrated executor:
  evidence-fsync fault → ROLLED_BACK with exact locked bytes;
  dry-run RuntimeError → ROLLED_BACK; rollback-write fault →
  HOLD_MANUAL, never a false ROLLED_BACK.
- e12/e13 `os._exit(42)` crashes after replace and during terminal
  write, cold recovery in a fresh process → POST_REPLACE_UNVERIFIED,
  exact legacy restored, 0 status calls during recovery.
- e14 forged 11/12 receipt → HOLD_MANUAL; e15 relocated journal /
  edited target binding → HOLD_MANUAL, ledger untouched.
- e16 live clearance gate (above); e17 scope refusals; e18 marker
  exclusive-create (no lease file created); e19 candidate pin drift
  refuses before the marker; e20 locked bytes matching the pin but
  failing the legacy schema → HOLD `LOCKED_LEDGER_SCHEMA_MISMATCH`.

Regressions, twice under `unshare -n`, **byte-identical to the pinned
matrices**: r4 gate 46/46 trials, 332/332 checks (`aafd4e1b…`);
-13 transaction 45/45 trials, 193/193 checks (`56084b75…`). All
accepted bases re-verified by sha256 before use and unchanged after.

## Corrected proposal

`FUTURE_READINESS_EXECUTION_PROPOSAL_R4.md` — the -13 review's
wording defect is fixed (the dry-run runs inside the **r3**
transaction semantics as integrated by this executor, not "r2"), all
pins are exact, and it remains **NOT AUTHORIZED**, explicitly
excluding all 51 market-data requests and token issuance.

## Failures, repair, budget — disclosed plainly

Two failed attempts are preserved (`executor_matrix_attempt0_failed.json`
21/23; `executor_matrix_attempt1_failed.json` 22/23 +
`trials_attempt1_failed/`): a harness fixture-clock misalignment
(3600 s) and a `/tmp` tmpfs exhaustion (512 MiB, filled by regression
scratch) that made the gate's calendar re-derivation fail with
ENOSPC and flaked concurrent gate runs. Both were harness/environment
defects, not executor defects; details in
`FAILURE_MEMORY_20261017_14.md`. One repair was used; total elapsed
≈30 minutes of the ≤35 cap (12:58:52 ET start; manifest generated
13:28 ET).

## Scope confirmation

Offline/network-denied throughout; zero authenticated or vendor
calls beyond the spec fetch; helper invocations against the real
credential 0 (offline path resolves only the pinned stub through the
same resolver; the sanctioned helper was hash-verified, never
imported by the offline path); credits spent 0; **real ledger writes
0** — the live ledger re-verified `7e5ccef0…` after all runs, all
adoption on fixture copies; zero token/armed transport/`time_series`/
installs/backtest/performance/holdout/production/trading/Issue #9;
no merge/adoption — the executor remains an uncommitted candidate;
all prior packages byte-identical (verified via git status + pins).

## Pins

Executor `689ab473…` · adapter `7a56d86a…` · r3 `db93f07e…` · r4 gate
`b5399645…` · resolver `c8271193…` · helper `8b1f42e8…` · Policy A
digest `5d9d82ca…` · gate-3 candidate `7e44a2e0…` · legacy ledger
`7e5ccef0…` · ledger candidate `79ff4844…` · manifest `71aade8b…` ·
supplement `3cbdbf63…` · executor matrix `19e8dc67…` · gate matrix
`aafd4e1b…` · txn regression matrix `56084b75…`.

— Muse
