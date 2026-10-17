# TD LIVE READINESS RUN — QF-TD-READINESS-LIVE-20261017-18

**Outcome: ROLLED_BACK — dry-run 11/12 (gate 3 ACCOUNT_EVIDENCE_STALE under the
dry-run's injected test clock). Exactly ONE authenticated `GET /api_usage` was
transmitted; exactly 1 free-tier credit spent ($0). The ledger adoption was
rolled back to the exact legacy bytes. The one-use transaction is CONSUMED and
was NOT retried.**

Authority: Issue #1 comment 6240787703 (verdict
`STATUS_QUERY_PLACEMENT_TARGETED_PASS_OFFLINE__TIME_BUDGET_BREACH__ONE_USE_READINESS_CLEARED`),
standing behind it Mike's Policy A GO (comment 6234434220, 52-credit ceiling).
Prior transaction -16 remains consumed/untouched (journal `4c01b1a0…`,
clearance `842be4f5…` re-verified unchanged after this run).

## Clearance verification (STEP 1 — all PASS, before any execution)

- Clearance artifact created with the exact canonical bytes from comment
  6240787703 (1,273 bytes, no trailing newline); recomputed sha256
  `5ef146227dc8dad6dbc072baf80d46874bfbbda397d504e43df7326dba500e94`
  == required sha. **Match.**
- Packet digest recomputed via the r3 executor's own `_packet_identity`:
  `e1cb2f6fa96af8abb591c9e05111722d900ffea48931c84685a5da9c1401bd41`
  == the digest bound in the clearance. **Match.**
- Every binding hash-verified against committed bytes: executor r3
  `8b01c6f5…` (source sha recomputed live), r4 gate `b5399645…`, r4 runner
  `93b911e0…`, r3 transaction `db93f07e…`, resolver `c8271193…`, gate-3
  contract `7e44a2e0…`, Policy A file `728c3def…` + canonical digest
  recomputed `5d9d82ca…`, sanctioned helper `8b1f42e8…`, adapter `7a56d86a…`,
  candidate `79ff4844…`, legacy ledger `7e5ccef0…`; ceiling 52; scope
  `READINESS_ONLY_ONE_API_USAGE`; canonical target/workdir/candidate/dry-run
  paths; placement parameter `apikey` per the -17 proof.
- The executor's own `validate_live_admission()` accepted the clearance with
  all schema-v2 bindings verified and created nothing (workdir absent after
  the check). No pre-existing marker/workdir for -18. Target not a symlink;
  realpath == canonical path.

## The single execution (2026-10-17T21:01:01Z → 21:01:08Z)

Executor output: `{"outcome": "ROLLED_BACK", "reason": "DRY_RUN_NOT_12_OF_12"}`,
exit code 0. Journal phases: BEGUN → PREFLIGHT_OK → LOCKS_HELD → HELPER_OK →
STATUS_CONSUMED → GATE3_OK → BACKED_UP → REPLACED → VERIFIED → REFROZEN →
TERMINAL_ROLLED_BACK. Locks taken lock-first; ledger read only under lock and
matched the legacy pin + schema; the status slot was consumed and journaled
before invocation (`status_calls: 1`).

**The status call WAS transmitted this time — exactly once.** HTTP 200.
Vendor-reported facts (recorded in evidence.json):

| field | value |
|---|---|
| timestamp | `2026-10-17 21:01:03` |
| current_usage | 1 |
| daily_usage | 1 |
| plan_limit | 8 |
| plan_daily_limit | 800 |
| plan_category | `basic` |

**Gate 3 (executor, Policy A, real UTC): PASS — `ACCOUNT_VERIFIED_POLICY_A`.**
Plan identity via the 8/800 limit pair; standing via authenticated
availability; Policy A computed remaining = 800 − 1 = **799 ≥ 52**. The
response self-counts this call (daily_usage 0 → 1); Policy A's conservative
non-self-counting assumption is satisfied either way.

**Credits spent: exactly 1** (vendor daily_usage 0 → 1; $0 free tier).

## Adoption and rollback

Gate 3 passed, so the executor backed up the locked legacy bytes
(`ledger_backup.bin`, sha `7e5ccef0…`), adopted the pinned candidate
(post-replace hash verified == `79ff4844…`), refroze evidence + derived the
token card, then ran the r4 dry-run against the post-adoption bytes.

**Dry-run: 11/12.** Gates 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12 PASS
(PACKET_BOUND, AUTHORITY_STANDING, LEDGER_STATE_VERIFIED, ENV_PINS_VERIFIED,
ALL_PINS_RECOMPUTED, CLOSED_DATE_REDERIVED, NAMESPACE_NEW,
CREDENTIAL_BOUNDARY_AND_HELPER_VERIFIED, ADAPTER_CONTRACT_BOUND,
STOP_RULES_BOUND, RETENTION_BOUND). **Gate 3
(account_plan_status_capacity) FAIL — `ACCOUNT_EVIDENCE_STALE`.**

