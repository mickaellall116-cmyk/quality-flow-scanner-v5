# XNYS isolated calendar generation (-35 r1) — GENERATED, awaiting independent review

Task: `QF-XNYS-ISOLATED-CALENDAR-GENERATION-20261019-35 r1`
Spec: GitHub Issue #1 comment `6267293436` (user GO recorded; contract §7 GO
under -34 r2, commit `a3761ef`). Cap ≤ 60 min, one run.
Package: `research_notes/xnys_isolated_calendar_generation_20261019_35/`

## Verdict

**`GENERATED__AWAITING_INDEPENDENT_CHATGPT_REVIEW`** — the schedule artifact
was generated under the accepted contract and passed all 48 frozen parity
rows against the -31/-32/-33 primary record. This is NOT final qualification:
ChatGPT independently inspects the pinned bytes and adjudicates.

## Headline results

- **Artifact:** `XNYS_SESSION_SCHEDULE_V2.json` — SHA-256
  `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88`,
  28,046 bytes, **524 sessions** over [2024-09-16, 2026-10-16],
  coverage_end exactly 2026-10-16, canonical serialization, generated twice
  byte-identically.
- **Environment:** isolated venv built inside a `unshare -n` no-network
  namespace from the pinned wheelhouse only (`--no-index --no-cache-dir
  --require-hashes`); `pip freeze` SHA-256 = `08b38cfa…` — byte-identical to
  the accepted NL lock; 11/11 wheels and 8/8 installed-member pins exact;
  3 deliberate network probes all failed to connect (zero network accesses).
- **Dual emission:** PMC native `NYSE` and EC `XNYS` produced byte-identical
  emission files (524 sessions; aux 2024 = 252, aux 2026 = 251) — a logged
  CORRELATED CONSISTENCY check only (-30); the mirror key was never used.
- **Parity (the qualification evidence): 48/48 PASS** — 2 HRS + 22 CLO
  (incl. Carter 2025-01-09) + 6 EC + 3 CNT (252/250/251) + 1 MST (761-day
  sweep) + 4 STR + 8 R + 2 COR. Row detail: `parity_results.json`.
- **Consumer:** frozen -28 synthetic suite 25/25 (consumer byte-unmodified);
  real artifact parsed via `fold_materializer_v3` with 1,043 synthetic
  timestamps — no `SCHEDULE_*` error, coverage first/last = 2024-09-16 /
  2026-10-16, 4 folds materialized.
- **Pre-flight:** 9/9 primary-source hashes, lock hash, wheelhouse manifest
  all exact before any install. Elapsed ~5 min of 60; repair ~2 min.

## Disclosed repairs (full detail in the receipt, §11)

1. Generator v1 failed on path C (tz-naive schedule index compared against
   tz-aware bounds — my code, not a source/env defect); fixed in v2 by
   filtering on session dates; all emissions regenerated with v2; v1 logs
   preserved. v2's path-A bytes are identical to v1's.
2. The -28 suite's first run exited 1 from a flat package copy (its
   repo-relative preservation paths need the sibling packages); re-run in a
   mirrored -25..-28 tree: 25/25, exit 0, results identical to frozen.

No §6 fail-closed condition fired. No network beyond the read-only public
spec fetch; no vendor/API calls, downloads, spending, credentials, market/
OHLC/real-timestamp data, holdout access, performance work, production/
trading/ledger change, or Issue #9 work. Prior frozen records unedited.
