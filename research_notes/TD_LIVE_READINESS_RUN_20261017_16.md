# TD LIVE READINESS RUN — 2026-10-17 (-16)

**Transaction:** `QF-TD-READINESS-LIVE-20261017-16` (one-use, no-retry).
**Authority:** Mike's Policy A 52-credit ceiling GO (Issue #1 comment
6234434220, record `QF-TD-POLICY-A-52-CREDIT-CEILING-GO-20261017`) +
the distinct one-use readiness clearance recorded in Issue #1 comment
6238900206 (verdict
`LIVE_CLEARANCE_PATH_BINDING_TARGETED_PASS__ONE_USE_READINESS_CLEARED`,
reviewing commits 6f05978 / 89c99f1).
**Verdict: `HOLD` — reason `STATUS_URL_BOUNDARY`.** The single cleared
execution was performed exactly once. The executor fail-closed at its
own URL boundary **before any transport**: zero authenticated requests
were transmitted, **zero credits were spent**, the live ledger is
byte-identical, and nothing was adopted. The one-use transaction is
consumed (marker + journal) and must not be re-run; any future attempt
requires a new clearance.

## STEP 1 — pre-execution verification (all PASS, zero vendor contact)

- Clearance file created with the exact canonical UTF-8 bytes from
  comment 6238900206 (no trailing newline); recomputed sha256
  `842be4f56f0cbd345efc74162132de91c0984ef68d1f19b4d299791d74d528a8`
  == the required clearance sha256. **Match.**
- Packet digest recomputed via the executor's own `_packet_identity`:
  `3d2351ddf9a243469dfe146ee3f76caf866da099bcc19c965eb8ecda8130fd0e`
  == the digest bound in the clearance. **Match.**
- File pins recomputed: executor r2 `e93e88a5…`, r4 gate `b5399645…`,
  r4 runner `93b911e0…`, r3 transaction `db93f07e…`, resolver
  `c8271193…`, gate-3 contract `7e44a2e0…`, Policy A file `728c3def…`
  and canonical Policy A digest `5d9d82ca…`, sanctioned helper
  `8b1f42e8…`, candidate `79ff4844…`, legacy ledger `7e5ccef0…`.
  **All match.**
- The executor's own `validate_live_admission()` returned the
  clearance (every schema-v2 binding verified: txn id, executor/gate
  sha, Policy A digest, candidate/legacy sha, ceiling 52, scope
  `READINESS_ONLY_ONE_API_USAGE`, target/workdir/candidate/dry-run
  canonical paths + packet digest, GO record, path hygiene) and
  created nothing; workdir absent and ledger untouched afterwards.

## STEP 2 — the single execution

Invoked once: `live_readiness_executor_r2.py run live_packet.json`,
2026-10-17T18:59:51Z → 18:59:52Z. Executor output:
`{"outcome": "HOLD", "reason": "STATUS_URL_BOUNDARY"}`.

Journal phase history (authoritative record):
`BEGUN → PREFLIGHT_OK → LOCKS_HELD → HELPER_OK → STATUS_CONSUMED →
TERMINAL_HOLD_PRE` (reason `STATUS_URL_BOUNDARY`). Locks were acquired
lock-first (owner lease, then ledger lock) and the ledger was read
only under lock; its locked hash matched the legacy pin and its schema
validated. The verified helper handle resolved. The single status slot
was consumed and journaled **before** invocation, per the accepted
design (`status_calls: 1` in the journal — the slot, not a transmitted
call). The helper then produced the credentialized URL locally, and
the executor's independent URL boundary refused it, so
`StatusBoundary.call()` raised **before** `transport` was invoked:
**transport invocations = 0; no HTTP request left this machine; no
vendor response exists; authenticated-call count (transmitted) = 0;
credits spent = 0.**

Diagnosis (code-level): the boundary requires the credential query to
be empty or exactly one `access_token` parameter. The sanctioned
helper's `url_with_surrogate_query_param` instead appends the
surrogate under the parameter name declared by the credential's own
placement metadata (`placement.query_param`; for Twelve Data that is
the vendor's `apikey` parameter). Every other URL component is
inherited unchanged by the helper from the pinned
`https://api.twelvedata.com/api_usage` constant (which itself passes
scheme/host/path/port/fragment checks), so the query-shape check is
the only boundary check that can have failed. The credentialized URL
was never recorded or exposed, per the clearance terms. The -15
offline URL trials used `access_token`-shaped helper fixtures, so
this mismatch between the boundary's assumed parameter name and the
real helper's placement-driven name is a genuine live-integration
finding, surfaced exactly by the fail-closed boundary doing its job.

## Outcome state

- **Adoption: NO.** Pre-run ledger sha256 `7e5ccef0…`; post-run ledger
  sha256 `7e5ccef0…` — byte-identical. No backup was created
  (`backup_sha: null`; `BACKED_UP` never reached).
- **Gate 3: not evaluated** (no `/api_usage` response exists to
  evaluate). Vendor-reported usage/plan facts: **none received**.
- **Dry-run: not run** (the run held pre-adoption); no 12-gate receipt
  exists.
- **Terminal record file: absent by design on this refusal path** —
  the journal itself carries the terminal phase
  (`TERMINAL_HOLD_PRE`) and is the terminal evidence, per the -13
  journal discipline.
- **No crash occurred**, so `recover()` was not run (its condition —
  a crash-interrupted nonterminal journal — did not occur; the
  journal reached a terminal phase through the executor's own failure
  discipline). The transaction is nonetheless consumed: the
  `CONSUMED.marker` exists and a second invocation would refuse
  `TXN_ALREADY_CONSUMED`.
- Filesystem side effects beyond the evidence set: the 0-byte
  `credit_ledger.json.dispatch_lease` sidecar created by lock
  acquisition (locks released at process exit), alongside the
  pre-existing Oct-14 `.lock` sidecar. No tracked file in the repo
  was modified; HEAD unchanged.

## Evidence set (uncommitted)

Run root: `research_notes/td_live_readiness_run_20261017_16/`

- `clearance.json` — sha256 `842be4f5…` (the cleared artifact itself)
- `live_packet.json` — sha256 `4819b8410325697d51db1822a89afa875093e073d3975b4320f27e22b6098bd5`
- `txn/journal.json` — sha256 `4c01b1a0b53599aa3423439684091acd03064727e45e1ea6d43eb7510cc82d88`
- `txn/CONSUMED.marker` — sha256 `edafbea50aa13bf90b5bef7e386e139717588c7edf33cd1022c3c62b1fac8744`
- No `evidence.json`, `token_card.json`, `dry_run_receipt.json`,
  `terminal_record.json`, or `ledger_backup.bin` exist (never
  reached).

## Prohibition attestations

Exactly one execution attempt; no retry and no second status call
(the slot was consumed once and no transport occurred at all); no
`time_series` or any market-data request; no token issuance or use;
no 51-request screen (still HOLD); no backtest/performance/holdout
access; no production/trading change; no Issue #9 work; no pinned
package file edited; no manual ledger edit (the ledger was only ever
read under lock by the executor); no credential or credentialized URL
exposed in any artifact or report.

## What would be needed before any future attempt (review matter)

A new one-use clearance, and reconciliation of the parameter-name
assumption: either the executor boundary accepts the placement's
declared parameter name (bound and pinned, not open-ended), or the
status call is constructed so the credential travels under the name
the boundary pins. Not patched here — the run's discipline is to
report, not to improvise around a HOLD.

— Muse