Diagnosis (code-level, from the preserved artifacts): the r4 dry-run is wired
through the -11 trial machinery (`run_dispatch_gate_trials_r4.py`), whose
context clock is a FIXED injected test clock, `NOW = 1792224000`
(2026-10-17T08:00:00Z; the dry-run receipt records `clock_mode:
"injected_test"`, `evaluated_at: "2026-10-17T08:00:00Z"`). Gate 3's freshness
bound is 3600 s against that clock. The live vendor evidence (timestamp
21:01:03Z, ~1 s old at the executor's real-UTC evaluation) sits ~13.0 hours
AHEAD of the frozen trial clock, so the freshness check failed. The failure is
in the dry-run wiring — the trial context clock was never advanced to live
time — not in the account evidence, which the executor's own Policy A gate-3
evaluation accepted at real time. Per the clearance's fail-closed terms, the
executor treated the non-12/12 dry-run as a failed post-adoption check and
rolled back: **final ledger sha256 = `7e5ccef0…`, byte-identical to the
pre-run legacy bytes** (rollback hash-verified by the executor; independently
re-hashed after the run).

Terminal record: outcome `ROLLED_BACK`, detail `DRY_RUN_NOT_12_OF_12`,
status_calls 1. Journal final phase `TERMINAL_ROLLED_BACK`. No crash occurred,
so `recover()` was not run (its crash-only condition was not met; the journal
reached a terminal phase through the executor's own failure discipline). The
CONSUMED marker stands — a second invocation would refuse
`TXN_ALREADY_CONSUMED`.

## Evidence set (this package, uncommitted)

| file | sha256 |
|---|---|
| clearance.json | `5ef146227dc8dad6dbc072baf80d46874bfbbda397d504e43df7326dba500e94` |
| live_packet.json | `8fe5ad8474098492281679a11c88ca56f955c498164c0ccc57155657ad81832e` |
| txn/journal.json | `2fa395f235ad6a13fa4d3f599176874764e1f9c79b9301679f01060afd956db2` |
| txn/CONSUMED.marker | `6c957a53e277eb4bf277b9db740a286a745b35314500649de04c612417eb56b2` |
| txn/terminal_record.json | `de76f6dcf8952f2b682314ce9f062656f53fbbb5bd7b5e9f779b7d06b8395388` |
| txn/dry_run_receipt.json | `e2eea2b947fbdec3e9fd087fda1cecf18d7ec875dc180c0abc4e2b569c50e012` |
| txn/evidence.json | `8da1d41d0558459a9c1a25da615d95243235ec5968267e66aeaf2fad633fc108` |
| txn/token_card.json | `67a73cf113e536b94269115d9581581a30b64702ed9227b2028859fd26dfb133` |
| txn/ledger_backup.bin | `7e5ccef0e5fd7e2faa744c8fe7ee646c3162fa4f72fc4a9a85317d52b5d890ed` |
| dryrun/dryrun/account/gate_receipt.json | `2fed6b5538312892c77d6509c1148c8fe9b833b9177a2732f9818fd877e7bff1` |

Ledger pre-run sha256: `7e5ccef0…`. Ledger post-run sha256: `7e5ccef0…`
(adopted transiently to `79ff4844…` during the run; rolled back exactly).
Status slot count: 1. Transmitted requests: 1. Credits: 1.

## Prohibitions honored

Exactly one attempt; no retry; no second status call; no `time_series` or any
market-data request (zero market-data calls, attested); no token issuance/use
for the screen (the derived token card is the readiness refreeze artifact
only, never used); no 51-request screen; no backtest/performance/holdout
access; no production/trading change; no Issue #9; no pinned file edited; no
manual ledger edit (the only ledger writes were the executor's own
adoption + verified rollback); no credential or credentialized URL recorded or
exposed (diagnostics are categorical; evidence carries only the vendor's
usage facts).

## Next step (review matter, not an improvisation)

The account side is now proven live: plan identity, standing, capacity
(799 remaining) and the 1-credit cost are vendor-evidenced. What failed is the
readiness dry-run's frozen test clock. Any further attempt needs a NEW one-use
clearance plus adjudicated reconciliation of the dry-run clock wiring (the
adapter/trial context must evaluate live evidence at live time, or the
readiness dry-run must be re-specified) — nothing was patched around this
outcome. The 51-request screen and token remain HOLD.

— Muse
