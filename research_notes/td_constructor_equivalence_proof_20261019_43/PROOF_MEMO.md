# QF-TD-CONSTRUCTOR-EQUIVALENCE-PROOF-20261019-43 r1 — PROOF MEMO

Spec: Issue #1 comment `6281741142`. Budget ≤45 min, ONE offline attempt,
first material failure stops, repair minutes = 0. Exactly one attempt was
made; the failure below was recorded, never repaired or rerun.

## TERMINAL VERDICT (verbatim)

`TD_CONSTRUCTOR_EQUIVALENCE_PROOF_HOLD__E2_CLEARED_ROUTE_ERROR`

The HOLD arises **solely from E2 fixture F3**. The E1 calendar-equivalence
family **passed in full (761/761)** before E2 began — that result is
established evidence and stands independently of the terminal HOLD.

## E1 — calendar equivalence: PASS, 761/761

- 524/524 artifact sessions: `construct_4h.session_close_et(date)` under the
  pinned env == artifact close (wall time localized to America/New_York).
- 237/237 non-session dates in the closed coverage interval
  [2024-09-16, 2026-10-16]: `session_close_et` raised ValueError iff the
  date is absent from the artifact.
- The direct-PMC close resolution in `construct_4h` is therefore **proven
  equal to the qualified `XNYS_SESSION_SCHEDULE_V2` artifact** over the
  artifact's entire coverage (pre-2024-09-16 warm-up closes remain outside
  this proof, exactly as the -42 artifact map stated).

## E2 — constructor behavior: STOPPED at F3 (first material failure)

| Fixture | Expectation (frozen) | Observed | Result |
|---|---|---|---|
| F1 regular day 2025-01-08 | cleared == reference, byte-identical | 2 bars both routes, serializations byte-identical | **PASS** |
| F2 early close 2024-11-29 | cleared == reference, byte-identical | 1 bar both routes, byte-identical | **PASS** |
| F3 DST-spring week 2025-03-07 → 2025-03-14 | cleared == reference, byte-identical | cleared route raised at VALIDATION, before any construction (below) | **FAIL — STOP** |
| F4 DST-fall week | byte-identical | NOT RUN (first-failure stop) | — |
| F5 two window lengths | byte-identical (4 checks) | NOT RUN | — |
| F6 closed day + stray bars | validator V4 | NOT RUN | — |
| F7 missing due constituent | validator V6 | NOT RUN | — |
| F8 mid-day as-of | completed bins only | NOT RUN | — |

**First failure (verbatim from proof_results.json):**
key `E2_CLEARED_ROUTE_ERROR`, fixture F3 —
`V8: exchange-OPEN session 2025-03-10 has 0 bars but 7 constituents are due as of 2025-03-14 16:00:00-04:00; missing retrieval (verified open via XNYS calendar)`

### Root cause (post-hoc STATIC analysis of the observed failure; no rerun)

The failure is in `validate_input.validate`'s window enumeration, not in
construction and not in the fixture:

- `validate()` enumerates window days by `day += pd.Timedelta(days=1)`
  starting from the normalized window start (validate_input.py, V8 block).
  On a tz-aware America/New_York timestamp that increment is absolute 24 h
  arithmetic: after the 2025-03-09 spring-forward, the enumerated "day"
  for 2025-03-10 is `2025-03-10 01:00:00-04:00`, not midnight.
- Session resolution still works (`xnys_schedule` keys off `day.date()`),
  which is why the validator correctly computed 7 due constituents — but
  the bar lookup `by_day.get(day)` compares that 01:00 key against
  `by_day` keys built from `ts.normalize()` (true midnights), misses, and
  concludes the session has 0 bars → V8 "missing retrieval".
- The fixture frame genuinely contained the 2025-03-10 bars at correct NY
  wall times (the generator builds each date independently from the pinned
  calendar). Corroboration: F1/F2 (single-day windows, no cross-transition
  iteration) passed; the failure struck exactly the first open session
  after the transition in the first DST-spanning window.
