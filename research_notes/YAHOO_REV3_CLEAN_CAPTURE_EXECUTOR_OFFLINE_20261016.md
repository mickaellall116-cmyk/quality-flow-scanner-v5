# QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-OFFLINE-20261016-19 r1 — WORK RESULT

**Verdict: `REV3_CLEAN_CAPTURE_EXECUTOR_OFFLINE_READY`** (offline preflight scope only;
adopts nothing, authorizes no Yahoo call, no capture, no publication. U-1 remains HOLD.)

Spec: GitHub Issue #1 comment `6213625775`, fetched first and followed exactly.
Elapsed ≈5 minutes of the ≤45 cap (spec fetch 2026-10-16T10:56:39Z → suite complete
≈11:02Z, packaging included). Repair: ONE driver-only repair ≈1.5 min of the ≤10
allowance (three fixture expectation/sizing defects, detailed below); the executor
source was never repaired. Two fixture runs, both reported: run 1 FAIL (102 checks,
4 failures — all fixture-side), run 2 PASS (103 checks, 0 failures).

## What was built

A NEW isolated executor, written fresh against the rev3 candidate — the parked
-08/-09 `execute_capture.py` lineage was not imported, copied, patched, or executed
(machine-audited, case C-09; the parked file is byte-identical at `8fe97abd…`).

- **Exact plan:** the candidate is consumed by full SHA-256 (`3d3d4ef5…`); ceilings
  are cross-checked against the spec literals (mismatch → `HOLD:CONSTANT_DRIFT`).
  The executor stages ONLY `raw/<SYMBOL>.csv`, `actions/<SYMBOL>.actions.csv`,
  `meta/<SYMBOL>.request.json` — exactly 156 payloads, in the frozen 52 order with
  the candidate's params (1h, auto_adjust=False, prepost=False, actions=True,
  explicit −729d start rule). It writes NO `manifest.json`/`SHA256SUMS`.
- **Separated control state:** strict capture ID (8–64, uppercase/hyphen grammar,
  case-collision siblings refused); journal ONLY at
  `<capture_id>.control/acquisition_attempt_journal.qfj2`; no control file under the
  payload root; symlinks/traversal/non-regular files refused (`HOLD:PATH_TYPE`,
  `HOLD:MEMBERSHIP` census).
- **Attempt/restart semantics:** authenticated framed ATTEMPT (fsync) before each
  injected transport call; COMPLETE (fsync) only after the triplet is finalized
  write-once (temp → rename → fsync), binding all three rel paths + SHA-256 hashes.
  Restart: valid COMPLETE + exact triplet → `SKIP_VERIFIED`, zero calls; attempt
  without COMPLETE → `HOLD:ATTEMPT_CONSUMED_AMBIGUOUS`, zero calls; missing/altered
  triplet member → `HOLD:FINAL_MISMATCH`, zero calls; torn journal →
  `HOLD:JOURNAL_TORN`, corrupt → `HOLD:JOURNAL_CORRUPT`, duplicate/conflicting →
  `HOLD:JOURNAL_CONFLICT` — never blind repair, never a re-request.
- **Budgets:** one injected process-wide limiter (≥1.0 s between the 52 request
  starts, virtual clock in fixtures); exactly one attempt per symbol, no
  retry/fallback/pagination; 32 MiB/symbol, 67,076,700 payload bytes,
  20,000 rows/symbol, 1,800 s wall — all enforced before the final COMPLETE.
- **Failure handling:** 429 → `HOLD:THROTTLE_429`; transport exception →
  `HOLD:TRANSPORT`; shape/schema/meta drift, unknown-symbol echo, partial
  (end-of-window uncovered) response, ceiling/wall breach → the run ends
  `INCOMPLETE_HOLD` with the named code, the attempt consumed, no further calls.
