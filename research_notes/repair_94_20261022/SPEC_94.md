# SPEC -94 — crypto calendar correction delta (checker candidate)

Status: CANDIDATE, HOLD for adjudication. Offline/synthetic only.
Trigger: ChatGPT review of -93 (Issue #1 comment 6353306848).
Scope: ONE isolated delta to the -93 checker candidate's crypto
mode, plus a by-reference correction to -93 MANIFEST_AMENDMENT
§4.3. The -93 package (commit 96cd2bb) is untouched; this package
supersedes its crypto mode BY REFERENCE if adopted (G4 extension —
Mike's GO after adjudication). Guard v3 is not modified.

## 1. The defect (ChatGPT -94, blocking mismatches 1–2)

Checker v3-candidate-1 encoded a midnight-anchored crypto session:
bars grouped by ET calendar date (`ts.normalize()`), expected
starts `_expected_starts_crypto(day) = [day + h for h in 0..23]`
ET wall hours. The ADOPTED spec (Gate 1 freeze a126ce5; reference
implementation -87 `fixtures/crypto_calendar_spec.py`) defines the
session as the half-open span **[D 09:30 ET, D+1 09:30 ET)**. The
v3 model therefore measures [00:00, 24:00) instead of the adopted
session: a 09:30-aligned capture could falsely fail, a
midnight-aligned one falsely pass — and its clean fixtures were
midnight-anchored, so the -93 20/20 did not establish
compatibility. Its DST handling hardcoded 24 bars and disclosed
the fall repeated wall hour as a STRUCTURAL duplicate and the
spring missing wall hour as a COUNT finding; both disclosures are
superseded by this delta.

## 2. The corrected model (checker/crypto_session_model.py)

Source-faithful to S-C1…S-C6 as adopted:

- Session D spans [D 09:30 ET, D+1 09:30 ET) in absolute time.
- Expected bar-open instants: start_utc + k·1h inside the span —
  generated from the timezone-aware boundaries as UTC instants,
  never from wall-clock labels. Counts: 23 for D = 2024-03-09
  (spring transition inside the span), 25 for D = 2024-11-02
  (fall), 24 otherwise.
- Assignment (S-C3): a bar-open instant belongs to D iff its ET
  wall time is ≥ 09:30 on D or < 09:30 on D+1 — implemented as
  calendar-date arithmetic on the ET date (see §4, finding F-2).
- The duplicated fall wall hour is two distinct UTC instants —
  never DUPLICATE_TIMESTAMP. The spring nonexistent wall hour is
  not an expected bar — never a missing bar. A genuine extra or
  missing 1h instant in the capture still fails closed (COUNT /
  STRUCTURAL, fixtures V94_K5/K6/K7).
- Model parity: spans and assignment were verified against the
  -87 reference implementation for all 1,096 session dates
  2023-01-01 → 2025-12-31 (identical spans; every expected instant
  assigned to its own session).

## 3. Checker changes (checker/tsla_completeness_check.py)

Version `checker-v3-candidate-2`. Crypto mode only:

- `_expected_starts_crypto` (wall-hour list) replaced by
  `_expected_instants_crypto(date)` (UTC instant list) and
  `_crypto_session_start_utc(date)`; new `_crypto_session_date`
  attribution helper.
- COUNT, missing-session iteration, session totals, and
  first/last-bar reads are driven by per-row session keys
  (S-C3 session date for crypto; ET calendar date for equity —
  equity grouping is the v1 expression of the same key).
  Crypto comparisons are on UTC instants; findings are reported
  as offset-aware ET labels.
- The crypto session-table VALUE is nominal and no longer read
  (the {date: 1440} sentinel): expectations derive from the
  adopted session definition. Table KEYS still required — the
  -91 missing-session rule is unchanged and a zero-bar session
  is a first-class finding (V94_K8: expected starts for the
  missing spring session number 23, not 24).
- A tz-naive crypto frame still produces the named STRUCTURAL
  defect and a FAIL verdict (no crash on the new code path —
  V94_K11).
- Equity lanes, defect classes, STEP/STEP-ALL/VBASIS semantics,
  and verdict composition are byte-for-byte the -93 candidate's
  logic (proven by the regression matrix in TEST_EVIDENCE.md).

Semantic disclosures (nothing silent):
- The -93 suite's midnight-anchored crypto fixtures V3_K1/K2/K3
  encode the superseded convention; against candidate-2 they
  fail (K3 also binds the :00 stamp phase; adopted-anchored bars
  are :30-phase). This is the correction closing the false pass,
  recorded check-for-check in TEST_EVIDENCE.md — NOT a regression
  of the -93 record, whose suites still pass 16/16 + 20/20
  against its pristine modules.
- V3_K4/K5/K6 pass against candidate-2 unchanged.

## 4. HO equity seam correction

See HO_SEAM_CORRECTION.md (by reference; -93 bytes untouched).

## 5. Out of scope (unchanged HOLDs)

No adoption, no capture, no vendor calls, no -75 snapshot
re-analysis (G4 still governs it), no holdout access, no
performance runs, no production changes. Crypto pilot
implementation and the DST conventions at the route pin remain
Mike's rulings (listed in -93 ADOPTION_NOTES; this delta does not
pre-decide them — it makes the checker match the already-adopted
calendar spec).
