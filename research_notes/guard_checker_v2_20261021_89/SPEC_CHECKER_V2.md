# SPEC — completeness/convention checker v2 (candidate)

**Task:** -89. **Design authority:** -86 REMEDIATION_PLAN §F4
(Claude's -82 re-review: the TSLA *label* passed, the completeness
*instrument* was held incomplete). **Base:** -82
fixtures/tsla_completeness_check.py (sha256 0a7712be…, 14/14).
This spec covers the v2 DELTA; the v1 design constraint is
inherited verbatim: ONE series, examined on its own terms;
completeness verdicts never print as convention verdicts.

**Module:** `checker/tsla_completeness_check.py`,
CHECKER_VERSION `checker-v2-candidate-1`. `run_check(bars,
sessions, declared_splits)` keeps the v1 signature and result
skeleton; lanes are added, none are removed.

## Constants (governed; amendable only by governed amendment)

  MIN_PLAUSIBLE_VOLUME = 2        (1-share price-moving = defect)
  STEP_LOG_TOLERANCE   = log(1.5) (anchor radius, all lanes)
  PLAUSIBLE_SPLIT_FACTORS = 2, 3, 4, 5, 7, 10, 20 (+ reciprocals)
      — 1.5 is deliberately NOT an anchor: log(1.5/1.001) <
      tolerance, so a 1.5 anchor would flag ordinary overnight
      drift as factor-shaped.
  VBASIS_BAND = [1/1.5, 1.5], sustained >= 5 sessions

## Lanes

COUNT — unchanged from v1.
ANOMALY — v1 zero-volume classes preserved; v2 adds per-bar
  defect enumeration: NAN_VALUE (NaN in Volume or any OHLC),
  NEGATIVE_VOLUME, SUB_PLAUSIBLE_VOLUME_PRICE_MOVING
  (0 < v < MIN_PLAUSIBLE_VOLUME with high > low or close != open).
  A sub-plausible FLAT bar (incl. 1-share) stays NO_TRADE_FLAT.
STEP (declared boundaries) — v1's blanket |log step| rule is
  REPLACED by classification (the false-flag guard):
    step ~ 1                      CONTINUOUS_ADJUSTED   (PASS)
    step ~ factor or ~ 1/factor  MIXED_BASIS_SUSPECT  (suspect)
    anything else                 PRICE_ACTION        (NO flag)
  A genuine +60% gap at a declared 3:1 boundary (step 1.6: nearer
  no anchor) classifies PRICE_ACTION and raises NO flag (C20).
  **Disclosed semantic change:** v1 flagged any |log step| >
  log(1.5) at a declared boundary; v2 flags only factor-shaped
  steps there. Cross-version readout comparability is governed in
  ADOPTION_NOTES.md.
STEP-ALL (new) — every UNdeclared session boundary scanned for a
  factor-shaped price step (nearest anchor within tolerance) →
  CONVENTION_BREAK_SUSPECT (undeclared split signature; C19).
VBASIS (new) — at each non-declared boundary with >= 5 following
  sessions: median volume of the next 5 sessions vs the median of
  the preceding sessions, outside [1/1.5, 1.5] →
  CONVENTION_BREAK_SUSPECT (volume-basis step; C18). Declared
  boundaries are excluded (the note lane measures them). A NaN
  volume anywhere abstains the lane (NOT_EVALUATED_NAN_VOLUME).
NOTES (new) — at each declared boundary, the volume scale step
  (pre-session total / boundary-session total): ~ factor →
  SCALED_BY_FACTOR; ~ 1 → UNSCALED; else OTHER_VOLUME_STEP;
  unmeasurable (NaN / zero) → UNTESTABLE. Notes are information,
  not failures — except the MISMATCH rule: CONTINUOUS_ADJUSTED
  prices with an OTHER_VOLUME_STEP means the price and volume
  bases disagree in an unclassifiable way → suspect.

## Suite

`checker/test_completeness_check_v2.py` — exit 0, **38/38**:
the -82 suite (byte-copy, sha256 47578946…) run unchanged as a
subprocess, reading the PINNED 10/14 divergence documented in
TEST_EVIDENCE.md (the -82 fixture embeds a second undeclared
3:1-shaped step at 2024-06-13; STEP-ALL fires as designed; no v1
lane regresses); FI-A…E reproducing the five -82 intents exactly
on a corrected builder (12 checks); C15–C22 per the -86 spec
(23 checks). Repeat-identical across two runs.

## Non-goals / invariants

Still a single-series instrument: no twin comparison is added or
implied, so the -75 C2 conflation (a completeness artifact
printing as an "inconsistent convention") remains impossible by
construction. No real data is read by this package; the -75
snapshot re-analysis belongs to GO G4 (ADOPTION_NOTES.md).