- **Separation of authority (spec §6):** the executor fabricates no validation
  pins, runs no G1–G11 qualification, publishes nothing, creates no anchor, and
  claims no data qualification. Its output is staged bytes only. (Note: the
  dispatch brief's mention of calendar-derived qualification is governed by the
  spec's explicit §6 separation — qualification is a later, separate stage.)

## Fixture results (no-socket; sockets denied before executor import)

| Case | Result |
|---|---|
| C-01 52-call success: exactly 156 payloads, journal outside root, limiter gaps ≥1.0 s, no bookkeeping/extra files; byte-identical twin rebuild (tree + journal) | PASS |
| C-02 crash after ATTEMPT, before finalization → restart: zero calls, `HOLD:ATTEMPT_CONSUMED_AMBIGUOUS` | PASS |
| C-03 valid COMPLETE restart: all `SKIP_VERIFIED`, zero calls | PASS |
| C-04 missing and altered triplet member → zero-call `HOLD:FINAL_MISMATCH` (both) | PASS |
| C-05 duplicate ATTEMPT / COMPLETE-without-ATTEMPT / duplicate COMPLETE → `HOLD:JOURNAL_CONFLICT`; torn tail → `HOLD:JOURNAL_TORN`; interior byte flip → `HOLD:JOURNAL_CORRUPT`; all zero-call | PASS |
| C-06 11 invalid capture IDs (lowercase, traversal, short, double hyphen, space, Cyrillic lookalike, newline, 65 chars, underscore, leading/trailing hyphen), case-collision sibling, root/control/inner symlinks → all fail before transport, zero calls | PASS |
| C-07 429 (stops at 4 calls), transport exception (2), shape drift (1), schema drift (1), meta drift (1), unknown symbol (1), partial response (3), per-symbol ceiling (1), row ceiling (1), total ceiling (stops at the breaching call), wall ceiling (2) → each `INCOMPLETE_HOLD` with the named code, no retry, no later calls | PASS |
| C-08 fixture-side validator computed the 156 payload hashes (never executor claims) and fed them to the accepted publisher (`1d4c1923…`, pin-verified) against a fake remote: census accepted the root, `build_container` sealed exactly **158** members, `publish` → `PUBLISHED`, archive ref updated, publication journal in the control dir, root still membership-pure. Compatibility evidence only — not qualification, not real publication | PASS |
| C-09 import audit: executor imports are stdlib-only (AST); source free of the parked lineage and of socket/urllib/requests/yfinance; socket constructor verifiably denied in the fixture process | PASS |

Run 2 totals: **103 checks, 0 failures.** Measured peak RSS (fixture driver process,
which materializes ~66 MB of synthetic payloads for the total-ceiling case):
**240.62 MB** (run 1: 240.41 MB) — a driver figure, not an executor-only footprint.

## Trials / failures (both runs reported)

Run 1 (102 checks, 4 failures) — all four fixture-side; executor behavior was
correct in each: (1) the C-06 battery listed `TEST-CAPTURE` as an invalid ID, but
it is a *valid* ID under the lineage grammar (12 chars) — replaced with `TEST-01`
(7 chars, genuinely too short); (2) the C-07 total-ceiling trial under-sized its
synthetic payloads (~58 MB aggregate < budget, run correctly completed) — payload
padding raised so the budget breaches mid-run; (3) the C-09 raw-substring scan
flagged the word "requests" inside the legitimate candidate field name
`max_requests_total` — the scan now bans import forms, with the AST stdlib-only
audit as the load-bearing check. One repair round (≈1.5 min), driver only.
Run 2: 103/103 PASS.

## Scope confirmation

Offline only: the spec-comment fetch was the sole network read; zero
Yahoo/vendor/model/API calls, zero downloads/installs/spend, zero authenticated
GitHub operations, zero adoption/merge, zero real capture/publication, zero
backtest/holdout/production changes; U-1 unprobed (HOLD). Verified byte-identical
after the runs: candidate `3d3d4ef5…`, frozen rev2 manifest `634c4541…`, accepted
publisher `1d4c1923…`, parked executor `execute_capture.py` `8fe97abd…` — none
edited, imported, or run (the publisher was imported read-only by the fixture for
the C-08 compatibility case, as the spec requires).

## Package

`research_notes/yahoo_rev3_clean_capture_executor_20261016/` —
`clean_capture_executor.py` (new isolated executor), `run_clean_capture_fixture.py`,
`fixture_results_run1.json` (FAIL, preserved), `fixture_results_run2.json` (PASS),
`SHA256_MANIFEST.txt`. Left uncommitted in the worktree.
