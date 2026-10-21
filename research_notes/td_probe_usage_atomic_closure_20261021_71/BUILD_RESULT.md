# TD PROBE USAGE ATOMIC CLOSURE — task -71 r1 RESULT

Task: QF-TD-PROBE-USAGE-ATOMIC-CLOSURE-20261021-71 r1
Spec: Issue #1 comment 6319460212 (-70 adjudication: HOLD
accepted; U02 diagnosis independently confirmed; additional
source finding on DailyUsageSession._persist_outcome).
Basis: -70 package (precommit d43e413, result 7cb942b),
immutable. Scope: ONE bounded OFFLINE successor, new additive
package only; -68/-69/-70 immutable. ONE implementation/test
attempt after a pushed precommit; first-failure stop. No
vendor/API/data calls, credentials, credits, real data,
holdouts, performance, S2 change, production, or trading.
Day 1 NOT re-run.

Precommit: 06a86faedbcf23eb371c78bbe3b499f175f7a0d0
(pushed and ancestry-verified against origin/main BEFORE
execution).

## TERMINAL

TD_PROBE_USAGE_ATOMIC_CLOSURE_HOLD__U12_AGGREGATE_CEILING_DAY1

The single qualification attempt stopped at its first failure
(case 50 of 62). Per discipline there was NO in-run repair and
NO byte-identity repeat (a repeat is permitted only after a
full pass). 49/62 cases passed. U13 and the eleven new
persistence cases P01-P11 were NOT RUN; their source is
committed and inspectable but carries NO test evidence, and no
outcome is claimed for them in either direction.

## What the run DID prove (49 cases)

- Full -68 regression block against the successor: 38/38
  (Q01-Q20, A01-A10, B01-B08, in order) — unchanged from -70.
- U01 — the -69 live-shape regression (minute 1/8 + daily
  1/800 PASSes; day budget charged to the daily allowance).
- U02 — FIXED AND VERIFIED BY EXECUTION. The daily sub-test
  now starts at the UTC-midnight-aligned derivation
  1762730000.0 - (1762730000 % 86400) = 2025-11-09 00:00:00
  UTC; all 100x8 grants + 61 s spacing stay inside that UTC
  date, daily_spent == 800 is reached, and the over-day
  refusal fires. Limiter logic and expected semantics were
  not altered.
- U03-U11 — daily-headroom HOLD, missing/malformed/
  contradictory daily fields, minute-cannot-satisfy-daily,
  PASS+REFUSE receipt/body hash binding and sticky refusal,
  U09 receipt-write-failure HOLD exercised end-to-end through
  run_probe_day against the NEW transactional writer, 429
  retry accounting, stored-PASS tampering refusals.

## First failure — U12, root-caused to the case's expectation
## against the FROZEN wrapper, not to the -71 changes

U12's second block serves a Day 1 in which NVDA, TSLA and
AAPL all fail (503 on every attempt) and asserts all five D1
legs are attempted: len(data.calls) == 10, total == 11. The
recorded total is 3 (1 usage + 2 data), so the assertion
fails as AssertionError: 3.

The frozen acquisition wrapper's semantics are the opposite
of the case's assumption. pilot_acquire.py (SHA-256 pinned,
acf39bbd...; AcquisitionWrapper.run, lines 329-332) iterates
the day's specs and BREAKS the run at the first stop outcome
— AUTH_STOP, SCHEMA_QUARANTINE, RETRIES_EXHAUSTED,
LEDGER_REFUSED, RATE_STOP — annotated "fail closed: stop the
run, report the blocker". The first D1 request (REQ-ADJ-01,
NVDA splits) exhausts its 2 attempts against the 503 fake,
returns RETRIES_EXHAUSTED, and the wrapper stops the day;
the remaining four legs are never attempted. 1 + 2 = 3 is
exactly the frozen behavior.

U12 was authored in -70 and had NEVER executed before this
run (-70 stopped at U02, case 40; U12 is case 50). Its
all-legs-attempted expectation contradicts the pinned
wrapper's documented fail-closed stop, so this is a
case-expectation defect of the same class as U02 — in the
harness, not in the candidate. Neither -71 change (the U02
clock derivation; the transactional persistence in
account_preflight.py) is implicated: every case that
exercises them passed, and the transactional writer's own
pre-existing coverage (U08/U09) passed against it. The
successor fix is harness-only: re-express U12's all-fail
block on the frozen stop semantics (first exhausted leg
stops the day; total == 3 <= the 12 hard ceiling) — and it
belongs to a successor task, not this one. This diagnosis
is stated from the frozen source plus the recorded call
arithmetic; it was NOT verified by a repair rerun, because
none is permitted in this task.

## Persistence design (account_preflight.py, as built)

DailyUsageSession._persist_outcome is now transactional:
(1) refuse up front if either final path already exists
(lexists) — collisions and ambiguous orphaned final evidence
are never silently overwritten (OSError
USAGE_PERSIST_COLLISION, which the session surfaces as
USAGE_RECEIPT_PERSIST_FAILED); (2) stage body and sanitized
receipt to same-directory temp files via mkstemp (mode
0o600, enforced with fchmod), each written with a write-all
loop over the _write_once seam (a <= 0 return is an error,
never a spin) and fsynced via the _fsync seam; (3) publish
the body first by hard link (the _link seam; link refuses an
existing final name), fsync the parent directory; (4)
publish the receipt LAST as the commit point, fsync the
parent directory again. A committed receipt therefore never
exists unless its exact body is present and durable. Temp
files are unlinked on any failure; a final already published
is left in place as evidence (a later session refuses on the
collision). -70 quota semantics are preserved exactly
(minute current_usage/plan_limit; explicit Basic daily pair
pinned to 800/day; headers refuse-only; rolling limiter,
12-call ceiling, <= 2 attempts, zero pagination, zero
/splits all untouched — probe_runner.py, probe_analyzer.py,
temporal_gate.py, make_fixtures.py, probe_manifest.json and
all fixtures are byte-identical to -70).

