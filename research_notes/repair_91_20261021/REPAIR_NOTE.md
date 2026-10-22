# REPAIR -91 — the three blockers from ChatGPT's independent review

Source of the blockers: ChatGPT, Slack TS 1792638081.444749
(2026-10-21 23:01 ET) + Issue #1 comment 6331619440. Scope honored:
offline / synthetic only — no vendor calls, no credits, no capture,
no holdout, no backtests, no -75 snapshot reads, no production or
pinned-file edits. The -88 and -89 packages are NOT edited: this
package carries corrected candidate copies and supersedes by
reference. Adoption gates are unchanged (checker G4, guard G3-v2,
capture GO) — this repair removes the three stated blockers to
those adoptions; it adopts nothing.

## FIX 1 — checker: expected sessions with zero rows were invisible

`checker/tsla_completeness_check.py` (corrected copy of the -89
candidate): the COUNT lane iterated only days present in the bars.
Now the session table is a **required** input (absent/empty →
`SESSION_TABLE_REQUIRED` refusal) and the lane iterates EXPECTED
sessions: a session with zero rows is a first-class finding,
`count.missing_sessions[]` = {session date, expected bar starts},
failing COUNT → overall **COMPLETENESS_FAIL** — the existing lane
vocabulary; a missing session in a qualified window cannot pass
silently. New suite `checker/test_completeness_check_repair91.py`:
mid-window missing (2024-01-03 named), first-session missing,
last-session missing, clean control, no-table refusal — **11/11**.
The -89 suite re-runs unchanged against the repaired module:
**38/38** (the documented -82-fixture divergence is unaffected —
the repair adds a lane input requirement, it does not touch any
v1/v2 lane semantics).

## FIX 2 — guard: exact index equality was defined, never invoked

`guard/constructor_guard.py` (corrected copy of the -89 candidate):
`assert_index_equality` existed since -84 but
`guarded_construct_4h` never called it. Now the guarded path
enforces the **exact ordered expected index** as a mandatory
pre-construction step (after duplicates → timezone → monotonic):
the expected sequence is derived from the session table
(`session_closes`: hourly 09:30 starts while start < close, per
session, sorted), and a missing session table refuses fail-closed
(`CONSTRUCTOR_GUARD_INDEX_MISMATCH`, "cannot verify") — the step
cannot be skipped. New sabotage suite
`guard/test_constructor_guard_repair91.py` — **8/8**: permuted
index refused (spy 0; the equality step itself names it), +1h
shifted index refused as INDEX_MISMATCH, dropped stamp refused,
in-order off-grid stamp (10:30→10:45 — survives monotonicity, only
exact-index enforcement catches it) refused, no-session-table
refused, clean path byte-identical with the spy invoked exactly
once. Regression: -84 floor **12/12** + -89 v2 suite **15/15**
through the repaired module.

## FIX 3 — capture credit accounting was incoherent

Full corrected scheme in `CREDIT_ACCOUNTING.md` (supersedes -88's
accounting clauses by reference). One sentence: per-leg
`credit_delta` is abolished; execution is sequential in blocks of
≤10 attempts, every block bracketed by chained `/api_usage` reads,
and each block must reconcile exactly
(`Δu = attempts + 1`, the closing read's charge) or execution
halts. Recounted totals: **program 146 expected / 289 worst**
(was 132 / 262); pilot 19 / 37. **The proposed 300 ceiling stands**
(worst-case margin narrows 38 → 11).

## Disclosed, deliberate

- `GUARD_VERSION` / `CHECKER_VERSION` strings are NOT bumped in
  the corrected copies: the -89 suites pin those strings as
  version anchors, and this package's claim is "the -89 suites
  pass byte-unchanged against the repaired modules." Adoption
  (G3-v2 / G4) mints successor pins in any case; the repair is
  identifiable by this package and its manifest.
- All suites were run TWICE in the pinned venv (CPython 3.12.3 /
  pandas 2.2.3) under `unshare -n`; outputs repeat-identical.
  Counts are real executed numbers (TEST_EVIDENCE.md).
