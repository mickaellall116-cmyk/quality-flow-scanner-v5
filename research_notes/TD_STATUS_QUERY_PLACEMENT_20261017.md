# TD STATUS QUERY PLACEMENT (-17 r1) — MEMO

Task: QF-TD-STATUS-QUERY-PLACEMENT-20261017-17 r1 (Issue #1 comment
6239474608). Offline/network-denied throughout. Deliverables
UNCOMMITTED.

## Verdict: STATUS_QUERY_PLACEMENT_TARGETED_PASS_OFFLINE

## Placement proven: `apikey`
Read-only, no credential resolved, helper never invoked. The helper
(sha256 8b1f42e8..., byte-identical at both sanctioned paths) takes
the query parameter NAME from the credential entry's placement
record. Committed sanitized attestation (TD_VAULT_BINDING_CORRECTION_
RESULT_20261014.md, 54c92d9b..., commit 1597988) records the
registered placement for custom.twelvedata as {"query_param":
"apikey"}, and the 2026-10-14 live screen (bfa431e7.../ce76ed4e...)
ran successfully through that exact path. Full chain:
td_status_query_placement_20261017_17/PLACEMENT_PROOF.md. The -15
boundary had pinned the vault ENTRY name (`access_token`) as if it
were the query parameter — the root cause of the -16 HOLD.

## Candidate
live_readiness_executor_r3.py, sha256 8b01c6f5117ea3edf61603095928a15c57c43b6cc8db2a7a22e5af108adf7356
— minimal revision of r2 (exact diff: executor_r2_to_r3.diff, 57
lines): PLACEMENT_QUERY_PARAM = "apikey" pinned as a proven input
fact; the final credentialized URL must carry EXACTLY that one key,
one occurrence, non-empty value; empty query now refuses
(query_missing) — no empty-query exception; all other boundary rules
unchanged; diagnostics remain category tokens only (no URL/value).

## Tests (twice under unshare -n, byte-identical)
placement_matrix_run1.json == placement_matrix_run2.json, sha256
e68ba5afe099125bbc9fcc47a7b0d4c8c5459ebadb661382ca299143b987a028:
30/30 trials, 113/113 checks. Includes: the -16 mismatch reproduced
against the ORIGINAL r2 validator (refuses the placement shape,
accepted the assumed shape); the unchanged -15 q01–q14 lock/
clearance/path trials; the 8 hostile URL cases (all HOLD, 0
transport); placement-faithful good run COMPLETE (exactly 1 status
slot consumed, 0 real requests — fixture transport); and the -17
exact-key cases, all HOLD pre-transport with 0 transport: old
access_token shape, empty query, empty value, duplicate key,
percent-encoded extra key, wrong-case key. Slot count vs transmitted
count are distinguished throughout: transmitted real requests = 0.

## Time / repair
~24 min wall including one <=5-min repair: attempt 0 was 28/30
(107/113) because the inherited fixture default helper (the -11 stub)
returns the bare URL unchanged — an empty query the r3 boundary
correctly refuses; the -17 default fixture helper is now
placement-faithful by construction (helper_stub_placement.py).
Failed matrix preserved (placement_matrix_attempt0_failed.json).
A first draft of two docs was corrupted by shell interpolation and
rewritten verbatim; no evidence was affected.

## Failure memory
FAILURE_MEMORY_20261017_17.md, canonical key
STATUS_URL_QUERY_PARAM_ASSUMPTION: fixture shape must be DERIVED from
the real counterpart's declaration, never assumed; self-consistent
fixtures proved nothing in -15.

## Proposal
FUTURE_READINESS_EXECUTION_PROPOSAL_R6.md — NOT AUTHORIZED; binds a
NEW transaction id (QF-TD-READINESS-LIVE-20261017-18) and the r3 pin;
the consumed -16 identity is never reused; the 51 requests and token
issuance remain excluded.

## Scope confirmation
Zero helper invocations, zero vendor calls, zero credits; live
ledger untouched (7e5ccef0... re-verified); -16 artifacts read-only;
-14/-15 packages byte-identical (r2 re-verified e93e88a5...); no
token/transport/time_series/backtest/production/Issue #9 work.
