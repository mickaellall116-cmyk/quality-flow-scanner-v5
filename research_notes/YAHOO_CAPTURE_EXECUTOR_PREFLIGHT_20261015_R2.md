# QF-YAHOO-CAPTURE-EXECUTOR-PREFLIGHT-20261015-09 r2 — bounded repair

**Verdict: `CAPTURE_EXECUTOR_PREFLIGHT_PASS`** (preflight scope only — this
PASS authorizes neither the 52 Yahoo requests nor publication; both remain
a separate explicit execution gate.)

Spec: GitHub Issue #1 comment `6198709259` (ChatGPT HOLD on r1, commit
`8b29b62`), followed exactly. r1's three load-bearing gaps are closed in
`execute_capture.py` (repaired in place; r1 bytes remain immutable in git
history at `8b29b62`).

## Timing / budget

- Spec fetched 2026-10-15 18:02:24Z; final verification 18:07Z (VM clock).
- Repair minutes this round: **≈5** of the ≤8 allowance; cumulative repair
  r1+r2 **≈7** of ≤10; total task elapsed well inside the ≤45 envelope.
- One repaired suite version; no failed trials (first full run 32/32).

## Per-gap closure proof

**G1 — Restart now authenticates all three artifacts.** The raw-only
`file_ledger.jsonl` semantics are replaced by one fsync'd per-symbol
`COMPLETE` record binding the exact three paths + SHA256 values
(`raw/<s>.csv`, `actions/<s>.actions.csv`, `meta/<s>.request.json`).
Restart `SKIP_VERIFIED` requires the record AND all three files present
with matching hashes. Missing companion → `HOLD:COMPLETION_INCOMPLETE`;
altered companion → `HOLD:FINAL_MISMATCH`; any partial artifact set with
no completion record → `HOLD:FINAL_MISMATCH` — all before any transport.
Proven by **E19a** (actions deleted), **E19b** (meta altered), **E19c**
(raw altered): each HOLDs with zero transport calls.

**G2 — Torn journal/ledger fails closed with named codes.** `_read_jsonl`
is strict: a malformed/truncated/non-object line raises
`HOLD:JOURNAL_CORRUPT` / `HOLD:LEDGER_CORRUPT` inside the executor and is
converted to a retained `INCOMPLETE_HOLD` marker — never an uncontrolled
`JSONDecodeError`. Completion records are schema-validated (event, symbol,
exact three-path set, 64-hex hashes); duplicates/conflicts →
`HOLD:LEDGER_CONFLICT`. Proven by **E20** (torn attempt-journal tail:
named HOLD, marker written, no exception escaped, zero calls),
**E21a** (torn completion record → `HOLD:LEDGER_CORRUPT`), **E21b**
(conflicting duplicate completion record → `HOLD:LEDGER_CONFLICT`).

**G3 — Wall time enforced in code at four points; transport exceptions
converted.** `check_wall()` runs before each request, immediately after
transport returns, after validation/publication work, and before
finalization. Proven by **E22** (slow middle request: aborts
`HOLD:CEILING` after return, the slow symbol is never published, calls
stop at 6) and **E23** (slow final request: `HOLD:CEILING`, final symbol
never published, no `manifest.json`/`SHA256SUMS` written). Unexpected
transport exceptions (and response-shape failures) convert to a named
retained `INCOMPLETE_HOLD` (`HOLD:TRANSPORT_ERROR` /
`HOLD:RESPONSE_SHAPE`), no retry — proven by **E24** (calls stop at 2,
marker carries the code).

**Final object-set enforcement.** Before finalization,
`verify_object_set()` requires exactly the expected 52 raw + 52 actions +
52 metadata objects and no temp/unexpected file anywhere in the capture
directory (`HOLD:OBJECT_SET`); `SHA256SUMS` binds exactly those 156
objects. The `ALREADY_COMPLETE` restart path now also requires the sums
file to bind exactly the expected 156-object set (a torn sums line fails
closed as `HOLD:FINAL_MISMATCH`). Proven by **E25a** (extra object) and
**E25b** (leftover `.tmp-` file): both HOLD pre-finalization with zero
transport calls.

## Fixture

`run_executor_fixture_r2.py` — **32/32 checks, run twice, byte-identical**
(`executor_fixture_results_r2.json` = `executor_fixture_results_r2_run1.json`,
sha256 `a14921d5…`). All 21 r1 checks (E0–E18 incl. E10a/b, E17b) are
preserved and pass against the repaired executor; 11 r2 checks added
(E19a–c, E20, E21a–b, E22, E23, E24, E25a–b).

**Disclosed expectation amendment (one):** E6's r1 sub-check
`crash_propagated` is renamed `crash_converted_to_hold`. The r2 spec
*requires* unexpected transport exceptions to convert to a retained
`INCOMPLETE_HOLD`, so the simulated crash no longer propagates out of
`run_capture`; it returns `INCOMPLETE_HOLD`/`HOLD:TRANSPORT_ERROR` with
the marker retained. Every E6 semantic is unchanged: the symbol was
attempted exactly once across both runs, the restart makes zero calls and
returns `ATTEMPT_CONSUMED_AMBIGUOUS`.

Retained r1 controls (re-verified in the same runs): exact manifest hash
binding (E1), frozen order/count (E3), runtime pins (E2), journal-before-
transport on every request + exact limiter spacing (E4), no-clobber
publication (E12), offline CLI refusal posture (E0 + source hygiene:
sockets denied before any code ran, `yfinance` never imported), and the
publication phase E13–E18 (fake-local remote only; target-name, visibility,
existing-prefix and re-fetch checks unchanged).

## Files

- `yahoo_clean_capture_preflight_20261015/execute_capture.py` — repaired
  executor, sha256 `f76e30fa…` (r1: `a7ab6d0b…`, preserved at `8b29b62`).
- `yahoo_clean_capture_preflight_20261015/run_executor_fixture_r2.py` —
  sha256 `81acd614…` (r1 fixture retained unchanged as the trial record).
- `executor_fixture_results_r2.json` / `executor_fixture_results_r2_run1.json`
  — sha256 `a14921d5…`, byte-identical.
- Package `SHA256_MANIFEST.txt` regenerated over the full package
  directory and verified.

## Scope confirmation

Zero Yahoo/vendor/API/model calls (the spec-comment fetch excepted), zero
sockets in the fixture (denial installed first, attempt counter live),
zero downloads, zero installs, zero spend, zero capture execution, zero
publication, zero GitHub writes, zero backtests, zero holdout access, zero
production or live-state changes. Deliverables left uncommitted in the
worktree for the parent agent to commit and post.