## Case count / order (62)

Cases 1-49 PASS, in order: Q01-Q20 (scope isolation, twins
mapping, ceiling arithmetic, attempt cap live, no
pagination, usage-failure-before-data, D1 run + once-per-day
reuse, sanitized receipts, base linkage, temporal
boundaries, analyzer C1-C6 set, CLI refusals, CLI end-to-end
days, no global verdict), A01-A10 (mixed volume, swapped
IDs, bar-set defects, meta mismatch, cache integrity set,
coverage), B01-B08 (mandatory expectations, C5
structure-first set, cross-midnight cache, wrong-endpoint
cache, malformed numerics), U01-U11 (minute/daily semantics
set incl. fixed U02, receipt persistence set, 429
accounting, stored-PASS tampering).
Case 50 FAIL: U12_aggregate_ceiling_day1 (above).
Cases 51-62 NOT RUN: U13_headers_never_waive,
P01_short_writes_completed, P02_zero_progress_write_refused,
P03_body_write_failure, P04_body_fsync_failure,
P05_receipt_write_failure, P06_receipt_fsync_failure,
P07_rename_link_failure, P08_parent_dir_fsync_failure,
P09_preexisting_orphan_body,
P10_preexisting_receipt_without_body,
P11_committed_outcomes_survive_reopen.

## Run record

- Command: python3 tests_qualification.py (package dir),
  warnings-as-errors inside cases, first-failure stop.
- Exit code: 1. all_pass: false. Cases recorded: 50.
- Stdout SHA-256 (== committed QUALIFICATION_RESULTS.json):
  29d72a1834c3e9b32e60a01280483423979c1d5f35b37065947ae7d5c92352b2
- Stderr SHA-256 (empty):
  e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- Elapsed: ~16 min wall for the whole task (dispatch to
  final result commit, including the corrective commit in
  disclosure 4), of the <= 30 min cap; the qualification
  run itself ~1 s. Repair minutes: 0 (no in-run repair;
  the corrective commit repaired commit construction, not
  the run).
- Byte-identity repeat: NOT RUN (not permitted — no full
  pass).

## Changed-file diff vs -70

- account_preflight.py — CHANGED: module docstring gains
  the task -71 section; imports tempfile; adds the
  _write_once/_fsync/_link syscall seams, the _write_all
  loop and _fsync_dir helpers; DailyUsageSession gains
  _stage_temp and the transactional _persist_outcome above.
  Quota semantics, parsing, gate, cache verification and the
  session contract are byte-preserved outside the
  persistence section.
- tests_qualification.py — CHANGED: header docstring gains
  the -71 block; U02's daily sub-test clock literal replaced
  by the UTC-midnight-aligned derivation (the ONLY change to
  an existing case's construction); P01-P11 persistence
  cases appended after U13; harness label
  td70_qualification_r1 -> td71_qualification_r1.
- Byte-identical to -70 (verified by cmp / diff -rq):
  probe_runner.py, probe_analyzer.py, temporal_gate.py,
  make_fixtures.py, probe_manifest.json, fixtures/ (all 56
  files).
- BUILD_RESULT.md, QUALIFICATION_RESULTS.json,
  SHA256_MANIFEST.txt — new/regenerated for this package
  (the -70 stale copies were NOT carried over).

## Disclosures

1. The HOLD is, for the second consecutive task, a defect
   in a never-before-executed harness case — this time an
   expectation that contradicts the SHA-pinned frozen
   wrapper's documented fail-closed stop. 49 cases of
   positive evidence (including the U02 fix and the new
   writer under U08/U09) do not convert the terminal.
2. P01-P11 (the deterministic persistence failure-injection
   cases ChatGPT's -71 spec added) were fully implemented
   but sit after U12 in the frozen order and were NOT RUN;
   they carry no test evidence. Any successor should run
   them exactly as committed here (their construction is
   part of this package) unless its own spec changes them.
3. Zero vendor/API/data calls, zero credentials resolved,
   zero credits spent; synthetic fixtures only. Day 1 was
   not re-run. REQ-S2 HOLD; entries PAUSED; the probe's
   fresh-user-GO gate is unchanged.
4. Commit-construction error, corrected: the first result
   commit (0df6cff) carried only the refreshed
   SHA256_MANIFEST.txt — the temp-index updates for the two
   NEW files (BUILD_RESULT.md, QUALIFICATION_RESULTS.json)
   failed for want of --add and the push proceeded on the
   partial tree. A corrective commit followed immediately,
   adding both files and a manifest regenerated without the
   fixtures/__pycache__/*.pyc byproduct the harness run
   creates when it imports the fixture module (the .pyc was
   never in the precommit tree — the precommit manifest's
   63 entries are clean — and it is not in the final tree).
   The qualification attempt itself is untouched by this:
   one run, exit 1, stdout/stderr hashes exactly as
   recorded above.