- Characterization: **the cleared route as shipped cannot validate any
  request window spanning a DST transition** (the fall transition drifts
  the key to 23:00 the prior day — the same defect class; stated as a
  static prediction about F4, NOT as evidence, since F4 never ran).
  `construct_4h` never executed for F3. This converts -42's B-1
  "equivalence unproven" into a concrete named divergence for
  adjudication: on DST-spanning windows the cleared route fails closed at
  validation while `resample_4h` (no calendar, no window enumeration)
  would silently proceed.

## Environment + hash gates (all verified BEFORE the single run)

- Hash gates (recomputed in-shell and re-verified inside the driver):
  construct_4h `d47e8df1…`, pilot_build `257d5bb9…`, validate_input
  `1b83cdcd…`, fetch_4h `2a4994a2…`, artifact `3358f2d9…` (working-tree
  bytes == commit `9c62e255` blob), TD lock `08b38cfa…`, wheelhouse
  manifest `210b8273…` with 11/11 wheels verifying. ALL MATCH.
- Environment: the pre-existing NL451 env was absent (/tmp ephemeral), so
  ONE disposable env was rebuilt **offline only** inside `unshare -n` from
  the pinned wheelhouse (`pip install --no-index --require-hashes`).
  Network probes inside the namespace all failed as required (socket
  Errno 101, DNS Errno -3, curl exit 7 — see env_receipt.txt). Resulting
  freeze is byte-identical to the TD lock `08b38cfa…` (both files hash to
  `08b38cfa1880…`). CPython 3.12.3, pandas 2.2.3, PMC 4.5.1.
- Single orchestrated execution: 2026-10-20T02:41:25Z → 02:44:04Z
  (env build + driver; driver itself 02:41:44Z → 02:44:04Z, exit 0 —
  the driver records a proof HOLD as a result, not a crash).
  driver_stderr.txt carries two benign pandas UserWarnings from
  construct_4h.py:171 (boolean-Series reindex) emitted during F1/F2.
- Reference isolation: `resample_4h` + `AGG` were extracted textually
  (AST source segments) from the hash-verified fetch_4h.py bytes and
  exec'd with pandas in scope — module import is impossible in the pinned
  env because fetch_4h.py imports yfinance, deliberately absent from the
  offline wheelhouse. Executed reference source sha256:
  `ffc6b7efba680858958321bb5cd23458df0cedb1a58144f93598ba04e1e8751f`
  (full source in proof_results.json).

## Elapsed / repairs

Elapsed ≈21 min of the ≤45 cap (dispatch 2026-10-20T02:29:01Z → package
complete ~02:50Z). **Repair minutes: 0.** Attempts: exactly ONE.

## What this does and does not establish

- ESTABLISHED: live-PMC closes ≡ qualified artifact closes over the full
  coverage (E1). Cleared-route construction ≡ canonical resampler on a
  regular day and an early-close day (F1/F2). The cleared route fails
  closed (validator V8) on DST-spanning windows — a real behavioral
  divergence from the resampler, surfaced by the frozen F3 fixture.
- NOT established: F4–F8 behavior (never ran); route precedence (still
  adjudication's, per D1/D2 of -42); warm-up closes (outside E1 coverage).
- A PASS would not have adopted a route; this HOLD adopts nothing either.

## Prohibitions honored

No source file edited (construct_4h, pilot_build, validate_input,
fetch_4h, harness — all read-only, hash-verified before and used as-is);
no vendor/API/model calls (the entire execution ran in a `unshare -n`
no-network namespace; the only network use in this task was the read-only
public GitHub fetch of the spec comment, before the run); no credentials,
credits, tokens, or spend; no real market data (all E2 inputs synthetic,
generated in-code); no SPT-08; no backtests/performance; no holdout
access; no ledger/state/production/trading changes; no Issue #9 work;
no Yahoo work. V5.4 PAUSED and all other standing holds untouched.
