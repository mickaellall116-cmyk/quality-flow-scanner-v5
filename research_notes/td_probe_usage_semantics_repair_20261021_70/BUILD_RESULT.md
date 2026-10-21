# TD PROBE USAGE-SEMANTICS REPAIR — task -70 r1 RESULT

Task: QF-TD-PROBE-USAGE-SEMANTICS-REPAIR-20261021-70 r1
Spec: Issue #1 comment 6317623205 (-69 adjudication; basis -69
result commit c24c545, terminal TD_PROBE_DAY1_HOLD__G_USE_
USAGE_HEADROOM accepted; -68 package accepted as offline
candidate evidence). Scope: ONE bounded OFFLINE successor, new
additive package only; -68/-69 immutable. ONE implementation/
test attempt after a pushed precommit; first-failure stop.
No vendor/API/data calls, credentials, credits, real data,
holdouts, performance, S2 change, production, or trading.

## TERMINAL

TD_PROBE_USAGE_SEMANTICS_REPAIR_HOLD__U02_MINUTE_SATURATION_LIMITER

The single qualification attempt stopped at its first failure
(case 40 of 51). Per discipline there was NO in-run repair and
NO byte-identity repeat. 39/51 cases passed — the full -68
regression block (Q01-Q20, A01-A10, B01-B08, in order) plus
U01. U03-U13 were NOT RUN; no outcome is claimed for them in
either direction. The successor fix for U02 is a harness-only
change (below) and belongs to a successor task.

## First failure — U02, root-caused to the case, not the limiter

U02's daily sub-test starts the pinned limiter's FakeWallClock
at 1_762_730_000_000 ms (2025-11-09 23:13:20 UTC — the harness
NOW) and performs 100 grants of weight 8, advancing the clock
61 s after each: a total span of ~6100 s, which crosses the UTC
midnight boundary at +2800 s. The pinned RollingCreditLimiter
(v3) resets daily spent at the UTC day rollover — its correct,
pinned semantics (the defect-2 fix in its own history: the
rolling 60 s window survives midnight, the daily counter does
not). Daily spent therefore accumulates only from the rollover
(~54 grants x 8 = ~432), and the case's closing accumulation
assertion (daily_spent == 800, then an over-day refusal) fails.
Every minute-window assertion in U02 before that point, and the
saturated-minute preflight assertion's prerequisites, are
time-local; the failing span is the daily accumulation. The
limiter behaved exactly as pinned; the case's start instant
was mischosen for a 100 x 61 s accumulation (a UTC-midnight-
aligned start, e.g. 2025-11-09 00:00:00 UTC, keeps the whole
span inside one UTC day). This diagnosis is stated from the
case's own arithmetic; it was NOT verified by a repair rerun,
because none is permitted in this task.

## What the run DID prove (39 cases, incl. the core repair)

- Full -68 regression against the successor: 38/38 (scope
  isolation, twins mapping, ceiling arithmetic (12, 24), live
  2-attempt cap, no pagination, usage-failure-before-data, D1
  run + once-per-day cached reuse under the corrected body,
  sanitized receipts, base linkage, temporal boundaries,
  analyzer C1-C6 set, CLI refusals + end-to-end days, mixed-
  volume closure, receipt-ID closure, cache integrity set,
  mandatory expectations, C5 structure-first, cross-midnight
  cache refusal, wrong-endpoint cache, malformed numerics).
- U01 PASS — the -69 regression case: the live Day-1 shape
  (minute bucket current_usage=1 / plan_limit=8, daily pair
  1/800) PASSes the repaired preflight, the D1 synthetic run
  completes (5 data calls), and the persisted PASS receipt
  records plan_limit=8 as the minute bucket with the daily
  gate satisfied at 1 + 10 <= 800.

## The repair as built (source committed at precommit; the
## U03-U13 proofs did not execute — see terminal)

account_preflight.py (rewritten; the only logic change):
1. Quota dimensions separated. parse_usage_body returns the
   minute pair (current_usage/plan_limit, required integers
   >= 0, else USAGE_SCHEMA) and the daily pair (parsed ONLY
   when both daily_usage and plan_daily_limit are present;
   half-present or non-integer/negative is
   USAGE_DAILY_SCHEMA). evaluate_daily_gate charges
   required_headroom ONLY against the daily allowance:
   absent pair -> USAGE_DAILY_SCHEMA; plan_daily_limit !=
   pinned 800 -> USAGE_DAILY_PLAN; daily_usage >
   plan_daily_limit -> USAGE_DAILY_SCHEMA (contradictory);
   daily_usage + headroom > 800 -> USAGE_DAILY_HEADROOM.
   Minute fields never satisfy the daily gate; per-minute
   spacing remains the pinned RollingCreditLimiter(8, 800)'s
   job (its try_acquire semantics are exercised by U02's
   minute-window assertions, which passed).
2. Credit headers: only api-credits-used / api-credits-left
   are captured (allowlist, case-insensitive); when present
   and integer-parseable they are reconciled against the same
   response's minute bucket (used == current_usage;
   used + left == plan_limit) — a contradiction refuses
   USAGE_HEADER_MISMATCH. Headers never waive the daily gate
   (gate runs first; the check can only refuse).
