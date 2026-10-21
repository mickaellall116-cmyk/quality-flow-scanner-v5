# TD PROBE OFFLINE CANDIDATE BUILD — task -65 r1 RESULT

Task: QF-TD-PROBE-OFFLINE-CANDIDATE-BUILD-20261021-65 r1
Spec: Issue #1 comment 6309668027 (one isolated, additive, offline
candidate package; precommit before execution; ONE implementation/
test attempt; synthetic fixtures only; no vendor/network/credential/
credit use of any kind).

## TERMINAL

TD_PROBE_OFFLINE_CANDIDATE_READY__INDEPENDENT_REVIEW_REQUIRED__USER_GO_STILL_REQUIRED

Candidate evidence only. This package is NOT adopted, NOT integrated
into any frozen/live path, and does NOT authorize the real probe.
The probe remains USER-GO HOLD; REQ-S2 / data qualification /
corrected performance remain HOLD; entries PAUSED. Passing the
sampled windows in any future probe cannot globally retire S2
(governance correction preserved — the analyzer emits sampled-window
PASS | DATA_UNQUALIFIED | HOLD only, case Q20).

## Sole ownership

Pre-check before ANY file operation: no td65 stage dir, no td65
worktree, no -65 commit on origin/main, no owner lease (parent
pre-check re-verified). Atomic owner lease (O_CREAT|O_EXCL) at
~/workspace/qf_td65_owner_lease.json; task-unique detached worktree
~/workspace/qf_td65_wt at origin/main e6403d7. Main working tree
never touched (pre-existing UU forward_test/kama_shadow.json
intact); no stash touched. Lease released LAST, after result-commit
remote verification.

## Components (all NEW files; no frozen file edited)

| component | file | sha256 |
|---|---|---|
| probe-only manifest (9 legs, max_attempts=2, budget 9/18, program ceiling 12/24 incl. usage) | probe_manifest.json | 65dc994eb9288b2931cd7657ca616307cc18ff4ed9bcbb8a35afbb37dcca5084 |
| pinned CLI runner candidate (hash-verified frozen import; scope allowlist before any preflight/transport construction; exit 3 refusals) | probe_runner.py | 0711e049a1d4fd48a44de32b688efcbcee84497e8d21b0dbd30730c6f4ebacc6 |
| account-preflight adapter candidate (injectable /api_usage, 1/day, ≤2 attempts, fail-closed verdict + O_EXCL daily receipt) | account_preflight.py | 19becc922c46d358ee3d4c8c3842bb4f5766d97c76b35f16a2ceb3026fe847d8 |
| temporal eligibility gate (REV7/REV30 elapsed-time from byte-verified base receipt; ±1ms boundaries) | temporal_gate.py | 552e1ff306c7728976f600046f3a25c086d608c4d557fe2d74e0690533263850 |
| C1–C6 analyzer candidate (Decimal, predeclared half-ulp tolerance from observed precision; sampled-window verdicts only) | probe_analyzer.py | 4f11a934b9133d0b9c9a3766e431760f58607de3ed2d88b96ea22b2a727d5e75 |
| fixture builder (deterministic synthetic payloads/receipts + rounding-boundary search) | make_fixtures.py | 1194f2df63d7aa830c1636aff9af74052d3bd9f8dc11858f567cc47ad67e2953 |
| qualification harness (20 cases, first-failure stop, warnings=errors) | tests_qualification.py | 686cfa26bbef83a99d88d9bff7d4367ef7889889346f886eeec95859c4ff7618 |

Frozen pins consumed (verified in-source, unchanged):
pilot_acquire.py acf39bbd98f7174a4205019e754fc714ca420b4a7df43
c815ea158a6fad67c59; rate_limiter.py 06ad383d856e62d126d1aae9edc
7804e1b09471d87d9b280ec55a25aea0b8d64. The runner imports the
frozen module by pinned path and refuses on hash mismatch.
Gap closure map: G1 → probe_runner.py; G2+G3 → probe_manifest.json
(data-only, frozen schema, twins + ADJ-linked REV legs, attempts=2,
no SPOT/PAR/PAG legs); G4 → account_preflight.py (injectable
interface; FRESH /api_usage shape b5399645… cited as a future
adapter binding only — Policy-A authority/manifest never copied);
G5 → probe_analyzer.py; -64 additional gap → temporal_gate.py.

