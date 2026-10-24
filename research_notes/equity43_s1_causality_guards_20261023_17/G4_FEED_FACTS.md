# G4/VBASIS + feed-route facts sheet — QF-EQUITY43-S1-CAUSALITY-GUARDS-20261023-17

Desk-only evidence assembly from existing checker/source documents and
lawful prior DEV receipts. NO adoption decision is made or implied;
every unproven condition is marked UNQUALIFIED. Sources are named per
fact; nothing here rests on a new vendor call or a new measurement.

## 1. Why CONVENTION_BREAK_SUSPECT fires (VBASIS lane)

- The checker keeps two lanes separate (completeness PASS/FAIL vs
  convention PASS / CONVENTION_BREAK_SUSPECT) since the -82 repair, so
  a completeness failure can never print as a convention failure.
  (research_notes/claude_cp1_repair_20261021_82/fixtures/
  tsla_completeness_check.py, header + verdict composition.)
- PRICE-side lane (STEP): at each DECLARED split boundary, the
  overnight log-step is compared with the declared factor, tolerance
  log(1.5). On the pilot bytes STEP PASSED on every leg and STEP-ALL
  reported 0 unexplained steps — i.e., no price-side basis break was
  found. (td_pilot_adjudication_20261023_02/ADJUDICATION.md, VBASIS
  disclosure.)
- VOLUME-side lane (VBASIS): flags any boundary where the 5-session
  median volume ratio exits [1/1.5, 1.5]. The composite
  CONVENTION_BREAK_SUSPECT on every pilot leg is driven SOLELY by this
  lane. Flag counts on actual bytes (HO/DEV windows): NVDA 32/90
  boundaries, TSLA 12/91, AAPL 32/108, SPY 44/94, SMCI 66.
- SPY has NO split or basis event in either window, yet VBASIS flags
  44 HO boundaries — at this calibration the lane's flagged set is
  false-positive dominated on an event-free control. NVDA/HO's flagged
  ratios form a continuum (0.528–1.950, median 1.565) hugging the 1.5
  band edge — the shape of gradual volume-regime drift, not a discrete
  basis rescaling, which would print at the split factor (~10 or ~0.1)
  at ONE boundary. (ADJUDICATION.md, same section.)
- Standing disposition (unchanged by this task): completeness
  qualification does not rest on VBASIS; G4 remains UNADOPTED and the
  label on all DEV inputs is CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED —
  candidate-grade, NOT QUALIFIED. No threshold was set, tuned, or
  touched in -02, -12, -13, -16, or this task. Whether VBASIS at this
  calibration belongs in the adopted instrument is a G4 adoption
  question for adjudication. (-12/-13 RESULT.md G4 lines; -02
  disposition.)

## 2. Calibrating the false positives WITHOUT return-based tuning

Options for adjudication — all UNQUALIFIED proposals, none adopted,
none evaluated against strategy returns:

- Negative/positive controls: measure the lane's flag rate on
  event-free series (SPY is the standing negative control: 44 flags
  with no event) and its hit rate at declared split boundaries
  (positive controls). A calibration is defensible only if it separates
  those two populations; the current [1/1.5, 1.5] band does not.
- Corroboration requirement: count a VBASIS flag only when the same
  boundary also shows a discrete price-side step at a plausible split
  factor (STEP lane) or matches a declared corporate action. This
  makes VBASIS a corroborating lane, never a standalone blocker.
- Regime-relative band: replace the fixed 1.5 band with a per-symbol
  baseline estimated from the symbol's own event-free volume-ratio
  distribution (a data-distribution calibration). Any such change is a
  checker change requiring its own fixtures and adjudication.

## 3. Split / volume adjustment compatibility

- The DEV/HO captures were requested from Twelve Data /time_series
  with adjust="splits" (receipt-verbatim request params: interval 1h,
  outputsize 5000, end/start pinned; e.g. SPY__DEV receipt, chain hash
  4aa5718c…, manifest root 79ccdd12…). Prices are therefore
  SPLIT-adjusted and NOT dividend-adjusted; volume is as delivered
  under that request.
- The frozen strategy and both DEV paths (batch reference and
  streaming observer) consume the SAME bytes under this convention;
  DEV decision parity is exact on them (44,849 bars; see the -17
  recheck in this package). DEV-internal compatibility is therefore a
  proven fact, not an assumption.
- UNQUALIFIED: live-feed equivalence — whether a future live TD pull
  under adjust=splits rescales historical volume at splits identically
  to the captured bytes has never been tested (no live pull exists).

## 4. Feed rights, latency, 43-name completeness

- Provider/plan facts (receipts): Twelve Data, plan_daily_limit 800
  credits/day, 1 credit per 1h leg at outputsize 5000; response meta
  declares exchange_timezone America/New_York and naive local stamps.
- Rights: the program's vendor screens (-06/-07 and the standing
  four-vendor finding) established that free API terms do not grant an
  affirmative archival right; captures are held in the private
  qf-data-archive under hash-chained receipts. Live S1 consumption
  rights are UNQUALIFIED until the adoption decision resolves them.
- Latency: NO live latency measurement exists — no live feed has ever
  been run (the -15 readiness record states FEED_NOT_READY). When a
  completed TD 1h bar becomes retrievable after its close is
  UNMEASURED / UNQUALIFIED.
- Completeness on captured bytes (fact): DEV window 43/43 legs
  admitted exactly 3,653 bars each (the pinned expectation); 61
  excluded rows, all in the generic early-close post-close class; zero
  price-moving zero-volume admitted bars. HO window: 25/44 legs
  NOT_EVALUABLE (the bounded 2024-04-04..22 zero-volume defect window,
  145 defective bars program-wide). SMCI: pre-declared EXCLUDED — no
  DEV bytes; its HO body is quarantined (sha256 737cb24a…) with 19
  price-moving zero-volume bars → NOT_EVALUABLE_PROVIDER_VOLUME.
- Live completeness for any future window: UNQUALIFIED.

## 5. Session-table / calendar facts

- The pinned session table spans 751 sessions, 2023-10-19 →
  2026-10-16 (524-session XNYS V2 table + the adopted 227-session 2023
  extension); closes 16:00 ET, 13:00 ET on early closes. The observer
  admits only this table's expected hourly starts.
- Extension beyond 2026-10-16 is NOT BUILT: any S1 operation after
  that date requires a newly built, hash-pinned session table (XNYS
  calendar) and a contract re-pin. UNQUALIFIED until built and
  adjudicated. The -17 synthetic suite exercised the existing table's
  DST-adjacent sessions (2024-03-08/11, 2024-11-01/04) and both 13:00
  early closes in-window (2024-11-29, 2024-12-24) only.

## 6. Separations kept

- Holdout window W_HO: SEALED; not accessed by this task (hashes/
  chain metadata only, as in -12/-13/-16).
- SMCI: separate disposition line (above); not a DEV leg.
- Legacy paper cohorts (V5.4 PAUSED production): untouched; pins
  re-proved identical before/after this task (see RESULT.md).