3. Persist every outcome (defect-B repair): check() returns
   the PASS receipt or raises PreflightRefusal carrying the
   REFUSE receipt; DailyUsageSession persists the terminal
   attempt's exact body bytes (api_usage.<DAY>.body.bin, local
   evidence store only) and then the sanitized receipt
   (api_usage.<DAY>.receipt.json — the commit point) BEFORE
   returning any verdict. Receipt carries HTTP status, byte
   count + SHA-256 of exact body bytes, normalized fields,
   captured headers, attempt count + per-attempt statuses,
   endpoint/params, execution UTC date/time, manifest/store
   pins, verdict, terminal reason. Persist failure ->
   USAGE_RECEIPT_PERSIST_FAILED (HOLD). Stored REFUSE is
   sticky for its binding; stored PASS reuse re-verifies
   bindings, body-byte hash, payload digest + fields, the
   daily gate and header reconciliation re-run, timestamps,
   and the -67 UTC execution-date equality.
probe_runner.py: provenance stamps only (runner marker
td_probe_runner_candidate_70; docstring) — scope, ceiling
arithmetic, wiring byte-equivalent otherwise.
fixtures/fake_transport_module.py: canned usage body corrected
to the four-field shape (Q19 fixture; listed below).

## Byte-equality vs -68 (unchanged files — all EQUAL)

  probe_analyzer.py   ebea8272f33786676140b22b408eca46d87237a747be0f9e43600e9038933a0d
  temporal_gate.py    f882dd29bdf229264fb60eb12d7121d7bdc60536d5d71b16d893e236dc41e17e
  probe_manifest.json 1bb86e17ee7907bae67db9c22b0a74cc61027c495c1f1ed74d65df17585a53e1
  make_fixtures.py    28733bed43bff4e25d4c604ffd76d50c57faf3282c73722fde403a15b66c495a
  fixtures/ (55 of 56 files) recursive diff vs -68: identical
    (only fixtures/fake_transport_module.py changed — the
    canned usage body correction listed below)

## Changed -68 expectations (explicit, per task instruction)

The -68 usage fixtures encoded the defective semantics
(plan_limit=800 read as the daily budget, no daily fields).
Corrections, with outcomes in this run:
  * CountUsageTransport (harness) and FakeUsageTransport
    (fixtures/fake_transport_module.py) now serve
    {current_usage:3, plan_limit:8, daily_usage:3,
    plan_daily_limit:800}. PASS-path outcomes unchanged
    (Q06 503-path, Q07, Q19, B06 all PASS); under the
    corrected semantics the OLD body would HOLD at
    USAGE_DAILY_SCHEMA — that is exactly what U04 proves
    against the verbatim -69 live body.
  * Q07's stored-receipt assertions read the four-field
    canonical payload via the new parse API and additionally
    assert the persisted body file hash-matches the receipt.
  * A05-A09 / B07 receipt fixtures carry the four-field
    payload plus a matching persisted body file (the session
    now verifies body evidence before any cached outcome);
    A07's weaker-headroom scenario is re-expressed on the
    recorded-headroom binding with daily_usage=795/800.
    Expected refusal tags unchanged; all PASS in this run.
No other -68 case construction or expectation changed.

## Qualification — ONE attempt, stopped at case 40

Command: python3 -W error tests_qualification.py
Run 1: exit 1, stderr empty (0 bytes), stdout sha256
efb27727bf9dca46acb8b245e72603ecfe0f9f7a792df63e2fcc8e3714633f41
(preserved verbatim as QUALIFICATION_RESULTS.json).
Passed (39, in order): Q01-Q20, A01-A10, B01-B08, U01.
First failure: U02_minute_saturation_limiter (AssertionError,
empty message — the daily-accumulation assertion analyzed
above). NOT RUN: U03-U13 (daily headroom HOLD; missing /
malformed / contradictory daily fields; minute-cannot-
satisfy-daily; receipt/body hash persistence incl. sticky
refusal; receipt-write-failure HOLD; 429 accounting; stored-
PASS tamper set; Day-1 aggregate ceiling; headers-never-
waive). The corresponding source is committed and
inspectable, but carries NO test evidence from this run.
Byte-identity repeat: NOT RUN (permitted only after a full
pass).

## Pins, elapsed, attestation

Precommit: d43e413df8b06d8cc4292ba24b961bccca4f8607
(source/manifest/fixtures/SHA manifest committed and pushed
BEFORE execution; verified ancestor of origin/main before the
run). Result commit: this commit (see git log);
SHA256_MANIFEST.txt regenerated at result to cover the final
package.
Elapsed: ≈11 min from spec fetch (14:07Z) to result write-up
(14:18Z) of the ≤35 min cap. Repair minutes: 0 (no in-run
repair; the U02 diagnosis is reported, not fixed).
Zero-call / zero-secret attestation: no vendor, network, API,
or model calls beyond the read-only spec fetch; no credentials
read or resolved; zero credits spent; synthetic fixtures only;
Day 1 was NOT re-run (the -69 GO was consumed at G-USE; any
future live call requires Mike's fresh GO after independent
review); no S2 change or implementation; no -61 rerun; no
performance, holdouts, production, or trading touched.
State separation: REQ-S2 / data qualification / corrected
performance remain HOLD; entries PAUSED; the live probe
remains FRESH-USER-GO HOLD.