## Qualification (ONE attempt, after precommit 45354b2)

Run 1: exit 0, stderr empty, 20/20 cases PASS.
Byte-identity repeat (permitted because run 1 passed): exit 0,
stderr empty, stdout BYTE-IDENTICAL to run 1
(sha256 3222976a00c9c1459fc9aeea0eec784f0dcf259325c4484ad778c8
b212c79fad). Full record: QUALIFICATION_RESULTS.json.

Case map to spec §6 minimum list: scope isolation Q01 (+ CLI
construction-order proof Q18: transports are never constructed on
hash/scope/day/traversal refusals); none/splits mapping Q02;
attempt-ceiling arithmetic incl. three usage preflights (expected
12, hard max 24) Q03 + live 2-attempt cap Q04; no pagination Q05
(5000-row ADJ response fires no child); usage failure before data
transport Q06; sanitized receipts Q08; base linkage Q09; R7/R30
temporal before/equal/after at 1ms boundaries Q10 (+ CLI D30-early
refusal Q19); uniform factor PASS Q11; mixed OHLC fail Q12;
inconsistent volume report/fail policy Q13; split-day flip Q11/C3
(flip located at the effective-date session, ON_EFFECTIVE_DATE);
revision identical/different Q15; malformed receipt/SHA/params
Q16; missing volume Q14; decimal-rounding boundary Q17 (searched
pairs straddle the predeclared tolerance: dev 0.00049995 ≤ tol
0.00054995 passes; dev 0.00079992 > tol fails); no global S2
verdict Q20. Once-per-day usage semantics + resume: Q07.

## Elapsed / repair

Total elapsed ≈16 min of the ≤60 cap (build+precommit ≈13 min,
qualification run ≈1 min, byte-identity repeat ≈0.5 min, results
≈2 min). Repair minutes: 0 — no in-run repair; the first and only
attempt passed. Two authoring corrections were made BEFORE
precommit (store-path rule scoped to traversal; Q06 retryable
status 503 not 500) and are part of the single build, not repairs
of a failed run.

## Failure-family tags (searchable)

UNEXPECTED_REQUEST_ID, SCOPE_FIELD_MISMATCH, SCOPE_INCOMPLETE,
MANIFEST_HASH_MISMATCH, MANIFEST_MALFORMED, UNRECOGNIZED_DAY,
EMPTY_DAY_LEG, STORE_PATH_TRAVERSAL, STORE_CONFLICT,
STORE_FOREIGN_CONTENT, STORE_MARKER_MALFORMED,
PILOT_SOURCE_HASH_MISMATCH, BASE_RECEIPT_MISSING,
BASE_SNAPSHOT_MISSING, BASE_RECEIPT_MALFORMED, BASE_RECEIPT_IDENTITY,
BASE_RECEIPT_PARAMS, BASE_EVIDENCE_TAMPERED, BASE_TS_MALFORMED,
BASE_TS_FUTURE, REV_NOT_YET_ELIGIBLE, USAGE_SCHEMA, USAGE_HEADROOM,
USAGE_TERMINAL_STATUS, USAGE_RETRIES_EXHAUSTED, RECEIPT_MISSING,
SNAPSHOT_MISSING, RECEIPT_MALFORMED, RECEIPT_IDENTITY,
RECEIPT_PARAMS_MISMATCH, SNAPSHOT_SHA_MISMATCH,
SNAPSHOT_BYTES_MISMATCH, SNAPSHOT_MALFORMED.

## Disclosures

- The /api_usage response schema (current_usage/plan_limit integer
  pair) is validated fail-closed by the adapter but remains an
  EXECUTION-DAY observation: the synthetic fake implements the
  documented/recorded shape only; real schema conformance is
  UNTESTED UNTIL USER GO (unchanged from -64 §5).
- The runner's live-transport path (pilot UrllibTransport) exists
  in the candidate but was never constructed or exercised in this
  task; all runs used injected synthetic fakes.
- Credential presence/validity, account/plan status, credit
  headroom, endpoint conformance, host clock, and network egress
  remain UNTESTED UNTIL USER GO. No credential was read or
  resolved; zero credits spent; zero network calls beyond the
  read-only spec fetch.
- SHA256_MANIFEST.txt was regenerated for this result commit: it
  adds BUILD_RESULT.md + QUALIFICATION_RESULTS.json; every
  precommitted file's hash is unchanged from precommit 45354b2.
