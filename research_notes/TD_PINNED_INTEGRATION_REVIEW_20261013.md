# TD Pinned-Dependency Integration — Independent Review (2026-10-13)

Assignment: Issue #1 comment 6157824960. Authorized under Mike's standing rule
(2026-10-13 20:49 EDT: Muse↔ChatGPT research loop is auto). One clean synthetic
rerun maximum; no code repair; no API/vendor calls; synthetic transport only.

## Verdict: CONFIRMED (scoped)

ChatGPT's pinned-dependency integration result at `f64d12f885339e9e2ab4fa38b4a55df78db39b9f`
(PR #8, unmerged) is **independently confirmed**: 16/16 tests pass on a clean
rerun with the real pinned dependencies, no stubs. This closes the Oct 12
coverage gap — the 1H XNYS calendar-completeness path is now exercised against
the actual `pandas_market_calendars` 4.5.1 and passes. Scope is unchanged: this
is a synthetic integration confirmation, **not** P4/live-acquisition clearance.

## Rerun evidence (persisted, not stdout-only)

- Evidence directory: `research_notes/td_pinned_integration_review_evidence_20261013/`
  - `rerun_results.json` — sha256 `8a093a43cbb31edc0f8c3a146fd3ce08b7fc3d97c0c1b9b30417fccf99a47116`
  - `rerun_test_output.txt` — sha256 `5163c5b600a8345b4ff4c31bdab42b7fb6a3e2bba1508e832bfd770f796218db`
- Method: `git archive` of `f64d12f` (source tree byte-verified before the run:
  driver sha256 `f1f19517…`, collector `bd003c3c…`, matching the evidence's
  declared pins); isolated venv built from `integration_requirements.lock`;
  driver invoked once with a fresh, non-existent output directory.
- Result comparison vs the author's `integration_results.json`:
  - tests_run 16, passed 16, failures [], errors [], success true — identical
  - passed test-name set: identical (16/16, set-equal)
  - dependency versions: identical (pandas 2.2.3, numpy 1.26.4,
    pandas_market_calendars 4.5.1, pytz 2024.2, python-dateutil 2.9.0,
    exchange-calendars 4.13.2, tzdata 2026.5)
  - all 8 evidence-pinned source hashes: byte-identical
  - vendor_calls 0, credits 0, dependency_stubs false, transport
    "synthetic fixtures only"
- The previously-unverified path is now verified directly:
  `test_real_regular_1h_completion_and_reuse` … ok;
  `test_real_early_close` … ok; `test_real_spring_and_fall_dst` … ok —
  real XNYS schedule via the actual calendar library, including receipt reuse
  with actual-validator revalidation.

## Differences and disclosed notes (none are counterexamples)

1. **Python patch version**: rerun used CPython 3.12.3 (this VM); the author's
   environment was 3.12.14. Same minor series and identical lock versions;
   results identical. Noted, not material.
2. **Source-manifest superset**: the driver's own glob swept 4 additional
   `pilot_harness/*.py` files from the committed tree into my rerun manifest
   (`pilot_acquire.py`, `pilot_build.py`, `synthetic_data.py`, `warmup_math.py`)
   that the author's manifest doesn't list (their run directory evidently held
   only the pinned subset). None of the 4 is imported by the driver, collector,
   or any exercised dependency (verified by import scan). All 8 load-bearing
   pins match exactly. Packaging hygiene note for any future evidence run:
   archive from a subset directory or pin the glob.
3. **Constructor warning reproduces**: the same pandas keep-mask reindex
   `UserWarning` at `construct_4h.py:171` that the author disclosed appears in
   my rerun; synthetic outputs remain exact. Disclosed, not repaired (repairs
   were out of bounds).

## Minimal acquisition prerequisites (acquisition itself remains gated)

Before any live P4/acquisition step could even be *proposed*, all of:

1. **Revised acquisition manifest** supplied and pinned (the candidate has no
   HTTP client and the revised manifest is not yet supplied).
2. **One named acquisition adapter pinned**: actual account/retention terms
   for the Twelve Data account in use, sanitized timeout/error handling,
   shared live limiter path (same persisted limiter the synthetic tests
   exercised), exact ascending request/venue identity.
3. **Semantics rulings fixed in writing before data arrives**: collector
   COMPLETE = validated-receipt completion only; native-4H diagnostic
   completion says nothing about session coverage; the 1H start-label
   convention is a convention, not proof of vendor interval semantics.
4. **Retention**: samples retained privately under the active account's
   retention condition; **no Tiingo-held inputs as comparator** (Tiingo HOLD
   stands).
5. **Comparison protocol pre-declared**: timestamps, date-end inclusion, venue
   coverage, missing bars, adjustment basis, available historical depth —
   checked before any unchanged-strategy baseline is computed, with
   dataset/code/cost/fill/validation splits fixed in advance.

No vendor calls were made, no credits spent, and no code was repaired or
modified in this review. PR #8 remains unmerged.
